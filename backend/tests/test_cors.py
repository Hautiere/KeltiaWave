import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.cors import configure_cors
from app.record.routes import router


def make_client(configured=""):
    application = FastAPI()
    configure_cors(application, configured)
    application.include_router(router)
    return TestClient(application)


@pytest.mark.parametrize("origin", ["http://localhost", "https://localhost", "capacitor://localhost", "http://localhost:4400"])
def test_record_preflight_and_validation_response(origin):
    with make_client() as client:
        response = client.options('/api/record/transcribe', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == origin
        assert response.headers['access-control-allow-credentials'] == 'true'
        response = client.post('/api/record/transcribe', headers={'Origin': origin})
        assert response.status_code == 422
        assert response.headers['access-control-allow-origin'] == origin


@pytest.mark.parametrize('origin', ['https://untrusted.example', 'http://localhost.evil.example', 'null'])
def test_unknown_origin_rejected(origin):
    with make_client() as client:
        response = client.options('/api/record/transcribe', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST',
        })
        assert response.status_code == 400
        assert 'access-control-allow-origin' not in response.headers


def test_explicit_configuration_replaces_defaults():
    with make_client(' https://web.example , https://web.example ') as client:
        for origin, expected in [('https://web.example', 200), ('http://localhost', 400)]:
            response = client.options('/api/record/transcribe', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST',
            })
            assert response.status_code == expected


def test_wildcard_is_rejected():
    with pytest.raises(ValueError):
        configure_cors(FastAPI(), '*')
