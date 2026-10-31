# Trạng thái triển khai hiện tại - VoiceScope

Ứng dụng web/API hiện dùng NII AntiDeepfake Wav2Vec2-Small ONNX Q4 trên CPU, không cần GPU hoặc huấn luyện lại. Web: https://voicescope-581u.onrender.com. Docker target `web` đóng gói model theo revision cố định và chạy bằng user không có quyền root.

Hướng dẫn CI/CD và Docker mới: [Markdown](docs/huong-dan-cicd-docker-ai.md) và [PDF](docs/huong-dan-cicd-docker-ai.pdf). Giấy phép model: [MODEL-NOTICE.md](MODEL-NOTICE.md), CC BY-NC-SA 4.0, phi thương mại.

Workflow kiểm tra PR không nhận secrets publish. Publish Docker Hub và deploy server là các bước riêng; trạng thái kiểm chứng cụ thể nằm trong hướng dẫn, không suy ra thành công chỉ từ cấu hình.

## Tài liệu nghiên cứu và lịch sử phiên bản đầu

Các phần bên dưới ghi lại thiết kế DINOv3 và trạng thái ban đầu; không mô tả model của Docker target `web` hiện tại.

# VoiceScope — nghiên cứu phát hiện giọng nói giả mạo tiếng Việt

**Trạng thái hiện tại: đã có ASVspoof 2019 LA và Vietnam-Celeb cục bộ;
chưa có detector đã huấn luyện hoặc checkpoint.** Dữ liệu còn cần import metadata,
QC và kiểm tra split/quyền sử dụng trước train. Không có accuracy/F1/EER để báo cáo. UI hiển thị
**“Chưa có mô hình hoặc dữ liệu để phân tích”**, API trả 503 cho suy luận khi chưa cấu hình.
Pretrained DINOv3 thị giác tự nó **không phải** detector giọng nói giả.

**Đính chính yêu cầu số 3: “link deploy hệ thống” là URL ứng dụng sau triển khai,
không phải “link delay” hoặc phép đo latency.** Benchmark giữ là công cụ tùy chọn.
Đã chuẩn bị Docker/Render cho frontend + API cùng một URL.
Người dùng đã xác nhận triển khai và mở được web trên Render. URL public chưa được
cung cấp trong repository để kiểm tra độc lập; web vẫn chờ detector checkpoint.
Xem [hướng dẫn deploy, cập nhật và checkpoint](docs/deployment.md).

## Bản nộp GitHub: thu thập và xử lý dữ liệu theo pipeline

**Phạm vi bản nộp này: mã pipeline dữ liệu và tài liệu tái lập. Huấn luyện/cấu hình
mô hình được hoãn theo yêu cầu.** Không có audio, checkpoint hoặc metadata cá nhân
được đưa vào Git. Hướng dẫn chi tiết theo từng khối trong ảnh:
[docs/data-pipeline.md](docs/data-pipeline.md).

| Bước cần kiểm tra | File đã bổ sung/có sẵn | Chức năng |
|---|---|---|
| Thu thập/tiếp nhận tiếng thật có quyền | [voicescope/collect.py](voicescope/collect.py) **mới** | Ingest file local hoặc record microphone; kiểm consent trước mở mic, giữ bytes nguồn, chống trùng ID/hash |
| Mẫu giả TTS/VC có quyền | [examples/collection.fake.example.json](examples/collection.fake.example.json) **mới** + collect ingest | Nhập file đã được tạo bằng công cụ được phép, lưu method/version/lineage; không tự gọi dịch vụ TTS |
| Audio gốc + metadata | [examples/collection.real.example.json](examples/collection.real.example.json) **mới**, [manifest schema](examples/manifest.schema.json) | ID thay thế, source, label, device/channel, sample rate/duration, consent/license và đường dẫn tương đối |
| Import benchmark đã tải | [voicescope/import_asvspoof.py](voicescope/import_asvspoof.py) **mới** | ASVspoof 2019 LA CM protocols; giữ official split và attack ID; rights pending mặc định |
| Chuẩn hóa và mức âm | [voicescope/audio.py](voicescope/audio.py), [configs/default.json](configs/default.json) | Mono 16 kHz, polyphase, peak/clipping/RMS, chuẩn hóa mức âm tùy chọn |
| Phân đoạn và mapping | [voicescope/audio.py](voicescope/audio.py) | Energy gate, cửa sổ theo config, giữ thời gian gốc; chưa phải learned VAD |
| Biến thể thiết bị/kênh tùy chọn | [voicescope/prepare.py](voicescope/prepare.py) | White noise 20 dB theo seed; giữ nguyên split/parent; chưa triển khai NS/AGC/AEC/codec/replay |
| QC, reject và đóng gói | [voicescope/prepare.py](voicescope/prepare.py) | Decode/duration/clipping/duplicate, PCM16, rejects, hashes, report và output version mới |
| Chia tập chống leakage | [voicescope/manifest.py](voicescope/manifest.py) | Nhóm liên thông speaker/source/parent/VC, chia trước biến thể và audit split |
| Kiểm chứng bản nộp | [tests/test_collect.py](tests/test_collect.py), [tests/test_import_asvspoof.py](tests/test_import_asvspoof.py), [tests/test_pipeline_rejects.py](tests/test_pipeline_rejects.py) **mới** | Consent, metadata, import/labels/split và reject decode/clipping/duration bằng fixture tổng hợp |
| Hướng dẫn và thay đổi | [docs/data-pipeline.md](docs/data-pipeline.md) **mới**, README cập nhật | Lệnh chạy, đối chiếu pipeline, dữ liệu thật đã kiểm tra giới hạn và phần chưa triển khai |

Chạy kiểm tra collection/import/prepare mà không cần microphone hoặc dataset riêng:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_core.py tests/test_collect.py tests/test_import_asvspoof.py tests/test_prepare.py tests/test_pipeline_rejects.py -q
```

`requirements-collection.txt` là dependency tùy chọn **chỉ cho ghi microphone thật**;
ingest/import/prepare không cần cài sounddevice. Template consent mặc định pending,
không được tự coi là đã có đồng ý. Tín hiệu sin trong tests không dùng báo cáo chất lượng.
Xem [bằng chứng bản nộp](docs/submission-data-pipeline.md).

## Khảo sát ban đầu

Ngày 18/10/2026, thư mục chỉ chứa `design.png`, `pipeline.png`, `068431-0288open.pdf`
và `2607.17761v2.pdf`. Không có mã, README, requirements, encoder cũ, dữ liệu,
checkpoint hoặc `.git`/remote. Bốn tài liệu gốc được giữ nguyên. Đây là xây dựng
dự án mới, không phải thay backbone của một hệ thống đã hoạt động.

PDF đầu là **TF-C (NeurIPS 2022)**, PDF thứ hai là **TFCL cho speech deepfake dưới AFE**.
Triển khai DINOv3 dưới đây là hướng nghiên cứu theo yêu cầu, **không phải bản tái lập
TF-C/TFCL**; không lấy kết quả trong hai bài làm kết quả dự án. Xem [ghi chú nghiên cứu](docs/research.md).

## Các giai đoạn

1. **Ứng dụng/pipeline:** đã có schema, adapter, CLI nghiên cứu, API và UI. Tín hiệu
   toán học chỉ dùng trong tests, không dùng báo cáo chất lượng.
2. **Deploy:** đã có startup theo PORT, container và Render Blueprint; người dùng
   xác nhận web đã mở trên Render. Chưa có URL trong repo để xác minh public.
3. **Dữ liệu/model:** corpus đã tải cục bộ; đã thêm importer ASVspoof LA, còn cần QC toàn bộ, weights DINOv3
   có quyền, train và đánh giá held-out rồi mới cấu hình checkpoint cho ứng dụng.

## Kiến trúc

```text
WAV/FLAC → kiểm tra decode/kích thước/thời lượng/clipping
         → mono + resample polyphase 16 kHz
         → energy gate + cửa sổ tối đa 4 giây, giữ offset gốc
         → STFT Hann 25 ms / hop 10 ms / FFT 512
         → 80 HTK Mel bins, log-power cố định [-80,20] dB
         → resize toàn ảnh 256×256, lặp 3 kênh, normalize ImageNet
         → DINOv3 ViT-S/16 → embedding 384 → Linear(384,2)
         → softmax Real/Fake, gộp cửa sổ theo thời lượng
```

DINOv3 không nhận waveform thô. Adapter không crop hoặc lật trục thời gian.
Tâm frame `i`: `(i*160+200)/16000` giây. Khi resize, cột ảnh `x` ánh xạ về
`(x+0.5)*source_columns/image_columns-0.5`, chặn ở hai biên, rồi cộng offset đoạn.
API trả mapping để phát triển công cụ xem lại. **Mapping/attention không phải temporal score.**
V1 chỉ phân loại cấp clip; `temporal_scores=null`, không tô vùng “giả” dựa trên biên độ.

FastAPI phục vụ cả web HTML/CSS/JS, cùng origin; không cần Node để chạy web.
Backend không tự kết nối dịch vụ AI, không tự tải weights hoặc dataset.

## Thiết lập môi trường

Python **3.12** khuyến nghị. Từ thư mục gốc, PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn voicescope.api:app --host 127.0.0.1 --port 8000
```

Mở [demo local](http://127.0.0.1:8000), [API docs](http://127.0.0.1:8000/docs),
[health](http://127.0.0.1:8000/health). Chạy được UI/API chưa cấu hình **không cần PyTorch**.
Nếu venv không bootstrap được pip, dùng bản Python chính thức có `ensurepip`.
Trong phiên Codex đã dùng pip của runtime để cài vào `.venv`, không sửa Python hệ thống.

`requirements-verified.txt` ghi phiên bản môi trường base thực sự đã kiểm thử;
`requirements*.txt` là các dải tương thích khai báo. Phiên bản ML chưa được xác minh trong phiên này.

## Deploy frontend và backend cùng một URL

`voicescope.server` đọc `HOST`/`PORT` của hosting, chạy một worker và phục vụ web/API
cùng origin; frontend gọi `/health` và `/inference` tương đối. Không cần CORS khi
dùng cấu trúc này. HTTPS do hosting/reverse proxy quản lý.

```powershell
# Chạy cùng startup dùng trên hosting:
$env:HOST = '127.0.0.1'
$env:PORT = '8000'
.\.venv\Scripts\python.exe -m voicescope.server

# Hoặc, trên máy đã có Docker:
docker compose up --build -d
```

Để lấy URL public: đưa mã nguồn lên repository được cấp quyền, kết nối tài khoản
Render và tạo Blueprint từ `render.yaml`. Lấy URL HTTPS thực tế mà Render cấp,
rồi kiểm tra (không upload audio):

```powershell
$deployUrl = Read-Host 'URL HTTPS thực tế từ Render'
.\.venv\Scripts\python.exe -m voicescope.smoke --url $deployUrl --require-https --expect unconfigured --timeout 60 --output artifacts/deploy-smoke.json
```

Không có URL public hoặc deployment thành công được giả định trong repository.
`Dockerfile` mặc định không cài torch hoặc chứa model; target `inference` bổ sung CPU
runtime khi có checkpoint. `.dockerignore` dùng allowlist để dataset/weights/.env
không vào build context. Docker build chưa được chạy vì máy hiện tại không có Docker.
Các lệnh deploy, danh sách biến môi trường, tài nguyên đề xuất, cách mount checkpoint,
cập nhật phiên bản và rollback nằm ở [docs/deployment.md](docs/deployment.md).

Biến web chính: `HOST`, `PORT`, `VOICESCOPE_VERSION`, `VOICESCOPE_ALLOWED_HOSTS`,
`VOICESCOPE_CORS_ORIGINS` (trống khi cùng origin), `VOICESCOPE_INFERENCE_PER_MINUTE`,
`FORWARDED_ALLOW_IPS`. Biến model: `VOICESCOPE_CONFIG`, `VOICESCOPE_DEVICE`,
`VOICESCOPE_CHECKPOINT`, `VOICESCOPE_DINOV3_REPO`, `VOICESCOPE_BACKBONE_WEIGHTS`.
Không có secret frontend; credential hosting được quản lý ngoài Git.

## DINOv3, weights và giấy phép

Làm theo [repository chính thức](https://github.com/facebookresearch/dinov3),
[PyTorch installation selector](https://pytorch.org/get-started/locally/) để chọn CPU/CUDA đúng máy.
Hướng dẫn Hub chính thức yêu cầu PyTorch; dự án này dùng Hub local, không cần Transformers.

```powershell
# Chỉ cài ML khi chuẩn bị huấn luyện; chọn torch CPU/CUDA theo hướng dẫn chính thức.
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
git clone https://github.com/facebookresearch/dinov3.git vendor/dinov3
git -C vendor/dinov3 rev-parse HEAD
```

Ghi lại commit DINOv3 và dùng cùng revision khi train/serve; code train cũng ghi revision
vào provenance. Nếu cần tái lập máy khác: checkout đúng SHA đã ghi trước khi nạp detector.
Xin quyền tải ở liên kết pretrained models trong repo; tự đọc/chấp nhận
[DINOv3 License](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md).
Đây là giấy phép riêng của Meta, không tự coi là MIT/Apache. Khi phân phối sản phẩm
phái sinh hoặc công bố nghiên cứu, kiểm tra nghĩa vụ giấy phép/ghi nhận trong văn bản gốc.
Không có weights hoặc bản license thay thế được đóng gói ở đây.

Tải **LVD-1689M ViT-S/16** được cấp quyền vào `checkpoints/`, giữ tên gốc của tệp tải về.
Không lưu URL tải có token trong Git. Hub identifier mặc định: **`dinov3_vits16`**.
Các lựa chọn được adapter hỗ trợ: `dinov3_vits16plus`, `dinov3_vitb16`, `dinov3_vitl16`.
Chỉ dùng weights LVD với normalize hiện tại; weights SAT cần adapter/config riêng.
Tương ứng HF chính thức cho lựa chọn mặc định là `facebook/dinov3-vits16-pretrain-lvd1689m`,
nhưng v1 **không dùng** HF loader.

```powershell
$env:VOICESCOPE_CONFIG = 'configs/default.json'
$env:VOICESCOPE_DINOV3_REPO = (Resolve-Path 'vendor/dinov3').Path
# Thay tên dưới đây bằng đúng tên tệp bạn đã tải:
$env:VOICESCOPE_BACKBONE_WEIGHTS = 'checkpoints/dinov3_vits16_pretrain_lvd1689m-08c60483.pth'
$env:VOICESCOPE_DEVICE = 'cpu'
```

`freeze_backbone=true` mặc định: train head, backbone eval và không gradient.
Đổi thành `false` trong JSON để fine-tune; tự chọn batch size/lr theo tài nguyên.
Mọi đường dẫn cấu hình là local; không hard-code đường dẫn máy người phát triển.
Các biến môi trường override JSON, `.env.example` chỉ là tài liệu, không được tự đọc.

Detector checkpoint phải có toàn bộ backbone+head, cấu hình tiền xử lý, nhãn, phiên bản
và provenance do lệnh train tạo. Backbone weights riêng không thể đưa vào `VOICESCOPE_CHECKPOINT`.
Loader dùng `weights_only=True`, strict state_dict, chặn checkpoint test fixture.
Chỉ nạp repository/checkpoint cục bộ đáng tin cậy; metadata checkpoint không phải chứng thực chất lượng.

## Dữ liệu và tiền xử lý

Đọc [hướng dẫn dữ liệu](docs/data.md), [schema](examples/manifest.schema.json),
[manifest mẫu](examples/manifest.example.jsonl). Mẫu chỉ có ID giả, `consent_status=pending`,
`is_test_fixture=true`, không có tệp audio và **cố ý không được pipeline chấp nhận**.
Không đổi cờ mẫu thành dữ liệu thật để chạy nghiên cứu.

```text
data/
  private/raw/                  # audio có quyền; không vào Git
  private/manifest.jsonl         # mỗi dòng một clip gốc
  processed/v001/
    audio/                      # mono 16k PCM16
    split-plan.jsonl             # chia trước tạo biến thể
    manifest.jsonl              # clip, lineage, split, offsets, hashes, quality
    rejects.jsonl               # lý do loại
    prepare-report.json         # config, seed, số lượng, fingerprint
  benchmarks/<name>/<version>/  # tách nguồn benchmark khỏi private
checkpoints/                    # weights riêng tư/local
artifacts/                      # run train, báo cáo evaluation/latency
```

```powershell
.\.venv\Scripts\python.exe -m voicescope.prepare --manifest data/private/manifest.jsonl --root data/private --output data/processed/v001 --config configs/default.json
# Tùy chọn thêm white-noise 20 dB, luôn kế thừa split/lineage:
# ... --augment-noise
```

Không ghi đè thư mục output đã tồn tại; chọn version mới. Seed trong JSON.
Chia theo **thành phần liên thông** speaker/source/parent/related IDs, khoảng 70/15/15
theo số nhóm (không bảo đảm theo số clip). Cần ít nhất 3 nhóm; train yêu cầu mỗi split
có cả Real/Fake. Không phá nhóm để cân bằng lớp. Nếu có split chính thức, ghi sẵn đủ
mọi dòng; pipeline kiểm tra thay vì chia lại. Mọi biến thể giữ cùng split với bản gốc.

Audio phải là WAV/FLAC, 0,25–120 giây, tối đa 20 MiB, ngân sách giải nén 16 triệu
mẫu đa kênh. MP3/M4A cần tự chuyển đổi bằng công cụ có quyền. Kiểm tra sample rate,
duration metadata, nonfinite, clipping >1%, peak sau resample, hash PCM trùng.
`peak_normalize=false` để tránh xóa tín hiệu biên độ không chủ ý. Energy gate mặc định
-45 dBFS, gap 200 ms, context 100 ms; đây là heuristic **không phải VAD đã học**.
QC phải có nghe/rà soát thủ công. Exact duplicate detection không phát hiện mọi near-duplicate.

## Train, đánh giá và latency — chỉ sau khi có dữ liệu thật

```powershell
.\.venv\Scripts\python.exe -m voicescope.train --manifest data/processed/v001/manifest.jsonl --root data/processed/v001 --config configs/default.json --output artifacts/run001 --epochs 10 --batch-size 8
$env:VOICESCOPE_CHECKPOINT = 'artifacts/run001/best.pt'
.\.venv\Scripts\python.exe -m voicescope.evaluate --manifest data/processed/v001/manifest.jsonl --root data/processed/v001 --config configs/default.json --output artifacts/evaluation001.json
.\.venv\Scripts\python.exe -m voicescope.benchmark --manifest data/processed/v001/manifest.jsonl --root data/processed/v001 --config configs/default.json --output artifacts/latency001.json --warmup 3 --repeats 10 --limit 20
# Khởi động lại API để nạp checkpoint mới:
.\.venv\Scripts\python.exe -m uvicorn voicescope.api:app --host 127.0.0.1 --port 8000
```

Train chọn checkpoint bằng validation loss, không truy cập audio test để tối ưu model.
Kiểm tra hash và metadata test phục vụ audit. Ngưỡng mặc định 0,5 cố định từ config;
nếu hiệu chuẩn/chọn ngưỡng sau này, chỉ dùng validation và lưu ngưỡng vào checkpoint.
Chế độ deterministic có thể báo lỗi trên một số kernel GPU; xử lý và ghi nhận thay đổi,
không tự chuyển sang nondeterministic mà giấu trong báo cáo.

Evaluate đo **cấp clip đoạn đã prepare, chỉ variant clean**, không phải cấp speaker
hay định vị đoạn giả. Fake là positive: precision/recall/F1, ROC-AUC, EER nội suy từ ROC,
confusion matrix thứ tự `[real,fake]` (hàng thật, cột dự đoán). Kiểm tra nhóm test không
giao với nhóm train/validation lưu trong checkpoint. Dataset lệch lớp/thiết bị/ngôn ngữ
có thể làm metric thay đổi; không so trực tiếp với protocol khác hoặc số trong bài tham khảo.
Chưa triển khai khoảng tin cậy hay đánh giá robustness AFE đầy đủ.

Benchmark warm-up rồi lặp mẫu test theo seed; ghi từng duration/bytes, CPU/GPU,
phiên bản thư viện, CUDA, số thread, hashes; median/p95 preprocessing, model và tổng
compute máy chủ. CUDA được synchronize. **Không gồm tải model, đọc disk hoặc HTTP/network**;
API trả thêm `server_request` gồm nhận request, chưa gồm serialize response/network trả về.
So sánh latency chỉ khi cùng hardware, precision, batch, cấu hình và phân phối thời lượng.

## API, giao diện và quyền riêng tư

- `GET /health`: liveness và `model_ready`, `status=not_configured/load_error/ready`.
- `GET /ready`: 503 khi chưa model/lỗi load, 200 khi detector đã nạp. Hosting kiểm tra
  `/health` để web vẫn mở được khi đang chờ checkpoint.
- `POST /inference`: body là byte WAV/FLAC, `Content-Type: audio/wav` hoặc `audio/flac`.
  Không dùng multipart. Trả 503 khi chưa cấu hình; 413 quá lớn; 415 content type sai;
  422 audio không hợp lệ; 429 khi máy chủ đang bận; 408 upload timeout.
- Xử lý inference trong worker thread, UI dùng fetch async và progress vô định lượng,
  không bịa phần trăm tiến độ. Một request inference tại một thời điểm cho mỗi process.
- Chọn tệp, drag-drop, preview waveform/thời lượng local, ghi âm có xin quyền,
  chuyển bản ghi thành WAV, tải JSON chỉ khi API đã trả kết quả.
- Không ghi audio upload ra disk, không log nội dung audio, không lưu lịch sử.
  Buffer được thả sau request; không cam kết xóa vật lý RAM/OS swap. Frontend giữ tệp
  trong RAM cho tới khi bỏ tệp/đóng trang. Nút ghi âm chỉ gửi khi bấm phân tích.
- Local bind `127.0.0.1`; startup hosting bind `0.0.0.0:$PORT`. Có rate limit inference
  theo IP/process và Host/CORS cấu hình. Chưa có auth/quota phân tán nhiều instance.
  Không có analytics/CDN trong giao diện chính.

## Các thay đổi trong phiên bản này

| Đường dẫn | Nội dung và lý do |
|---|---|
| `voicescope/config.py`, `configs/default.json`, `.env.example` | Cấu hình tái lập, override local paths, không hard-code máy cá nhân |
| `voicescope/audio.py` | Decode/QC/resample, energy gate, log-Mel và mốc thời gian |
| `voicescope/manifest.py` | Schema runtime, consent, đường dẫn an toàn, nhóm liên thông và audit leakage |
| `voicescope/prepare.py` | CLI chia trước biến thể, PCM16, duplicate/reject, provenance và version output |
| `voicescope/collect.py`, `requirements-collection.txt`, `examples/collection.*.example.json` | **Bản nộp pipeline:** tiếp nhận/ghi âm local có kiểm consent, metadata, chống trùng, dependency mic tùy chọn |
| `voicescope/import_asvspoof.py` | **Bản nộp pipeline:** nhập protocol benchmark đã tải, giữ nhãn/split, không tự xác nhận quyền sử dụng |
| `docs/data-pipeline.md`, `docs/submission-data-pipeline.md`, các test collection/import/reject | **Bản nộp pipeline:** bản đồ code theo ảnh, hướng dẫn tái lập và bằng chứng kiểm chứng |
| `voicescope/model.py` | DINOv3 Hub local, adapter ảnh 3 kênh, freeze/fine-tune, head hai lớp |
| `voicescope/train.py` | Train supervised, validation chọn checkpoint, seed/hashes, chặn fixture |
| `voicescope/inference.py` | Nạp detector strict, dùng config checkpoint, inference thật và timing |
| `voicescope/evaluate.py` | Đánh giá held-out clean clips, ROC/EER/confusion matrix |
| `voicescope/benchmark.py` | Warm-up, median/p95 và thông tin môi trường thật |
| `voicescope/api.py` | Health/inference, upload RAM có giới hạn, lỗi tiếng Việt |
| `voicescope/deployment.py`, `voicescope/server.py` | PORT hosting, Host/CORS, version và rate limit tách khỏi cấu hình checkpoint |
| `voicescope/smoke.py`, `tests/test_deployment.py` | Kiểm tra URL thực, health/readiness và trạng thái thiếu model |
| `Dockerfile`, `.dockerignore`, `compose.yaml`, `render.yaml` | Đóng gói và cấu hình frontend/API cùng URL, không gửi dataset/weights vào image |
| `requirements-runtime.txt`, `docs/deployment.md` | Dependency API ghim phiên bản, hướng dẫn deploy/update/model và giới hạn kiểm chứng |
| `web/` | VoiceScope responsive tiếng Việt theo mockup, không có score giả |
| `examples/`, `data/README.md`, `docs/data.md` | Schema, ví dụ metadata không nhận dạng, hướng dẫn thu thập |
| `tests/`, `pytest.ini` | Test tín hiệu tổng hợp, leakage, QC và API; ML tests tùy dependency |
| `requirements*.txt`, `.gitignore` | Dependency tách base/ML, loại audio/weights/cache/secrets khỏi Git |
| `docs/research.md`, `docs/verification.md`, `docs/plans/` | Phân biệt tài liệu tham khảo, kế hoạch và bằng chứng kiểm thử |

## Kiểm chứng và giới hạn

Kết quả thực tế ghi tại [docs/verification.md](docs/verification.md). Không suy diễn
smoke test thành khả năng phát hiện thật. V1 chưa xác minh full DINOv3 forward,
train GPU, load checkpoint trained hoặc chất lượng dữ liệu tiếng Việt. Các phần còn
cần hoàn thiện: import/QC dữ liệu đã có, quyền sử dụng phù hợp, weights được cấp quyền,
phần cứng, huấn luyện và đánh giá protocol; hosting/repository để có URL public.
Không mô phỏng AEC/NS/AGC rồi gọi là WebRTC thật.

## Git/GitHub và cách nộp

Repository hiện tại: [nqming/voicescope](https://github.com/nqming/voicescope).
Commit nền ứng dụng/deploy: `d4e373e` trên `feature/deploy-voicescope`.
Bản nộp mã dữ liệu được chuẩn bị trên branch **`feature/data-pipeline-submission`**,
để review riêng và giữ nguyên branch deploy đang hoạt động.

Nộp **link branch/commit** có README này cùng mã trong `voicescope/`, templates,
configs, docs và tests. Không chỉ gửi link mặc định nếu default branch chưa có bản mới.
Mọi kết quả push/commit thực tế được báo ở cuối phiên làm việc; không coi tên branch
trong tài liệu là bằng chứng đã push nếu lệnh Git thất bại.

Không force-push, không push trực tiếp main/master, không dùng `git add -f` cho audio,
archives, metadata riêng hoặc weights. Hai ảnh/PDF tham khảo giữ local, không tự
đưa lên Git khi chưa xác minh quyền phân phối. Dataset chỉ nằm ở `data/` ngoài Git.
