# Dataset Visualization — 30/10/2026

Notebook: `notebooks/voicescope_dataset_visualization.ipynb`.
Tạo lại nguồn notebook bằng `python notebooks/build_visualization.py` (xóa outputs).

Notebook độc lập với VoiceScope/DINOv3, sử dụng numpy, pandas, matplotlib,
scipy và soundfile có sẵn trên Kaggle. Gắn một bản ASVspoof 2019 đã giải nén
bằng Add Input. Không gắn nhiều bản sao cùng protocol/audio.
Mặc định đọc `/kaggle/input`; local dùng biến `VOICESCOPE_EDA_INPUT`.

Toàn bộ protocol dùng cho đếm nhãn, attack và speaker overlap. Audio lấy mẫu
100 clip mỗi split/nhãn với seed 42, không suy rộng thống kê thời lượng ra toàn bộ
corpus. Không train, không sinh điểm chất lượng detector, không xuất audio.

Kiểm chứng local: chạy tuần tự cả 6 code cells thành công trên corpus thực;
121461 clip, 107 speaker, 3 split; 600 audio được đọc, không lỗi trong mẫu.
Không có speaker ID chung giữa các split. Biểu đồ kiểm tra nằm ở artifacts/eda-*.
ASVspoof LA không phải corpus tiếng Việt. Vietnam-Celeb chưa nằm trong notebook này.

Giao diện: điều hướng ngang; hai vùng nhập audio/kết quả; quy trình dữ liệu
được thu gọn bằng details/summary; giữ các ID thao tác và API hiện có.
DINOv3 giữ nguyên như hướng nghiên cứu, chưa có bằng chứng chất lượng detector.

Kiểm tra API/deploy: 9 tests passed (ngoài sandbox, do socketpair nội bộ bị chặn trong sandbox).
Kaggle public: https://www.kaggle.com/code/quminh19/voicescope-audio-deepfake-dataset-visualization
Bản Quick Save chứa outputs đã thực thi local; phiên Save & Run All đầu tiên còn chạy trên Kaggle.

## Render deployment

2026-10-30: giao diện mới đã deploy thành công tại https://voicescope-581u.onrender.com.
Branch `feature/deploy-voicescope`, commit `aa6211132b391c7a26ad38d117426df1b2b8cd64`.
Render báo Live; HTTP smoke đạt trang chủ, frontend routes, health, readiness và thiếu checkpoint trả 503 không có score.
Bằng chứng local: `artifacts/render-ui-smoke.json`. Model chưa cấu hình.
