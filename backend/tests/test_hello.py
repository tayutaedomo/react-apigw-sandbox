from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_hello():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_hello_allows_frontend_origin():
    response = client.get("/hello", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in response.headers


def test_hello_does_not_allow_other_origin():
    response = client.get("/hello", headers={"Origin": "http://localhost:9999"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
