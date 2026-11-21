# Quán Ăn Chợ Nổi v1.0.0

Bài làm solo của Trần Hải Long (2A202603891). Bản phát hành gồm vòng chơi năm Ngày, cá bơi theo seed, Cá Sấu, thực đơn ngày, cửa hàng, kho cá thể và cơ chế độ tươi. Ba cảnh báo có chữ và nút tương phản cao.

## Cách chạy

Tải và giải nén `chonoi-v1.0.0.zip`, mở terminal ở thư mục giải nén và chạy `python3 -m chonoi.live --mode day`. Mở địa chỉ in ra. Cần Python 3.9+ trên macOS/Linux. Thêm `--days 1` cho một vòng thử. WASD hoặc mũi tên di chuyển, Space bắt cá, E tương tác, Esc/P tạm dừng.

## Kiểm chứng và giới hạn

- `sh tools/verify_phase1.sh` chạy kiểm thử. README có lệnh headless, benchmark và soak.
- Contract v1.3 đọc kho cá thể; kho đếm thuộc tag `phase-2`.
- Benchmark cần Chrome/Chromium. Game dùng điều khiển bàn phím trên trình duyệt máy tính.
- Bài làm theo yêu cầu một người. Công cụ kiểm nhóm của starter áp ngưỡng 4–6 người. Thời hạn nộp và điểm test ẩn do lớp xác nhận.
