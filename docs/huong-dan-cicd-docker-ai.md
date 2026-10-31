# VoiceScope: CI/CD và Docker cho AI inference

Tài liệu thực hành từng bước | Ngày kiểm chứng: 31/10/2026

Dự án: https://github.com/nqming/voicescope

Bản web hiện có: https://voicescope-581u.onrender.com

Phạm vi: đóng gói và phục vụ inference CPU; không huấn luyện lại model.

CI, publish Docker Hub và deploy Render đã hoàn tất cho source của v0.2.0. Đã kiểm pull công khai, inference container và inference trên web Live. Tài liệu không chứa token hay audio riêng tư.

## 1. Tổng quan và khảo sát dự án

VoiceScope nhận WAV/FLAC hoặc âm thanh ghi bằng trình duyệt, chuẩn hóa waveform mono 16 kHz và phân loại cấp clip thành real/fake. FastAPI phục vụ cả API và giao diện HTML/CSS/JavaScript tại cùng origin. Audio yêu cầu được xử lý trong RAM; không tạo kho lưu âm thanh ở máy chủ.

Model phục vụ hiện tại là NII AntiDeepfake Wav2Vec2-Small, bản ONNX Q4 với activation FP32. ONNX Runtime 1.20.1 chạy CPU, một luồng tính toán. Không cần CUDA, driver NVIDIA hay NVIDIA Container Toolkit. DINOv3 và các module huấn luyện cũ còn trong mã nghiên cứu nhưng không tham gia model mặc định của image web.

Các endpoint: GET / mở web; GET /health và /api/status trả trạng thái; GET /ready trả 200 khi model sẵn sàng, 503 khi chưa tải được; POST /inference nhận bytes WAV/FLAC, không phải multipart form. GET /docs mở tài liệu OpenAPI.

Python đích: 3.12. Dependencies API được pin trong requirements-runtime.txt. requirements-ci.txt bổ sung pytest và httpx. Dockerfile có nhiều stage: runtime API, inference DINOv3 tùy chọn cũ, antideepfake-build để chuyển đổi weights và web là image inference mặc định cuối cùng. Compose local đã chỉ rõ target web.

Weights Q4 được lưu tại /opt/models/antideepfake/model_q4.onnx. Revision upstream cố định: 9a13264b5dcc827a8d5a4f8e01fccefa392f886b. Kích thước và checksum thực tế có trong báo cáo image audit. Build tải public checkpoint, kiểm checksum nguồn, chuyển đổi và đóng gói weights. Runtime không cần tải model qua mạng.

Không tìm thấy AGENTS.md áp dụng trong thư mục dự án và các thư mục cha đã kiểm tra. Repository root có thay đổi sẵn của người dùng; việc chuẩn bị commit CI dùng checkout riêng tmp/cicd-release, không reset hay commit lẫn dữ liệu của bạn. Đường dẫn hiện tại là D:\Codex\BTTHCDTTNT; đường dẫn Bai2_CD trong lịch sử không còn tồn tại.

## 2. CI, CD, image, container và luồng triển khai

CI là các kiểm tra tự động khi code thay đổi: test Python, test ghi âm PCM, build image và gọi inference thật trong container. CD là bước đưa một image đã kiểm chứng lên môi trường chạy và kiểm tra sau triển khai.

Docker image là gói bất biến chứa chương trình, dependencies và model. Container là một phiên chạy của image. Inference là đưa audio qua model để lấy điểm và nhãn, không cập nhật weights. Tín hiệu sin tổng hợp trong smoke test chỉ kiểm đường thực thi; không phải mẫu dùng chứng minh độ chính xác.

```text
Code / Pull request
        |
        v
Python tests + PCM tests
        |
        v
Build Linux/amd64 image
        |
        v
Readiness + inference + payload audit
        |
        +-- PR: kết thúc; không có secret publish
        |
        +-- main / release/** / tag v*: đăng nhập Docker Hub
                 |
                 v
          Push image đã test
                 |
                 v
          Image digest bất biến
                 |
                 v
       CD riêng: Docker host đã cấu hình
                 |
                 v
       Health + inference; lỗi thì rollback
```

Render hiện dùng source-based Docker build và auto-deploy tắt. Đã deploy cùng source commit với v0.2.0 lên dịch vụ hiện có; Render build lại từ Git, không pull digest Docker Hub. CI/publish và deploy Render là hai bước riêng. Dịch vụ giữ gói Free và URL cũ.

## 3. Điều kiện chuẩn bị và cấu trúc file

Mục đích: có môi trường đủ để tái lập build, kiểm thử và vận hành.

Cần Git, Docker Desktop dùng Linux containers, Python 3.12 và Node.js 22 cho test JavaScript. Docker Engine kiểm tra thực tế trên máy này là 29.9.2, kiến trúc linux/amd64. Cần tài khoản GitHub có quyền ghi repository và Docker Hub có quyền push repository đích. Không cần sounddevice, dataset hay microphone để chạy CI.

Build cần mạng đến PyPI, PyTorch CPU index và Hugging Face. Nên dành ít nhất 8 GB RAM và 10 GB trống cho builder vì stage chuyển đổi có PyTorch và weights FP32. Đây là dự trù vận hành, không phải đo đạc RAM tối thiểu. Image cuối không chứa PyTorch.

Từ thư mục gốc dự án trong PowerShell:

```powershell
Set-Location D:\Codex\BTTHCDTTNT
docker version
docker context show
python --version
node --version
```

Không có giá trị cần thay nếu dùng đúng máy hiện tại. Máy khác thay đường dẫn Set-Location bằng thư mục clone của bạn. Kết quả mong đợi: Docker hiển thị cả Client và Server, context desktop-linux, Python 3.12.

Các file chính:

- Dockerfile, .dockerignore: base digest, stage model và allowlist context.
- MODEL-NOTICE.md, licenses/: nguồn, thay đổi model và license gốc.
- requirements-runtime.txt, requirements-ci.txt: dependencies API và test.
- compose.yaml: build và chạy local; compose.production.yaml: chạy image theo digest.
- tools/container_smoke.py: kiểm readiness và thực thi inference qua HTTP.
- tools/audit_image.py: kiểm model checksum, payload và user runtime.
- tools/publish_image.py: tag và push image đã test.
- .github/workflows/ci-docker.yml: CI và publish có điều kiện.
- .github/workflows/deploy-docker-host.yml, deploy/remote.sh: CD riêng.
- voicescope/smoke.py, tests/test_api.py: cập nhật giả định UI/API cũ.

## 4. Chạy ứng dụng và test local

Mục đích: xác minh mã API và pipeline cơ bản trước khi build. File dùng: requirements-ci.txt và tests/. Thư mục chạy: gốc repository.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ci.txt
.\.venv\Scripts\python.exe -m pytest -q
node tests/test_pcm_capture.cjs
.\.venv\Scripts\python.exe -m voicescope.server
```

Nếu đã có .venv thì dùng môi trường hiện có, không cần tạo lại. Mở http://127.0.0.1:8000. API local không tự có model chỉ nhờ cài dependencies; model đã đóng gói sẵn trong Docker là cách khuyến nghị cho người mới.

Nếu đã có bộ ONNX hợp lệ và muốn chạy native, cài onnxruntime==1.20.1 rồi đặt:

```powershell
$env:VOICESCOPE_MODEL = 'antideepfake-int8'
$env:VOICESCOPE_ANTIDEEPFAKE_DIR = 'tmp/antideepfake-q4-deploy'
.\.venv\Scripts\python.exe -m voicescope.server
```

Tên selector antideepfake-int8 được giữ để tương thích cấu hình cũ; weights thực tế là Q4, không phải INT8. Thay đường dẫn model bằng thư mục chứa model_q4.onnx và manifest.json khớp. Không dùng checkpoint bất kỳ hoặc sửa manifest để vượt qua kiểm tra checksum.

Kết quả kiểm tra mong đợi: test pass; /health có model_ready phù hợp. Ứng dụng chưa có model phải trả 503 cho /inference thay vì bịa điểm. Khi dừng native server dùng Ctrl+C. Không chạy hai server cùng cổng 8000.

## 5. Build image và kiểm tra nội dung

Mục đích: tạo gói inference tự chứa và tránh đưa dữ liệu riêng vào Docker. File: Dockerfile, .dockerignore, tools/export_antideepfake.py, MODEL-NOTICE.md và licenses/. Chạy tại gốc repository.

```powershell
$revision = git rev-parse HEAD
docker build --target web --build-arg VCS_REF=$revision `
  --tag voicescope:cicd-test --progress plain .
python tools/audit_image.py --image voicescope:cicd-test
docker image inspect voicescope:cicd-test `
  --format '{{.Config.User}} {{.Size}}'
```

Trong workspace đã chuyển đường dẫn, nếu Git báo không có work tree, dùng git --git-dir=.git --work-tree=. rev-parse HEAD hoặc dùng checkout tmp/cicd-release. VCS_REF phải là commit của source bạn thực sự build. Build workspace còn thay đổi chưa commit dùng nhãn workspace-cicd để tránh giả là một commit sạch.

Base Python được pin digest trong Dockerfile. API dependencies được pin exact version; các thư viện ML chính của builder cũng được pin. Dependency bắc cầu của builder chưa có lockfile kèm hash đầy đủ, vì vậy không khẳng định rebuild khác thời điểm sẽ giống từng byte. Image digest đã publish là cách tái dùng đúng gói đã test.

Allowlist context chỉ cho Dockerfile, requirements-runtime.txt, source .py, web HTML/CSS/JS, config mặc định, exporter, notice và license. Không đưa .git, .env, credential, data/, tmp/, artifacts/, notebook, PDF hay audio vào context. Final stage không sao chép /opt/source hay môi trường PyTorch của builder.

Model dùng giấy phép CC BY-NC-SA 4.0. Notice ghi rõ tác giả upstream, revision, thay đổi ONNX/Q4 và license của weights phái sinh. Model card, văn bản license, manifest và checksum được giữ trong image. Public image phục vụ nghiên cứu/giáo dục phi thương mại; public không có nghĩa được dùng thương mại.

Audit phải xác nhận UID khác 0, không có torch trong runtime, không có audio/secret trong payload ứng dụng và SHA256 weights đúng manifest. Đây là kiểm tra payload dự án; chưa phải chứng nhận image không có mọi lỗ hổng bảo mật.

## 6. Chạy container và gọi API dự đoán

Mục đích: kiểm ứng dụng thực sự tải và chạy model. File: tools/container_smoke.py. Chạy tại gốc repository, Docker Desktop đang hoạt động.

```powershell
docker run -d --name voicescope-cicd-test `
  --read-only --tmpfs /tmp:size=64m,mode=1777 `
  --cap-drop ALL --security-opt no-new-privileges `
  -p 127.0.0.1:8000:8000 voicescope:cicd-test
python tools/container_smoke.py
Invoke-RestMethod http://127.0.0.1:8000/ready
docker logs voicescope-cicd-test
```

Tên container có thể thay nếu bị trùng. Nếu cổng bận, đổi phần trước dấu hai chấm thành 8001 và truyền --url http://127.0.0.1:8001 cho smoke. Kết quả mong đợi: /ready trả model_ready=true; smoke ghi artifacts/container-smoke.json với nhãn và fake_score hữu hạn. Smoke tự tạo WAV sin 2 giây trong RAM, chỉ xác minh khả năng thực thi.

Gọi inference bằng một WAV/FLAC của bạn được phép xử lý:

```powershell
curl.exe --fail-with-body -X POST `
  -H 'Content-Type: audio/wav' `
  --data-binary '@sample.wav' `
  http://127.0.0.1:8000/inference
```

Thay sample.wav bằng tệp thật; với FLAC dùng Content-Type: audio/flac. Không dùng -F vì endpoint nhận raw body. Chạy HTTP local chỉ giới hạn loopback; ghi âm trong trình duyệt ở môi trường public cần HTTPS.

Dừng và xóa đúng container thử nghiệm sau khi kiểm tra:

```powershell
docker stop voicescope-cicd-test
docker rm voicescope-cicd-test
```

Lệnh này chỉ xóa container thử, không xóa image hay dữ liệu trên máy. Có thể dùng docker compose up --build -d cho lần chạy local tiếp theo; compose.yaml chọn target web và giới hạn cổng loopback.

## 7. Docker Hub và secrets CI

Mục đích: cấp khả năng push có kiểm soát. File workflow: .github/workflows/ci-docker.yml. Repository đích dự kiến: qminh19/voicescope; namespace được xác định từ credential helper Docker đang đăng nhập.

Repository public đã được tạo và xác minh: https://hub.docker.com/r/qminh19/voicescope. Sau xác nhận cụ thể của người dùng, DOCKERHUB_TOKEN đã được lưu dạng secret mã hóa trong GitHub Actions và DOCKERHUB_USERNAME=qminh19 đã được cấu hình. Giá trị PAT chỉ qua credential helper và bộ nhớ tiến trình; không ghi vào Git hoặc tài liệu.

Đối với một tài khoản hoặc repository mới, tạo repository Docker Hub theo namespace của bạn, visibility Public. Với qminh19/voicescope hiện tại, bước này đã hoàn tất và không cần tạo lại. Dùng PAT chỉ có quyền cần thiết cho push. Trong GitHub vào repository > Settings > Secrets and variables > Actions, tạo:

- Variable DOCKERHUB_USERNAME: qminh19.
- Secret DOCKERHUB_TOKEN: PAT Docker Hub có quyền push.

Không dán PAT vào chat, source, log hoặc tài liệu. Nhập PAT vào giao diện secrets chính thức hoặc GitHub CLI tương tác an toàn. Để đăng nhập local nếu cần, dùng docker login --username qminh19, nhập token ở prompt bảo mật. Không đặt --password TOKEN trên dòng lệnh.

```powershell
docker login --username qminh19
```

Chạy từ bất kỳ thư mục nào. Chỉ nhập credential khi chương trình yêu cầu; không thay username bằng email. Kiểm tra thành công khi Docker báo Login Succeeded và tên secret xuất hiện trong GitHub; không mở giá trị secret để xác minh.

PR dùng event pull_request và quyền contents: read. Không dùng pull_request_target để chạy code PR có secrets. Bước login/push chỉ chạy sau các kiểm tra và khi event là push trên main, release/** hoặc version tag. Action bên thứ ba được pin commit SHA từ repository chính thức.

## 8. Kích hoạt CI và quy tắc tag

Mục đích: kiểm code tự động và truy vết image về commit. File: .github/workflows/ci-docker.yml và tools/publish_image.py. Chạy Git từ checkout dùng cho CI; không add toàn bộ workspace đang có dữ liệu/thay đổi chưa kiểm tra.

Lịch sử tích hợp: PR #2 đã được thay thế; PR #3 (https://github.com/nqming/voicescope/pull/3) đã merge mã hiện tại vào main. Nhánh ci/voicescope-docker ban đầu tách từ feature/deploy-voicescope. Khi cập nhật PR, tests và image job tự chạy. Mở tab Checks hoặc Actions, đọc log bước thất bại; báo cáo JSON nằm trong artifact container-evidence.

```powershell
git switch -c feature/my-change
# Sua code va commit cac file lien quan
git push -u origin feature/my-change
```

Thay tên nhánh bằng tên việc của bạn. Tạo PR vào nhánh đã chứa workflow. Kết quả mong đợi: tests pass rồi image build và inference pass. PR không push image.

Sau khi merge phần CI vào nhánh phát hành được tin cậy và cấu hình credentials, push main hoặc release/** tạo tag sha-<40-ky-tu-commit>. Tag này truy vết source; không cập nhật latest ở mỗi commit nhánh.

Ví dụ phát hành một phiên bản ổn định chưa tồn tại:

```powershell
git tag v0.2.1
git push origin v0.2.1
```

Chỉ chạy sau kiểm tra và dùng phiên bản chưa có. Tag vMAJOR.MINOR.PATCH tạo tag cùng tên và latest; prerelease như v0.2.0-rc.1 không cập nhật latest. Workflow vẫn thêm tag SHA đầy đủ. Đã phát hành v0.2.0; ví dụ v0.2.1 ở trên là lần phát hành kế tiếp, chỉ chạy khi thực sự có phiên bản mới. Không ghi đè tag phát hành cũ; sửa lỗi bằng phiên bản mới. Deploy production nên dùng digest, không dùng latest để rollback.

## 9. Image public: pull, chạy và gọi API

Mục đích: sử dụng đúng image đã được CI kiểm và công bố. Chạy PowerShell từ gốc repository. Không cần đăng nhập để pull image public.

- Docker Hub: https://hub.docker.com/r/qminh19/voicescope
- Version: v0.2.0; tag latest hiện trỏ cùng digest.
- Source: a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd; tag SHA tương ứng cũng đã publish.
- Digest registry: sha256:29fe6d6ec3aea079af51f52fdf7cd10acad9bc12d006d97cabc7d540cdac4d95.

Không có giá trị cần thay trong các lệnh sử dụng bản phát hành này:

```powershell
docker pull qminh19/voicescope:v0.2.0
$digest = 'sha256:29fe6d6ec3aea079af51f52fdf7cd10acad9bc12d006d97cabc7d540cdac4d95'
$image = "qminh19/voicescope@$digest"
docker pull $image
docker run -d --name voicescope `
  --read-only --tmpfs /tmp:size=64m,mode=1777 `
  --cap-drop ALL --security-opt no-new-privileges `
  -p 127.0.0.1:8000:8000 $image
python tools/container_smoke.py
```

Mở http://127.0.0.1:8000, kiểm /ready trả model_ready=true và /health.version khớp source SHA phía trên. Nếu cổng/name đã dùng, chọn cổng/name khác rồi truyền --url phù hợp cho smoke. Cách gọi POST /inference bằng WAV/FLAC nằm ở mục 6.

Lệnh kiểm pull ẩn danh đã thực hiện, không logout tài khoản Docker hiện tại:

```powershell
# config.json trong thu muc nay chi chua {}
docker --config tmp/docker-public-v020 pull `
  qminh19/voicescope:v0.2.0
```

Kết quả thực tế: tải image thành công, digest khớp Docker Hub; chạy chính image theo digest, model ready, inference sin và câu TTS pass, UID 10001 và payload audit sạch. Image linux/amd64; không tuyên bố đã kiểm ARM64.

Không ghi đè tag v0.2.0. Với một bản mới, publish từ version tag mới qua workflow để có cùng kiểm thử, tag SHA và quy tắc latest. Deploy/rollback nên dùng digest thay vì latest. Giữ model notice/license trong mọi bản phân phối; weights dùng CC BY-NC-SA 4.0, phi thương mại.

## 10. Deploy và rollback trên Render

Mục đích: cập nhật đúng dịch vụ VoiceScope sau khi CI và publish pass. File nguồn: Dockerfile, voicescope/server.py và cấu hình dịch vụ Render. Chạy lệnh Git từ gốc checkout sạch; không cần tạo server mới.

Dịch vụ: voicescope; workspace My Workspace đã được người dùng xác nhận. Dashboard: https://dashboard.render.com/web/srv-dbacag3ncjis73d1c3h0. URL: https://voicescope-581u.onrender.com. Plan Free, Singapore, nhánh feature/deploy-voicescope, auto-deploy Off.

Bước 1: chọn release commit đã qua CI. Lần này là a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd (v0.2.0). Promote nhánh deploy bằng fast-forward, không force-push:

```powershell
git fetch origin
$release = 'a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd'
git merge-base --is-ancestor origin/feature/deploy-voicescope $release
if ($LASTEXITCODE -ne 0) { throw 'Khong phai fast-forward' }
git push origin "${release}:refs/heads/feature/deploy-voicescope"
```

Bước 2: trong Environment của dịch vụ, đặt VOICESCOPE_VERSION bằng release SHA. Chỉ sửa key này, giữ các biến khác. Lần thực hiện qua kết nối Render dùng thao tác merge env và đã tự kích hoạt deploy mới; không trigger thêm deploy trùng. Trên Dashboard có thể chọn Save, rebuild, and deploy sau khi nhánh đã cập nhật.

Bước 3: theo dõi deploy ID đến Live. Lần đã hoàn tất: dep-dbiqqt142hec73b8nrm0, Live lúc 15:59:39 ngày 31/10/2026 (giờ Việt Nam). Render build Docker từ Git; đây là cùng source với image public, không phải tuyên bố cùng một binary image.

Bước 4: kiểm HTTPS, readiness và phiên bản:

```powershell
python -m voicescope.smoke `
  --url https://voicescope-581u.onrender.com `
  --expect ready --require-https
```

Kết quả thực tế: HTTP checks pass, /ready 200, model_ready=true, version khớp release SHA. Câu TTS tổng hợp qua /inference trả fake_score 0,99997365, khớp container public. Không gửi bản ghi microphone riêng của người dùng. Kiểm log mức error sau startup không thấy bản ghi lỗi trong khoảng đã truy vấn.

Rollback khi cần: Dashboard > Deploys > chọn deploy trước dep-dbi8tiutlv9c7396glm0 (commit f196402) > Rollback, nếu artifact còn được Render giữ. Sau rollback kiểm lại /ready, /health.version và inference. Auto-deploy hiện Off; kiểm lại trạng thái sau rollback. Chưa chủ động rollback production vì deploy mới đang hoạt động tốt.

Nếu vận hành Docker host riêng, mẫu compose.production.yaml và deploy/remote.sh vẫn có sẵn: pull digest mục 9, kiểm health/inference và phục hồi digest trước nếu thất bại. Mẫu host SSH chưa được triển khai trong công việc này.

## 11. Lỗi đã gặp và cách xử lý

Docker API permission denied: shell sandbox không truy cập được named pipe Docker Desktop. Kiểm tra Engine ở phiên có quyền phù hợp; không sửa bảo mật pipe toàn hệ thống. Docker Desktop phải đang chạy Linux engine.

Directory name invalid: workspace cũ D:\Codex\Bai2_CD không tồn tại. Dùng đường dẫn thực tế D:\Codex\BTTHCDTTNT. Không tạo dự án mới vào đường dẫn cũ hoặc ghi đè dữ liệu.

Git báo must be run in a work tree: trong môi trường này, dùng checkout độc lập tmp/cicd-release hoặc chỉ rõ --git-dir và --work-tree khi cần. Không xóa .git hay reset thay đổi để xử lý.

HTTP 403 khi tải legalcode.en.txt: lần build đầu đã tải và export weights, nhưng thất bại ở bước tải văn bản license. Đã thay bằng license gốc từ repository Creative Commons, lưu nguồn commit và checksum tại licenses/SOURCE.md. Image không còn phụ thuộc request đó khi build.

Model chưa ready: /health có thể trả 200 trong khi model_ready=false. Dùng /ready để kiểm model và smoke để thực thi thật. Kiểm manifest, checksum, revision và log Docker. Không đổi nhãn/threshold để làm test qua.

Port/container name đã dùng: chọn cổng/name khác hoặc dừng đúng container thử của mình. 415: gửi WAV/FLAC raw body với Content-Type đúng. 422: audio không decode được, quá ngắn, quá im lặng hoặc vi phạm giới hạn. 429: server đang bận hoặc vượt rate limit; thử lại sau.

Lỗi bash unexpected end of file khi kiểm qua pipe Windows: gửi bytes LF thay vì để subprocess chuyển input thành CRLF; .gitattributes giữ script .sh là LF trong checkout Linux.

CI lần đầu thiếu test_pcm_capture.cjs trên nhánh deploy: đã bổ sung tệp test từ workspace. Audit lần đầu còn thấy __pycache__: đã siết lại exclude bên trong từng thư mục và build lại, không chỉ bỏ qua lỗi audit.

Push unauthorized hoặc insufficient_scope: xác minh namespace, repository và quyền PAT. Không in token ra log. Actions không có secret: cấu hình đúng tên, event PR không được publish. Q4 yêu cầu ORT tương thích; bản đã chọn là 1.20.1.

TestClient có cảnh báo deprecation httpx trên phiên Starlette hiện tại; bộ test vẫn pass. Cần theo dõi nâng cấp tương thích riêng, không tự bỏ test để che cảnh báo.

## 12. Kết quả kiểm chứng thực tế

CI phát hành: THÀNH CÔNG, https://github.com/nqming/voicescope/actions/runs/41185814386. Tag Git v0.2.0 trỏ source a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd. Tests, build, hardened container, inference, audit, login và push đều thành công.

- Public repository: https://hub.docker.com/r/qminh19/voicescope. Tags v0.2.0, latest và sha-a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd cùng digest.
- Registry digest: sha256:29fe6d6ec3aea079af51f52fdf7cd10acad9bc12d006d97cabc7d540cdac4d95. Đây là digest đã publish và pull công khai, không phải ID bản build local cũ.
- Pull ẩn danh: PASS, Docker config riêng trống, không có credential/helper; không logout phiên đang dùng.
- Image tải từ registry: linux/amd64, 833.850.217 bytes (khoảng 795 MiB); OCI revision và /health.version khớp source SHA.
- Container UID 10001, read-only, tmpfs /tmp, drop capabilities, no-new-privileges. Model sẵn sàng, HTTP và ONNX inference đều pass.
- Câu Windows TTS tổng hợp 5,368 giây: fake, fake_score 0,99997365; expected-label=fake pass. Sin 2 giây chạy được. Đây là kiểm thực thi, không phải benchmark accuracy.
- Payload audit sạch: không có torch, audio, token hoặc __pycache__ trong /app. Model card, notice, license và manifest được giữ. Weights 89.730.755 bytes, SHA256 66a094e0d039c899e07fd08f8c3ff6ecf24145ce8bf5f53a3d23e25c5775f4f5 khớp manifest.
- Test đã xác minh trước đó: Windows 25 passed/1 skipped, Linux 23 passed/2 skipped, PCM test pass. Compose và bash -n hợp lệ.

GitHub Actions đã có DOCKERHUB_TOKEN mã hóa và DOCKERHUB_USERNAME=qminh19. Token không nằm trong source, image, log bàn giao hay tài liệu. Lỗi API tạo repository ban đầu đã xử lý bằng endpoint Docker Hub hiện hành; repository public đã được xác minh sau đó.

Báo cáo nằm tại docs/cicd-verification.json và artifacts/public-*.json. Audio TTS chỉ ở tmp/; không dùng hay upload bản ghi microphone riêng của người dùng.

Deploy Render: ĐÃ LIVE, deploy dep-dbiqqt142hec73b8nrm0, source a8a29e7fb422fab1cda54bc16e43e0e4f396f2dd. HTTP/readiness và TTS inference pass, điểm khớp container public. Gói Free và URL cũ được giữ; auto-deploy vẫn Off. Render build lại cùng source từ Git, không pull image Docker Hub. Đã chuẩn bị hướng dẫn rollback nhưng chưa thực hiện rollback production.

## 13. Giới hạn và việc cần thêm cho production

Model có thể false positive/false negative; chưa có bằng chứng đủ để bảo đảm mọi giọng nói/ngôn ngữ/thiết bị. Test sin và vài mẫu benchmark chỉ kiểm thực thi và regression. Cần tập held-out đủ lớn, calibration, đo chất lượng theo thiết bị/ngôn ngữ và kiểm drift.

Cần bổ sung quét CVE/SBOM và ký image theo chính sách vận hành; lockfile kèm hash cho toàn bộ dependency bắc cầu; quy trình cập nhật base digest và action SHA. Chưa thực hiện kiểm thử tải, đo RAM peak hay xác minh GPU/ARM64.

API hiện dùng một worker và giới hạn request theo process; production cần gateway/rate limit chung, TLS, auth nếu phù hợp, quan sát lỗi và hiệu năng không log audio, giới hạn tài nguyên và timeout tại reverse proxy. Không coi liveness là chất lượng model. Không dùng kết quả như kết luận giám định.

Phạm vi bàn giao đã hoàn tất: CI/build/publish tự động qua GitHub Actions, pull công khai, triển khai thủ công qua kết nối Render và kiểm sau deploy. Những lần phát hành tiếp theo cần promote đúng release commit, cập nhật VOICESCOPE_VERSION và deploy theo mục 10; auto-deploy chưa được bật. Không coi CD hiện tại là tự động từ mỗi push main đến production.

Nguồn kỹ thuật chính thức để tra cứu thêm:

- Docker GitHub Actions: https://docs.docker.com/build/ci/github-actions/
- GitHub secrets: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Docker image digest: https://docs.docker.com/reference/cli/docker/image/pull/
- NII model và giấy phép: https://huggingface.co/nii-yamagishilab/wav2vec-small-anti-deepfake
- Creative Commons: https://creativecommons.org/licenses/by-nc-sa/4.0/
