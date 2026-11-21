# Kiểm chứng Phase 1

| Hạng mục theo starter | Cách kiểm | Bằng chứng | Kết quả |
|---|---|---|---|
| Oxy, ngạt, ngất và làm rỗng giỏ | Fixture cận ngưỡng oxy, di chuyển lên mặt nước, ngất khi vừa bấm E | [Test gameplay](../../tests/test_gameplay.py) | Đạt trong bộ test địa phương |
| Hái rau, mọc lại, chọn mục tiêu, giỏ đầy và bắt cá | Fixture hòa khoảng cách, hái lại theo bộ đếm, bắt khi thiếu sức chứa | [Test gameplay](../../tests/test_gameplay.py) | Đạt trong bộ test địa phương |
| Kho sáng chuyển sang tối, nấu, bưng, phục vụ, trả tiền và boa | Replay seed 12 trên bản đồ mặc định | [Kết quả replay](../proof/phase-1/replay.md) | Đạt, thu 72k |
| Khách rời bàn, mở lại chỗ giữ nguyên liệu và từ chối kho thiếu | Fixture khách sắp hết kiên nhẫn và tổng giữ chỗ vượt kho | [Test gameplay](../../tests/test_gameplay.py) | Đạt trong bộ test địa phương |
| CLI, thứ tự tick và kết quả tất định | 38 test và so ba tệp đầu ra của hai lần replay | [Kết quả replay](../proof/phase-1/replay.md) | 38/38 đạt, đầu ra giống từng byte |

PRD chi tiết nằm trên lab board yêu cầu đăng nhập Claude. Kết quả ở đây đối chiếu với starter công khai và các kiểm thử trong repo. Chưa có kết quả test ẩn hoặc xác nhận hạn tag.
