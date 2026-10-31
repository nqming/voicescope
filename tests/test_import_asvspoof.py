import numpy as np
import soundfile as sf
import pytest
from voicescope.import_asvspoof import import_la
from voicescope.manifest import read_manifest


def test_protocol_import_does_not_assert_rights(tmp_path):
    root=tmp_path/'LA'; protocols=root/'ASVspoof2019_LA_cm_protocols'; protocols.mkdir(parents=True)
    for split,tag,suffix,speaker in [('train','T','train.trn','s1'),('dev','D','dev.trl','s2'),('eval','E','eval.trl','s3')]:
        audio=root/f'ASVspoof2019_LA_{split}'/'flac'; audio.mkdir(parents=True)
        lines=[]
        for i,label in enumerate(['bonafide','spoof']):
            clip=f'LA_{tag}_{i}'
            sf.write(audio/f'{clip}.flac',np.zeros(16000),16000)
            lines.append(f'{speaker} {clip} - {"-" if i==0 else "A01"} {label}\n')
        (protocols/f'ASVspoof2019.LA.cm.{suffix}.txt').write_text(''.join(lines))
    output=tmp_path/'imported'
    report=import_la(root,output,test_fixture=True)
    assert report['rows']==6 and report['rights_review_required']
    import json
    rows=[json.loads(line) for line in (output/'manifest.jsonl').read_text().splitlines()]
    assert {r['consent_status'] for r in rows}=={'pending'}
    assert {r['split'] for r in rows}=={'train','validation','test'}
    approved=tmp_path/'approved'
    report=import_la(root,approved,rights_ref='operator-reviewed-local-license',test_fixture=True)
    assert len(read_manifest(approved/'manifest.jsonl',allow_fixtures=True))==6
    assert all(r['label']=='fake' for r in read_manifest(approved/'manifest.jsonl',allow_fixtures=True) if r['attack_id']=='A01')
    with pytest.raises(ValueError,match='kiểm thử'):
        read_manifest(approved/'manifest.jsonl')
