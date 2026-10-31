import numpy as np
import soundfile as sf
from voicescope.config import Config
from voicescope.manifest import write_manifest
from voicescope.prepare import prepare
from test_core import row


def test_decode_clipping_duration_reject_report(tmp_path):
    raw=tmp_path/'raw'; raw.mkdir(); rows=[]
    for i in range(3):
        r=row(f'good{i}'); r['origin']='test_fixture'; r['is_test_fixture']=True
        sf.write(raw/r['path'],.1*np.sin(np.arange(16000)*(.1+i*.1)),16000)
        rows.append(r)
    for name in ('bad_decode','clipped','short'):
        r=row(name); r['origin']='test_fixture'; r['is_test_fixture']=True
        if name=='bad_decode': (raw/r['path']).write_bytes(b'not an audio file')
        elif name=='clipped': sf.write(raw/r['path'],np.ones(16000),16000)
        else:
            sf.write(raw/r['path'],np.zeros(800),16000); r['duration']=.05
        rows.append(r)
    manifest=tmp_path/'input.jsonl'; write_manifest(manifest,rows)
    output=tmp_path/'output'
    report=prepare(manifest,raw,output,Config(),allow_fixtures=True)
    assert report['rejected']==3
    import json
    rejected=[json.loads(line) for line in (output/'rejects.jsonl').read_text(encoding='utf-8').splitlines()]
    assert {r['clip_id'] for r in rejected}=={'bad_decode','clipped','short'}
    assert any('clipping' in r['reason'] for r in rejected)
