"""Kiểm thử các vòng chơi mới qua giao diện headless dùng để chấm bài."""

import json
import os
import unittest

from helpers import item_list, Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json
from chonoi.contract import load_contract

TUNING = load_contract()["tuning"]


class Gameplay(unittest.TestCase):
    def headless(self, work, mode, ticks, scenario, inputs, *args):
        sc = write_json(work.path(f"{mode}.scenario.json"), {mode: scenario})
        keys = write_json(work.path(f"{mode}.inputs.json"), frames(*inputs))
        output = work.path(f"{mode}.jsonl")
        code, err = run_headless("--mode", mode, "--seed", "12", "--ticks", str(ticks),
                                 "--scenario", sc, "--inputs", keys, "--out", output, *args)
        self.assertEqual(code, 0, err)
        return read_jsonl(output)

    def test_faint_discards_hold_before_interact_or_timeout(self):
        with Workdir() as work:
            inventory = work.path("inventory.json")
            rows = self.headless(work, "gather", 2, {
                "player": {"pos": [2, 1], "hp": 1, "oxygen_ticks": 0,
                           "zero_oxy_ticks": TUNING["gather"]["choke_interval_ticks"] - 1},
                "hold": item_list("ca_loc"), "time_left_ticks": 1,
            }, [{"tick": 0, "interact": True, "catch": True}], "--inventory-out", inventory)
            self.assertEqual([e["name"] for e in events(rows)], ["choke", "faint", "gather_end"])
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inventory, encoding="utf-8") as file:
                self.assertEqual(json.load(file), {"items": []})

    def test_surface_transition_refills_and_harvest_regrows(self):
        g = TUNING["gather"]
        with Workdir() as work:
            rows = self.headless(work, "gather", round(g["regrow_s"] * TUNING["tick_hz"]) + 10, {
                "player": {"pos": [12, g["surface_depth"] + 0.001], "oxygen_ticks": 1},
                "random_fish": False, "nodes": [{"id": "N10", "kind": "bong_sung", "pos": [11, 0]},
                          {"id": "N2", "kind": "bong_dien_dien", "pos": [13, 0]}],
            }, [{"tick": 0, "move": [0, -1], "interact": True}])
            self.assertEqual([e["name"] for e in events(rows)], ["surface", "gather", "node_regrown"])
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2")
            self.assertEqual([item["kind"] for item in snapshots(rows)[-1]["hold"]], ["bong_dien_dien"] * g["node_yield"])

    def test_full_basket_leaves_fish_and_does_not_start_cooldown(self):
        g = TUNING["gather"]
        with Workdir() as work:
            rows = self.headless(work, "gather", 1, {
                "player": {"pos": [15, 5]}, "hold": item_list(*(["ca_loc"] * (g["hold_capacity"] - 1))),
                "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}],
            }, [{"tick": 0, "catch": True}])
            self.assertEqual([e["name"] for e in events(rows)], ["hold_full"])
            self.assertEqual(snapshots(rows)[-1]["fish"][0]["id"], "F1")
            self.assertEqual(snapshots(rows)[-1]["player"]["catch_cd_ticks"], 0)

    def test_catch_export_cook_serve_and_pay(self):
        q = TUNING["quan"]
        dish = TUNING["menu"]["ca_loc_nuong_trui"]
        hz = TUNING["tick_hz"]
        with Workdir() as work:
            inventory = work.path("inventory.json")
            morning = self.headless(work, "gather", 2, {
                "player": {"pos": [20, 5]}, "time_left_ticks": 2,
                "fish": [{"id": "F1", "kind": "ca_loc", "pos": [20, 5]}],
            }, [{"tick": 0, "catch": True}], "--inventory-out", inventory)
            self.assertEqual([e["name"] for e in events(morning)], ["fish_caught", "gather_end"])

            # Đặt bếp và bàn gần nhau để fixture ngắn, vẫn dùng lệnh di chuyển thật.
            order = q["first_customer_tick"]
            cook = round(dish["cook_s"] * hz)
            pick = order + cook
            serve = pick + round(3 * hz / q["walk_speed"])
            evening = self.headless(work, "quan", serve + round(q["eat_s"] * hz) + 2, {
                "player": {"pos": [2, 5]},
                "stoves": [{"id": "B1", "pos": [2, 5]}],
                "tables": [{"id": "T1", "pos": [5, 5]}],
            }, [{"tick": order, "interact": True},
                {"tick": order + 1, "interact": False},
                {"tick": pick, "interact": True},
                {"tick": pick + 1, "interact": False, "move": [1, 0]},
                {"tick": serve, "interact": True, "move": [0, 0]}], "--inventory", inventory)
            self.assertEqual([e["name"] for e in events(evening) if e["name"] != "no_dish"],
                             ["customer_arrived", "cook_started", "dish_ready", "dish_picked", "served", "paid"])
            base = events(evening, "cook_started")[0]["data"]["base_price"]
            self.assertEqual(base, dish["price"] - 1)
            self.assertEqual(evening[-1]["money"], base + int(base * q["tip_rate"]))
            self.assertEqual(snapshots(evening)[-1]["stock"], [])

    def test_customer_timeout_releases_reserved_items(self):
        with Workdir() as work:
            shifted = self.headless(work, "quan", 121, {
                "stock": item_list("ca_loc"),
                "customers": [{"id": "C9", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                               "patience_ticks_left": 1}],
            }, [])
            self.assertEqual([e["name"] for e in events(shifted)], ["customer_left", "customer_arrived"])
            self.assertEqual(snapshots(shifted)[-1]["customers"][0]["id"], "C10")
            self.assertEqual(snapshots(shifted)[-1]["stock"], item_list("ca_loc", fresh=100 - 121 / 240))

    def test_overbooked_reservation_stops_before_output(self):
        with Workdir() as work:
            output = work.path("out.jsonl")
            scenario = write_json(work.path("scenario.json"), {"quan": {
                "stock": [],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
            }})
            code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                   "--scenario", scenario, "--out", output)
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(output))
