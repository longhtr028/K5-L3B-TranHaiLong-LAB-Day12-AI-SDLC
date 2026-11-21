"""Kho cá thể và xuất file kho nguyên tử theo Test Contract v1.2."""

import json
import math
import os
import tempfile
from fractions import Fraction
from numbers import Real

from .errors import BadInput
from .ids import sort_by_id

KINDS = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")


def load_items(items):
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể")
    seen = set()
    result = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "kind", "fresh"}:
            raise BadInput("cá thể phải có id, kind và fresh")
        ident, kind, fresh = item["id"], item["kind"], item["fresh"]
        if not isinstance(ident, str) or not ident or ident in seen or kind not in KINDS:
            raise BadInput("id trùng hoặc loại nguyên liệu không hợp lệ")
        if not isinstance(fresh, Real) or isinstance(fresh, bool) or not 0 <= fresh <= 100 or not math.isfinite(fresh):
            raise BadInput("fresh phải là số hữu hạn trong [0, 100]")
        seen.add(ident)
        result.append(dict(item, fresh=fresh if isinstance(fresh, Fraction) else Fraction(str(fresh))))
    return result


def item_rows(items):
    rows = []
    for item in items:
        exact = item["fresh"]
        value = float(exact)
        if exact < 30 == value:
            value = math.nextafter(value, 0)
        rows.append(dict(item, fresh=value))
    return rows


def age_items(items, decay_per_tick, threshold, location, events):
    spoiled = []
    for item in items:
        before = item["fresh"]
        after = max(0, before - decay_per_tick)
        item["fresh"] = after
        if before >= threshold > after:
            spoiled.append(item)
    for item in sort_by_id(spoiled):
        events.append(("spoiled", {"item_id": item["id"], "kind": item["kind"], "location": location}))
    return {item["id"] for item in spoiled}


def read_inventory(path):
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError) as error:
        raise BadInput(f"không đọc được file kho {path}: {error}")
    if not isinstance(data, dict) or set(data) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return load_items(data["items"])


def write_inventory(path, items):
    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            json.dump({"items": item_rows(sort_by_id(items))}, file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
