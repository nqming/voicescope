# Cơ sở nghiên cứu và phạm vi tái lập

Hai ảnh gốc được mở để đối chiếu trực tiếp. `pipeline.png` mô tả thu thập có đồng ý,
TTS/VC, metadata, mono 16 kHz WAV/PCM, mức âm, VAD, biến thể thiết bị/kênh và QC/split.
V1 cụ thể hóa split trước sinh/chọn biến thể theo yêu cầu chống leakage.
`design.png` có sidebar xanh đậm, đầu vào/dạng sóng bên trái, kết quả bên phải.
UI giữ bố cục, không chép số điểm hoặc đoạn đáng ngờ minh họa.

## Tài liệu thứ nhất

`068431-0288open.pdf`: Xiang Zhang, Ziyuan Zhao, Theodoros Tsiligkaridis,
Marinka Zitnik, **Self-Supervised Contrastive Pre-Training for Time Series via
Time-Frequency Consistency**, NeurIPS 2022, 16 trang trong bản địa phương.
[DOI](https://doi.org/10.52202/068431-0288),
[mã tác giả](https://github.com/mims-harvard/TFC-pretraining).

TF-C có time encoder và frequency encoder, hai projector vào không gian chung,
contrastive estimation và consistency giữa biểu diễn thời gian/tần số. Đầu vào
là time series và phổ rời rạc; không phải DINOv3 hay detector speech giả đã sẵn sàng.
Code hiện tại chưa cài objective contrastive hai nhánh; supervised DINOv3 là baseline
để nghiên cứu tiếp, không được gọi là TF-C reproduction.

## Tài liệu thứ hai

`2607.17761v2.pdf`: Jun Xue và cộng sự, **Time-Frequency Consistency Learning for
Robust Speech Deepfake Detection**, bản arXiv v2 ngày 28/07/2026, 9 trang địa phương.
[arXiv](https://arxiv.org/abs/2607.17761),
[repository được tác giả dẫn trong PDF](https://github.com/JunXue-tech/TFCL).

TFCL dùng clean/distorted speech khi train, attention soft alignment và ràng buộc
cấu trúc frequency, kết hợp classification loss. Các nhánh consistency không cần
ở inference. Bài nghiên cứu AEC → NS → AGC → VAD và các cấu hình SSL/AASIST;
đây không phải bằng chứng DINOv3 hiệu quả với audio tiếng Việt.
V1 dùng noise đơn giản để kiểm tra provenance của biến thể, chưa tái lập AFE WebRTC,
cross-attention/CKA hoặc các ablation trong bài. Các con số của bài không được ghi
thành kết quả của repository này.

## DINOv3

[Official implementation](https://github.com/facebookresearch/dinov3),
[license](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md),
[Hub backbone definitions](https://github.com/facebookresearch/dinov3/blob/main/dinov3/hub/backbones.py).
Đối chiếu identifier Hub, embedding size, local weights, `pretrained=False` để khởi
tạo kiến trúc khi restore full detector; resize và normalize theo hướng dẫn LVD.
Việc chuyển audio thành log-Mel là **thiết kế adapter của dự án**, không phải pipeline
audio được Meta xác nhận. Cần đánh giá domain gap, sample rate 16k làm mất tần số >8k,
ảnh resize làm giảm độ phân giải thời gian và window aggregation có thể bỏ sót chỉnh sửa ngắn.

Các thí nghiệm sau: frozen vs fine-tuned, waveform/audio SSL baseline, log-Mel settings,
cross-speaker/source/tool, AFE từng bước và clean/distorted consistency. Chỉ chạy sau
khi có dữ liệu/weights và protocol được chốt; tách validation khỏi test, báo cáo cả giới hạn.
