import argparse
import importlib.metadata
import json
import platform
import time
from pathlib import Path
import numpy as np
from .config import load_config
from .inference import InferenceService
from .manifest import safe_path, fingerprint
from .evaluate import test_rows


def main():
    p=argparse.ArgumentParser(description='Warm benchmark of local server inference, excluding HTTP transport.')
    p.add_argument('--manifest',required=True); p.add_argument('--root',required=True)
    p.add_argument('--config',default='configs/default.json'); p.add_argument('--output',required=True)
    p.add_argument('--warmup',type=int,default=3); p.add_argument('--repeats',type=int,default=10)
    p.add_argument('--limit',type=int,default=20)
    args=p.parse_args(); cfg=load_config(args.config)
    if min(args.warmup,args.repeats,args.limit)<1: raise ValueError('Các tham số phải dương.')
    out=Path(args.output)
    if out.exists(): raise ValueError('Output đã tồn tại.')
    service=InferenceService(cfg)
    if not service.ready: raise SystemExit('Chưa cấu hình checkpoint hợp lệ; không đo latency.')
    rows=sorted(test_rows(args.manifest,args.root,service),key=lambda r:r['clip_id'])
    rng=np.random.default_rng(cfg.seed)
    selected=rng.choice(len(rows),min(args.limit,len(rows)),replace=False)
    samples=[(rows[i],safe_path(args.root,rows[i]['path']).read_bytes()) for i in selected]
    for i in range(args.warmup): service.predict(samples[i%len(samples)][1])
    trials=[]
    for _ in range(args.repeats):
        for i in rng.permutation(len(samples)):
            row,data=samples[i]; service.synchronize(); start=time.perf_counter()
            result=service.predict(data); service.synchronize()
            trials.append({'clip_id':row['clip_id'],'audio_duration_seconds':result['duration_seconds'],
                           'file_bytes':len(data),**result['timing_ms'],
                           'end_to_end_server_ms':(time.perf_counter()-start)*1000})
    timing_keys=['preprocessing','model','server_compute','end_to_end_server_ms']
    summary={k:{'median_ms':float(np.median([t[k] for t in trials])),
                'p95_ms':float(np.percentile([t[k] for t in trials],95))} for k in timing_keys}
    torch=service.torch
    report={'summary':summary,'trials':trials,'warmup':args.warmup,'repeats':args.repeats,
            'n_files':len(samples),'seed':cfg.seed,'device':cfg.device,
            'cpu':platform.processor(),'platform':platform.platform(),'python':platform.python_version(),
            'gpu':torch.cuda.get_device_name(cfg.device) if cfg.device.startswith('cuda') else None,
            'cuda_version':torch.version.cuda,'torch_threads':torch.get_num_threads(),
            'versions':{p:importlib.metadata.version(p) for p in ('torch','numpy','scipy','soundfile')},
            'checkpoint_sha256':fingerprint(cfg.checkpoint),'manifest_sha256':fingerprint(args.manifest),
            'scope':'warm single-request server compute; RAM input; excludes file read, model load, HTTP/network; CUDA synchronized'}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Đã lưu phép đo thực tế vào',out)


if __name__=='__main__': main()
