import pytest
from fastapi.testclient import TestClient
from voicescope.api import create_app
from voicescope.config import Config
from voicescope.deployment import WebSettings
from voicescope.server import server_options


def test_provider_port_and_single_worker(monkeypatch):
    monkeypatch.setenv('PORT','10000')
    options=server_options()
    assert options['port']==10000
    assert options['host']=='0.0.0.0'
    assert options['workers']==1
    assert options['access_log'] is False
    monkeypatch.setenv('PORT','invalid')
    with pytest.raises(ValueError): server_options()


def test_liveness_and_model_readiness_are_separate():
    with TestClient(create_app(Config(),WebSettings(version='test-version'))) as client:
        health=client.get('/health')
        assert health.status_code==200
        assert health.json()['version']=='test-version'
        assert health.json()['model_ready'] is False
        assert client.get('/ready').status_code==503
        assert health.headers['cache-control']=='no-store'
        index=client.get('/')
        assert "default-src 'self'" in index.headers['content-security-policy']
        assert index.headers['x-content-type-options']=='nosniff'
        assert client.get('/static/app.js').status_code==200


def test_explicit_cors_and_host_allowlist():
    settings=WebSettings(allowed_hosts=('testserver',),cors_origins=('https://frontend.example',))
    with TestClient(create_app(Config(),settings)) as client:
        response=client.options('/inference',headers={'origin':'https://frontend.example',
            'access-control-request-method':'POST','access-control-request-headers':'content-type'})
        assert response.status_code==200
        assert response.headers['access-control-allow-origin']=='https://frontend.example'
        denied=client.options('/inference',headers={'origin':'https://untrusted.example',
            'access-control-request-method':'POST'})
        assert 'access-control-allow-origin' not in denied.headers
        assert client.get('/health',headers={'host':'untrusted.example'}).status_code==400


def test_rate_limit_and_busy_release():
    class RejectingService:
        ready=True
        def predict(self,data): raise ValueError('invalid test audio')
    app=create_app(Config(),WebSettings(inference_per_minute=1))
    with TestClient(app) as client:
        app.state.service=RejectingService()
        headers={'content-type':'audio/wav'}
        assert client.post('/inference',content=b'bad',headers=headers).status_code==422
        response=client.post('/inference',content=b'bad',headers=headers)
        assert response.status_code==429
        assert response.headers['retry-after']=='60'
        assert app.state.busy is False


def test_invalid_deploy_settings_fail_early(monkeypatch):
    monkeypatch.setenv('VOICESCOPE_CORS_ORIGINS','*')
    with pytest.raises(ValueError): WebSettings.from_env()
    with pytest.raises(ValueError): WebSettings(inference_per_minute=0)


def test_default_same_origin_does_not_allow_cross_origin():
    with TestClient(create_app(Config(),WebSettings())) as client:
        result=client.get('/health',headers={'origin':'https://untrusted.example'})
        assert 'access-control-allow-origin' not in result.headers

def test_render_health_reports_platform_commit_instead_of_pinned_version(monkeypatch):
    monkeypatch.setenv('VOICESCOPE_VERSION','a'*40)
    monkeypatch.setenv('RENDER_GIT_COMMIT','b'*40)
    with TestClient(create_app(Config(),WebSettings.from_env())) as client:
        assert client.get('/health').json()['version']=='b'*40


@pytest.mark.parametrize('configured,expected',[('image-revision','image-revision'),('','local')])
def test_non_render_version_retains_image_revision_or_local_fallback(monkeypatch,configured,expected):
    monkeypatch.delenv('RENDER_GIT_COMMIT',raising=False)
    monkeypatch.setenv('VOICESCOPE_VERSION',configured)
    assert WebSettings.from_env().version==expected
