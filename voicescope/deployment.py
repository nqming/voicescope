"""Web runtime settings, separate from checkpoint preprocessing configuration."""
from collections import OrderedDict, deque
from dataclasses import dataclass
import os
import time
from urllib.parse import urlsplit


@dataclass(frozen=True)
class WebSettings:
    allowed_hosts: tuple[str,...] = ('*',)
    cors_origins: tuple[str,...] = ()
    inference_per_minute: int = 6
    version: str = 'local'

    def __post_init__(self):
        if not self.allowed_hosts or self.inference_per_minute < 1:
            raise ValueError('Allowed hosts và rate limit phải hợp lệ.')
        for origin in self.cors_origins:
            url=urlsplit(origin)
            if (url.scheme not in {'http','https'} or not url.netloc or
                url.username or url.password or url.path or url.query or url.fragment or '*' in origin):
                raise ValueError('CORS cần origin http(s) cụ thể, không wildcard hoặc path.')

    @classmethod
    def from_env(cls):
        def values(name,default):
            return tuple(x.strip() for x in os.getenv(name,default).split(',') if x.strip())
        return cls(allowed_hosts=values('VOICESCOPE_ALLOWED_HOSTS','*'),
                   cors_origins=values('VOICESCOPE_CORS_ORIGINS',''),
                   inference_per_minute=int(os.getenv('VOICESCOPE_INFERENCE_PER_MINUTE','6')),
                   version=os.getenv('VOICESCOPE_VERSION') or os.getenv('RENDER_GIT_COMMIT','local'))


class InferenceRateLimit:
    """Bounded, per-process sliding window. Called on the async event loop only."""
    def __init__(self,per_minute,max_clients=4096):
        self.per_minute=per_minute
        self.max_clients=max_clients
        self.clients=OrderedDict()

    def allow(self,client):
        now=time.monotonic()
        # Entries are ordered by last access; evict expired clients only.
        while self.clients:
            _,timestamps=next(iter(self.clients.items()))
            if timestamps[-1]>now-60:
                break
            self.clients.popitem(last=False)
        if client not in self.clients:
            if len(self.clients)>=self.max_clients:
                return False
            self.clients[client]=deque()
        timestamps=self.clients[client]
        while timestamps and timestamps[0]<=now-60:
            timestamps.popleft()
        if len(timestamps)>=self.per_minute:
            return False
        timestamps.append(now)
        self.clients.move_to_end(client)
        return True
