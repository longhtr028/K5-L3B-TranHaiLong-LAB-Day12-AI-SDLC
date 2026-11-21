import unittest

from chonoi.contract import load_contract
from chonoi.inputs import BUTTONS, InputPlayer
from chonoi.runner import Session
from helpers import item_list

TUNING = load_contract()["tuning"]


class FreshnessContract(unittest.TestCase):
    def test_spoiled_edge_and_pause(self):
        session = Session("gather", TUNING, {"hold": item_list("ca_linh", fresh=30)}, 1)
        keys = InputPlayer([{"tick": 0, "pause": True}, {"tick": 1, "pause": False},
                            {"tick": 2, "pause": True}], BUTTONS)
        self.assertEqual([e["name"] for e in session.step(keys.advance(0))], ["paused"])
        self.assertEqual(session.snapshot()["hold"][0]["fresh"], 30)
        session.step(keys.advance(1))
        self.assertEqual([e["name"] for e in session.step(keys.advance(2))], ["resumed", "spoiled"])
        self.assertLess(session.snapshot()["hold"][0]["fresh"], 30)
        self.assertEqual(session.step(keys.advance(3)), [])

    def test_spoiled_reservation_reassigned_before_cooking(self):
        scenario = {"player": {"pos": [2, 8]}, "stock": item_list("ca_loc", fresh=30) +
                    [{"id": "I11", "kind": "ca_loc", "fresh": 80}], "customers": [
                      {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]}
        session = Session("quan", TUNING, scenario, 1)
        events = session.step(InputPlayer([{"tick": 0, "interact": True}]).advance(0))
        self.assertEqual([e["name"] for e in events], ["spoiled", "cook_started"])
        self.assertEqual(events[1]["data"]["items"][0]["id"], "I11")
        self.assertEqual(events[1]["data"]["base_price"], 47)
        self.assertEqual(session.snapshot()["customers"][0]["order_status"], "assigned")

    def test_day_fixture_id_increases_after_shop(self):
        scenario = {"gather": {"hold": [{"id": "I8", "kind": "ca_loc", "fresh": 95}], "time_left_ticks": 1},
                    "quan": {"time_left_ticks": 1}}
        session = Session("day", TUNING, scenario, 1, days=2)
        keys = InputPlayer([{"tick": 2, "shop_done": True}], BUTTONS)
        self.assertEqual(session.snapshot()["hold"][0]["id"], "I8")
        session.step(keys.advance(0))
        self.assertEqual(session.snapshot()["stock"][0]["id"], "I8")
        session.step(keys.advance(1))
        session.step(keys.advance(2))
        self.assertEqual(session.snapshot()["hold"][0]["id"], "I9")
