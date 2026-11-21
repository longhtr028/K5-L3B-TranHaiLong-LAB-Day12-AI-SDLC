"""Kho thô của Quán, giữ từng cá thể theo thứ tự tươi và id."""

import math
from collections import Counter
from fractions import Fraction

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import age_items, item_rows, load_items


class Stock:
    def __init__(self, items, tuning, ids):
        self.items = {item["id"]: item for item in load_items(items)}
        freshness = tuning["freshness"]
        self.decay = Fraction(str(freshness["quan_decay_per_s"])) / tuning["tick_hz"]
        self.threshold = freshness["spoiled_below"]
        for ident in self.items:
            ids.reserve(ident)

    def snapshot(self):
        return item_rows(sort_by_id(self.items.values()))

    @staticmethod
    def empty():
        return []

    def reserve(self, recipe, reservations):
        held = {ident for reservation in reservations for ident in reservation}
        candidates = sorted((item for item in self.items.values()
                             if item["id"] not in held and item["fresh"] >= self.threshold),
                            key=lambda item: (-item["fresh"], id_key(item["id"])))
        result = []
        for kind in sorted(recipe):
            chosen = [item["id"] for item in candidates if item["kind"] == kind][:recipe[kind]]
            if len(chosen) != recipe[kind]:
                return None
            result.extend(chosen)
        return sorted(result, key=id_key)

    def validate(self, reservation, recipe, others):
        if not isinstance(reservation, list) or not all(isinstance(item, str) for item in reservation):
            raise BadInput("phần giữ phải là mảng id")
        held = {ident for existing in others for ident in existing}
        counts = Counter()
        for ident in reservation:
            if ident in held or ident not in self.items or self.items[ident]["fresh"] < self.threshold:
                raise BadInput("cá thể giữ chỗ trùng, đã ươn hoặc không có trong kho")
            held.add(ident)
            counts[self.items[ident]["kind"]] += 1
        if counts != recipe:
            raise BadInput("đơn giữ chỗ phải khớp công thức")
        return sorted(reservation, key=id_key)

    def cook(self, reserved, price):
        used = [self.items.pop(ident) for ident in reserved]
        value = math.floor(price * sum(item["fresh"] for item in used) / (100 * len(used)))
        return item_rows(sorted(used, key=lambda item: (item["kind"], id_key(item["id"])))), value

    def age(self, customers, menu, events):
        spoiled = age_items(self.items.values(), self.decay, self.threshold, "stock", events)
        if not spoiled:
            return
        affected = [c for c in customers if any(ident in spoiled for ident in c["reserved"])]
        affected.sort(key=lambda c: (c["order_tick"], id_key(c["table_id"])))
        for customer in affected:
            customer["reserved"] = []
            recipe = menu[customer["dish_id"]]["recipe"]
            items = self.reserve(recipe, (c["reserved"] for c in customers))
            if items is None:
                customer["order_status"] = "unfulfillable"
            else:
                customer["reserved"] = items
