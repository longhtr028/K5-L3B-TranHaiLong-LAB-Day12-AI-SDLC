# Kiểm chứng Phase 3 · Test Contract v1.2

| AC | Kiểm tra | Kết quả |
|---|---|---|
| AC-P3-01 | File v1.2, từ chối schema v1.1, bàn giao đúng id/kind/fresh | Đạt, smoke qua hai tiến trình |
| AC-P3-02 | Fresh 30 vượt ngưỡng sau đúng một bước, tạm dừng giữ nguyên | Đạt, `test_spoiled_edge_and_pause` |
| AC-P3-03 | Món chuyển sang cá thể còn tươi và chốt giá 47 | Đạt, `test_spoiled_reservation_reassigned_before_cooking` |
| AC-P3-04 | Kho bàn giao và cấp id xuyên Ngày | Đạt, `test_day_fixture_id_increases_after_shop` |
| AC-P3-05 | Thay đổi hợp đồng, HUD hàng ươn và regression | [ADR](../adr/0001-kho-ca-the.md) · [Bằng chứng](../proof/phase-3/integration.md) |

Fixture đổi kiểu do kho cá thể thay kho đếm. Kỳ vọng doanh thu thay đổi theo giá chốt bằng độ tươi.
