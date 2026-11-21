# Retro

## Phase 1

- Replay trên bản đồ mặc định phát hiện lỗi tích hợp giữa điều khiển, xuất kho và nấu ăn nếu một trong hai mode đổi nhịp tick.
- Starter có 32 test xanh trước khi triển khai. Sau khi bổ sung luật, sáu test mới bao quát các hành vi chưa có trong bộ smoke.
- Trong lúc triển khai, kiểm tra `zero_oxy_ticks` ban đầu giới hạn cố định ở 59 từ starter. Đã chuyển điều kiện sang `choke_interval_ticks` của preset để fixture vẫn hợp lệ khi thay đổi chu kỳ.
- Việc cần làm ở phase sau là lấy Test Contract chi tiết và giữ replay Phase 1 làm kiểm tra hồi quy.

## Phase 2 và Phase 4

Chưa tiến hành retro cho các phase này.
