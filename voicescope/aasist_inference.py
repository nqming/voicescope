"""CPU inference for official NAVER AASIST-L; classes: spoof=0, bonafide=1."""
import hashlib
import io
import os
import time
from pathlib import Path
import numpy as np
from .audio import decode

WEIGHTS_SHA256 = '814331d088032bb4c3fa61cc014789eadeed464209dd094ab3a2dd6ffbdce27a'


class AASISTService:
    def __init__(self, cfg):
        self.cfg = cfg
        self.status = 'load_error'
        self.model = None
        self.error = None
        try:
            import torch
            from .aasist_model import Model
            from .aasist_config import MODEL_CONFIG
            path = Path(os.environ.get('VOICESCOPE_AASIST_WEIGHTS', '/opt/models/AASIST-L.pth'))
            if hashlib.sha256(path.read_bytes()).hexdigest() != WEIGHTS_SHA256:
                raise ValueError('Checkpoint checksum mismatch')
            torch.set_num_threads(1)
            model = Model(MODEL_CONFIG)
            model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True), strict=True)
            self.model = model.eval()
            self.torch = torch
            self.status = 'ready'
        except Exception as exc:
            self.error = type(exc).__name__

    @property
    def ready(self):
        return self.status == 'ready' and self.model is not None

    def predict(self, data):
        if not self.ready:
            raise ValueError('Chưa nạp được AASIST-L.')
        begin = time.perf_counter()
        if len(data) > self.cfg.max_upload_bytes:
            raise ValueError('Tệp vượt giới hạn kích thước.')
        wave, sr = decode(io.BytesIO(data), self.cfg)
        if float(np.max(np.abs(wave))) < .0001:
            raise ValueError('Âm thanh quá nhỏ hoặc chỉ có im lặng.')
        prepared = time.perf_counter()
        scores, weights = [], []
        # Match official evaluation's 64600-sample input and repeat padding.
        with self.torch.inference_mode():
            for start in range(0, len(wave), 64600):
                chunk = wave[start:start + 64600]
                weights.append(len(chunk))
                padded = np.tile(chunk, (64600 + len(chunk) - 1) // len(chunk))[:64600]
                _, logits = self.model(self.torch.from_numpy(padded.copy()).unsqueeze(0))
                scores.append(float(logits.softmax(-1)[0, 0]))
        score = float(np.average(scores, weights=weights))
        if not np.isfinite(score):
            raise ValueError('Mô hình trả điểm không hợp lệ.')
        finish = time.perf_counter()
        return {'label': 'fake' if score >= .5 else 'real', 'fake_score': score,
                'threshold': .5, 'duration_seconds': len(wave)/sr,
                'temporal_scores': None, 'suspicious_segments': [], 'scope': 'clip',
                'aggregation': 'duration_weighted_window_mean', 'spectrogram_mapping': [],
                'model': 'NAVER AASIST-L (ASVspoof 2019 LA pretrained)',
                'timing_ms': {'preprocessing': (prepared-begin)*1000,
                              'model': (finish-prepared)*1000, 'server_compute': (finish-begin)*1000},
                'notice': 'AASIST-L pretrained trên ASVspoof 2019 LA. Chưa đánh giá trên tiếng Việt; điểm chưa hiệu chuẩn, không phải kết luận giám định.'}
