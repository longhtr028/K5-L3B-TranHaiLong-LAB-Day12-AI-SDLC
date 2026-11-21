# Trần Hải Long · @longhtr028 · 2A202603891

- Phạm vi bài làm solo có thiết lập nhóm (999420c), Gather (4226da3) và Quán kèm kiểm thử (f82e965).
- Codex hỗ trợ triển khai và kiểm chứng. Bằng chứng chạy thật nằm trong [kiểm chứng Phase 1](../verification/phase-1.md).
- Smoke test của starter đã xanh từ đầu. Sáu test bổ sung kiểm các đường đi mới, như ngất cùng tick với lệnh cập bến, thiếu chỗ trong giỏ và trả tiền sau khi hết thời gian ăn.
- Các mốc sau có bằng chứng ở tag `phase-2` (vòng Ngày), `phase-3` (di trú kho) và `phase-4` (release). Phạm vi solo gồm tích hợp, QA và phát hành.
- Lỗi Codex từng gặp là import fixture sai cú pháp trong lần đổi kho. Test discovery phát hiện lỗi trước khi gắn tag. Bài học ghi nhận trong quá trình làm là cần chạy regression ngay khi đổi schema công khai.
- Đây là ghi chép bằng chứng có Codex hỗ trợ. Phần tự phản tư cá nhân và đánh giá chéo do người học xác nhận.
