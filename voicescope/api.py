"""Same-origin local demo. Raw request body avoids multipart disk spooling."""
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool
from .config import load_config
from .inference import InferenceService
from .deployment import WebSettings, InferenceRateLimit

WEB=Path(__file__).resolve().parent.parent/'web'


def create_app(config=None,web_settings=None):
    cfg=config or load_config(os.getenv('VOICESCOPE_CONFIG'))
    settings=web_settings or WebSettings.from_env()
    limiter=InferenceRateLimit(settings.inference_per_minute)
    @asynccontextmanager
    async def lifespan(app):
        app.state.service=await run_in_threadpool(InferenceService,cfg)
        app.state.busy=False
        yield
    app=FastAPI(title='VoiceScope',lifespan=lifespan)
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware,allow_origins=list(settings.cors_origins),
                           allow_methods=['GET','POST'],allow_headers=['Content-Type'],
                           allow_credentials=False)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.allowed_hosts))

    @app.middleware('http')
    async def response_headers(request,call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Permissions-Policy']='microphone=(self), camera=(), geolocation=()'
        if request.url.path in {'/','/health','/ready','/inference'}:
            response.headers['Cache-Control']='no-store'
        if request.url.path=='/':
            response.headers['Content-Security-Policy']=(
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        return response

    @app.get('/health')
    def health():
        service=app.state.service
        return {'status':service.status,'model_ready':service.ready,'version':settings.version,
                'message':'Sẵn sàng phân tích' if service.ready else 'Chưa cấu hình mô hình',
                'max_upload_bytes':cfg.max_upload_bytes,'max_duration_seconds':cfg.max_duration,
                'formats':['wav','flac'],'retention':'RAM only; released after request; no audio logging'}

    @app.get('/ready')
    def model_readiness():
        if not app.state.service.ready:
            raise HTTPException(503,'Chưa cấu hình mô hình.')
        return {'model_ready':True,'version':settings.version}

    @app.post('/inference')
    async def inference(request:Request):
        service=app.state.service
        if not service.ready:
            raise HTTPException(503,'Chưa cấu hình mô hình. Chưa có mô hình hoặc dữ liệu để phân tích.')
        if app.state.busy:
            raise HTTPException(429,'Máy chủ đang phân tích một tệp khác; hãy thử lại.')
        if request.headers.get('content-type','').split(';')[0] not in {'audio/wav','audio/x-wav','audio/flac','audio/x-flac','application/octet-stream'}:
            raise HTTPException(415,'Chỉ hỗ trợ WAV/FLAC.')
        if not limiter.allow(request.client.host if request.client else 'unknown'):
            raise HTTPException(429,'Đã đạt giới hạn yêu cầu; hãy thử lại sau một phút.',
                                headers={'Retry-After':'60'})
        app.state.busy=True
        payload=bytearray(); begin=time.perf_counter()
        try:
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    if len(payload)+len(chunk)>cfg.max_upload_bytes:
                        raise HTTPException(413,'Tệp vượt giới hạn kích thước.')
                    payload.extend(chunk)
            if not payload:
                raise HTTPException(400,'Tệp audio rỗng.')
            result=await run_in_threadpool(service.predict,bytes(payload))
            result['timing_ms']['server_request']=(time.perf_counter()-begin)*1000
            return result
        except TimeoutError:
            raise HTTPException(408,'Tải tệp quá lâu; hãy thử lại.')
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(500,'Không thể phân tích; kiểm tra cấu hình/môi trường máy chủ.') from exc
        finally:
            payload.clear(); app.state.busy=False

    @app.get('/')
    def index():
        return FileResponse(WEB/'index.html')

    app.mount('/static',StaticFiles(directory=WEB),name='static')
    return app


app=create_app()
