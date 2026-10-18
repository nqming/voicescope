"""Supervised DINOv3 detector training; intentionally not run without real data."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import random
import subprocess
from .config import load_config
from .manifest import read_manifest, audit_splits, safe_path, fingerprint


def checked_rows(manifest,root):
    rows=read_manifest(manifest)
    audit_splits(rows)
    for row in rows:
        path=safe_path(root,row['path'])
        if not row.get('sha256') or fingerprint(path)!=row['sha256']:
            raise ValueError('Cần manifest đã prepare; hash tệp không khớp.')
        if not row.get('parent_clip_id') or not row.get('original_sha256'):
            raise ValueError('Thiếu lineage; hãy chạy prepare.')
    return rows


def group_keys(rows):
    keys=set()
    for r in rows:
        keys.update(['speaker:'+r['speaker_id'],'source:'+r['source_id'],'hash:'+r['original_sha256']])
        keys.update('speaker:'+x for x in r.get('related_speaker_ids',[]))
        keys.update('source:'+x for x in r.get('related_source_ids',[]))
    return sorted(keys)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True); p.add_argument('--root',required=True)
    p.add_argument('--config',default='configs/default.json'); p.add_argument('--output',required=True)
    p.add_argument('--epochs',type=int,default=10); p.add_argument('--batch-size',type=int,default=8)
    p.add_argument('--lr',type=float,default=1e-4)
    args=p.parse_args(); cfg=load_config(args.config)
    rows=checked_rows(args.manifest,args.root)
    prep_path=Path(args.manifest).parent/'prepare-report.json'
    if not prep_path.is_file():
        raise ValueError('Thiếu prepare-report.json cạnh manifest.')
    prepared=json.loads(prep_path.read_text(encoding='utf-8'))
    if prepared.get('test_fixture_run'):
        raise ValueError('Không train bằng run kiểm thử.')
    for key in ('sample_rate','window_seconds','min_duration','vad_db','peak_normalize','hop_length'):
        if prepared['config'][key]!=getattr(cfg,key):
            raise ValueError('Cấu hình prepare/train khác nhau: '+key)
    subsets={s:[r for r in rows if r['split']==s] for s in ('train','validation','test')}
    for name,part in subsets.items():
        if {r['label'] for r in part}!={'real','fake'}:
            raise ValueError(f'{name} cần cả real/fake; không tách nhóm để ép cân bằng.')
    if args.epochs<1 or args.batch_size<1 or args.lr<=0:
        raise ValueError('epochs, batch-size và lr phải dương.')
    if any(r['duration']>cfg.window_seconds+.001 for r in rows):
        raise ValueError('Segment dài hơn window; prepare lại với cùng config.')
    import numpy as np
    import torch
    from torch.utils.data import Dataset,DataLoader
    from .audio import decode
    from .model import Detector,spectrogram_tensor,PREPROCESS_VERSION
    random.seed(cfg.seed); np.random.seed(cfg.seed); torch.manual_seed(cfg.seed)
    torch.use_deterministic_algorithms(True)
    class Clips(Dataset):
        def __init__(self,items): self.items=items
        def __len__(self): return len(self.items)
        def __getitem__(self,i):
            r=self.items[i]; y,_=decode(safe_path(args.root,r['path']),cfg)
            return spectrogram_tensor(y,cfg)[0],int(r['label']=='fake')
    generator=torch.Generator().manual_seed(cfg.seed)
    train_loader=DataLoader(Clips(subsets['train']),batch_size=args.batch_size,shuffle=True,generator=generator)
    val_loader=DataLoader(Clips(subsets['validation']),batch_size=args.batch_size)
    model=Detector(cfg).to(cfg.device)
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=args.lr)
    criterion=torch.nn.CrossEntropyLoss()
    output=Path(args.output)
    if output.exists(): raise ValueError('Output đã tồn tại; chọn run mới.')
    output.mkdir(parents=True)
    try:
        revision=subprocess.check_output(['git','-C',cfg.dinov3_repo,'rev-parse','HEAD'],text=True).strip()
    except (OSError,subprocess.CalledProcessError):
        revision='unavailable'
    provenance={'manifest_sha256':fingerprint(args.manifest),
                'training_and_validation_groups':group_keys(subsets['train']+subsets['validation']),
                'dinov3_revision':revision,'backbone_weights_sha256':fingerprint(cfg.backbone_weights),
                'seed':cfg.seed,'torch_version':str(torch.__version__),
                'threshold_policy':'fixed_in_config_not_tuned_on_test','epochs_requested':args.epochs}
    best=float('inf'); history=[]
    for epoch in range(args.epochs):
        model.train(); train_loss=0
        for x,y in train_loader:
            x,y=x.to(cfg.device),y.to(cfg.device)
            optimizer.zero_grad(); loss=criterion(model(x),y)
            loss.backward(); optimizer.step(); train_loss+=float(loss.detach())*len(y)
        model.eval(); val_loss=0
        with torch.inference_mode():
            for x,y in val_loader:
                loss=criterion(model(x.to(cfg.device)),y.to(cfg.device))
                val_loss+=float(loss)*len(y)
        val_loss/=len(subsets['validation'])
        if not np.isfinite(val_loss): raise ValueError('Validation loss không hữu hạn; dừng run.')
        entry={'epoch':epoch+1,'train_loss':train_loss/len(subsets['train']),'validation_loss':val_loss}
        history.append(entry); print(json.dumps(entry),flush=True)
        if val_loss<best:
            best=val_loss
            # Full state supports frozen and fine-tuned backbones alike.
            portable=replace(cfg,dinov3_repo='',backbone_weights='',checkpoint='').to_dict()
            torch.save({'format_version':1,'trained':True,'test_fixture_run':False,
                'labels':['real','fake'],'preprocess_version':PREPROCESS_VERSION,'config':portable,
                'model':{k:v.detach().cpu() for k,v in model.state_dict().items()},
                'provenance':provenance,'epoch':epoch+1},output/'best.pt')
        (output/'history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')


if __name__=='__main__': main()
