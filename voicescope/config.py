import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class Config:
    sample_rate: int = 16000
    n_fft: int = 512
    win_length: int = 400
    hop_length: int = 160
    n_mels: int = 80
    image_size: int = 256
    window_seconds: float = 4.0
    max_duration: float = 120.0
    min_duration: float = 0.25
    max_upload_bytes: int = 20971520
    max_decoded_samples: int = 16000000
    vad_db: float = -45.0
    peak_normalize: bool = False
    seed: int = 42
    backbone: str = 'dinov3_vits16'
    freeze_backbone: bool = True
    dinov3_repo: str = ''
    backbone_weights: str = ''
    checkpoint: str = ''
    device: str = 'cpu'
    threshold: float = 0.5

    def __post_init__(self):
        if self.sample_rate != 16000:
            raise ValueError('Pipeline v1 yêu cầu sample_rate=16000.')
        if not 0 < self.hop_length <= self.win_length <= self.n_fft:
            raise ValueError('Yêu cầu 0 < hop <= win <= n_fft.')
        if self.image_size < 16 or self.image_size % 16:
            raise ValueError('image_size phải là bội số của 16.')
        if not 0 < self.min_duration <= self.window_seconds <= self.max_duration:
            raise ValueError('Thời lượng cấu hình không hợp lệ.')
        if not 0 < self.threshold < 1 or self.n_mels < 2 or self.max_upload_bytes < 1 or self.max_decoded_samples < 1:
            raise ValueError('Cấu hình không hợp lệ.')

    def to_dict(self):
        return asdict(self)


def load_config(path=None):
    values = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
    for key in ('dinov3_repo','backbone_weights','checkpoint','device'):
        value = os.getenv('VOICESCOPE_' + key.upper())
        if value is not None:
            values[key] = value
    return Config(**values)
