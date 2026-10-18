"""Import local ASVspoof 2019 LA CM protocols; never downloads audio."""
import argparse
from collections import Counter
import json
import logging
import sys
from pathlib import Path
import soundfile as sf
from .manifest import audit_splits, validate, write_manifest, safe_path, fingerprint

LOG=logging.getLogger(__name__)
PARTS=[('train','train.trn','train'),('dev','dev.trl','validation'),('eval','eval.trl','test')]


def import_la(root,output,rights_ref=None,limit_per_class=None,test_fixture=False):
    root=Path(root).resolve(); output=Path(output)
    if output.exists(): raise ValueError('Output đã tồn tại; chọn version mới.')
    if limit_per_class is not None and limit_per_class<1:
        raise ValueError('limit-per-class phải dương.')
    rows=[]; rejects=[]; protocols={}; seen=set()
    for directory,suffix,split in PARTS:
        protocol=root/'ASVspoof2019_LA_cm_protocols'/f'ASVspoof2019.LA.cm.{suffix}.txt'
        protocols[split]=fingerprint(protocol)
        counts=Counter()
        for line_number,line in enumerate(protocol.read_text(encoding='utf-8').splitlines(),1):
            fields=line.split()
            if len(fields)!=5: raise ValueError(f'Protocol {split} dòng {line_number} không có 5 trường.')
            speaker,clip,_,attack,label=fields
            if label not in {'bonafide','spoof'}:
                raise ValueError('Nhãn protocol không được hỗ trợ.')
            label='real' if label=='bonafide' else 'fake'
            if limit_per_class and counts[label]>=limit_per_class: continue
            # IDs are validated before deriving any file path.
            row={'clip_id':clip,'speaker_id':speaker,'source_id':f'asv2019_speaker_{speaker}',
                 'label':label,'synthesis_method':'none' if label=='real' else f'asvspoof2019_{attack}',
                 'attack_id':attack,'device':'not_provided','channel':'not_provided',
                 'sample_rate':16000,'duration':1.0,'consent_status':'licensed',
                 'consent_ref':rights_ref or 'PENDING_OPERATOR_LICENSE_REVIEW',
                 'origin':'test_fixture' if test_fixture else 'benchmark',
                 'license':'ODC-By-1.0; check bundled content terms',
                 'license_url':'https://zenodo.org/records/6906306',
                 'dataset_name':'ASVspoof2019_LA','dataset_version':'2019_release',
                 'is_test_fixture':test_fixture,'split':split,
                 'path':f'ASVspoof2019_LA_{directory}/flac/{clip}.flac',
                 'source_grouping':'speaker_proxy; original-recording file-map not imported'}
            validate(row)
            if clip in seen: raise ValueError('clip_id protocol bị trùng.')
            seen.add(clip)
            try:
                path=safe_path(root,row['path'])
                info=sf.info(path)
                if info.format!='FLAC': raise ValueError('Tệp không phải FLAC.')
                row.update(sample_rate=info.samplerate,duration=info.duration,channels=info.channels)
                validate(row)
            except (ValueError,OSError,RuntimeError):
                rejects.append({'clip_id':clip,'split':split,'reason':'missing_or_invalid_audio_header'})
                continue
            if not rights_ref: row['consent_status']='pending'
            rows.append(row); counts[label]+=1
        LOG.info('Imported %s: %s',split,dict(counts))
    audit_splits(rows)
    output.mkdir(parents=True)
    write_manifest(output/'manifest.jsonl',rows)
    write_manifest(output/'rejects.jsonl',rejects)
    report={'rows':len(rows),'rejected':len(rejects),'rights_review_required':not bool(rights_ref),
            'test_fixture_run':test_fixture,
            'root':str(root),'protocol_sha256':protocols,'limit_per_class_per_split':limit_per_class,
            'counts':dict(Counter(f"{r['split']}/{r['label']}" for r in rows)),
            'split_policy':'preserved_official_train_dev_eval',
            'source_grouping_limit':'speaker proxy only; audit original file maps before cross-dataset pooling',
            'scope':'header_and_protocol_import; not full decode/QC or model evaluation'}
    (output/'import-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,help='Thư mục LA chứa CM protocols và ba tập audio')
    parser.add_argument('--output',required=True)
    parser.add_argument('--rights-ref',help='Chỉ điền sau khi tự kiểm tra quyền/license; bỏ trống thì pending')
    parser.add_argument('--limit-per-class',type=int,help='Giới hạn mỗi nhãn ở mỗi split để kiểm tra importer')
    parser.add_argument('--test-fixture',action='store_true',help='Đánh dấu protocol/audio tổng hợp chỉ dùng kiểm thử, cấm train')
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO)
    report=import_la(args.root,args.output,args.rights_ref,args.limit_per_class,args.test_fixture)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['rows']: raise SystemExit('Không import được audio; xem rejects.jsonl.')


if __name__=='__main__': main()
