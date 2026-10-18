# Thu thập và quản lý dữ liệu

**Hướng dẫn nộp và mã mới:** xem [data-pipeline.md](data-pipeline.md) để chạy
`collect ingest/record`, importer ASVspoof 2019 LA và prepare theo từng khối pipeline.

Chưa có người tham gia, consent hoặc dữ liệu nào được xác nhận trong dự án.
Không coi giá trị trong manifest là bằng chứng pháp lý; người phụ trách phải quản lý hồ sơ quyền thực tế.

## 1. Thu thập tiếng thật

Lập phạm vi sử dụng, thời hạn lưu, cách rút đồng ý và quyền tạo giọng tổng hợp trước khi
ghi âm. Chỉ thu khi đã có sự đồng ý phù hợp. Cất hồ sơ danh tính/consent ở nơi bảo vệ riêng,
không trong Git; manifest chỉ lưu ID thay thế và `consent_ref` trỏ hồ sơ nội bộ.
Không ghi tên/số điện thoại/địa chỉ vào clip_id hoặc tên file.

Thu nhiều người nói, thiết bị, môi trường và nội dung phù hợp mục tiêu tiếng Việt.
Ghi thiết bị/kênh, ngôn ngữ, phương ngữ nếu được phép; tránh để nhãn luôn tương ứng
một thiết bị hay một nguồn duy nhất. Nghe và kiểm tra nhãn thủ công.

## 2. Tạo mẫu giả có quyền

Tự chọn công cụ TTS/VC đã kiểm tra điều kiện sử dụng và quyền giọng nguồn.
Không có script gọi dịch vụ ngoài hoặc tự clone giọng ở đây. Ghi `synthesis_method`
gồm công cụ/version/settings, nguồn văn bản nếu được phép, seed tạo âm nếu có.
Mẫu giả kế thừa `source_id` và lineage của bản thật liên quan. Với VC có người nói
nguồn và đích, điền cả hai vào `related_speaker_ids`; tương tự `related_source_ids`.
Không gán mỗi bản biến đổi một source mới độc lập để né grouping.

`source_id` là **họ nguồn/provenance liên quan**, không phải nhãn dataset chung cho
mọi clip và không phải tùy ý random ID cho từng phiên bản của cùng audio.
Dataset-wide ID dùng `dataset_name`. Định nghĩa grouping phải được quyết định trước split.

## 3. Manifest

Mỗi dòng JSON là một clip. Xem schema trong `examples/`. Các trường bắt buộc:

| Trường | Ý nghĩa |
|---|---|
| clip_id | ID duy nhất, ASCII chữ/số/_/- |
| speaker_id, source_id | Nhóm người nói và họ nguồn dùng chống leakage |
| label | real hoặc fake; Fake là positive trong đánh giá |
| synthesis_method | none nếu real; công cụ/version nếu fake |
| device, channel | Thiết bị và đường truyền thực tế, không đoán |
| sample_rate, duration | Số Hz và giây theo tệp gốc; pipeline kiểm tra lại |
| consent_status, consent_ref | pending/granted/licensed/withdrawn và hồ sơ quyền |
| path | Tương đối với `--root`, dùng `/`, cấm path ra ngoài root |
| origin, license | private/benchmark/test_fixture và quyền sử dụng |
| is_test_fixture | true chỉ cho kiểm thử; train/evaluate luôn từ chối |

Private chỉ chấp nhận `granted`. Benchmark cần `dataset_name`, `dataset_version`,
`license_url`; dùng `licensed` chỉ sau khi kiểm tra điều kiện bản tải cụ thể.
`pending`/`withdrawn` lưu được trong schema nhưng không được pipeline xử lý.
Khi rút đồng ý, phải gỡ dữ liệu khỏi run/dataset liên quan và xem xét huấn luyện lại;
v1 không tự thực hiện quy trình xóa hoặc machine unlearning.

## 4. Chia, xử lý và QC

Split trước biến đổi. Các quan hệ speaker/source/parent/VC tạo thành nhóm liên thông.
Nếu tất cả dữ liệu nằm trong một nhóm, dừng để thiết kế/thu thập thêm dữ liệu độc lập;
không ép tách clip cùng người nói. Để đánh giá cả generalization sang công cụ TTS chưa
thấy, phải có protocol giữ tool/source độc lập ngoài grouping hiện tại.

Prepare lưu split-plan trước xử lý. QC xem mức âm, clipping, duration, decode,
hash tệp và hash PCM sau chuẩn hóa. Duplicate bị reject; near-duplicate, bản dịch,
text trùng và bản codec khác nhau vẫn cần audit thêm. Metadata đầu vào sai schema
thì dừng toàn run để sửa; lỗi audio theo clip ghi trong `rejects.jsonl`.

Energy gate không biết phân biệt tiếng nói và tiếng ồn; phải nghe mẫu và kiểm tra
ảnh phổ trước dùng. Không ghép các đoạn thời gian xa nhau thành một đoạn mất mapping.
Biến thể có sẵn: white noise 20 dB, không thay thế mô phỏng thiết bị/codec/AFE thật.
Các NS/AGC/AEC/replay sau này phải ghi công cụ, version, thông số, quyền nguồn noise/RIR
và giữ split của bản gốc. Không sinh thêm dữ liệu test rồi chọn biến thể có kết quả đẹp.

## Benchmark tùy chọn

Phiên này không tải benchmark. Một lựa chọn được tài liệu hóa là
[ASVspoof 2021](https://www.asvspoof.org/index2021.html), có các nhánh LA/PA/DF.
Trang chính thức nêu Open Data Commons Attribution Licence và liên kết bản tải trên Zenodo.
Xem [DF release](https://zenodo.org/records/4835108) và
[ODC Attribution license](https://opendatacommons.org/licenses/by/1-0/) để đọc điều kiện;
đối chiếu bản tải/phụ lục cụ thể trước sử dụng. Không coi license dữ liệu là quyền
clone bất kỳ giọng nào ngoài phạm vi đã cấp.

Đặt benchmark trong `data/benchmarks/asvspoof2021/<version>/`, giữ official protocol
và file map nguồn để tránh lẫn dữ liệu ASVspoof 2019/2021 hoặc nguồn liên quan.
Đừng random re-split official test. Đã có importer **ASVspoof 2019 LA** trong
`voicescope.import_asvspoof`; **chưa có importer ASVspoof 2021**. Importer 2019 dùng
speaker proxy cho source grouping và ghi rõ giới hạn; cần file maps gốc trước khi
pooling benchmark liên quan. Quyền mặc định pending cho tới khi người dùng xác nhận.
Không hướng dẫn MLAAD trong v1 do chưa xác minh release/license cụ thể; không đoán license.
