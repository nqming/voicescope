# Deploy VoiceScope: frontend và API cùng một URL

Yêu cầu số 3 là **link deploy hệ thống**, tức URL mở ứng dụng đã triển khai.
Benchmark latency được giữ làm tiện ích nghiên cứu, không phải đầu ra bắt buộc.

## Trạng thái hiện tại

Đã có ASVspoof 2019 LA và Vietnam-Celeb cục bộ. Đã có mã frontend/backend và các
CLI nghiên cứu. Chưa có detector checkpoint, PyTorch hoặc repository DINOv3 local.
Dataset không được đóng gói vào web service và không cần để mở UI/health.

Chưa có URL HTTPS public được cấp hoặc xác minh. Render có connector trong catalog
nhưng chưa được cài/kết nối; thư mục cũng chưa có Git repository/remote.
Máy này chưa có Docker CLI/engine, nên Dockerfile/Compose chưa được build/run thực tế.

## Phương án và tài nguyên

Giữ FastAPI phục vụ `web/` tại `/`, `/static` và API `/health`, `/ready`, `/inference`.
JavaScript dùng URL tương đối nên dùng được ngay trên domain mới, không hard-code localhost.
Same-origin không cần CORS. Không cần Node để chạy production.

| Chế độ | Tài nguyên dự kiến và trạng thái |
|---|---|
| UI/API chưa checkpoint | Container Python CPU, không torch; Render Blueprint chọn free để mở demo. Phải xác nhận build và giới hạn của tài khoản trước khi deploy. |
| Detector DINOv3 ViT-S CPU | Điểm bắt đầu để thử: 2 vCPU, RAM 4 GB, một worker, một inference đồng thời. Đây là đề xuất cấu hình, chưa phải mức sử dụng RAM/latency đo được. |
| Fine-tune/train | Chạy riêng trên máy nghiên cứu có tài nguyên phù hợp; không chạy train trong process web. Không mặc định có GPU. |

Render free có thể sleep và có giới hạn; không coi free service là hạ tầng suy luận
đã được kiểm chứng. Khi có checkpoint, đo peak RAM để chọn plan có đủ tài nguyên.
Không kích hoạt gói trả phí trong phiên này.

Nguồn hosting: [Docker on Render](https://render.com/docs/docker),
[Blueprint specification](https://render.com/docs/blueprint-spec),
[free services](https://render.com/docs/free), [TLS](https://render.com/docs/tls).
Sites dùng Workers, không được chọn để thay thế backend Python/PyTorch này.

## Chạy local

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
$env:HOST = '127.0.0.1'
$env:PORT = '8000'
$env:VOICESCOPE_VERSION = 'local'
.\.venv\Scripts\python.exe -m voicescope.server
```

Mở `http://127.0.0.1:8000`. Nếu cổng bận, đổi PORT, ví dụ 8080.
Server giữ một worker để không nhân bản model trong RAM. Access log mặc định tắt;
không ghi tên file hoặc audio request. `.env.example` không tự load: đặt biến qua shell
hoặc trang Environment của hosting. CLI chỉ dùng các biến đã được export.

## Docker local hoặc VPS

Sau khi cài Docker trên máy bạn chọn:

```powershell
docker compose up --build -d
docker compose ps
.\.venv\Scripts\python.exe -m voicescope.smoke --url http://127.0.0.1:8000 --expect unconfigured
```

`compose.yaml` bind localhost. `Dockerfile` chạy user không phải root; Compose
read-only và drop capabilities. `.dockerignore` dùng allowlist, không gửi
`data/`, archives, `.env`, `.git`, `artifacts/`, weights hay reference PDFs vào build context.
Container healthcheck dùng `/health`, không dùng `/ready` để service vẫn mở khi chưa có model.

Nếu dùng VPS với domain riêng: để container bind localhost, cấu hình reverse proxy
HTTPS của VPS trỏ về cổng này, thêm domain vào `VOICESCOPE_ALLOWED_HOSTS`, chỉ trust
địa chỉ reverse proxy trong `FORWARDED_ALLOW_IPS`. Domain/certificate chưa được cấp
trong phiên này; không có URL VPS được giả định.

## Deploy Render bằng repository

1. Tạo repository Git đích và đưa **chỉ mã nguồn** lên branch review. Dùng danh sách
   `git add` trong README; không upload dataset, `.env` hoặc checkpoints.
2. Cài/kết nối Render trong Codex, hoặc tự đăng nhập Render Dashboard và cấp quyền
   đọc repository đó. Không gửi token qua chat hoặc commit vào file.
3. Chọn **New → Blueprint**, chọn repository và branch có `render.yaml`.
4. Xem lại plan `free`, region Singapore và cấu hình. Blueprint dùng Dockerfile mặc
   định target `web`, không cài ML. Không phải nhập checkpoint để deploy UI/API.
5. Render cung cấp `PORT`; server bind `0.0.0.0:$PORT`. Health check là `/health`.
   `FORWARDED_ALLOW_IPS=*` trong Blueprint chỉ phù hợp khi mọi traffic đi qua ingress
   do Render quản lý. Không dùng cấu hình trust mọi proxy này cho cổng VPS mở trực tiếp.
6. Sau deploy thành công, lấy **URL thật từ Dashboard**. HTTPS do Render quản lý.
   Không suy đoán subdomain từ tên service: tên có thể được đổi để tránh trùng.
7. Chạy kiểm tra bên dưới rồi mới ghi URL đã xác minh vào README/báo cáo.

Blueprint tắt auto-deploy để bạn chọn phiên bản sau khi kiểm tra. Git branch được
chọn khi tạo Blueprint; không tự push main/master và không có repo URL hard-code.
Nếu dùng domain riêng, thêm domain đó vào allowed hosts ngoài `*.onrender.com`.

## Biến môi trường

| Biến | Mặc định / cách dùng |
|---|---|
| `HOST` | server module mặc định `0.0.0.0`; local đặt `127.0.0.1` |
| `PORT` | 8000 local; Render cấp tự động, không hard-code 8000 trên hosting |
| `VOICESCOPE_CONFIG` | Đường dẫn JSON; image mặc định `/app/configs/default.json` |
| `VOICESCOPE_DEVICE` | `cpu`; GPU cần image/runtime khác phù hợp máy |
| `VOICESCOPE_CHECKPOINT` | Trống: web hoạt động, inference 503; khi có model đặt đường dẫn tệp full detector |
| `VOICESCOPE_DINOV3_REPO` | Đường dẫn clone chính thức đúng revision dùng lúc train |
| `VOICESCOPE_BACKBONE_WEIGHTS` | Chỉ cần khi train từ backbone pretrained; restore full detector không cần tệp backbone riêng |
| `VOICESCOPE_VERSION` | Nhãn phiên bản không chứa secret; nếu bỏ trống dùng `RENDER_GIT_COMMIT`, nếu không có thì `local` |
| `VOICESCOPE_ALLOWED_HOSTS` | Danh sách hostname, không scheme/port. Local `localhost,127.0.0.1`; Render như Blueprint |
| `VOICESCOPE_CORS_ORIGINS` | Trống mặc định. Chỉ khi frontend riêng: các origin http(s) cụ thể cách nhau dấu phẩy, không `/` cuối, không `*`. Web có sẵn vẫn dùng same-origin |
| `VOICESCOPE_INFERENCE_PER_MINUTE` | 6 cho mỗi IP/process, trả 429 khi vượt; một inference đồng thời |
| `FORWARDED_ALLOW_IPS` | Mặc định `127.0.0.1`; chỉ điền proxy tin cậy của hạ tầng |

Không đặt API key vào biến frontend hoặc `web/app.js`. Các biến đang dùng không
đòi credential. Credential truy cập hosting/weights nếu có phải do secret manager của
hạ tầng quản lý. V1 không tự tải model từ URL, không cần gửi credential vào app.

## Bổ sung checkpoint sau khi huấn luyện

Không dùng file DINOv3 pretrained làm detector Real/Fake. Cần `best.pt` được train
và đánh giá trên dữ liệu phù hợp, có config và provenance từ `voicescope.train`.

Dockerfile có target `inference` để chuẩn bị **CPU** image: chọn đúng SHA DINOv3
được ghi trong provenance, không mặc định clone main. Target cài torch 2.7.1 CPU theo
[kênh cài chính thức](https://pytorch.org/get-started/previous-versions/); đây là target
đã soạn, chưa build hoặc chạy DINOv3 ở môi trường hiện tại. Nếu train bằng phiên bản
khác, đối chiếu và đồng bộ dependency trước build/đánh giá lại.

```powershell
$dinoSha = Read-Host 'DINOv3 commit SHA đầy đủ đã dùng khi train'
docker build --target inference --build-arg "DINOV3_REF=$dinoSha" -t voicescope:inference .
$checkpointDir = (Resolve-Path 'artifacts/run001').Path
docker run --rm -p 127.0.0.1:8000:8000 --mount "type=bind,source=$checkpointDir,target=/models,readonly" -e VOICESCOPE_CHECKPOINT=/models/best.pt -e VOICESCOPE_ALLOWED_HOSTS=localhost,127.0.0.1 voicescope:inference
```

Nếu dùng Render: đổi service sang image inference bạn đã build/push lên registry
được cấp quyền, chọn tài nguyên phù hợp, gắn volume/đường cấp model an toàn của
hạ tầng rồi đặt đường dẫn checkpoint. Blueprint free ban đầu không tự tạo disk hoặc
tự provision model. Không commit weights hoặc đặt chúng trong Docker build context.
User non-root UID 10001 cần quyền đọc checkpoint. Khởi động lại service sau đổi model.
Giữ bản model và image cũ để rollback; xác minh `/ready` chuyển 200 trước công bố
sẵn sàng suy luận. License DINOv3 tiếp tục áp dụng cho mã/model liên quan.

## Kiểm tra URL thật sau deploy

```powershell
$deployUrl = Read-Host 'Dán URL HTTPS thực tế mà Render đã cấp'
.\.venv\Scripts\python.exe -m voicescope.smoke --url $deployUrl --require-https --expect unconfigured --timeout 60 --output artifacts/deploy-smoke.json
```

Nếu free service đang sleep, mở URL chờ khởi động xong rồi chạy lại. Smoke kiểm tra:
trang chủ, JS gọi `/health` và `/inference` cùng origin, health 200/version,
readiness 503 và inference 503 không score khi thiếu model. Smoke không upload audio.
Sau có checkpoint: dùng `--expect ready`; lệnh này kiểm tra trạng thái, chưa chứng minh
chất lượng detector. Mở browser để xác nhận loading, thông báo và nút bấm thực tế.

Endpoints cùng một origin:
- `/`: frontend.
- `/health`: web/API sống, HTTP 200 kể cả model chưa cấu hình.
- `/ready`: HTTP 200 khi detector nạp thành công; 503 khi chưa cấu hình/lỗi load.
- `/docs`: API docs; `/inference`: POST raw WAV/FLAC.

## Cập nhật và rollback

Chạy tests/syntax check trước, commit mã vào branch review, merge theo quy trình của
bạn rồi **Manual Deploy** commit đã chọn trên Render. Kiểm tra version trong `/health`
và chạy smoke với URL thật. Không dùng `--expect ready` khi chưa có model.
Muốn rollback, redeploy image/commit trước đó và trỏ lại model tương thích trước đó;
kiểm tra health/ready và smoke lại. Không thay schema preprocessing trong checkpoint
mà vẫn dùng detector cũ.

## Chức năng và giới hạn

Đã hoạt động local: UI tiếng Việt, static assets, health, cảnh báo chưa model, API lỗi
503 đúng; cấu hình Host/CORS/rate limit được test. Không lưu audio request vào disk.
Deploy public và Docker build còn chưa được kiểm chứng vì thiếu quyền hosting/engine.
Chưa có detector checkpoint nên chưa suy luận thật hoặc đo chất lượng.
Rate limit là per-process, không thay auth/quota phân tán khi vận hành nhiều instance.
Nếu mở app có model cho nhiều người dùng, bổ sung kiểm soát truy cập theo nhu cầu
của bạn trước khi tăng quy mô; HTTPS không tự cung cấp xác thực người dùng.
