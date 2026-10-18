# Kiểm chứng thực tế — 18/10/2026

## Bản nộp mã pipeline dữ liệu

Sau khi người dùng hoãn huấn luyện và yêu cầu submit code dữ liệu: đã thêm CLI
collect ingest/record, importer ASVspoof2019 LA, templates và tài liệu đối chiếu
pipeline. Toàn bộ tests: **23 passed, 2 skipped, 1 warning**. Import protocol/header
thật có giới hạn: 12 dòng, 0 reject, rights pending, không train/evaluate.
Chi tiết: [submission-data-pipeline.md](submission-data-pipeline.md).
Repository đã có remote GitHub và commit nền d4e373e; các mục cũ bên dưới là lịch sử.

## Cập nhật triển khai sau khi đã bổ sung corpus

Đã xác nhận các thư mục ASVspoof 2019 LA (train/dev/eval và CM protocols) và
Vietnam-Celeb (`original/data` cùng metadata) có trên máy. Chưa import/QC lại toàn bộ
audio trong phiên deploy này; không xem dữ liệu đã tải là dữ liệu đã được train.

- Đính chính yêu cầu số 3 là **link deploy**. Không yêu cầu kết quả latency.
- Kiểm thử phần mới từ RED (thiếu module deployment) đến GREEN: 6 test deploy pass.
- Toàn bộ test sau thay đổi: **17 passed, 2 skipped, 1 warning** qua
  `python -m pytest -q --basetemp=tmp/deploy-full-tests`.
- `python -m compileall -q voicescope tests`, `node --check web/app.js`: exit 0.
- `python -m pip check`: `No broken requirements found.`
- `python -m voicescope.smoke --url http://127.0.0.1:8080 --expect unconfigured`:
  exit 0. Trang chủ/JS/health/readiness và inference 503 không score đúng;
  version `deploy-local-check`, `model_ready=false`. Báo cáo cục bộ nằm ở
  `artifacts/deploy-local-smoke.json`, được .gitignore loại khỏi Git.
- Trình duyệt mở bản local 8080, hiển thị trạng thái thiếu model và nút phân tích
  disabled sau fetch health thật. Không thay API bằng mock trong browser.
- Rà 40 file text mã/tài liệu: không thấy pattern secret/conflict phổ biến hoặc
  trailing whitespace. Không đọc/in giá trị credential. Không thấy biến credential
  hosting/GitHub phổ biến trong session.
- `git diff --check` không chạy được như Git repository: vẫn chưa có `.git`/remote.

Chưa có URL public, chưa publish, chưa cấp HTTPS hoặc tạo commit/PR. Render được
tìm thấy nhưng chưa cài/kết nối; chưa có Docker CLI/engine nên chưa build/run image,
chưa validate Blueprint bằng Render API. `Dockerfile`, `.dockerignore`, `compose.yaml`,
`render.yaml` là cấu hình đã soạn; kiểm tra local không được tính là deploy cloud.
Target inference CPU cũng chưa build và không có detector checkpoint để test.
Review mã triển khai độc lập không phát hiện blocker cụ thể; các giới hạn còn lại là
Linux/Docker build, model runtime và public HTTPS chưa kiểm chứng. Nhận xét này chỉ
áp dụng cho cấu hình mã nguồn, không phải xác nhận đã triển khai thành công.

Các kết quả bên dưới là lịch sử khảo sát/kiểm thử phiên xây dựng ban đầu.

## Đã thực hiện

- Khảo sát toàn bộ thư mục đầu vào: đúng hai PNG và hai PDF; không có Git/code/data/weights.
- Mở cả hai PNG; đọc text PDF (TF-C 16 trang, TFCL 9 trang), xem các phần kiến trúc liên quan.
- Đối chiếu README/license/Hub definitions trên repository DINOv3 chính thức.
- Tạo venv Python 3.12.14, cài dependency base/dev. Không tải weights/dataset, không cài torch/sklearn.
- `python -m pytest -q --basetemp=tmp/final-run`: **11 passed, 2 skipped, 1 warning**.
  Hai module tùy chọn skip vì thiếu torch và sklearn, không được tính pass.
- `python -m compileall -q voicescope tests`: exit 0.
- `node --check web/app.js`: exit 0.
- `--help` của bốn CLI prepare/train/evaluate/benchmark: exit 0; không khởi động training.
- Bootstrap pip trong `.venv` đã hoàn tất (pip 25.0.1). Lưu 28 dependency pins base/dev
  trong `requirements-verified.txt`.
- Rà 33 file text nguồn/tài liệu: không thấy conflict marker, mẫu private-key/token thông dụng,
  trailing whitespace, weights hoặc file nguồn >1 MB. Đây không phải audit secret toàn diện.
- Chạy Uvicorn local, mở trang bằng trình duyệt: health phản ánh thiếu model, CTA phân tích
  disabled, không score/latency giả. Kiểm tra desktop và viewport 390×844; sửa logo tràn sidebar.
- Review mã độc lập phát hiện train/serve segmentation và decoded-memory budget; đã sửa,
  thêm test hồi quy và reviewer xác nhận hai finding được xử lý.

## Test bao phủ

1. Nhóm liên thông speaker/source và tính tái lập khi đổi thứ tự manifest.
2. Consent pending bị chặn; đường dẫn traversal/absolute bị chặn.
3. Stereo 48 kHz → mono 16 kHz và mapping tâm frame/hop của log-Mel.
4. Audio không decode được và duration vượt giới hạn.
5. Phát hiện split cùng speaker bị rò rỉ.
6. Energy gate loại silence và giữ offset; bỏ tail quá ngắn.
7. Giới hạn decoded samples trước cấp phát mảng audio lớn.
8. Prepare tín hiệu sin tổng hợp: exact duplicate reject, sinh noise, giữ lineage/split.
9. API thiếu model trả 503, health false, UI có đúng thông báo.
10. Checkpoint không tồn tại giữ trạng thái load_error/503.
11. API xử lý 413/415/422/400 và giải phóng busy flag (service test chỉ báo lỗi, không dự đoán).

Tín hiệu kiểm thử chỉ sinh trong thư mục tạm pytest, là toán học/sine wave,
**không phải giọng người, không phải bộ dữ liệu Real/Fake, không dùng báo cáo chất lượng**.

## Hạn chế kiểm chứng

- Chưa chạy DINOv3 thật, gradient/forward thật, GPU, huấn luyện, checkpoint detector thật,
  evaluation metric trên dữ liệu, benchmark latency, microphone thật hoặc upload lớn trên browser.
- Tests adapter/frozen gradient/metrics được viết nhưng skip do thiếu dependency ML.
- Một warning: Starlette TestClient khuyến cáo chuyển từ httpx sang httpx2 ở phiên bản
  đang cài. Tests vẫn pass; chưa đổi transport vì cần kiểm tra tương thích riêng.
- Không chạy linter chuyên dụng Ruff/ESLint; Python compile và JS syntax check không thay thế lint.
- Pytest trong sandbox gặp lỗi/treo truy cập temp; lần chạy thành công sử dụng quyền được cấp
  và temp bên trong workspace. Không kết luận đây là lỗi pipeline.
- `git diff --check`/`git status` không thực hiện được theo chế độ repository vì không có `.git`.
  Không có staged content/commit/push/PR. `.gitignore` và danh sách stage giới hạn được cung cấp.

## Kết quả nghiên cứu

Không có. Không báo accuracy, F1, EER hoặc median/p95 latency. Thời gian chạy pytest
không phải latency detector. Giai đoạn tiếp theo cần dữ liệu có quyền, weights, hardware
và chạy các lệnh trong README.
