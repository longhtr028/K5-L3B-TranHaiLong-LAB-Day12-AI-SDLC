# Kết quả thực chạy

- `sh tools/verify_phase1.sh` đạt 40 test, gồm smoke hai tiến trình Gather → kho → Quán.
- `python3 -m chonoi.headless --mode day --days 2 --seed 3 --ticks 50000 --snapshot-every 3600 --out day.jsonl` kết thúc với `ticks:44400`, `days_completed:2`, `reason:"days_complete"`.
- Đây là thời điểm ghi nhận trên bản tích hợp. Mốc thời hạn lab chưa được xác minh.
