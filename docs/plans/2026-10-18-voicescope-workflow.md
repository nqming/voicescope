---
intent: Chuẩn bị VoiceScope và pipeline nghiên cứu khi chưa có dữ liệu/checkpoint
success_criteria: Kiểm thử pipeline và API chưa cấu hình; không có kết quả mô hình giả
risk_level: medium
auto_approve: true
worktree: false
---

## Khảo sát và quyết định
Chỉ có design.png, pipeline.png và hai PDF; không có .git, code, dữ liệu hay weights.
Triển khai trực tiếp theo ủy quyền của người dùng. Không tải weights/dataset hoặc chạy huấn luyện.
Chọn FastAPI + HTML/CSS/JS cùng origin thay vì framework frontend để giảm dependency.
Chọn PyTorch Hub local chính thức thay vì dịch vụ inference bên ngoài.

## Contracts
- Intent: audio → log-Mel → ảnh 3 kênh → DINOv3 → head Real/Fake; không giả lập kết quả.
- Verification: unit tests dùng tín hiệu tổng hợp chỉ kiểm tra code; API 503 khi thiếu checkpoint; compile và kiểm tra UI.
- Governance: không gửi audio ra ngoài; không tải weights; không push main; không xóa tài liệu gốc.
- Rollback: tất cả mã mới nằm trong các file mới; giữ nguyên bốn tài liệu nguồn.

## Steps
- [x] **Step 1: Tests và pipeline**
action: Tạo tests/test_core.py, voicescope/config.py, audio.py, manifest.py, prepare.py và examples/manifest.example.jsonl; kiểm tra split liên thông speaker/source, consent, traversal, duplicate và mapping thời gian.
loop: until tests pass
max_iterations: 3
verify: python -m pytest tests/test_core.py
gate: auto

- [x] **Step 2: Model và nghiên cứu**
action: Tạo model.py, inference.py, train.py, evaluate.py, benchmark.py; chỉ load local weights; checkpoint chứa cấu hình và provenance; không chạy training thật.
loop: false
verify: python -m compileall -q voicescope
gate: auto

- [x] **Step 3: API và VoiceScope**
action: Tạo api.py và web/index.html, app.js, styles.css; giới hạn upload và decode; trả 503 chưa cấu hình; UI hiển thị trạng thái thật và pipeline.
loop: until tests pass
max_iterations: 3
verify: python -m pytest tests/test_api.py
gate: auto

- [x] **Step 4: Kiểm chứng và tài liệu**
action: Viết README.md, docs/data.md, docs/research.md và docs/verification.md; chạy test toàn bộ; rà file không chứa private data/weights; ghi rõ không có remote.
loop: false
verify: python -m pytest -q
gate: auto

## Giai đoạn sau
Người dùng thu thập dữ liệu có quyền, kiểm tra manifest và split, lấy quyền tải DINOv3, rồi mới train/evaluate/benchmark trên hardware thực tế. TF-C/TFCL đầy đủ và AFE WebRTC là thí nghiệm mở rộng, không được gọi là đã tái lập.
