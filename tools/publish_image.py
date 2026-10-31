"""Publish an already tested image; no build or secret handling here."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--image',required=True);a=p.parse_args()
sha=os.environ['GITHUB_SHA'];assert re.fullmatch('[a-f0-9]{40}',sha)
namespace=os.environ['DOCKERHUB_USERNAME'];assert re.fullmatch('[a-z0-9][a-z0-9_-]*',namespace)
ref=os.environ.get('GITHUB_REF','');tags=['sha-'+sha]
if ref.startswith('refs/tags/'):
    version=ref.removeprefix('refs/tags/')
    assert re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?',version),'Use vMAJOR.MINOR.PATCH[-prerelease]'
    tags.append(version)
    if '-' not in version: tags.append('latest')
repo=namespace+'/voicescope'
for tag in tags:
    target=repo+':'+tag
    subprocess.run(['docker','tag',a.image,target],check=True)
    subprocess.run(['docker','push',target],check=True)
r=subprocess.run(['docker','image','inspect',repo+':'+tags[0],'--format','{{json .RepoDigests}}'],check=True,capture_output=True,text=True)
report={'repository':repo,'source_sha':sha,'tags':tags,'digests':json.loads(r.stdout)}
Path('artifacts').mkdir(exist_ok=True);Path('artifacts/publish.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
