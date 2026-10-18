"""Local consent-aware collection: ingest recordings or record a microphone clip."""
import argparse
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import os
import shutil
import sys
import tempfile
import numpy as np
import soundfile as sf
from .config import load_config
from .manifest import validate, read_manifest, write_manifest, safe_path, fingerprint

LOG=logging.getLogger(__name__)


def checked_metadata(metadata):
    # Validate rights/IDs before filesystem writes or opening the microphone.
    row={**metadata,'path':'raw/validation.wav','sample_rate':16000,'duration':1.0}
    validate(row)
    if row['origin']=='benchmark':
        raise ValueError('Dùng importer benchmark, không ghi nhầm vào private collection.')
    return row


@contextmanager
def collection_lock(root):
    lock=root/'.collection.lock'
    try:
        handle=lock.open('x')
    except FileExistsError as exc:
        raise ValueError('Collection đang được ghi; kiểm tra tiến trình trước khi xóa lock cũ.') from exc
    try:
        handle.close()
        yield
    finally:
        lock.unlink(missing_ok=True)


def ingest_clip(source,root,metadata,cfg):
    row=checked_metadata(metadata)
    source=Path(source)
    if source.suffix.lower() not in {'.wav','.flac'} or source.stat().st_size>cfg.max_upload_bytes:
        raise ValueError('Chỉ tiếp nhận WAV/FLAC trong giới hạn kích thước.')
    info=sf.info(source)
    if (info.format not in {'WAV','WAVEX','FLAC'} or not 8000<=info.samplerate<=192000 or
        not 1<=info.channels<=8 or info.frames*info.channels>cfg.max_decoded_samples or
        not cfg.min_duration<=info.duration<=cfg.max_duration):
        raise ValueError('Audio đầu vào ngoài giới hạn cấu hình.')
    # Preserve original bytes; full QC/normalization is the prepare stage.
    digest=fingerprint(source)
    row.update(path=f"raw/{row['clip_id']}{source.suffix.lower()}",sample_rate=info.samplerate,
               duration=info.duration,sha256=digest,channels=info.channels,
               capture_method=metadata.get('capture_method','local_file_ingest'))
    validate(row)
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    with collection_lock(root):
        manifest=root/'manifest.jsonl'
        rows=read_manifest(manifest,allow_fixtures=True) if manifest.exists() else []
        if any(r['clip_id']==row['clip_id'] or r.get('sha256')==digest for r in rows):
            raise ValueError('clip_id hoặc audio trùng trong collection.')
        target=safe_path(root,row['path']); target.parent.mkdir(parents=True,exist_ok=True)
        created=False
        staging=root/'manifest.jsonl.tmp'
        try:
            with source.open('rb') as src, target.open('xb') as dst:
                created=True
                shutil.copyfileobj(src,dst)
            if fingerprint(target)!=digest:
                raise ValueError('Nguồn audio thay đổi trong khi copy; hãy thử lại.')
            write_manifest(staging,rows+[row])
            os.replace(staging,manifest)
        except BaseException:
            if created: target.unlink(missing_ok=True)
            staging.unlink(missing_ok=True)
            raise
    LOG.info('Collected clip %s (local only)',row['clip_id'])
    return row


def record_clip(root,metadata,seconds,cfg,device=None,recorder=None):
    checked_metadata(metadata)
    if metadata['label']!='real':
        raise ValueError('Ghi microphone chỉ đăng ký nhãn real; nhập TTS/VC qua ingest.')
    if not cfg.min_duration<=seconds<=cfg.max_duration:
        raise ValueError('Thời lượng ghi ngoài giới hạn.')
    if recorder is None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise ValueError('Cần cài requirements-collection.txt để ghi microphone.') from exc
        def recorder(frames,samplerate,device):
            try:
                result=sd.rec(frames,samplerate=samplerate,channels=1,dtype='float32',device=device)
                status=sd.wait()
                if status: raise ValueError('Microphone bị overflow; ghi lại mẫu.')
                return result
            finally:
                sd.stop()
    wave=np.asarray(recorder(int(seconds*cfg.sample_rate),cfg.sample_rate,device),dtype=np.float32)
    if wave.shape not in {(int(seconds*cfg.sample_rate),),(int(seconds*cfg.sample_rate),1)} or not np.isfinite(wave).all():
        raise ValueError('Microphone trả dữ liệu không hợp lệ.')
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='capture-',dir=root) as temp:
        path=Path(temp)/'capture.wav'
        sf.write(path,wave,cfg.sample_rate,subtype='PCM_16')
        return ingest_clip(path,root,{**metadata,'capture_method':'microphone'},cfg)


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='configs/default.json')
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('ingest','record'):
        p=sub.add_parser(command)
        p.add_argument('--root',required=True)
        p.add_argument('--metadata',required=True,help='JSON quyền/ID/label, không có danh tính trực tiếp')
        if command=='ingest': p.add_argument('--file',required=True)
        else:
            p.add_argument('--seconds',type=float,default=10)
            p.add_argument('--device',type=int)
            p.add_argument('--confirm-recording',action='store_true',required=True,
                           help='Xác nhận được phép ghi âm những người tham gia')
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO)
    metadata=json.loads(Path(args.metadata).read_text(encoding='utf-8'))
    cfg=load_config(args.config)
    if args.command=='ingest': row=ingest_clip(args.file,args.root,metadata,cfg)
    else: row=record_clip(args.root,metadata,args.seconds,cfg,args.device)
    print(json.dumps({'clip_id':row['clip_id'],'path':row['path'],'duration':row['duration']},ensure_ascii=False))


if __name__=='__main__': main()
