import io
import numpy as np
import pytest
import soundfile as sf
from voicescope.config import Config
from voicescope.audio import decode, log_mel, windows, speech_windows
from voicescope.manifest import assign_splits, validate, safe_path, audit_splits


def row(i, speaker=None, source=None):
    return dict(clip_id=str(i), speaker_id=speaker or str(i), source_id=source or str(i),
                label='real', synthesis_method='none', device='test', channel='test',
                sample_rate=16000, duration=1.0, consent_status='granted',
                consent_ref='local-test-only', path=f'{i}.wav', origin='private',
                license='consent-record', is_test_fixture=False)


def test_connected_groups_and_determinism():
    rows = [row(0,'a','x'), row(1,'a','y'), row(2,'b','y')] + [row(i) for i in range(3,20)]
    out = assign_splits(rows, 42)
    assert len({r['split'] for r in out[:3]}) == 1
    assert {r['clip_id']: r['split'] for r in out} == {r['clip_id']: r['split'] for r in assign_splits(list(reversed(rows)),42)}
    audit_splits(out)


def test_consent_and_path(tmp_path):
    r = row(1); r['consent_status'] = 'pending'
    with pytest.raises(ValueError): validate(r)
    with pytest.raises(ValueError): safe_path(tmp_path, '../outside.wav')
    with pytest.raises(ValueError): safe_path(tmp_path, 'C:/outside.wav')


def test_decode_and_time_mapping():
    sr = 48000
    y = .1*np.sin(2*np.pi*440*np.arange(sr*2)/sr)
    buf = io.BytesIO(); sf.write(buf, np.stack([y,y],axis=1),sr,format='WAV'); buf.seek(0)
    audio, rate = decode(buf, Config())
    assert rate == 16000 and len(audio) == 32000
    spec, times = log_mel(audio, Config())
    assert spec.shape[0] == 80 and spec.shape[1] == len(times)
    assert np.isfinite(spec).all()
    assert times[0] == pytest.approx(.0125)
    assert np.diff(times).mean() == pytest.approx(.01)
    assert list(windows(audio,16000,1))[1][0] == 1.0


def test_empty_and_oversize_decode():
    with pytest.raises(ValueError): decode(io.BytesIO(b'bad'),Config())
    buf=io.BytesIO(); sf.write(buf,np.zeros(32000),16000,format='WAV'); buf.seek(0)
    with pytest.raises(ValueError): decode(buf,Config(max_duration=1))


def test_leakage_rejected():
    rows=[row(1,'s','a'),row(2,'s','b')]
    rows[0]['split']='train'; rows[1]['split']='test'
    with pytest.raises(ValueError): audit_splits(rows)


def test_speech_selection_preserves_offsets_and_rejects_silence():
    cfg=Config(window_seconds=1)
    assert list(speech_windows(np.zeros(32000,dtype=np.float32),cfg))==[]
    y=np.zeros(48000,dtype=np.float32)
    y[16000:32000]=.1*np.sin(2*np.pi*440*np.arange(16000)/16000)
    parts=list(speech_windows(y,cfg))
    assert parts[0][0]==pytest.approx(.9)
    assert all(b-a>=cfg.min_duration for a,b,_ in parts)


def test_decoded_memory_limit():
    buf=io.BytesIO(); sf.write(buf,np.zeros((16000,2)),16000,format='FLAC'); buf.seek(0)
    with pytest.raises(ValueError,match='bộ nhớ'): decode(buf,Config(max_decoded_samples=20000))
