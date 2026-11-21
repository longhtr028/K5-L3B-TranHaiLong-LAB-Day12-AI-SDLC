# Quán Ăn Chợ Nổi · Day 12 AI SDLC

**Trần Hải Long · 2A202603891 · @longhtr028**

Nhóm một người · Test Contract v1.3

Út Sen lặn bắt cá và hái rau theo thực đơn của Má Tư, rồi phục vụ khách ở nhà bè. Giữ nguyên liệu tươi, dành tiền mua bình oxy hoặc áo phao và hoàn thành năm Ngày.

## Chơi từ clone sạch

Yêu cầu macOS hoặc Linux, Python 3.9+ và trình duyệt cho bản chơi. Không cần cài package Python. Benchmark cần Chrome hoặc Chromium.

```sh
git clone https://github.com/longhtr028/K5-L3B-TranHaiLong-LAB-Day12-AI-SDLC.git
cd K5-L3B-TranHaiLong-LAB-Day12-AI-SDLC
python3 -m chonoi.live --mode day
```

Mở địa chỉ in ở terminal. Nếu dùng bản ZIP của Release, giải nén rồi chạy lệnh thứ ba trong thư mục game. Thêm `--days 1` để chơi thử một Ngày.

| Điều khiển | Tác dụng |
|---|---|
| WASD hoặc mũi tên | Bơi hoặc đi lại |
| Space | Bắt cá dưới nước |
| E | Hái hoặc cập bến, nấu, bưng và phục vụ |
| Esc hoặc P | Tạm dừng hoặc tiếp tục |
| R | Về menu (chế độ Ngày) hoặc chơi lại buổi hiện tại |
| Tương phản cao | Bật/tắt trên góc trên bên phải |
| Ctrl+C trong terminal | Dừng máy chủ |

Món giữ đúng đơn và sử dụng phần nguyên liệu còn tươi. Điểm bằng tổng thu, gồm boa, cộng 100 lần phần nguyên của uy tín. Mua nâng cấp dùng số dư; hiệu lực từ ngày kế tiếp.

## Test, headless và đo hiệu năng

```sh
sh tools/verify_phase1.sh
python3 -m chonoi.headless --mode day --days 1 --seed 42 --ticks 22200 --out day.jsonl
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

`CHONOI_BROWSER` có thể chỉ đường dẫn tới Chrome hoặc Chromium. Benchmark vẽ cảnh thật 1280 × 720, làm nóng 3 giây. Chạy benchmark bằng tài khoản thường có sandbox của trình duyệt. Dùng `--mode gather --inventory-out kho.json` và `--mode quan --inventory kho.json` để chạy hai buổi riêng. File kho cá thể có ví dụ trong [hợp đồng kho](docs/contracts/inventory.sample.json).

## Bàn giao

| Pha | Bằng chứng |
|---|---|
| 1 | [Smoke hai tiến trình và replay gốc](docs/verification/phase-1.md) |
| 2 | [Cá, Cá Sấu, vòng Ngày và Shop](docs/verification/phase-2.md) |
| 3 | [Kho cá thể, độ tươi và ADR](docs/verification/phase-3.md) |
| 4 | [Benchmark, soak, cảnh báo và đóng gói](docs/verification/phase-4.md) |

Đọc thêm [nhật ký AI](docs/ai-usage-log.md), [retro](docs/retro.md) và [ghi chú thay đổi](CHANGELOG.md). Đề bài nằm trên [Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg).
