"""Audit app/model payload and runtime properties before public distribution."""
import argparse,json,subprocess
from pathlib import Path

CHECK = r"""
import hashlib,importlib.util,json,pathlib,os
root=pathlib.Path('/app')
files=[p for p in root.rglob('*') if p.is_file()]
bad=[str(p) for p in files if any(x in p.parts for x in ['.git','data','tmp','.venv','.aws','.docker']) or p.suffix.lower() in ['.wav','.flac','.mp3','.pem','.key','.pth','.pt','.safetensors'] or p.name.startswith('.env')]
assert not bad,bad
assert os.getuid()!=0
assert importlib.util.find_spec('torch') is None
model=pathlib.Path('/opt/models/antideepfake')
m=json.loads((model/'manifest.json').read_text())
assert hashlib.sha256((model/'model_q4.onnx').read_bytes()).hexdigest()==m['sha256']
for name in ['model-card.md','MODEL-NOTICE.md','LICENSE-MODEL.txt']: assert (model/name).stat().st_size>100
print(json.dumps({'uid':os.getuid(),'app_files':[str(p.relative_to(root)) for p in files], 'model_bytes':(model/'model_q4.onnx').stat().st_size,'manifest':m,'torch_in_runtime':False,'forbidden_app_payload':bad}))
"""
p=argparse.ArgumentParser();p.add_argument('--image',required=True);a=p.parse_args()
r=subprocess.run(['docker','run','--rm','--read-only','--network','none','--entrypoint','python',a.image,'-c',CHECK],check=True,capture_output=True,text=True)
report=json.loads(r.stdout);report['image']=a.image
out=Path('artifacts/image-audit.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
