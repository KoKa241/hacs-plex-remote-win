import pytest
from fastapi.testclient import TestClient
from test_control import FakeBackend

from server.app import create_app
from server.control import Controller

TOKEN = "test-token-" * 4


@pytest.fixture
def client():
    return TestClient(create_app(Controller(FakeBackend(), "test-pc"), TOKEN))


@pytest.mark.parametrize("path,method", [("/api/status", "get"), ("/api/command", "post")])
def test_auth_required(client, path, method):
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_status_and_power(client):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    assert client.get("/api/status", headers=headers).json()["running"] is False
    for expected in [True, False]:
        response = client.post("/api/command", headers=headers, json={"command": "toggle"})
        assert response.status_code == 200
        assert response.json()["running"] is expected


@pytest.mark.parametrize(
    "body", [{"command": "shutdown"}, {"command": "up", "shell": "cmd"}, {}, {"command": 1}]
)
def test_invalid_payload(client, body):
    assert (
        client.post("/api/command", headers={"Authorization": f"Bearer {TOKEN}"}, json=body).status_code
        == 422
    )


def test_input_when_off_returns_conflict(client):
    assert (
        client.post(
            "/api/command", headers={"Authorization": f"Bearer {TOKEN}"}, json={"command": "up"}
        ).status_code
        == 409
    )


def test_weak_token_rejected():
    with pytest.raises(ValueError):
        create_app(Controller(FakeBackend(), "id"), "short")
