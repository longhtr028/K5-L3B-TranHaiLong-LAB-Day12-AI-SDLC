"""Mô phỏng lặn bắt cá và hái rau theo từng tick."""

import math
from fractions import Fraction

from ..ids import id_key, sort_by_id
from ..inventory import age_items, item_rows, load_items
from .ramp import ramp_velocity
from .wildlife import Wildlife

AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1):
        t = tuning["gather"]
        self.t = t
        self.hz = tuning["tick_hz"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * self.hz))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = load_items(scenario.get("hold", []))
        for item in self.hold:
            ids.reserve(item["id"])
        self.freshness = tuning["freshness"]
        self.decay = Fraction(str(self.freshness["gather_decay_per_s"])) / self.hz
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * self.hz)))
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        for node in self.nodes:
            ids.reserve(node["id"])
        self.wildlife = Wildlife(t, scenario, streams, ids, day, self.hz)
        self.fish = self.wildlife.fish
        self.tick = 0
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self):
        return sort_by_id(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": item_rows(self.hold), "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": sort_by_id(self.fish),
            "monsters": sort_by_id(self.wildlife.monsters),
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.tick += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        age_items(self.hold, self.decay, self.freshness["spoiled_below"], "hold", events)
        at_surface_before_move = self._at_surface()
        self._move(inp)
        at_surface = self._at_surface()
        if at_surface != at_surface_before_move:
            events.append(("surface" if at_surface else "dive", {"pos": list(self.pos)}))
        self._update_oxygen(events)
        if self.done:
            return events

        self.wildlife.update_monsters(self, events)
        if self.done:
            return events

        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if at_surface:
                self._harvest(events)
        if inp.pressed("catch") and not at_surface and self.catch_cd_ticks == 0:
            self._catch(events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
        else:
            self.wildlife.move_fish(self.tick, events)
        return events

    # --- tiện ích ---------------------------------------------------------------
    def _update_oxygen(self, events):
        if self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
            return
        if self.oxygen_ticks > 0:
            self.oxygen_ticks -= 1
            if self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks > 0:
            return
        self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks < self.t["choke_interval_ticks"]:
            return
        self.zero_oxy_ticks = 0
        self.hp -= 1
        events.append(("choke", {"hp": self.hp}))
        if self.hp == 0:
            self._faint("choke", events)

    def _faint(self, cause, events):
        lost = item_rows(reversed(self.hold))
        self.hold.clear()
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    def _closest(self, entities, radius):
        distances = [(math.dist(self.pos, e["pos"]), id_key(e["id"]), e) for e in entities]
        distance, _, target = min(distances, default=(math.inf, (), None))
        return target if distance <= radius else None

    def _collect(self, kind, quantity, action, target, events):
        if len(self.hold) + quantity > self.t["hold_capacity"]:
            events.append(("hold_full", dict(target, action=action, required=quantity,
                                             free=self.t["hold_capacity"] - len(self.hold))))
            return False
        self.hold.extend({"id": self.ids.new("I"), "kind": kind, "fresh": Fraction(self.freshness["initial"])}
                         for _ in range(quantity))
        return True

    def _harvest(self, events):
        ready = (n for n in self.nodes if n["regrow_ticks"] == 0)
        node = self._closest(ready, self.t["interact_radius"])
        if node is None:
            return
        kind, quantity = node["kind"], self.t["node_yield"]
        target = {"node_id": node["id"]}
        if self._collect(kind, quantity, "gather", target, events):
            node["regrow_ticks"] = round(self.t["regrow_s"] * self.hz)
            events.append(("gather", dict(target, kind=kind, amount=quantity)))

    def _catch(self, events):
        fish = self._closest(self.fish, self.t["catch_radius"])
        if fish is None:
            return
        kind = fish["kind"]
        quantity = self.t["fish_yield"][kind]
        target = {"fish_id": fish["id"]}
        if self._collect(kind, quantity, "catch", target, events):
            self.fish.remove(fish)
            self.catch_cd_ticks = round(self.t["catch_cooldown_s"] * self.hz)
            events.append(("fish_caught", dict(target, kind=kind, **{"yield": quantity})))

    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": item_rows(self.inventory_items())}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / self.hz
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
