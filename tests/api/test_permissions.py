"""api/deps.py の権限チェックを、テスト用のエンドポイントで確認する。"""

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.deps import require_general, require_master
from app.main import create_app
from tests.conftest import GENERAL_PASSWORD, create_general_user, signup

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"


@pytest.fixture
def client(settings):
    app = create_app(settings)
    probe = APIRouter(prefix="/api/test")

    @probe.get("/master", dependencies=[Depends(require_master)])
    def master_only() -> dict:
        return {"ok": True}

    @probe.get("/general", dependencies=[Depends(require_general)])
    def general_only() -> dict:
        return {"ok": True}

    # 画面ファイルの配信（"/" へのマウント）は全パスに一致するので、常に最後に照合させる
    frontend = next(r for r in app.router.routes if getattr(r, "name", None) == "frontend")
    app.router.routes.remove(frontend)
    app.include_router(probe)
    app.router.routes.append(frontend)
    with TestClient(app) as c:
        yield c


def test_anonymous_is_rejected(client):
    assert client.get("/api/test/master").status_code == 401
    assert client.get("/api/test/general").status_code == 401


def test_master_can_only_use_master_endpoints(client):
    signup(client)
    assert client.get("/api/test/master").status_code == 200
    res = client.get("/api/test/general")
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_general_user_is_blocked_until_password_changed(client, settings):
    master = signup(client)
    client.post(LOGOUT)
    create_general_user(settings, master["organization"]["id"])
    client.post(LOGIN, json={"email": "general@example.com", "password": GENERAL_PASSWORD})

    res = client.get("/api/test/general")
    assert res.status_code == 403
    assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"

    client.put(
        "/api/v1/me/password",
        json={"current_password": GENERAL_PASSWORD, "new_password": "new-pass-123"},
    )
    assert client.get("/api/test/general").status_code == 200
    assert client.get("/api/test/master").status_code == 403
