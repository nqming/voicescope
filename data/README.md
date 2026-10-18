# Dữ liệu cục bộ

Chưa có dữ liệu private tự thu được xác nhận. ASVspoof 2019 LA và Vietnam-Celeb
đã được người dùng tải vào `benchmarks/`; chưa coi là đã import/QC/train.
Tự tạo `private/raw/`, `private/manifest.jsonl`,
`processed/v001/` khi đã có nguồn âm thanh và quyền sử dụng. `.gitignore` bỏ qua
toàn bộ nội dung `data/`, trừ tài liệu này. Không dùng `git add -f` cho audio/metadata riêng.
Ví dụ không có audio nằm trong `examples/manifest.example.jsonl`.

Benchmark công khai phải nằm riêng ở `data/benchmarks/<dataset>/<version>/`,
ghi `origin=benchmark`, nguồn và license; không gọi là private data.
