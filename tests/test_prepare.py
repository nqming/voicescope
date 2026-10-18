import json
import numpy as np
import soundfile as sf
from voicescope.prepare import prepare
from voicescope.config import Config
from voicescope.manifest import write_manifest, read_manifest, audit_splits
from test_core import row


def test_pipeline_rejects_duplicate_and_preserves_splits(tmp_path):
    raw=tmp_path/'raw'; raw.mkdir()
    rows=[]
    for i in range(10):
        # Synthetic sine ONLY for code testing, never a speech dataset.
        y=.1*np.sin(2*np.pi*(200+20*i)*np.arange(16000)/16000)
        sf.write(raw/f'{i}.wav',y,16000)
        r=row(i); r['is_test_fixture']=True; r['origin']='test_fixture'; rows.append(r)
    (raw/'10.wav').write_bytes((raw/'0.wav').read_bytes())
    r=row(10); r['is_test_fixture']=True; r['origin']='test_fixture'; rows.append(r)
    manifest=tmp_path/'input.jsonl'; write_manifest(manifest,rows)
    report=prepare(manifest,raw,tmp_path/'out',Config(),allow_fixtures=True,augment=True)
    assert report['rejected']==1
    output=read_manifest(tmp_path/'out'/'manifest.jsonl',allow_fixtures=True)
    audit_splits(output)
    assert len(output)==20
    assert all(r['start_seconds']==0 for r in output)
    assert all(r['is_test_fixture'] for r in output)
