def test_health_returns_ok(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_unknown_api_returns_error_format(client):
    res = client.get("/api/v1/does-not-exist")
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_frontend_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
