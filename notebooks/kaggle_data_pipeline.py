# %% [markdown]
# VoiceScope — pipeline dữ liệu trên Kaggle
# Chỉ tiếp nhận/import/QC/chuẩn hóa/phân đoạn/đóng gói. Không train hoặc suy luận.
# Add Input: ASVspoof 2019 LA đã giải nén. Bật Internet nếu lấy source từ GitHub.
# Kaggle là môi trường cloud: chỉ gắn dữ liệu bạn được phép sử dụng tại đây.
# Giữ notebook/dataset private nếu chưa có quyền công bố audio và metadata đầu ra.
# Không có dữ liệu/consent hoặc metric giả được điền vào notebook.

# %%
# Ô 1 — Thư viện và thư mục output
import sys, json, logging, importlib.util, subprocess
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

missing = [name for name in ("numpy", "scipy", "soundfile")
           if importlib.util.find_spec(name) is None]
if missing:
    subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=True)

import numpy as np
import scipy
import soundfile as sf
WORK = Path("/kaggle/working/voicescope")
WORK.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO)
print({"python": sys.version.split()[0], "numpy": np.__version__,
       "scipy": scipy.__version__, "soundfile": sf.__version__})

# %%
# Ô 2 — Nạp đúng mã nguồn đã nộp GitHub, không tải dataset/weights
# Nếu repo private/Internet tắt: gắn source đã giải nén bằng Add Input và điền
# đường dẫn thư mục chứa voicescope/ vào SOURCE_INPUT. Không đặt token vào code.
SOURCE_INPUT = ""  # Ví dụ /kaggle/input/voicescope-source/voicescope-...
SOURCE_COMMIT = "5c83445052238e12b8d75aeac3e7d97af66ff101"

if SOURCE_INPUT:
    CODE = Path(SOURCE_INPUT)
else:
    import io, urllib.request, zipfile, hashlib
    CODE = WORK / "source" / SOURCE_COMMIT
    required = ["__init__.py", "config.py", "audio.py", "manifest.py",
                "prepare.py", "collect.py", "import_asvspoof.py"]
    if not all((CODE / "voicescope" / name).is_file() for name in required):
        url = f"https://codeload.github.com/nqming/voicescope/zip/{SOURCE_COMMIT}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                archive = response.read(10_000_001)
        except Exception as exc:
            raise RuntimeError("Không lấy được source. Bật Internet hoặc gắn source bằng Add Input và điền SOURCE_INPUT.") from exc
        if len(archive) > 10_000_000:
            raise RuntimeError("Source archive vượt giới hạn 10 MB.")
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for name in required:
                matches = [n for n in bundle.namelist() if n.endswith(f"/voicescope/{name}")]
                if len(matches) != 1:
                    raise RuntimeError(f"Source thiếu hoặc trùng module {name}.")
                target = CODE / "voicescope" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(matches[0]))
    # Ghi checksum những module thực sự được sử dụng, kể cả khi dùng lại source cache.
if not (CODE / "voicescope" / "prepare.py").is_file():
    raise RuntimeError("SOURCE_INPUT cần trỏ thư mục chứa voicescope/prepare.py.")
sys.path.insert(0, str(CODE))
from voicescope.config import Config
from voicescope.collect import ingest_clip
from voicescope.import_asvspoof import import_la
from voicescope.prepare import prepare
from voicescope.manifest import read_manifest, audit_splits, fingerprint
from voicescope.audio import log_mel
print("Đã nạp source từ:", CODE)

# %%
# Ô 3 — Chọn input và cấu hình. Chỉ thay quyền sau khi bạn tự kiểm tra thực tế.
INPUT = Path("/kaggle/input")
print("Input đã gắn:", [p.name for p in INPUT.iterdir() if p.is_dir()])
LA_ROOT = ""  # Để tự tìm; hoặc điền /kaggle/input/<dataset>/LA
if not LA_ROOT:
    found = sorted({p.parent for p in INPUT.rglob("ASVspoof2019_LA_cm_protocols") if p.is_dir()})
    if len(found) != 1:
        raise RuntimeError(f"Tìm thấy {len(found)} thư mục LA. Gắn LA đã giải nén và điền LA_ROOT cụ thể.")
    LA_ROOT = str(found[0])
LA_ROOT = Path(LA_ROOT).resolve()
if not LA_ROOT.is_relative_to(INPUT.resolve()):
    raise ValueError("LA_ROOT phải nằm trong input đã gắn.")

RIGHTS_CONFIRMED = False
RIGHTS_REF = ""  # Mã hồ sơ bạn đã kiểm tra license/content terms, không ghi PII
LIMIT_PER_CLASS = 10  # 10 mỗi nhãn mỗi split = tối đa 60 clip để chạy thử; None để import toàn bộ
AUGMENT_NOISE = False
cfg = Config(seed=42, peak_normalize=False)
run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
RUN = WORK / "runs" / run_id
RUN.mkdir(parents=True)
provenance = {"source_commit": SOURCE_COMMIT if not SOURCE_INPUT else "user_supplied_source",
              "module_sha256": {name: fingerprint(CODE / "voicescope" / name)
                                for name in ("audio.py", "manifest.py", "prepare.py", "import_asvspoof.py")},
              "config": cfg.to_dict(), "limit_per_class": LIMIT_PER_CLASS,
              "scope": "data_pipeline_only; no training or quality metrics"}
(RUN / "notebook-provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
print("LA root:", LA_ROOT)
print("Output version:", RUN)

# %%
# Ô 4 — Tiếp nhận ASVspoof từ protocol; giữ split official, không tự xác nhận quyền
if RIGHTS_CONFIRMED and not RIGHTS_REF.strip():
    raise ValueError("Cần điền RIGHTS_REF sau khi đã kiểm tra quyền thực tế.")
import_report = import_la(
    root=LA_ROOT, output=RUN / "imported",
    rights_ref=RIGHTS_REF.strip() if RIGHTS_CONFIRMED else None,
    limit_per_class=LIMIT_PER_CLASS,
)
print(json.dumps({k: import_report[k] for k in
                 ("rows", "rejected", "rights_review_required", "counts", "scope")}, indent=2))

# %%
# Ô 5 — QC, mono 16k PCM16, energy segmentation, optional noise, versioned packaging
if not RIGHTS_CONFIRMED or not RIGHTS_REF.strip():
    raise RuntimeError("Manifest đang pending. Chỉ sau khi có quyền thật: sửa RIGHTS_CONFIRMED/RIGHTS_REF và chạy lại từ ô 3.")
process_report = prepare(
    manifest=RUN / "imported" / "manifest.jsonl", root=LA_ROOT,
    output=RUN / "processed", cfg=cfg, augment=AUGMENT_NOISE,
)
if process_report["accepted_segments"] == 0:
    raise RuntimeError("Không còn đoạn hợp lệ. Xem processed/rejects.jsonl.")
print(json.dumps(process_report, indent=2, ensure_ascii=False))

# %%
# Ô 6 — Audit split, thống kê dữ liệu và kiểm tra đầu ra thực tế
rows = read_manifest(RUN / "processed" / "manifest.jsonl")
audit_splits(rows)
counts = Counter((r["split"], r["label"], r["variant"]) for r in rows)
for key, count in sorted(counts.items()):
    print(key, "segments:", count)
print("Tổng giây các đoạn (kể cả biến thể):", round(sum(r["duration"] for r in rows), 2))
for row in rows:
    info = sf.info(RUN / "processed" / row["path"])
    assert info.samplerate == 16000 and info.channels == 1 and info.subtype == "PCM_16"
    assert row["end_seconds"] >= row["start_seconds"]
reject_file = RUN / "processed" / "rejects.jsonl"
rejects = [json.loads(line) for line in reject_file.read_text(encoding="utf-8").splitlines() if line]
print("Lý do reject:", dict(Counter(r["reason"] for r in rejects)))
print("Đã xác minh định dạng và audit nhóm của output; chưa nghe/rà soát thủ công toàn bộ.")

# %%
# Ô 7 — Kiểm tra log-Mel và mapping thời gian, không phân loại Real/Fake
first = rows[0]
wave, sr = sf.read(RUN / "processed" / first["path"], dtype="float32")
mel, centers = log_mel(wave, cfg)
assert mel.shape[0] == 80 and mel.shape[1] == len(centers) and np.isfinite(mel).all()
absolute_centers = first["start_seconds"] + centers
print({"log_mel_shape": mel.shape, "hop_seconds": cfg.hop_length / sr,
       "first_frame_center_in_original_seconds": float(absolute_centers[0]),
       "padding_note": "last STFT frame may include right padding; no temporal fake score"})

# %%
# Ô 8 — Archive metadata/report; không tự đưa audio vào file chia sẻ
import zipfile
summary = {"input_clips": import_report["rows"],
           "accepted_segments": len(rows), "rejected_clips": len(rejects),
           "dataset_subset": LIMIT_PER_CLASS is not None,
           "model_status": "not_trained", "metrics": None}
(RUN / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
package = RUN / "metadata-reports.zip"
include = ["summary.json", "notebook-provenance.json", "imported/import-report.json",
           "processed/manifest.jsonl", "processed/rejects.jsonl",
           "processed/split-plan.jsonl", "processed/prepare-report.json"]
with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for relative in include:
        bundle.write(RUN / relative, arcname=relative)
print("Report archive:", package)
print("Audio đã xử lý vẫn ở:", RUN / "processed" / "audio")
print("Kiểm tra quyền công bố trước khi Save Version/public notebook hoặc outputs.")

# %% [markdown]
# Dữ liệu riêng / TTS / VC (tùy chọn)
# Kaggle không thu microphone của máy cá nhân bằng sounddevice. Ghi âm có đồng ý
# trên máy local bằng voicescope.collect record, rồi chỉ gắn audio lên cloud nếu
# được phép. Dùng ingest_clip(file, collection_root, metadata, cfg) để nhận file
# đã gắn, với metadata thật: clip_id, speaker_id, source_id, label, method,
# device/channel, consent_status=granted, consent_ref, origin=private, license,
# is_test_fixture=False. Xem template examples/collection.*.example.json trên GitHub.
# TTS/VC được tạo trước bằng công cụ và giọng nguồn có quyền, giữ parent/source và
# related_speaker_ids. Không gán noise thành fake. Không tự gọi dịch vụ TTS/VC.
# Vietnam-Celeb chỉ là phần real; notebook này chưa có importer riêng cho corpus đó.
# Không báo cáo accuracy/F1/EER hoặc chất lượng mô hình từ notebook dữ liệu này.
