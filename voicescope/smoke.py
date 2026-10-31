"""Verify a running VoiceScope URL without uploading audio or loading a model."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def check_url(base_url,expected='unconfigured',timeout=15):
    url=urlsplit(base_url)
    if (url.scheme not in {'http','https'} or not url.netloc or url.username or
        url.password or url.query or url.fragment or url.path not in {'','/'}):
        raise ValueError('URL phải là origin http(s), không chứa token/path/query.')
    base_url=base_url.rstrip('/')
    checks=[]

    def fetch(path,method='GET'):
        request=Request(base_url+path,data=b'' if method=='POST' else None,
                        method=method,headers={'Content-Type':'audio/wav'} if method=='POST' else {})
        try:
            response=urlopen(request,timeout=timeout)
        except HTTPError as exc:
            response=exc
        with response:
            body=response.read(2_000_001)
            if len(body)>2_000_000:
                raise ValueError('Response quá lớn cho smoke test.')
            return response.code,body.decode('utf-8')

    status,body=fetch('/')
    if status!=200 or 'VoiceScope' not in body or '/static/app.js' not in body:
        raise ValueError('Trang chủ không mở đúng VoiceScope.')
    checks.append('homepage')
    status,script=fetch('/static/app.js')
    if status!=200 or "fetch('/api/status')" not in script or "fetch('/inference'" not in script:
        raise ValueError('Frontend chưa nối API cùng origin.')
    checks.append('frontend_api_routes')
    status,body=fetch('/health')
    if status!=200:
        raise ValueError('Health endpoint không trả 200.')
    health=json.loads(body)
    if type(health.get('model_ready')) is not bool:
        raise ValueError('Health thiếu model_ready boolean.')
    ready=health['model_ready']
    if expected=='unconfigured' and ready:
        raise ValueError('Đang có model trong khi yêu cầu kiểm tra chưa cấu hình.')
    if expected=='ready' and not ready:
        raise ValueError('Checkpoint chưa sẵn sàng.')
    checks.append('health')
    status,_=fetch('/ready')
    if status!=(200 if ready else 503):
        raise ValueError('Readiness không khớp trạng thái model.')
    checks.append('model_readiness')
    if not ready:
        status,body=fetch('/inference','POST')
        result=json.loads(body)
        if status!=503 or 'fake_score' in result or 'score' in result:
            raise ValueError('API chưa cấu hình phải trả 503, không trả score.')
        checks.append('missing_checkpoint_503_without_score')
    return {'url':base_url,'https':url.scheme=='https','checks':checks,
            'model_ready':ready,'version':health.get('version'),
            'scope':'HTTP smoke only; no audio upload, no model-quality or latency claim'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--expect',choices=['unconfigured','ready','either'],default='unconfigured')
    parser.add_argument('--timeout',type=float,default=15)
    parser.add_argument('--require-https',action='store_true')
    parser.add_argument('--output')
    args=parser.parse_args()
    if args.timeout<=0 or args.timeout>60:
        parser.error('timeout phải trong (0,60] giây.')
    if args.require_https and urlsplit(args.url).scheme!='https':
        parser.error('Deploy public cần URL HTTPS thực tế.')
    report=check_url(args.url,args.expect,args.timeout)
    if args.output:
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
