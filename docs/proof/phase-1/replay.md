# Kết quả thực chạy Phase 1

```text
$ sh tools/verify_phase1.sh
Ran 38 tests
OK

$ sh tools/demo_phase1.sh
gather    429 dive
gather    569 fish_caught       F2, ca_loc ×1
gather    714 surface
gather   1137 gather_end        docked
inventory     {"items":{"ca_loc":1}}
quan      120 customer_arrived  C1, ca_loc_nuong_trui
quan      121 cook_started      B1
quan      481 dish_ready
quan      481 dish_picked
quan      620 served            T1
quan     1220 paid              60 + 12 = 72
quan    10800 quan_end          time, 72k, uy tín 3.2, điểm 372
```

Hai lần replay với seed 12 cho kết quả giống từng byte khi chạy `cmp`. Mã SHA-256 của kết quả lưu lại:

| Tệp | SHA-256 |
|---|---|
| `gather.jsonl` | `5df001c38317fe5ce5387707776b86bf935f24a0adf6b084457db34134cb8df9` |
| `quan.jsonl` | `029d97bedf7f232450496a78b0a55a8af1e93813baed7b470884ef4d92c89a23` |
| `inventory.json` | `212912a22e0f0396ebe65b3bed5b3d27739ae3c2321cc8b15bc2dcd0d481c173` |
