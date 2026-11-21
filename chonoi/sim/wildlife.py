"""Chuyển động và sinh đàn cá, tuần tra và va chạm Cá Sấu Năm Chèo."""

import math

from ..ids import sort_by_id


def direction(angle):
    radians = math.radians(angle)
    return [math.cos(radians), math.sin(radians)]


def move_toward(pos, target, distance):
    dx, dy = (end - start for start, end in zip(pos, target))
    length = math.hypot(dx, dy)
    if length <= distance:
        return list(target)
    return [pos[0] + distance * dx / length, pos[1] + distance * dy / length]


def reflect(value, component, low, high):
    while value < low or value > high:
        wall = low if value < low else high
        value = 2 * wall - value
        component = -component
    if (value == low and component < 0) or (value == high and component > 0):
        component = -component
    return value, component


class Wildlife:
    def __init__(self, tuning, scenario, streams, ids, day, hz):
        self.t, self.hz, self.rng, self.ids = tuning, hz, streams, ids
        self.random_fish = scenario.get("random_fish", True)
        self.fish = [dict(f, heading_deg=f.get("heading_deg", 0), age_ticks=f.get("age_ticks", 0))
                     for f in scenario.get("fish", [])]
        config = tuning["monsters"]
        self.species = config["species"]
        self.hit_settings = config
        initial = scenario.get("monsters", [m for m in config["spawns"] if m["from_day"] <= day])
        self.monsters = [{key: value for key, value in m.items() if key != "from_day"} for m in initial]
        for m in self.monsters:
            m.update(target_idx=m.get("target_idx", 1), state=m.get("state", "patrol"),
                     state_ticks_left=m.get("state_ticks_left", 0), recoil_dir=m.get("recoil_dir"))
        for entity in self.fish + self.monsters:
            self.ids.reserve(entity["id"])
        if self.random_fish and "fish" not in scenario:
            for _ in range(tuning["fish_initial"]):
                self.spawn(require_distinct=True)

    def spawn(self, require_distinct=False):
        clearance = 0 if require_distinct else self.t["fish_spawn_clearance"]
        options = {}
        for kind in sorted(self.t["fish_weights"]):
            points = [[x, depth] for x in self.t["fish_spawn_x"] for depth in self.t["fish_spawn_depths"][kind]]
            valid = [pos for pos in points if all(math.dist(pos, f["pos"]) > clearance for f in self.fish)]
            if valid:
                options[kind] = valid
        if not options:
            return None
        rng = self.rng.get("fish_spawn")
        kind = rng.choices(list(options), weights=[self.t["fish_weights"][k] for k in options])[0]
        fish = {"id": self.ids.new("F"), "kind": kind, "pos": rng.choice(options[kind]),
                "heading_deg": rng.random() * 360, "age_ticks": 0}
        self.fish.append(fish)
        return fish

    def move_fish(self, tick, events):
        if not self.random_fish:
            return
        rng = self.rng.get("fish_turn")
        speed = self.t["fish_speed"] / self.hz
        for fish in sort_by_id(self.fish):
            fish["age_ticks"] += 1
            if fish["age_ticks"] % self.t["fish_turn_ticks"] == 0:
                fish["heading_deg"] = rng.random() * 360
            dx, dd = direction(fish["heading_deg"])
            x, d = fish["pos"]
            nx, vx = reflect(x + speed * dx, dx, *self.t["fish_x"])
            nd, vd = reflect(d + speed * dd, dd, *self.t["fish_depths"][fish["kind"]])
            fish.update(pos=[nx, nd], heading_deg=math.degrees(math.atan2(vd, vx)) % 360)
        if tick % self.t["fish_spawn_ticks"] == 0 and len(self.fish) < self.t["fish_max"]:
            fish = self.spawn()
            if fish:
                events.append(("fish_spawned", {k: fish[k] for k in ("id", "kind", "pos")}))

    def update_monsters(self, player, events):
        near = []
        for monster in sort_by_id(self.monsters):
            if not self._move_monster(monster, player.pos):
                continue
            species = self.species[monster["kind"]]
            distance = math.dist(monster["pos"], player.pos)
            if distance <= species["hit_radius"] and player.pos[1] >= species["depths"][0]:
                near.append((distance, monster))
        if near and player.invuln_ticks == 0:
            self._hit(min(near, key=lambda entry: entry[0])[1], player, events)

    def _move_monster(self, monster, player_pos):
        species = self.species[monster["kind"]]
        pos = monster["pos"]
        if monster["state"] == "recoil":
            monster["state_ticks_left"] -= 1
            speed = species["recoil_dist"] / species["recoil_ticks"]
            next_pos = [c + speed * d for c, d in zip(pos, monster["recoil_dir"])]
            monster["pos"] = self._clamp(next_pos, species)
            if monster["state_ticks_left"] == 0:
                monster.update(state="patrol", recoil_dir=None)
            return False
        distance = math.dist(pos, player_pos)
        depth_ok = player_pos[1] >= species["depths"][0]
        if monster["state"] == "chase":
            if not depth_ok or distance > species["exit_radius"]:
                monster["state"] = "patrol"
        elif depth_ok and distance <= species["detect_radius"]:
            monster["state"] = "chase"
        chasing = monster["state"] == "chase"
        target = player_pos if chasing else monster["waypoints"][monster["target_idx"]]
        speed = species["chase_speed"] if chasing else species["patrol_speed"]
        next_pos = move_toward(pos, target, speed / self.hz)
        monster["pos"] = self._clamp(next_pos, species)
        if not chasing and next_pos == target:
            monster["target_idx"] = 1 - monster["target_idx"]
        return True

    def _clamp(self, pos, species):
        bounds = (self.t["bounds"]["x"], species["depths"])
        return [min(high, max(low, value)) for value, (low, high) in zip(pos, bounds)]

    def _hit(self, monster, player, events):
        player.hp -= 1
        player.invuln_ticks = self.hit_settings["invuln_ticks"]
        lost = [player.hold.pop() for _ in range(math.floor(len(player.hold) * self.hit_settings["loss_ratio"]))]
        delta = [a - b for a, b in zip(monster["pos"], player.pos)]
        distance = math.hypot(*delta)
        recoil = [c / distance for c in delta] if distance else [1, 0]
        monster.update(state="recoil", recoil_dir=recoil, state_ticks_left=self.species[monster["kind"]]["recoil_ticks"])
        events.append(("monster_hit", {"monster_id": monster["id"], "hp": player.hp,
                                       "lost": lost, "pos": list(player.pos)}))
        if player.hp == 0:
            player._faint("monster", events)
