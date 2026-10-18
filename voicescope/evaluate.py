import argparse
import json
from pathlib import Path
import numpy as np
from .config import load_config
from .inference import InferenceService
from .manifest import safe_path, fingerprint
from .train import checked_rows, group_keys


def test_rows(manifest,root,service):
    rows=checked_rows(manifest,root)
    selected=[r for r in rows if r['split']=='test' and r.get('variant')=='clean']
    if not selected or {r['label'] for r in selected}!={'real','fake'}:
        raise ValueError('Test cần các clip clean thuộc cả hai nhãn.')
    used=set(service.provenance['training_and_validation_groups'])
    if used.intersection(group_keys(selected)):
        raise ValueError('Test trùng nhóm đã dùng train/validation của checkpoint.')
    return selected


def metrics(labels,scores,threshold):
    from sklearn.metrics import precision_recall_fscore_support,roc_auc_score,roc_curve,confusion_matrix
    predicted=np.asarray(scores)>=threshold
    precision,recall,f1,_=precision_recall_fscore_support(labels,predicted,average='binary',zero_division=0)
    fpr,tpr,_=roc_curve(labels,scores,drop_intermediate=False)
    fnr=1-tpr
    # Linear interpolation at the crossing; score ties handled by sklearn ROC.
    delta=fpr-fnr
    j=int(np.flatnonzero(delta>=0)[0]); i=max(0,j-1)
    weight=0.0 if i==j or delta[j]==delta[i] else -delta[i]/(delta[j]-delta[i])
    eer=float(fpr[i]+weight*(fpr[j]-fpr[i]))
    return {'precision_fake':float(precision),'recall_fake':float(recall),'f1_fake':float(f1),
            'roc_auc':float(roc_auc_score(labels,scores)),'eer_interpolated':eer,
            'confusion_matrix_real_fake':confusion_matrix(labels,predicted,labels=[0,1]).tolist(),
            'threshold':threshold,'level':'prepared_clip_segment; clean only; NOT speaker-level'}


def main():
    p=argparse.ArgumentParser(description='Evaluate held-out clean test segments, no fabricated results.')
    p.add_argument('--manifest',required=True); p.add_argument('--root',required=True)
    p.add_argument('--config',default='configs/default.json'); p.add_argument('--output',required=True)
    args=p.parse_args(); cfg=load_config(args.config)
    output=Path(args.output)
    if output.exists(): raise ValueError('Output đã tồn tại.')
    service=InferenceService(cfg)
    if not service.ready: raise SystemExit('Chưa cấu hình checkpoint detector hợp lệ; không đánh giá.')
    rows=test_rows(args.manifest,args.root,service); predictions=[]
    for row in rows:
        result=service.predict(safe_path(args.root,row['path']).read_bytes())
        predictions.append({'clip_id':row['clip_id'],'label':int(row['label']=='fake'),'score':result['fake_score']})
    report=metrics([p['label'] for p in predictions],[p['score'] for p in predictions],service.cfg.threshold)
    report.update({'n_clips':len(rows),'checkpoint_sha256':fingerprint(cfg.checkpoint),
                   'manifest_sha256':fingerprint(args.manifest),'predictions':predictions})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Đã lưu đánh giá test thực tế vào',output)


if __name__=='__main__': main()
