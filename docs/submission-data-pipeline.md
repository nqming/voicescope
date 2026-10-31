# Bằng chứng bản nộp mã dữ liệu

## Phạm vi và thay đổi

Commit nền: `d4e373e`, branch nền `feature/deploy-voicescope`.
Branch nộp dự kiến: `feature/data-pipeline-submission`; chỉ được coi là đã submit
sau khi Git push thành công và có commit/link trong báo cáo phiên làm việc.

Mới: `voicescope/collect.py`, `voicescope/import_asvspoof.py`, dependency microphone
tùy chọn, hai template metadata, tests collection/import/reject và hướng dẫn đối
chiếu pipeline. README đã có mục nổi bật liệt kê file cập nhật và chức năng cụ thể.
Giữ nguyên mã web/model/train hiện có; không huấn luyện hoặc cấu hình checkpoint.

## Kiểm thử thực tế

- Tests mới trước implementation: RED vì thiếu collect/import modules.
- Sau implementation: tests collection/import và QC reject pass.
- Toàn bộ: **23 passed, 2 skipped, 1 warning**, lệnh
  `python -m pytest -q --basetemp=tmp/data-submit-final`.
- Hai module ML skip vì thiếu torch/sklearn; không tính là model test đã pass.
- Warning duy nhất là Starlette khuyến cáo transport httpx2; không có test failure.
- Compile Python và `pip check` đã chạy; dependency base không bị xung đột.
- CLI help gặp UnicodeEncodeError do cp1252 của terminal Windows; thêm cấu hình
  UTF-8 cho stdout/stderr trong hai CLI mới và kiểm tra lại sau sửa.
- Không ghi microphone thật: test record dùng sine-wave test double có cờ fixture.
- Importer có cờ test-fixture; tests xác nhận output fixture bị chặn khỏi train.
- Không gọi TTS/VC bên ngoài, không tạo dataset giọng giả rồi tuyên bố là dữ liệu thật.

## Kiểm tra trên dữ liệu đã tải

Đã chạy importer ASVspoof 2019 LA với `--limit-per-class 2` trên thư mục local:

| Split | Real | Fake | Audio header lỗi |
|---|---:|---:|---:|
| train | 2 | 2 | 0 |
| validation | 2 | 2 | 0 |
| test | 2 | 2 | 0 |

Tổng 12 dòng, giữ split official, không huấn luyện hoặc đánh giá model. Đây chỉ là
kiểm tra importer/protocol/header có giới hạn, chưa full decode/QC toàn corpus.
Output nằm dưới `data/imported/asvspoof2019-submission-preview/` ngoài Git.
Rights mặc định **pending**, không tự khẳng định người dùng đã xem/chấp thuận license.
Không đưa manifest thật, audio hoặc đường dẫn máy cá nhân từ output này lên Git.

## Tính phù hợp pipeline

Đã có code cho thu âm có xác nhận, nhập audio có metadata, mono/16k/PCM16, mức âm,
phân đoạn giữ timestamp, noise tùy chọn, QC/reject/hash, group split và version report.
Split trước biến thể được chọn để tránh leakage dù ảnh thể hiện bước đóng gói ở cuối.
Chưa có learned VAD, WebRTC AFE đầy đủ, near-duplicate detector, importer Vietnam-Celeb,
provider TTS/VC hoặc bằng chứng consent thực. Các phần này được ghi rõ, không gán
nhãn “hoàn thành toàn bộ nghiên cứu”.

## Quy tắc nộp

Chỉ source/config/tests/docs và template metadata không định danh. `.gitignore`
bỏ qua dataset, audio, archive, checkpoint, cache và `.env` thật. README trong
`data/` chỉ là hướng dẫn, không chứa data. Không stage hai ảnh/PDF gốc chưa rõ quyền.
Không push main/master hoặc force-push. Xem diff và danh sách staged trước commit.
