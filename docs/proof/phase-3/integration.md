# Kết quả thực chạy

`sh tools/verify_phase1.sh` chạy 43 test, tất cả đạt. Test smoke lưu file kho sau khi giảm 1/120 độ tươi và so trực tiếp `quan.stock` ở tick 0 với nội dung file. Test giữ chỗ dựng I1 ở fresh 30 và I11 ở fresh 80. Tick 1 phát `spoiled(I1)`, sau đó nấu I11 với giá 47.
