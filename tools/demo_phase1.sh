#!/bin/sh
# Chạy lại bảng điều khiển có sẵn trên bản đồ mặc định, rồi in bằng chứng.
set -eu
if [ "$#" -gt 1 ]; then
    printf '%s\n' 'Cách dùng: sh tools/demo_phase1.sh [thư mục kết quả]' >&2
    exit 2
fi
if [ "$#" -eq 1 ]; then
    mkdir -p -- "$1"
    demo_dir=$(cd "$1" && pwd)
else
    demo_dir=$(mktemp -d)
fi
cd "$(dirname "$0")/.."
python3 -m chonoi.headless --mode gather --seed 12 --ticks 1200 \
    --inputs tools/demo/gather.inputs.json --snapshot-every 600 \
    --out "$demo_dir/gather.jsonl" --inventory-out "$demo_dir/inventory.json"
python3 -m chonoi.headless --mode quan --seed 12 --ticks 12000 \
    --inputs tools/demo/quan.inputs.json --snapshot-every 600 \
    --inventory "$demo_dir/inventory.json" --out "$demo_dir/quan.jsonl"

python3 - "$demo_dir" <<'PY'
import json
import sys
from pathlib import Path

directory = Path(sys.argv[1])
with (directory / "inventory.json").open() as file:
    print("Kho sau buổi sáng", json.load(file))
for mode, required in (("gather", ["dive", "fish_caught", "surface", "gather_end"]),
                       ("quan", ["customer_arrived", "cook_started", "dish_ready",
                                 "dish_picked", "served", "paid", "quan_end"])):
    print(f"\n{mode}")
    with (directory / f"{mode}.jsonl").open() as file:
        rows = [json.loads(line) for line in file]
    actual = [row for row in rows if row["type"] == "event" and row["name"] in required]
    if [row["name"] for row in actual] != required:
        raise SystemExit(f"Sự kiện demo không đúng ở {mode}. Xem {directory}")
    for row in actual:
        print(row["tick"], row["name"], row["data"])
    print(rows[-1])
PY
printf '\nCác file kết quả được lưu tại %s\n' "$demo_dir"
