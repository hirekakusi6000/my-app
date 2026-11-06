import sqlite3

import pytest

from app.core.security import hash_session_token
from app.db.connection import connect
from tests.conftest import GENERAL_PASSWORD, MASTER_PASSWORD, create_general_user, signup

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/me"
PASSWORD = "/api/v1/me/password"


def _db(settings) -> sqlite3.Connection:
    return connect(settings.database_path)


# ───────── 新規登録 ─────────


def test_signup_creates_organization_and_master_and_logs_in(client):
    body = signup(client, email="Master@Example.com")

    assert body["role"] == "master"
    assert body["email"] == "master@example.com"  # 小文字にそろえて保存
    assert body["organization"]["name"] == "組織A"
    assert body["must_change_password"] is False

    cookie = client.cookies.get("session")
    assert cookie
    assert client.get(ME).json()["id"] == body["id"]


def test_signup_cookie_is_httponly_and_samesite_lax(client):
    res = client.post(
        SIGNUP,
        json={"organization_name": "組織A", "email": "m@example.com", "password": MASTER_PASSWORD},
    )
    set_cookie = res.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_signup_rejects_duplicate_email_case_insensitive(client):
    signup(client, email="master@example.com")
    res = client.post(
        SIGNUP,
        json={"organization_name": "組織B", "email": "MASTER@example.com", "password": "x" * 8},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "EMAIL_TAKEN"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"organization_name": "A", "email": "not-an-email", "password": "x" * 8}, "email"),
        ({"organization_name": "A", "email": "a@example.com", "password": "short"}, "password"),
        (
            {"organization_name": "   ", "email": "a@example.com", "password": "x" * 8},
            "organization_name",
        ),
    ],
)
def test_signup_validates_input(client, payload, field):
    res = client.post(SIGNUP, json=payload)
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert field in {e["field"] for e in body["errors"]}


def test_signup_is_rate_limited_per_ip(client):
    for i in range(5):
        client.post(
            SIGNUP,
            json={"organization_name": "A", "email": f"u{i}@example.com", "password": "x" * 8},
        )
    res = client.post(
        SIGNUP, json={"organization_name": "A", "email": "u9@example.com", "password": "x" * 8}
    )
    assert res.status_code == 429
    assert res.json()["code"] == "RATE_LIMITED"


# ───────── ログイン・ログアウト ─────────


def test_login_and_logout(client):
    signup(client)
    client.post(LOGOUT)
    assert client.get(ME).status_code == 401

    res = client.post(LOGIN, json={"email": "MASTER@example.com", "password": MASTER_PASSWORD})
    assert res.status_code == 200
    assert res.json()["role"] == "master"
    assert client.get(ME).status_code == 200


def test_login_failure_does_not_reveal_whether_email_exists(client):
    signup(client)
    client.post(LOGOUT)

    wrong_password = client.post(LOGIN, json={"email": "master@example.com", "password": "nope"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": "nope"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["code"] == "INVALID_CREDENTIALS"


def test_login_is_rate_limited_after_repeated_failures(client):
    signup(client)
    client.post(LOGOUT)
    for _ in range(10):
        client.post(LOGIN, json={"email": "master@example.com", "password": "wrong"})

    # 正しいパスワードでも、制限中は受け付けない
    res = client.post(LOGIN, json={"email": "master@example.com", "password": MASTER_PASSWORD})
    assert res.status_code == 429


def test_login_rejects_form_encoded_body(client):
    """CSRF 対策: JSON 以外の送信は受け付けない。"""
    signup(client)
    client.post(LOGOUT)
    res = client.post(LOGIN, data={"email": "master@example.com", "password": MASTER_PASSWORD})
    assert res.status_code == 422


def test_logout_without_session_is_ok(client):
    assert client.post(LOGOUT).status_code == 204


# ───────── セッション ─────────


def test_me_requires_login(client):
    res = client.get(ME)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_invalid_token_is_rejected(client):
    client.cookies.set("session", "forged-token")
    assert client.get(ME).status_code == 401


def test_expired_session_is_rejected(client, settings):
    signup(client)
    conn = _db(settings)
    with conn:
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00Z'")
    conn.close()
    assert client.get(ME).status_code == 401


def test_session_token_is_stored_hashed(client, settings):
    signup(client)
    token = client.cookies.get("session")
    conn = _db(settings)
    stored = [row[0] for row in conn.execute("SELECT token_hash FROM sessions")]
    conn.close()
    assert token not in stored
    assert hash_session_token(token) in stored


# ───────── 一般ユーザーの初回ログインとパスワード変更 ─────────


def test_general_user_must_change_password_first(client, settings):
    master = signup(client)
    client.post(LOGOUT)
    create_general_user(settings, master["organization"]["id"])

    res = client.post(LOGIN, json={"email": "general@example.com", "password": GENERAL_PASSWORD})
    me = res.json()
    assert me["role"] == "general"
    assert me["must_change_password"] is True
    assert me["profile_completed"] is False

    res = client.put(
        PASSWORD,
        json={"current_password": GENERAL_PASSWORD, "new_password": "my-new-pass-1"},
    )
    assert res.status_code == 204
    assert client.get(ME).json()["must_change_password"] is False

    # 新しいパスワードでログインでき、古いパスワードでは失敗する
    client.post(LOGOUT)
    ok = client.post(LOGIN, json={"email": "general@example.com", "password": "my-new-pass-1"})
    ng = client.post(LOGIN, json={"email": "general@example.com", "password": GENERAL_PASSWORD})
    assert ok.status_code == 200
    assert ng.status_code == 401


def test_change_password_rejects_wrong_current_password(client):
    signup(client)
    res = client.put(PASSWORD, json={"current_password": "wrong", "new_password": "x" * 8})
    assert res.status_code == 422
    assert res.json()["code"] == "INVALID_CURRENT_PASSWORD"


def test_change_password_rejects_same_password(client):
    signup(client)
    res = client.put(
        PASSWORD, json={"current_password": MASTER_PASSWORD, "new_password": MASTER_PASSWORD}
    )
    assert res.status_code == 422
    assert res.json()["code"] == "SAME_PASSWORD"


def test_change_password_logs_out_other_sessions(client, settings):
    from fastapi.testclient import TestClient

    signup(client)
    # 同じアカウントで別の端末からログインしておく
    other = TestClient(client.app)
    other.post(LOGIN, json={"email": "master@example.com", "password": MASTER_PASSWORD})
    assert other.get(ME).status_code == 200

    client.put(PASSWORD, json={"current_password": MASTER_PASSWORD, "new_password": "new-pass-99"})

    assert client.get(ME).status_code == 200  # 変更した端末はそのまま
    assert other.get(ME).status_code == 401  # 他の端末はログアウトされる
