"""Nạp scenario và kiểm tra các trạng thái trước khi mở file đầu ra."""

import json
import math

from .errors import BadInput
from .inventory import KINDS, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    allowed_modes = {"gather", "quan", "day"} if mode == "day" else {mode}
    if not isinstance(data, dict) or set(data) - allowed_modes:
        raise BadInput(f"khối sai mode: {mode}")
    if mode == "day":
        day = data.get("day", {})
        if not isinstance(day, dict) or set(day) - {"money", "earned", "reputation", "upgrades", "day_plan"}:
            raise BadInput("khối day không hợp lệ")
        for key in ("money", "earned"):
            _nonneg_int(key, day.get(key, 0))
        if day.get("money", 0) and "earned" not in day or day.get("money", 0) > day.get("earned", 0):
            raise BadInput("cần 0 ≤ money ≤ earned")
        _validate_reputation(day, tuning["quan"])
        upgrades = day.get("upgrades", {})
        valid = tuning["shop"]["upgrades"]
        if not isinstance(upgrades, dict) or set(upgrades) - set(valid):
            raise BadInput("danh sách nâng cấp không hợp lệ")
        for key, level in upgrades.items():
            _nonneg_int(key, level)
            if level > len(valid[key]):
                raise BadInput("cấp nâng cấp vượt trần")
        gather = data.get("gather", {})
        effective = dict(tuning, gather=dict(tuning["gather"]))
        for key, level in upgrades.items():
            if level:
                upgrade = valid[key][level - 1]
                effective["gather"].update({name: value for name, value in upgrade.items()
                                             if name not in ("price", "level")})
        _validate_block(gather, "gather", effective)
        quan = data.get("quan", {})
        _validate_block(quan, "quan", tuning)
        if {"stock", "reputation"} & set(quan):
            raise BadInput("day không nhận quan.stock hoặc quan.reputation")
        return data
    return _validate_block(data.get(mode, {}), mode, tuning)


def _validate_block(block, mode, tuning):
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * tuning["tick_hz"]))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


def _num(v):
    return type(v) is int or (type(v) is float and math.isfinite(v))


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * tuning["tick_hz"]))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] >= g["choke_interval_ticks"]:
            raise BadInput("player.zero_oxy_ticks phải nhỏ hơn chu kỳ ngạt")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")

        if "age_ticks" in f:
            _nonneg_int("age_ticks", f["age_ticks"])
    species = g.get("monsters", {}).get("species", {})
    for monster in b.get("monsters", []):
        if set(monster) - {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}:
            raise BadInput("trường thủy quái không hợp lệ")
        kind = monster.get("kind")
        if not isinstance(kind, str) or kind not in species:
            raise BadInput("loài thủy quái không hợp lệ")
        region = dict(bounds, d=species[kind]["depths"])
        _pos("monsters.pos", monster.get("pos"), region)
        waypoints = monster.get("waypoints")
        if not isinstance(waypoints, list) or len(waypoints) != 2:
            raise BadInput("thủy quái cần hai waypoint")
        for waypoint in waypoints:
            _pos("monsters.waypoints", waypoint, region)
        target = monster.get("target_idx", 1)
        ticks = monster.get("state_ticks_left", 0)
        _nonneg_int("target_idx", target)
        _nonneg_int("state_ticks_left", ticks)
        state = monster.get("state", "patrol")
        recoil = monster.get("recoil_dir")
        if target not in (0, 1) or state not in ("patrol", "chase", "recoil") or (state == "recoil") != bool(ticks):
            raise BadInput("trạng thái thủy quái mâu thuẫn")
        if state == "recoil":
            if not isinstance(recoil, list) or len(recoil) != 2 or not all(_num(c) for c in recoil) or not math.isclose(math.hypot(*recoil), 1):
                raise BadInput("recoil_dir phải là vector đơn vị")
        elif recoil is not None:
            raise BadInput("chỉ recoil có hướng lùi")


def _validate_reputation(block, quan):
    if "reputation" in block:
        reputation = block["reputation"]
        if not _num(reputation) or not quan["reputation_min"] <= reputation <= quan["reputation_max"]:
            raise BadInput("reputation ngoài giới hạn")


def _validate_quan(b, tuning):
    quan = tuning["quan"]
    menu = tuning["menu"]
    if "random_customers" in b and type(b["random_customers"]) is not bool:
        raise BadInput("random_customers phải là boolean")
    _validate_reputation(b, quan)
    def dish_payload(dish):
        if (not isinstance(dish, dict) or set(dish) != {"order_id", "dish_id", "base_price"}
                or not isinstance(dish["order_id"], str) or not isinstance(dish["dish_id"], str)
                or dish["dish_id"] not in menu):
            raise BadInput("payload món không hợp lệ")
        _nonneg_int("base_price", dish["base_price"])

    if b.get("hand") is not None:
        dish_payload(b["hand"])
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        validate_items(b["stock"])
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = tuning["quan"]["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    for fixtures in ("stoves", "tables"):
        known_ids = {entry["id"] for entry in quan[fixtures]}
        for entry in b.get(fixtures, []):
            if entry["id"] not in known_ids:
                raise BadInput(f"{fixtures}.{entry['id']} không tồn tại")
            if "pos" in entry:
                _pos(f"{fixtures}.{entry['id']}.pos", entry["pos"], qb, axes=("x", "z"))

    for stove in b.get("stoves", []):
        state = stove.get("state", "idle")
        dish = stove.get("dish")
        if state not in ("idle", "cooking", "ready"):
            raise BadInput("trạng thái bếp không hợp lệ")
        for field in ("cook_ticks_left", "ready_ticks"):
            if field in stove:
                _nonneg_int(field, stove[field])
        cook, ready = stove.get("cook_ticks_left", 0), stove.get("ready_ticks", 0)
        if state == "idle" and (dish is not None or cook or ready):
            raise BadInput("bếp rảnh không thể có món")
        if state != "idle":
            dish_payload(dish)
            if (state == "cooking" and (not cook or ready)) or (state == "ready" and cook):
                raise BadInput("timer bếp mâu thuẫn với trạng thái")

    known_tables = {table["id"] for table in quan["tables"]}
    occupied = set()
    for customer in b.get("customers", []):
        table_id = customer.get("table_id")
        if not isinstance(table_id, str) or table_id not in known_tables:
            raise BadInput(f"customers.{customer['id']}: table_id phải là bàn có thật")
        if table_id in occupied:
            raise BadInput("hai khách cùng bàn")
        occupied.add(table_id)
        dish_id = customer.get("dish_id")
        if not isinstance(dish_id, str) or dish_id not in menu:
            raise BadInput("đơn của khách phải có món hợp lệ")
        state = customer.get("state", "waiting")
        status = customer.get("order_status", "reserved")
        for field in ("order_tick", "patience_ticks_left", "eat_ticks_left", "base_price", "tip"):
            if field in customer:
                _nonneg_int(field, customer[field])
        if state == "waiting" and status in ("reserved", "assigned", "unfulfillable"):
            if customer.get("eat_ticks_left", 0) or (status != "reserved" and customer.get("reserved")):
                raise BadInput("trạng thái và phần giữ của khách mâu thuẫn")
        elif state == "eating" and status == "served":
            if not customer.get("eat_ticks_left") or not {"base_price", "tip"} <= set(customer) or customer.get("reserved"):
                raise BadInput("khách đang ăn cần timer, giá và boa hợp lệ")
        else:
            raise BadInput("trạng thái khách không hợp lệ")
