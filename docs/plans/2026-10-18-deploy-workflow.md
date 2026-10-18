# VoiceScope: triển khai bằng một URL

Yêu cầu số 3 được đính chính là **link deploy hệ thống**, không phải latency.
Người dùng cho phép hoàn thiện cấu hình nếu chưa có tài khoản/quyền hosting.

## Intent
Giữ FastAPI phục vụ frontend cùng origin, đóng gói container Python, chuẩn bị Render
Blueprint, HTTPS do hosting quản lý; không đưa dataset/weights/secrets vào image/source.
Dataset đã có cục bộ; chưa có torch, DINOv3 repo hoặc detector checkpoint.

## Verification
Kiểm thử cấu hình PORT, API health/ready/missing checkpoint, CORS tùy chọn, Host,
security headers và rate limit; chạy lại tests. Chạy server và kiểm tra browser
gọi health thật. Smoke CLI chạy được với URL deploy sau khi hosting cấp URL.
Không coi test local là deployment public hoặc suy luận thật.

## Governance
Không đăng ký dịch vụ trả phí, không đọc/in secret, không đưa audio lên hosting,
không chạy huấn luyện tự động. Không có .git/remote/CLI hosting hiện tại.
Đã tìm connector: Render/Railway có trong catalog nhưng chưa cài/kết nối.
Sites dùng Workers không phù hợp Python/PyTorch; không thay API bằng bản mô phỏng.

## Thứ tự
1. Viết test thất bại cho vận hành deploy.
2. Thêm startup/config web, health readiness, headers/CORS/rate limit.
3. Dockerfile, .dockerignore allowlist, compose, render.yaml, smoke CLI.
4. README deploy/update/checkpoint/resource và trạng thái dữ liệu hiện tại.
5. Kiểm thử, browser QA local, ghi trạng thái URL trung thực.

## Đầu ra còn phụ thuộc bên ngoài
URL HTTPS public cần tài khoản hosting kết nối và repository nguồn được upload.
Docker build cần Docker engine (chưa có trên máy); suy luận thật cần checkpoint
đã train và môi trường PyTorch tương ứng. Benchmark giữ là công cụ tùy chọn.
