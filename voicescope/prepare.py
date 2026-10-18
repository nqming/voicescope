"""python -m voicescope.prepare --help"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import numpy as np
import soundfile as sf
from .audio import decode, quality, speech_windows
from .config import load_config
from .manifest import read_manifest, write_manifest, assign_splits, audit_splits, safe_path, fingerprint

LOG=logging.getLogger(__name__)


def prepare(manifest,root,output,cfg,allow_fixtures=False,augment=False):
    rows=read_manifest(manifest,allow_fixtures=allow_fixtures)
    output=Path(output)
    if output.exists():
        raise ValueError('Output đã tồn tại; chọn thư mục phiên bản mới, không ghi đè.')
    # Split raw metadata BEFORE decoding/segmentation/augmentations.
    if any('split' in r for r in rows):
        audit_splits(rows)
    else:
        rows=assign_splits(rows,cfg.seed)
    output.mkdir(parents=True); (output/'audio').mkdir()
    write_manifest(output/'split-plan.jsonl',rows)
    accepted=[]; rejected=[]; hashes=set()
    rng=np.random.default_rng(cfg.seed)
    for row in sorted(rows,key=lambda r:r['clip_id']):
        try:
            path=safe_path(root,row['path'])
            if path.stat().st_size>cfg.max_upload_bytes:
                raise ValueError('Tệp vượt giới hạn bytes.')
            info=sf.info(path)
            if info.samplerate!=row['sample_rate'] or abs(info.duration-row['duration'])>.05:
                raise ValueError('Metadata sample_rate/duration không khớp tệp.')
            audio,sr=decode(path,cfg)
            # PCM hash also catches identical audio in different containers.
            digest=hashlib.sha256(np.round(audio*32767).astype('<i2').tobytes()).hexdigest()
            if digest in hashes:
                raise ValueError('duplicate: audio chuẩn hóa trùng một mẫu đã gặp.')
            hashes.add(digest)
            segments=list(speech_windows(audio,cfg))
            if not segments:
                raise ValueError('Không có đoạn đủ mức âm/thời lượng; cần rà soát thủ công.')
            count=0
            for start,end,segment in segments:
                variants=[('clean',segment)]
                if augment:
                    rms=max(float(np.sqrt(np.mean(segment**2))),1e-8)
                    noisy=segment+rng.normal(0,rms/10,len(segment))
                    if np.max(np.abs(noisy))>=.999:
                        raise ValueError('Biến thể noise vượt biên PCM.')
                    variants.append(('noise20db',noisy.astype(np.float32)))
                for variant,wave in variants:
                    cid=f"{row['clip_id']}_s{count:04d}_{variant}"
                    relative=f'audio/{cid}.wav'
                    sf.write(output/relative,wave,sr,subtype='PCM_16')
                    accepted.append({**row,'clip_id':cid,'parent_clip_id':row['clip_id'],
                        'path':relative,'sample_rate':sr,'duration':len(wave)/sr,
                        'start_seconds':start,'end_seconds':end,
                        'variant':variant,'original_sha256':digest,
                        'sha256':fingerprint(output/relative),'quality':quality(wave)})
                count+=1
            if not count:
                raise ValueError('Không còn đoạn đủ dài.')
        except (ValueError,OSError,RuntimeError) as exc:
            # Roll back this clip's partial writes only inside output/audio.
            partial=[r for r in accepted if r['parent_clip_id']==row['clip_id']]
            for r in partial:
                safe_path(output,r['path']).unlink(missing_ok=True)
            accepted=[r for r in accepted if r['parent_clip_id']!=row['clip_id']]
            rejected.append({'clip_id':row['clip_id'],'reason':str(exc)})
            LOG.warning('Reject clip %s: %s',row['clip_id'],type(exc).__name__)
    audit_splits(accepted)
    write_manifest(output/'manifest.jsonl',accepted)
    write_manifest(output/'rejects.jsonl',rejected)
    report={'input':len(rows),'accepted_segments':len(accepted),'rejected':len(rejected),
            'seed':cfg.seed,'input_manifest_sha256':fingerprint(manifest),'config':cfg.to_dict(),
            'test_fixture_run':allow_fixtures,'augmentation':'white_noise_20db' if augment else 'none',
            'segmentation':'energy_gate_not_learned_vad',
            'splits':{s:sum(r['split']==s for r in accepted) for s in ('train','validation','test')}}
    (output/'prepare-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True); p.add_argument('--root',required=True)
    p.add_argument('--output',required=True); p.add_argument('--config',default='configs/default.json')
    p.add_argument('--augment-noise',action='store_true'); p.add_argument('--allow-test-fixtures',action='store_true')
    args=p.parse_args(); logging.basicConfig(level=logging.INFO)
    report=prepare(args.manifest,args.root,args.output,load_config(args.config),args.allow_test_fixtures,args.augment_noise)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['accepted_segments']:
        raise SystemExit('Không có audio được chấp nhận; xem rejects.jsonl.')


if __name__=='__main__':
    main()
