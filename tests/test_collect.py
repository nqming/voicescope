import numpy as np
import pytest
import soundfile as sf
from voicescope.collect import ingest_clip, record_clip
from voicescope.config import Config
from voicescope.manifest import read_manifest
from test_core import row


def test_ingest_preserves_original_and_records_metadata(tmp_path):
    source=tmp_path/'input.wav'
    sf.write(source,.1*np.sin(np.arange(16000)*.2),16000)
    metadata=row('r1'); metadata['is_test_fixture']=True; metadata['origin']='test_fixture'
    result=ingest_clip(source,tmp_path/'collection',metadata,Config())
    assert result['path']=='raw/r1.wav'
    assert result['duration']==1
    assert source.read_bytes()==(tmp_path/'collection'/result['path']).read_bytes()
    assert read_manifest(tmp_path/'collection'/'manifest.jsonl',allow_fixtures=True)[0]['sha256']
    with pytest.raises(ValueError,match='trùng'):
        ingest_clip(source,tmp_path/'collection',metadata,Config())
    metadata['clip_id']='r2'
    with pytest.raises(ValueError,match='trùng'):
        ingest_clip(source,tmp_path/'collection',metadata,Config())


def test_pending_consent_blocks_before_microphone(tmp_path):
    metadata=row('r1'); metadata['consent_status']='pending'
    def forbidden(*args,**kwargs): raise AssertionError('Microphone must not open')
    with pytest.raises(ValueError):
        record_clip(tmp_path/'collection',metadata,1,Config(),recorder=forbidden)
    assert not (tmp_path/'collection').exists()


def test_pending_consent_blocks_before_ingest(tmp_path):
    metadata=row('r1'); metadata['consent_status']='pending'
    with pytest.raises(ValueError):
        ingest_clip(tmp_path/'missing.wav',tmp_path/'collection',metadata,Config())
    assert not (tmp_path/'collection').exists()


def test_record_test_double_only(tmp_path):
    metadata=row('r1'); metadata['is_test_fixture']=True; metadata['origin']='test_fixture'
    def sine_recorder(frames,samplerate,device):
        return (.1*np.sin(np.arange(frames)*.2)).astype(np.float32)
    result=record_clip(tmp_path/'collection',metadata,1,Config(),recorder=sine_recorder)
    assert result['capture_method']=='microphone'
    assert result['is_test_fixture'] is True
    assert result['sample_rate']==16000
