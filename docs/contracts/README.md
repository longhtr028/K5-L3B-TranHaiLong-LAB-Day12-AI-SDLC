# Hợp đồng tích hợp Phase 1

- Gather viết kho theo [mẫu JSON](inventory.sample.json) khi kết thúc buổi. `items` chứa số lượng theo mã nguyên liệu. Ngất làm rỗng giỏ. Dừng do giới hạn tick giữ nguyên tệp đích.
- Quán đọc kho bằng `--inventory` hoặc `quan.stock` trong scenario. Đơn khách giữ nguyên liệu trước và trừ kho khi vào bếp.
- Client gửi di chuyển và hai nút `interact`, `catch`. Một lần bấm tạo cạnh lên. Client đọc snapshot từ `GET /state`, chung mô phỏng với headless.
- Gather phát các sự kiện `dive`, `surface`, `oxygen_empty`, `choke`, `faint`, `gather`, `node_regrown`, `fish_caught`, `hold_full` và `gather_end`. Các sự kiện tương tác chứa id của thực thể tương ứng.
- Quán phát `customer_arrived`, `no_dish`, `customer_left`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid` và `quan_end`. Xem [replay](../proof/phase-1/replay.md) để đối chiếu thứ tự một ca mẫu.

## Thay đổi ở v1.2

`items` là mảng cá thể có id duy nhất, loại và độ tươi. Dạng đếm áp dụng tới `phase-2`. `reserved` của đơn là mảng id, `cook_started.items` và `lost` chứa cá thể. Xem [ADR 0001](../adr/0001-kho-ca-the.md).
