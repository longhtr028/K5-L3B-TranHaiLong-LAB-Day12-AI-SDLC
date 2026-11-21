# ADR 0001 · Đổi kho sang cá thể ở v1.2

| Phạm vi | Tệp | Thay đổi kiểm thử |
|---|---|---|
| Schema, JSONL, CLI | `inventory.py`, `jsonl.py`, `headless.py` | Smoke bàn giao kiểm đủ id, kind, fresh và từ chối kho đếm |
| Lặn, Quán và Ngày | `gather.py`, `stock.py`, `quan.py`, `runner.py` | Ngưỡng 30, giữ lại trước khi nấu, giá làm tròn xuống và id qua Ngày |
| HUD | `web/index.html` | Hiện số hàng ươn ở giỏ và kho, loại hàng ươn khỏi kho khả dụng |

Trần Hải Long dùng Codex triển khai theo thứ tự adapter → Gather → Quán → Day → HUD. Bật v1.2 trong cùng commit sau khi smoke hai tiến trình chạy. Tag v1.1 còn dùng kho đếm. Dùng phân số cho hao tươi để so ngưỡng và tính giá trước khi định dạng JSON.
