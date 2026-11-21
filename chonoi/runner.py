"""Phiên mô phỏng dùng chung cho CLI, cửa sổ chơi và soak."""

import math
import os
import tempfile
from collections import Counter

from .errors import BadInput
from .ids import IdAllocator
from .inputs import BUTTONS, InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.gather import GatherSim
from .sim.quan import QuanSim
from .sim.shop import ShopSim


def day_plans(tuning, overrides):
    if not isinstance(overrides, list):
        raise BadInput("day.day_plan phải là mảng")
    plans = {p["day"]: p for p in tuning["day_plan"]}
    seen = set()
    for plan in overrides:
        if not isinstance(plan, dict) or set(plan) - {"day", "dishes", "ingredients"}:
            raise BadInput("kế hoạch ngày không hợp lệ")
        day, dishes = plan.get("day"), plan.get("dishes")
        if type(day) is not int or day not in plans or day in seen or not isinstance(dishes, dict) or not dishes:
            raise BadInput("ngày hoặc thực đơn trong kế hoạch không hợp lệ")
        ingredients = Counter()
        for dish, servings in dishes.items():
            if dish not in tuning["menu"] or type(servings) is not int or servings <= 0:
                raise BadInput("món và số suất không hợp lệ")
            for key, units in tuning["menu"][dish]["recipe"].items():
                ingredients[key] += units * servings
        if plan.get("ingredients", ingredients) != ingredients:
            raise BadInput("nguyên liệu trong kế hoạch mâu thuẫn với thực đơn")
        plans[day] = {"day": day, "dishes": dishes, "ingredients": dict(ingredients)}
        seen.add(day)
    return plans


class Session:
    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode, self.tuning, self.scenario = mode, tuning, scenario
        self.streams, self.ids = Streams(seed), IdAllocator()
        self.tick = self.sim_tick = self.phase_tick = 0
        self.paused = self.done = False
        self.reason = None
        self.days, self.day, self.days_completed = days, 1, 0
        self.initial_events = []
        if mode == "day":
            state = scenario.get("day", {})
            self.plans = day_plans(tuning, state.get("day_plan", []))
            self.upgrades = dict(state.get("upgrades", {}))
            self._start_day(state.get("money", 0), state.get("earned", 0),
                            state.get("reputation", tuning["quan"]["reputation_initial"]))
            self.initial_events = self._start_events()
        elif mode == "gather":
            self.sim = GatherSim(tuning, scenario, self.streams, self.ids)
        else:
            self.sim = QuanSim(tuning, scenario, self.streams, self.ids, inventory)

    def _start_day(self, money, earned, reputation):
        self.active_upgrades = dict(self.upgrades)
        self.plan = self.plans[(self.day - 1) % len(self.plans) + 1]
        gather = dict(self.tuning["gather"])
        for key, level in self.active_upgrades.items():
            if level:
                stats = self.tuning["shop"]["upgrades"][key][level - 1]
                gather.update({name: value for name, value in stats.items() if name not in ("level", "price")})
        tuning = dict(self.tuning, gather=gather)
        scenario = self.scenario.get("gather", {})
        if self.day > 1 and "hold" in scenario:
            scenario = dict(scenario, hold=[dict(item, id=self.ids.new("I")) for item in scenario["hold"]])
        self.sim = GatherSim(tuning, scenario, self.streams, self.ids, self.day)
        self.sim.money, self.sim.earned, self.sim.reputation = money, earned, reputation

    def _start_events(self):
        return [self._event("day_start", {}), self._event("day_plan", {
            key: self.plan[key] for key in ("dishes", "ingredients")}), self._event("phase_start", {})]

    def _event(self, name, data):
        event = {"type": "event", "tick": self.tick, "phase": self.sim.phase, "name": name, "data": data}
        if self.mode == "day":
            event["day"] = self.day
        return event

    def _totals(self):
        sim = self.sim
        score = sim.earned + self.tuning["score"]["reputation_multiplier"] * math.floor(sim.reputation)
        return {"money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": score}

    def _state(self):
        return "finished" if self.done else "paused" if self.paused else "playing"

    def snapshot(self):
        snapshot = {"type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
                    "phase": self.sim.phase, "phase_tick": self.phase_tick, "state": self._state(),
                    "time_left_ticks": self.sim.time_left_ticks, **self._totals(), **self.sim.snapshot()}
        if self.mode == "day":
            snapshot.update(day=self.day, day_plan=self.plan, upgrades=self.upgrades,
                            active_upgrades=self.active_upgrades)
        return snapshot

    def step(self, inp):
        if self.done:
            return []
        self.tick += 1
        events = []
        if inp.pressed("pause"):
            self.paused = not self.paused
            events.append(self._event("paused" if self.paused else "resumed", {}))
        if self.paused:
            return events
        self.sim_tick += 1
        self.phase_tick += 1
        events.extend(self._event(name, data) for name, data in self.sim.step(inp))
        if self.sim.done:
            events.extend(self._advance())
        return events

    def _advance(self):
        previous = self.sim
        if self.mode != "day":
            self.done, self.reason = True, previous.reason
            return []
        if previous.phase == "gather":
            scenario = dict(self.scenario.get("quan", {}), reputation=previous.reputation)
            self.sim = QuanSim(self.tuning, scenario, self.streams, self.ids, previous.inventory_items(),
                               allowed_dishes=self.plan["dishes"])
            self.sim.money, self.sim.earned = previous.money, previous.earned
        elif previous.phase == "quan":
            self.sim = ShopSim(self.tuning, previous.stock, previous, self.upgrades)
        else:
            self.days_completed += 1
            if self.days_completed == self.days:
                self.done, self.reason = True, "days_complete"
                return []
            self.day += 1
            self.phase_tick = 0
            self._start_day(previous.money, previous.earned, previous.reputation)
            return self._start_events()
        self.phase_tick = 0
        return [self._event("phase_start", {})]

    def end_row(self):
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": self.mode,
               "state": self._state(), "reason": self.reason if self.done else "tick_limit", **self._totals()}
        if self.mode == "day":
            row["days_completed"] = self.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        if self.mode == "gather" and self.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None,
        inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days)
    player = InputPlayer(frames, BUTTONS)
    directory = os.path.dirname(os.path.abspath(out_path))
    fd, temporary = tempfile.mkstemp(prefix=".chonoi-", dir=directory)
    os.close(fd)
    writer = JsonlWriter(temporary)
    try:
        for event in sess.initial_events:
            writer.write(event)
        writer.write(sess.snapshot())
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            phase = sess.sim.phase
            for row in sess.step(player.advance(sess.tick)):
                writer.write(row)
            if sess.tick % snapshot_every == 0 or sess.done or phase != sess.sim.phase:
                writer.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            writer.write(sess.snapshot())
        writer.write(sess.end_row())
        writer.close()
        os.replace(temporary, out_path)
    finally:
        writer.close()
        if os.path.exists(temporary):
            os.unlink(temporary)
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
