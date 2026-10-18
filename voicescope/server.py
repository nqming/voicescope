"""python -m voicescope.server: one process for frontend and API."""
import os


def server_options():
    port=int(os.getenv('PORT','8000'))
    if not 1<=port<=65535:
        raise ValueError('PORT phải từ 1 đến 65535.')
    return {'host':os.getenv('HOST','0.0.0.0'),'port':port,'workers':1,
            'access_log':False,'proxy_headers':True,
            'forwarded_allow_ips':os.getenv('FORWARDED_ALLOW_IPS','127.0.0.1'),
            'timeout_keep_alive':5,'limit_concurrency':32}


def main():
    import uvicorn
    uvicorn.run('voicescope.api:app',**server_options())


if __name__=='__main__': main()
