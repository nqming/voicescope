# Nộp mã pipeline dữ liệu

## Intent
Nộp branch GitHub với README chỉ rõ file thay đổi, mã thu thập/tiếp nhận audio,
import benchmark và xử lý theo pipeline.png. User hoãn training/model.

## Verification
Test consent trước mở microphone/copy, duplicate ID/hash, metadata/lineage,
protocol import và split, prepare/QC. Chạy một import metadata ASVspoof giới hạn
trên corpus thật, không assert quyền thay người dùng và không train. Chạy toàn bộ tests.

## Governance
Tạo branch feature riêng từ commit đang hoạt động d4e373e. Chỉ stage allowlist code,
docs và manifest ví dụ tổng hợp. Không audio, metadata cá nhân, archive, weights, secret.
Không commit ảnh/PDF nguồn chưa xác minh quyền. Push branch để review, không main.
Không upload dữ liệu thô hoặc tự gọi TTS/VC bên ngoài. Không mở microphone trong phiên này.

## Các bước
1. Viết tests RED cho collection/import.
2. Collection ingest/record local, metadata bắt buộc; optional sounddevice cho record.
3. ASVspoof2019 LA importer giữ official split, audit speaker grouping, quyền pending mặc định.
4. Bổ sung regression tests QC và báo cáo nộp, hướng dẫn pipeline, bảng file trong README.
5. Kiểm thử, review staged diff/secret/data, commit/push branch và đưa link nộp thật.
