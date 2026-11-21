# Kiểm chứng Phase 2 · Test Contract v1.1

| AC | Kiểm tra | Kết quả |
|---|---|---|
| AC-P2-01 | Preset sáu món, hai bếp, bốn bàn, sinh cá và va chạm | Bộ test gameplay và `test_day.py` |
| AC-P2-02 | Gather xuất kho → tiến trình Quán nhập, nấu, giao, trả tiền | `test_catch_export_cook_serve_and_pay` |
| AC-P2-03 | Pause, bàn giao pha, mua đúng giá và áp cấp vào ngày sau | `test_pause_shop_purchase_and_active_level` |
| AC-P2-04 | Hai ngày mặc định chạy đến khi đóng Shop | [Bằng chứng](../proof/phase-2/integration.md) |

Smoke P1 đổi số cá từ 6 lên preset 8. Kiểm mode lạ đổi sang `shop` vì `day` đã hợp lệ. Fixture hái tắt cá ngẫu nhiên để chỉ kiểm sự kiện mong đợi.
