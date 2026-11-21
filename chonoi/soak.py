"""Chạy nhiều Ngày liên tục trong cùng một Session, ghi kết quả ở mỗi Shop."""

import argparse
import json
import math
from pathlib import Path
import time

from .contract import load_contract
from .ids import sort_by_id
from .inputs import BUTTONS, InputState
from .runner import Session


def move_to(origin, target):
    delta = tuple(b - a for a, b in zip(origin, target))
    distance = math.hypot(*delta)
    scale = max(distance, 0.15)
    return tuple(value / scale for value in delta)


class Pilot:
    """Điều khiển tất định; bán món đơn giản rồi quay về bến khi đủ nguyên liệu."""

    def __init__(self):
        self.held = set()

    def next(self, session):
        sim = session.sim
        move, actions, purchase = (0, 0), set(), None
        if sim.phase == "gather":
            move, actions = self.gather(session)
        elif sim.phase == "quan":
            move, actions = self.quan(sim)
        else:
            actions = {"shop_done"}
            for name, levels in sim.t["upgrades"].items():
                level = sim.upgrades.get(name, 0)
                if level < len(levels) and sim.money >= levels[level]["price"]:
                    purchase = name
                    break
        # Tạo một bước nhả nếu hành động giống nút của bước trước.
        pressed = actions - self.held
        self.held = pressed
        return InputState(move, {button: button in pressed for button in BUTTONS}, pressed, purchase)

    def gather(self, session):
        sim = session.sim
        count = sum(item["kind"] == "ca_loc" and item["fresh"] >= 30 for item in sim.hold)
        salad = "ca_loc_nuong_trui" not in session.plan["dishes"]
        flowers = sum(item["kind"] == "bong_sung" and item["fresh"] >= 30 for item in sim.hold)
        enough = flowers >= 2 if salad else count >= 1
        if enough or sim.time_left_ticks < 1800 or sim.oxygen_ticks < 600:
            dock = sim.t["dock_pos"]
            return move_to(sim.pos, dock), {"interact"} if math.dist(sim.pos, dock) < sim.t["dock_radius"] - 0.2 else set()
        if salad:
            nodes = [n for n in sim.nodes if n["kind"] == "bong_sung" and not n["regrow_ticks"]]
            if nodes:
                node = min(nodes, key=lambda n: math.dist(sim.pos, n["pos"]))
                return (move_to(sim.pos, node["pos"]),
                        {"interact"} if math.dist(sim.pos, node["pos"]) < sim.t["interact_radius"] - 0.2 else set())
        fish = [f for f in sort_by_id(sim.fish)
                if f["kind"] == "ca_loc" and f["pos"][1] < 16 and f["pos"][0] < 64]
        if fish:
            target = min(fish, key=lambda f: math.dist(sim.pos, f["pos"]))["pos"]
            return move_to(sim.pos, target), {"catch"} if math.dist(sim.pos, target) < 1.8 else set()
        return move_to(sim.pos, [30, 0]), set()

    @staticmethod
    def quan(sim):
        if sim.hand:
            customer = next(c for c in sim.customers if c["id"] == sim.hand["order_id"])
            target = next(table for table in sim.tables if table["id"] == customer["table_id"])
        else:
            ready = [stove for stove in sim.stoves if stove["state"] == "ready"]
            pending = any(c["order_status"] == "reserved" for c in sim.customers)
            idle = [stove for stove in sim.stoves if stove["state"] == "idle"]
            candidates = ready or (idle if pending else [])
            if not candidates:
                return (0, 0), set()
            target = min(candidates, key=lambda stove: math.dist(sim.pos, stove["pos"]))
        distance = math.dist(sim.pos, target["pos"])
        if distance > 0.7:
            return move_to(sim.pos, target["pos"]), set()
        return (0, 0), {"interact"}


def run(tuning, seed, days):
    started = time.perf_counter()
    session = Session("day", tuning, {}, seed, days=days)
    pilot = Pilot()
    results = []
    crashes = 0
    max_ticks = tuning["tick_hz"] * (tuning["gather"]["duration_s"] + tuning["quan"]["duration_s"])
    max_ticks += tuning["shop"]["max_ticks"]
    try:
        while not session.done and session.tick < max_ticks * days:
            previous = session.sim
            closed = session.days_completed
            session.step(pilot.next(session))
            if session.days_completed != closed:
                results.append({"day": session.days_completed, "earned": previous.earned,
                                "reputation": previous.reputation,
                                "score": previous.earned + tuning["score"]["reputation_multiplier"]
                                * math.floor(previous.reputation)})
    except Exception:
        import traceback
        traceback.print_exc()
        crashes += 1
    return {"days": days, "days_completed": session.days_completed, "crashes": crashes, "results": results,
            "duration_s": time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--days", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.days < 1:
        parser.error("days phải dương")
    result = run(load_contract()["tuning"], args.seed, args.days)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return int(result["crashes"] != 0 or result["days_completed"] != args.days)


if __name__ == "__main__":
    raise SystemExit(main())
