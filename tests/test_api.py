from fastapi.testclient import TestClient
from voicescope.api import create_app
from voicescope.config import Config


def test_no_model_never_predicts():
    with TestClient(create_app(Config())) as client:
        health=client.get('/health').json()
        assert health['model_ready'] is False
        assert health['status']=='not_configured'
        response=client.post('/inference',content=b'RIFF',headers={'content-type':'audio/wav'})
        assert response.status_code==503
        assert 'score' not in response.json()
        assert 'VoiceScope' in client.get('/').text


def test_failed_checkpoint_is_unavailable(tmp_path):
    with TestClient(create_app(Config(checkpoint=str(tmp_path/'missing.pt')))) as client:
        assert client.get('/health').json()['status']=='load_error'
        assert client.post('/inference',content=b'x').status_code==503


def test_upload_limits_and_decode_error_without_fake_prediction():
    class RejectingTestService:
        ready=True
        def predict(self,data):
            raise ValueError('Không giải mã được audio kiểm thử.')
    app=create_app(Config(max_upload_bytes=4))
    with TestClient(app) as client:
        app.state.service=RejectingTestService()
        assert client.post('/inference',content=b'12345',headers={'content-type':'audio/wav'}).status_code==413
        assert client.post('/inference',content=b'bad',headers={'content-type':'audio/wav'}).status_code==422
        assert client.post('/inference',content=b'bad',headers={'content-type':'text/plain'}).status_code==415
        assert client.post('/inference',content=b'',headers={'content-type':'audio/wav'}).status_code==400
        assert app.state.busy is False
