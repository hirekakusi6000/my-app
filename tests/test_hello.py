from fastapi.testclient import TestClient

from app.main import app
from app.services.hello_service import HelloService

client = TestClient(app)


def test_service_returns_hello_world():
    assert HelloService().get_message() == "Hello World"


def test_hello_api():
    res = client.get("/api/v1/hello")
    assert res.status_code == 200
    assert res.json() == {"message": "Hello World"}


def test_index_page_is_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
