"""Mô phỏng ca mở quán theo từng tick."""

from collections import Counter
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import validate_items
from ..scenario import validate_reservations
from .ramp import ramp_velocity


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.hz = tuning["tick_hz"]
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", self._ticks(t["duration_s"]))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = [self._load_customer(c) for c in scenario.get("customers", [])]
        reserved = Counter()
        for c in self.customers:
            ids.reserve(c["id"])
            reserved.update(c["reserved"])
        validate_reservations(reserved, self.stock)
        self.spawn_customers = scenario.get("random_customers", True)
        self.next_customer_tick = t["first_customer_tick"]
        self.tick = 0
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def _ticks(self, seconds):
        return round(seconds * self.hz)

    def _load_customer(self, source):
        customer = dict(source)
        customer.setdefault("state", "assigned")
        if customer["state"] == "assigned":
            customer.setdefault("patience_ticks_left", self._ticks(self.t["patience_s"]))
            recipe = self.menu.get(customer.get("dish_id"), {}).get("recipe", {})
            customer["reserved"] = validate_items(source.get("reserved", recipe))
        else:
            customer["reserved"] = {}
        return customer

    def step(self, inp):
        events = []
        self.tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self._update_stoves(events)
        self._update_customers(events)
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        if self.spawn_customers and self.tick == self.next_customer_tick:
            self._seat_customer(events)
            self.next_customer_tick += self._ticks(self.t["customer_interval_s"])
        if self.time_left_ticks == 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": self.reason, "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def _update_stoves(self, events):
        for stove in self.stoves:
            if stove["state"] == "cooking":
                stove["cook_ticks_left"] = max(0, stove["cook_ticks_left"] - 1)
                if stove["cook_ticks_left"] == 0:
                    stove["state"] = "ready"
                    stove["ready_ticks"] = 0
                    events.append(("dish_ready", {"stove_id": stove["id"], "dish_id": stove["dish"]}))
            elif stove["state"] == "ready":
                stove["ready_ticks"] += 1

    def _update_customers(self, events):
        for customer in sort_by_id(self.customers):
            data = {"customer_id": customer["id"], "table_id": customer["table_id"],
                    "dish_id": customer.get("dish_id")}
            if customer["state"] == "assigned":
                customer["patience_ticks_left"] = max(0, customer["patience_ticks_left"] - 1)
                if customer["patience_ticks_left"] == 0:
                    self.customers.remove(customer)
                    self._change_reputation(self.t["left_reputation_delta"])
                    events.append(("customer_left", data))
            elif customer["state"] == "eating":
                customer["eat_ticks_left"] = max(0, customer["eat_ticks_left"] - 1)
                if customer["eat_ticks_left"] == 0:
                    self._pay(customer, data, events)

    def _change_reputation(self, delta):
        self.reputation = min(self.t["reputation_max"], max(self.t["reputation_min"],
                                                           round(self.reputation + delta, 10)))

    def _pay(self, customer, data, events):
        self.customers.remove(customer)
        price, tip = customer["price"], customer["tip"]
        amount = price + tip
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if tip:
            self._change_reputation(self.t["tip_reputation"])
        events.append(("paid", dict(data, price=price, tip=tip, amount=amount)))

    def _seat_customer(self, events):
        occupied = {c["table_id"] for c in self.customers}
        table = next((t for t in self.tables if t["id"] not in occupied), None)
        if table is None:
            return
        available = Counter(self.stock)
        for customer in self.customers:
            available.subtract(customer["reserved"])
        options = [dish_id for dish_id in sorted(self.menu)
                   if self._has_recipe(available, self.menu[dish_id]["recipe"])]
        ident = self.ids.new("C")
        if not options:
            events.append(("no_dish", {"customer_id": ident, "table_id": table["id"]}))
            return
        dish_id = self.rng.get("customer_order").choice(options)
        customer = self._load_customer({"id": ident, "table_id": table["id"], "dish_id": dish_id})
        self.customers.append(customer)
        events.append(("customer_arrived", {"customer_id": ident, "table_id": table["id"], "dish_id": dish_id}))

    @staticmethod
    def _has_recipe(stock, recipe):
        return all(stock.get(kind, 0) >= quantity for kind, quantity in recipe.items())

    def _interact(self, events):
        targets = [(math.dist(self.pos, entity["pos"]), priority, id_key(entity["id"]), entity)
                   for priority, entities in enumerate((self.stoves, self.tables)) for entity in entities]
        distance, priority, _, target = min(targets, default=(math.inf, 0, (), None))
        if distance > self.t["interact_radius"]:
            return
        if priority == 0:
            self._use_stove(target, events)
        else:
            self._serve(target, events)

    def _use_stove(self, stove, events):
        if stove["state"] == "ready" and self.hand is None:
            self.hand = stove["dish"]
            events.append(("dish_picked", {"stove_id": stove["id"], "dish_id": self.hand}))
            stove.update(state="idle", dish=None, ready_ticks=0, cook_ticks_left=0)
            return
        if stove["state"] != "idle":
            return
        customer = next((c for c in sort_by_id(self.customers)
                         if c["state"] == "assigned" and c["reserved"]), None)
        if customer is None or not self._has_recipe(self.stock, customer["reserved"]):
            return
        for kind, quantity in customer["reserved"].items():
            self.stock[kind] -= quantity
        customer["reserved"] = {}
        dish_id = customer["dish_id"]
        stove.update(state="cooking", dish=dish_id, cook_ticks_left=self._ticks(self.menu[dish_id]["cook_s"]),
                     ready_ticks=0)
        events.append(("cook_started", {"stove_id": stove["id"], "customer_id": customer["id"],
                                        "dish_id": dish_id}))

    def _serve(self, table, events):
        customer = next((c for c in self.customers if c["table_id"] == table["id"]), None)
        dish_id = self.hand.get("dish_id") if isinstance(self.hand, dict) else self.hand
        if not dish_id or customer is None or customer["state"] != "assigned" or customer["dish_id"] != dish_id:
            return
        price = self.menu[dish_id]["price"]
        threshold = self._ticks(self.t["patience_s"]) * self.t["tip_min_patience_ratio"]
        tip = round(price * self.t["tip_rate"]) if customer["patience_ticks_left"] >= threshold else 0
        customer.update(state="eating", reserved={}, price=price, tip=tip,
                        eat_ticks_left=self._ticks(self.t["eat_s"]))
        self.hand = None
        events.append(("served", {"table_id": table["id"], "customer_id": customer["id"], "dish_id": dish_id}))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t["ramp_max_ticks"]))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / self.hz
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
