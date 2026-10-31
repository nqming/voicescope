"""ONNX CPU adapter for NII AntiDeepfake (CC BY-NC-SA 4.0)."""
import hashlib
import io
import json
import os
import time
from pathlib import Path
import numpy as np
from .audio import decode


class AntiDeepfakeService:
    def __init__(self,cfg):
        self.cfg=cfg;self.model=None;self.status='load_error';self.error=None
        self.model_name='NII AntiDeepfake Wav2Vec2-Small Q4'
        try:
            import onnxruntime as ort
            folder=Path(os.getenv('VOICESCOPE_ANTIDEEPFAKE_DIR','/opt/models/antideepfake'))
            metadata=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            path=folder/'model_q4.onnx'
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
            if (digest.hexdigest()!=metadata['sha256'] or metadata['labels']!=['fake','real'] or
                metadata['revision']!='9a13264b5dcc827a8d5a4f8e01fccefa392f886b'):
                raise ValueError('Invalid model provenance/checksum')
            options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
            options.enable_cpu_mem_arena=False;options.enable_mem_pattern=False
            options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            self.model=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
            self.status='ready'
        except Exception as exc:
            self.error=type(exc).__name__

    @property
    def ready(self):
        return self.status=='ready' and self.model is not None

    def predict(self,data):
        if not self.ready:raise ValueError('Chưa nạp được model AntiDeepfake.')
        if len(data)>self.cfg.max_upload_bytes:raise ValueError('Tệp vượt giới hạn kích thước.')
        begin=time.perf_counter();wave,sr=decode(io.BytesIO(data),self.cfg)
        if len(wave)<sr:raise ValueError('Hãy ghi ít nhất 1 giây; nên nói liên tục từ 3–6 giây.')
        if float(np.sqrt(np.mean(wave*wave)))<1e-5:raise ValueError('Âm thanh quá nhỏ hoặc chỉ có im lặng.')
        prep=time.perf_counter();scores=[];weights=[]
        for start in range(0,len(wave),96000):
            chunk=wave[start:start+96000];weight=len(chunk)
            if len(chunk)<16000 and start:chunk=wave[-96000:]
            # Official NII preprocessing uses layer_norm over the waveform.
            x=((chunk-chunk.mean())/np.sqrt(chunk.var()+1e-5)).astype('float32')
            logits=self.model.run(['logits'],{'input_values':x[None,:]})[0][0]
            probabilities=np.exp(logits-logits.max());probabilities/=probabilities.sum()
            scores.append(float(probabilities[0]));weights.append(weight)
        score=float(np.average(scores,weights=weights));finish=time.perf_counter()
        if not np.isfinite(score):raise ValueError('Mô hình trả điểm không hợp lệ.')
        return {'label':'fake' if score>=.5 else 'real','fake_score':score,'threshold':.5,
                'duration_seconds':len(wave)/sr,'temporal_scores':None,'suspicious_segments':[],
                'scope':'clip','aggregation':'duration_weighted_window_mean','spectrogram_mapping':[],
                'model':self.model_name,'license':'CC-BY-NC-SA-4.0',
                'timing_ms':{'preprocessing':(prep-begin)*1000,'model':(finish-prep)*1000,
                             'server_compute':(finish-begin)*1000},
                'notice':'Model nghiên cứu NII AntiDeepfake (CC BY-NC-SA 4.0), bản Q4. Điểm chưa hiệu chuẩn; có thể báo nhầm, không phải kết luận giám định.'}
