"""Mua cấp kế tiếp, giữ thu nhập và chuyển ngày khi đóng cửa."""


class ShopSim:
    phase = "shop"

    def __init__(self, tuning, stock, previous, upgrades):
        self.t = tuning["shop"]
        self.stock = stock
        self.money, self.earned, self.reputation = previous.money, previous.earned, previous.reputation
        self.upgrades = upgrades
        self.time_left_ticks = self.t["max_ticks"]
        self.done, self.reason = False, None

    def snapshot(self):
        return {"stock": self.stock.snapshot()}

    def step(self, inp):
        events = []
        self.time_left_ticks -= 1
        if inp.buy is not None:
            events.append(self._buy(inp.buy))
        if inp.pressed("shop_done") or self.time_left_ticks == 0:
            self.done = True
            self.reason = "done" if inp.pressed("shop_done") else "time"
            events.append(("shop_end", {"reason": self.reason}))
        return events

    def _buy(self, action):
        options = self.t["upgrades"].get(action)
        level = self.upgrades.get(action, 0)
        if options is None:
            reason = "unknown"
        elif level == len(options):
            reason = "max_level"
        elif options[level]["price"] > self.money:
            reason = "funds"
        else:
            price = options[level]["price"]
            self.money -= price
            self.upgrades[action] = level + 1
            return "bought", {"upgrade": action, "level": level + 1, "price": price, "money": self.money}
        return "buy_failed", {"action": action, "reason": reason}
