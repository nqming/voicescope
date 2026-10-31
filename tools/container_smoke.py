"""Readiness + actual ONNX API execution. Synthetic input is not accuracy evidence."""
import argparse, io, json, math, struct, time, wave
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8000')
    p.add_argument('--output', default='artifacts/container-smoke.json')
    p.add_argument('--audio', type=Path)
    p.add_argument('--expected-label', choices=['real','fake'])
    a=p.parse_args(); base=a.url.rstrip('/')
    error=None
    for _ in range(90):
        try:
            with urlopen(base+'/ready',timeout=5) as f:
                assert json.load(f)['model_ready'] is True
            break
        except Exception as e: error=e; time.sleep(2)
    else: raise RuntimeError('Model not ready') from error
    for path in ['/','/health','/api/status','/static/app.js']:
        with urlopen(base+path,timeout=10) as f: assert f.status==200
    if a.audio:
        payload=a.audio.read_bytes(); source=a.audio.name
    else:
        out=io.BytesIO()
        with wave.open(out,'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b''.join(struct.pack('<h',int(3000*math.sin(2*math.pi*220*i/16000))) for i in range(32000)))
        payload=out.getvalue(); source='synthetic 2s sine: execution test only'
    request=Request(base+'/inference',data=payload,headers={'Content-Type':'application/octet-stream'})
    with urlopen(request,timeout=120) as f: result=json.load(f)
    assert result['label'] in ['real','fake']
    assert math.isfinite(result['fake_score']) and 0<=result['fake_score']<=1
    assert 'Q4' in result['model']
    if a.expected_label: assert result['label']==a.expected_label,result
    report={'url':base,'input':source,'expected_label':a.expected_label,'result':result,
            'scope':'Container API execution; not a general accuracy benchmark'}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__': main()
