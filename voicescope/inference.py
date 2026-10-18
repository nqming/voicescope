import io
import time
from pathlib import Path
import numpy as np
from .audio import decode, speech_windows
from .config import Config


class InferenceService:
    def __init__(self,cfg):
        self.runtime=cfg; self.model=None; self.status='not_configured'; self.error=None
        if not cfg.checkpoint:
            return
        self.status='load_error'
        try:
            if not Path(cfg.checkpoint).is_file():
                raise ValueError('Checkpoint không tồn tại.')
            import torch
            from .model import Detector, PREPROCESS_VERSION
            state=torch.load(cfg.checkpoint,map_location='cpu',weights_only=True)
            if state.get('format_version')!=1 or state.get('trained') is not True or state.get('test_fixture_run') is not False:
                raise ValueError('Checkpoint không phải detector đã train trên dữ liệu nghiên cứu.')
            if state.get('preprocess_version')!=PREPROCESS_VERSION or state.get('labels')!=['real','fake']:
                raise ValueError('Checkpoint không tương thích preprocessing/labels.')
            if not state.get('provenance',{}).get('manifest_sha256'):
                raise ValueError('Checkpoint thiếu provenance dữ liệu.')
            values=state['config'] | {'dinov3_repo':cfg.dinov3_repo,'device':cfg.device,
                                      'checkpoint':cfg.checkpoint,'max_duration':cfg.max_duration,
                                      'max_upload_bytes':cfg.max_upload_bytes,
                                      'max_decoded_samples':cfg.max_decoded_samples}
            self.cfg=Config(**values)
            self.model=Detector(self.cfg,load_pretrained=False)
            self.model.load_state_dict(state['model'],strict=True)
            self.model.to(cfg.device).eval()
            self.torch=torch; self.provenance=state['provenance']; self.status='ready'
        except Exception as exc:
            self.model=None; self.error=type(exc).__name__

    @property
    def ready(self):
        return self.model is not None and self.status=='ready'

    def synchronize(self):
        if self.cfg.device.startswith('cuda'):
            self.torch.cuda.synchronize(self.cfg.device)

    def predict(self,data):
        if not self.ready:
            raise ValueError('Chưa cấu hình mô hình.')
        from .model import spectrogram_tensor
        if len(data)>self.cfg.max_upload_bytes:
            raise ValueError('Tệp vượt giới hạn kích thước.')
        self.synchronize(); begin=time.perf_counter()
        wave,sr=decode(io.BytesIO(data),self.cfg)
        tensors=[]; durations=[]; mappings=[]
        for start,end,part in speech_windows(wave,self.cfg):
            tensor,mapping=spectrogram_tensor(part,self.cfg)
            tensors.append(tensor); durations.append(end-start)
            mappings.append({'start_seconds':start,'end_seconds':end,**mapping})
        if not tensors:
            raise ValueError('Không có đoạn đủ mức âm/thời lượng để phân tích.')
        prep=time.perf_counter()-begin
        model_start=time.perf_counter(); scores=[]
        with self.torch.inference_mode():
            # Bounded batch size; no memory proportional to long batch on GPU.
            for tensor in tensors:
                logits=self.model(tensor.unsqueeze(0).to(self.cfg.device))
                scores.append(float(logits.softmax(-1)[0,1].cpu()))
        self.synchronize(); model_time=time.perf_counter()-model_start
        score=float(np.average(scores,weights=durations))
        if not np.isfinite(score):
            raise ValueError('Mô hình trả điểm không hợp lệ.')
        result={'label':'fake' if score>=self.cfg.threshold else 'real','fake_score':score,
                'threshold':self.cfg.threshold,'duration_seconds':len(wave)/sr,
                'temporal_scores':None,'suspicious_segments':[],
                'scope':'clip','aggregation':'duration_weighted_mean_of_window_probabilities',
                'spectrogram_mapping':mappings,
                'waveform':[float(np.max(np.abs(chunk))) for chunk in np.array_split(wave,min(600,len(wave)))],
                'timing_ms':{'preprocessing':prep*1000,'model':model_time*1000},
                'notice':'Điểm mô hình chưa được hiệu chuẩn; không phải kết luận giám định.'}
        result['timing_ms']['server_compute']=(time.perf_counter()-begin)*1000
        return result
