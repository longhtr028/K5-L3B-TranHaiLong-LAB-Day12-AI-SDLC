import unittest

from helpers import item_list

from chonoi.contract import load_contract
from chonoi.inputs import BUTTONS, InputPlayer
from chonoi.runner import Session

TUNING = load_contract()["tuning"]


class DayContract(unittest.TestCase):
    def test_pause_shop_purchase_and_active_level(self):
        scenario = {"day": {"money": 200, "earned": 200},
                    "gather": {"time_left_ticks": 1, "monsters": []},
                    "quan": {"time_left_ticks": 1}}
        ses = Session("day", TUNING, scenario, 42, days=2)
        frames = InputPlayer([
            {"tick": 0, "pause": True, "interact": True},
            {"tick": 1, "pause": False},
            {"tick": 2, "pause": True},
            {"tick": 4, "buy": "oxygen", "shop_done": True},
        ], BUTTONS)
        observed = []
        for k in range(5):
            observed.extend(event["name"] for event in ses.step(frames.advance(k)))
            if k == 0:
                self.assertEqual((ses.sim_tick, ses.phase_tick, ses.snapshot()["state"]), (0, 0, "paused"))
        self.assertEqual(observed, ["paused", "resumed", "gather_end", "phase_start", "quan_end", "phase_start",
                                    "bought", "shop_end", "day_start", "day_plan", "phase_start"])
        snap = ses.snapshot()
        self.assertEqual((snap["day"], snap["phase"], snap["phase_tick"], snap["money"], snap["earned"]),
                         (2, "gather", 0, 0, 200))
        self.assertEqual(snap["active_upgrades"], {"oxygen": 1})
        self.assertEqual(snap["player"]["oxygen_ticks"], 2700)

    def test_monster_contact_discards_last_items(self):
        scenario = {"player": {"pos": [60, 24]}, "random_fish": False,
                    "hold": item_list("ca_loc", "ca_linh", "bong_sung", "keo_neo")}
        session = Session("gather", TUNING, scenario, 1)
        hit = session.step(InputPlayer([]).advance(0))[0]
        self.assertEqual(hit["name"], "monster_hit")
        self.assertEqual([item["kind"] for item in hit["data"]["lost"]], ["keo_neo", "bong_sung"])
        self.assertEqual(session.snapshot()["player"]["invuln_ticks"], 90)
        self.assertEqual(session.snapshot()["monsters"][0]["state"], "recoil")
