"""公開用の設定。

セキュリティヘッダー・リクエストID・予期しないエラー・API 仕様書の公開・監査ログを確認する。
"""

import logging

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import MASTER_PASSWORD, signup

API = "/api/v1"


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        **overrides,
    )


# ───────── セキュリティヘッダー ─────────


@pytest.mark.parametrize("path", ["/", "/login.html", f"{API}/health", f"{API}/me"])
def test_security_headers_on_pages_and_api(client, path):
    headers = client.get(path).headers
    csp = headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "same-origin"
    assert "strict-transport-security" not in headers  # HTTPS の設定をしていないとき


def test_hsts_when_cookie_secure(tmp_path):
    with TestClient(create_app(_settings(tmp_path, cookie_secure=True))) as c:
        assert "max-age=31536000" in c.get(f"{API}/health").headers["strict-transport-security"]


def test_api_docs_have_no_csp_and_can_be_disabled(client, tmp_path):
    res = client.get("/docs")
    assert res.status_code == 200
    assert "content-security-policy" not in res.headers

    with TestClient(create_app(_settings(tmp_path, enable_api_docs=False))) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404


def test_pages_have_no_inline_scripts(settings):
    """CSP でインラインスクリプトを禁止しているので、HTML に直接スクリプトを書いていないこと。"""
    for html in settings.frontend_dir.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        for tag in text.split("<script")[1:]:
            assert "src=" in tag.split(">")[0], f"{html.name} にインラインスクリプトがあります"
        assert ' style="' not in text, f"{html.name} に style 属性があります"


# ───────── リクエストID ─────────


def test_request_id_is_generated(client):
    request_id = client.get(f"{API}/health").headers["x-request-id"]
    assert len(request_id) == 16
    assert client.get(f"{API}/health").headers["x-request-id"] != request_id


def test_valid_incoming_request_id_is_kept(client):
    res = client.get(f"{API}/health", headers={"X-Request-ID": "proxy-abc_123"})
    assert res.headers["x-request-id"] == "proxy-abc_123"


@pytest.mark.parametrize("value", ["bad id with spaces", "x" * 65, "<script>"])
def test_invalid_incoming_request_id_is_replaced(client, value):
    res = client.get(f"{API}/health", headers={"X-Request-ID": value})
    assert res.headers["x-request-id"] != value


# ───────── 予期しないエラー ─────────


def test_unexpected_error_returns_json_with_request_id(tmp_path):
    app = create_app(_settings(tmp_path))
    boom = APIRouter()

    @boom.get("/api/test/boom")
    def explode() -> None:
        raise RuntimeError("内部の詳細")

    frontend = next(r for r in app.router.routes if getattr(r, "name", None) == "frontend")
    app.router.routes.remove(frontend)
    app.include_router(boom)
    app.router.routes.append(frontend)

    with TestClient(app, raise_server_exceptions=False) as c:
        res = c.get("/api/test/boom")
    body = res.json()
    assert res.status_code == 500
    assert body["code"] == "INTERNAL_ERROR"
    assert "内部の詳細" not in body["detail"]  # 内部の情報は利用者に見せない
    assert body["request_id"] == res.headers["x-request-id"]


# ───────── 監査ログ ─────────


@pytest.fixture
def audit_records():
    records: list[logging.LogRecord] = []

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Collector()
    logger = logging.getLogger("app.audit")
    logger.addHandler(handler)
    yield records
    logger.removeHandler(handler)


def test_login_failure_is_logged_without_password(client, audit_records):
    signup(client)
    client.post(f"{API}/auth/logout")
    client.post(f"{API}/auth/login", json={"email": "master@example.com", "password": "secret-x"})

    messages = [r.getMessage() for r in audit_records]
    failure = next(m for m in messages if "ログインに失敗" in m)
    assert "ma***@example.com" in failure  # メールアドレスは一部を伏せる
    assert all("secret-x" not in m and MASTER_PASSWORD not in m for m in messages)
    assert any("組織を作成しました" in m for m in messages)
