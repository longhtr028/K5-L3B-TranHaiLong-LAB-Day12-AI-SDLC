"""Ca mở quán. Đơn giữ hàng cho đến khi bếp nhận, sau đó đi cùng payload món."""

import math
from fractions import Fraction

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity


from .stock import Stock


class QuanSim:
    mode = phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, allowed_dishes=None):
        self.t = tuning["quan"]
        self.hz = tuning["tick_hz"]
        self.menu = {k: v for k, v in tuning["menu"].items() if allowed_dishes is None or k in allowed_dishes}
        self.rng, self.ids = streams, ids
        player = scenario.get("player", {})
        self.pos = list(player.get("pos", self.t["start_pos"]))
        self.vel = list(player.get("vel", [0.0, 0.0]))
        self._tgt = None
        self._ramp_left = 0
        self.stock = Stock(inventory if inventory is not None else scenario.get("stock", []), tuning, ids)
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", self._ticks(self.t["duration_s"]))
        self.reputation = scenario.get("reputation", self.t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(self.t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(self.t["tables"], scenario.get("tables", []))
        self.customers = []
        fixtures = [dict(c, order_tick=c.get("order_tick", 0)) for c in scenario.get("customers", [])]
        fixtures.sort(key=self._order_key)
        for source in sorted(fixtures, key=lambda fixture: "reserved" not in fixture):
            self._load_customer(source)
        self._validate_dishes()
        self.spawn_customers = scenario.get("random_customers", True)
        self.next_customer_tick = self.t["first_customer_tick"]
        self.tick = 0
        self.money = self.earned = self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for update in updates:
            by_id[update["id"]].update(update)
        return sort_by_id(by_id.values())

    def snapshot(self):
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": self.stock.snapshot(),
            "hand": self.hand,
            "stoves": self.stoves,
            "tables": [dict(t, customer_id=occupied.get(t["id"])) for t in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def _ticks(self, seconds):
        return round(seconds * self.hz)

    @staticmethod
    def _order_key(customer):
        return customer["order_tick"], id_key(customer["table_id"])

    def _reservations(self):
        return [c["reserved"] for c in self.customers]

    def _load_customer(self, source):
        dish_id = source["dish_id"]
        if dish_id not in self.menu:
            raise BadInput("món của khách không thuộc thực đơn")
        customer = dict(source, state=source.get("state", "waiting"), order_status=source.get("order_status", "reserved"),
                        patience_ticks_left=source.get("patience_ticks_left", self._ticks(self.t["patience_s"])),
                        eat_ticks_left=source.get("eat_ticks_left", 0))
        recipe = self.menu[dish_id]["recipe"]
        if customer["order_status"] == "reserved":
            if "reserved" in source:
                reserved = self.stock.validate(source["reserved"], recipe, self._reservations())
            else:
                reserved = self.stock.reserve(recipe, self._reservations())
                if reserved is None:
                    raise BadInput("không đủ nguyên liệu giữ cho đơn")
        else:
            reserved = self.stock.empty()
        customer["reserved"] = reserved
        self.ids.reserve(customer["id"])
        self.customers.append(customer)

    def _validate_dishes(self):
        payloads = [s["dish"] for s in self.stoves if s["dish"] is not None]
        if self.hand is not None:
            payloads.append(self.hand)
        assigned = {c["id"]: c for c in self.customers if c["order_status"] == "assigned"}
        for dish in payloads:
            customer = assigned.pop(dish["order_id"], None)
            if customer is None or customer["dish_id"] != dish["dish_id"]:
                raise BadInput("món không khớp đơn đang nấu hoặc giao")
        if assigned:
            raise BadInput("đơn assigned phải có một món tại bếp hoặc trên tay")

    def step(self, inp):
        events = []
        self.tick += 1
        self.time_left_ticks -= 1
        for customer in self.customers:
            field = "patience_ticks_left" if customer["state"] == "waiting" else "eat_ticks_left"
            customer[field] = max(0, customer[field] - 1)
        self.stock.age(self.customers, self.menu, events)
        self._update_stoves(events)
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        self._settle(events)
        if self.time_left_ticks == 0:
            self.done, self.reason = True, "time"
            events.append(("quan_end", {"reason": self.reason, "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        elif self.spawn_customers and self.tick == self.next_customer_tick:
            self._seat_customer(events)
            self.next_customer_tick += self._ticks(self.t["customer_interval_s"])
        return events

    def _update_stoves(self, events):
        for stove in self.stoves:
            if stove["state"] == "ready":
                stove["ready_ticks"] += 1
            elif stove["state"] == "cooking":
                stove["cook_ticks_left"] -= 1
                if stove["cook_ticks_left"] == 0:
                    stove["state"] = "ready"
                    events.append(("dish_ready", self._stove_event(stove)))

    @staticmethod
    def _stove_event(stove):
        dish = stove["dish"]
        return {"stove_id": stove["id"], "order_id": dish["order_id"], "dish_id": dish["dish_id"]}

    @staticmethod
    def _clear_stove(stove):
        stove.update(state="idle", dish=None, ready_ticks=0, cook_ticks_left=0)

    def _remove(self, customer):
        self.customers.remove(customer)
        if self.hand and self.hand["order_id"] == customer["id"]:
            self.hand = None
        for stove in self.stoves:
            if stove["dish"] and stove["dish"]["order_id"] == customer["id"]:
                self._clear_stove(stove)

    def _settle(self, events):
        closing = self.time_left_ticks == 0
        for customer in sort_by_id(self.customers, key=lambda c: c["table_id"]):
            data = {"order_id": customer["id"], "table_id": customer["table_id"]}
            if customer["state"] == "eating":
                if customer["eat_ticks_left"] == 0 or closing:
                    reason = "finished_eating" if customer["eat_ticks_left"] == 0 else "closing"
                    self._pay(customer, data, reason, events)
            elif closing or customer["patience_ticks_left"] == 0:
                self._remove(customer)
                if not closing:
                    self._change_reputation(self.t["left_reputation_delta"])
                events.append(("customer_left", dict(data, reason="closing" if closing else "patience",
                                                      reputation=self.reputation)))

    def _change_reputation(self, delta):
        self.reputation = min(self.t["reputation_max"], max(self.t["reputation_min"],
                                                           round(self.reputation + delta, 10)))

    def _pay(self, customer, data, reason, events):
        self._remove(customer)
        price, tip = customer["base_price"], customer["tip"]
        amount = price + tip
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if tip:
            self._change_reputation(self.t["tip_reputation"])
        events.append(("paid", dict(data, base_price=price, tip=tip, amount=amount, reason=reason)))

    def _seat_customer(self, events):
        occupied = {c["table_id"] for c in self.customers}
        table = next((t for t in self.tables if t["id"] not in occupied), None)
        if table is None:
            return
        reservations = self._reservations()
        options = {}
        for dish_id, dish in sorted(self.menu.items()):
            reserved = self.stock.reserve(dish["recipe"], reservations)
            if reserved is not None:
                options[dish_id] = reserved
        if not options:
            events.append(("no_dish", {}))
            return
        dish_id = self.rng.get("customer_order").choice(list(options))
        ident = self.ids.new("C")
        self._load_customer({"id": ident, "table_id": table["id"], "dish_id": dish_id, "order_tick": self.tick,
                             "reserved": options[dish_id]})
        events.append(("customer_arrived", {"order_id": ident, "table_id": table["id"], "dish_id": dish_id}))

    def _interact(self, events):
        targets = [(math.dist(self.pos, entity["pos"]), priority, id_key(entity["id"]), entity)
                   for priority, entities in enumerate((self.stoves, self.tables)) for entity in entities]
        distance, priority, _, target = min(targets, default=(math.inf, 0, (), None))
        if distance <= self.t["interact_radius"]:
            if priority == 0:
                self._use_stove(target, events)
            else:
                self._serve(target, events)

    def _use_stove(self, stove, events):
        if stove["state"] == "ready" and self.hand is None:
            self.hand = stove["dish"]
            events.append(("dish_picked", self._stove_event(stove)))
            self._clear_stove(stove)
        elif stove["state"] == "idle":
            available = [c for c in self.customers if c["order_status"] == "reserved"]
            if not available:
                return
            customer = min(available, key=self._order_key)
            dish_id = customer["dish_id"]
            recipe = self.menu[dish_id]
            items, price = self.stock.cook(customer["reserved"], recipe["price"])
            customer.update(reserved=self.stock.empty(), order_status="assigned")
            payload = {"order_id": customer["id"], "dish_id": dish_id, "base_price": price}
            stove.update(state="cooking", dish=payload, cook_ticks_left=self._ticks(recipe["cook_s"]))
            events.append(("cook_started", dict(self._stove_event(stove), items=items, base_price=price)))

    def _serve(self, table, events):
        if self.hand is None:
            return
        customer = next((c for c in self.customers if c["id"] == self.hand["order_id"]
                         and c["table_id"] == table["id"]), None)
        if customer is None:
            return
        price = self.hand["base_price"]
        patience = customer["patience_ticks_left"]
        threshold = self._ticks(self.t["patience_s"]) * self.t["tip_min_patience_ratio"]
        tip = math.floor(price * Fraction(str(self.t["tip_rate"]))) if patience >= threshold else 0
        events.append(("served", dict(self.hand, table_id=table["id"], patience_ticks_left=patience, tip=tip)))
        customer.update(state="eating", order_status="served", base_price=price, tip=tip,
                        eat_ticks_left=self._ticks(self.t["eat_s"]))
        self.hand = None

    def _move(self, inp):
        target = tuple(component * self.t["walk_speed"] for component in inp.move)
        self.vel = ramp_velocity(self, target, self.t["ramp_max_ticks"])
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / self.hz
            lo, hi = self.t["bounds"][axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
