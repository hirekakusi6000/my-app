import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.core.time import to_iso, utc_now
from app.db.connection import connect
from app.entities.user import Role
from app.repositories.user_repository import UserRepository
from app.services.user_service import MAX_GENERAL_USERS
from tests.conftest import MASTER_PASSWORD, signup

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
INITIAL = "initial-pass-123"


def _create(client: TestClient, email: str = "taro@example.com") -> dict:
    res = client.post(USERS, json={"email": email, "initial_password": INITIAL})
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def master(client) -> dict:
    return signup(client)


@pytest.fixture
def other_client(client) -> TestClient:
    """別の組織のマスターとしてログインしたクライアント。"""
    other = TestClient(client.app)
    signup(other, email="other-master@example.com", org="組織B")
    return other


# ───────── 一覧・作成 ─────────


def test_create_general_user(client, master, settings):
    user = _create(client, "Taro@Example.com")

    assert user["email"] == "taro@example.com"
    assert user["role"] == "general"
    assert user["must_change_password"] is True

    # 在席状態が「未出勤」で用意される
    conn = connect(settings.database_path)
    row = conn.execute("SELECT status, seat_id FROM presence WHERE user_id = ?", (user["id"],))
    assert tuple(row.fetchone()) == ("not_working", None)
    conn.close()

    # 作成したユーザーは初期パスワードでログインできる
    other = TestClient(client.app)
    res = other.post(LOGIN, json={"email": "taro@example.com", "password": INITIAL})
    assert res.json()["must_change_password"] is True


def test_list_users_shows_only_own_organization(client, master, other_client):
    _create(client, "a@example.com")
    _create(other_client, "b@example.com")

    body = client.get(USERS).json()
    emails = [u["email"] for u in body["items"]]
    assert emails == ["master@example.com", "a@example.com"]  # マスターが先頭
    assert body["general_user_count"] == 1
    assert body["general_user_limit"] == MAX_GENERAL_USERS


def test_create_rejects_duplicate_email_across_organizations(client, master, other_client):
    _create(other_client, "dup@example.com")
    res = client.post(USERS, json={"email": "DUP@example.com", "initial_password": INITIAL})
    assert res.status_code == 409
    assert res.json()["code"] == "EMAIL_TAKEN"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"email": "bad", "initial_password": INITIAL}, "email"),
        ({"email": "a@example.com", "initial_password": "short"}, "initial_password"),
    ],
)
def test_create_validates_input(client, master, payload, field):
    res = client.post(USERS, json=payload)
    assert res.status_code == 422
    assert field in {e["field"] for e in res.json()["errors"]}


def test_create_is_limited_to_50_general_users(client, master, settings):
    conn = connect(settings.database_path)
    password_hash = hash_password(INITIAL)
    with conn:
        repo = UserRepository(conn)
        for i in range(MAX_GENERAL_USERS):
            repo.create(
                organization_id=master["organization"]["id"],
                email=f"user{i}@example.com",
                password_hash=password_hash,
                role=Role.GENERAL,
                must_change_password=True,
                now=to_iso(utc_now()),
            )
    conn.close()

    res = client.post(USERS, json={"email": "one-more@example.com", "initial_password": INITIAL})
    assert res.status_code == 422
    assert res.json()["code"] == "LIMIT_EXCEEDED"


# ───────── 変更・リセット・削除 ─────────


def test_update_email(client, master):
    user = _create(client)
    res = client.patch(f"{USERS}/{user['id']}", json={"email": "new@example.com"})
    assert res.status_code == 200
    assert res.json()["email"] == "new@example.com"


def test_update_email_rejects_taken_address(client, master):
    user = _create(client, "a@example.com")
    _create(client, "b@example.com")
    res = client.patch(f"{USERS}/{user['id']}", json={"email": "b@example.com"})
    assert res.status_code == 409


def test_update_email_to_same_address_is_ok(client, master):
    user = _create(client, "a@example.com")
    res = client.patch(f"{USERS}/{user['id']}", json={"email": "A@example.com"})
    assert res.status_code == 200


def test_reset_password_forces_change_and_logs_out(client, master):
    user = _create(client)
    general = TestClient(client.app)
    general.post(LOGIN, json={"email": "taro@example.com", "password": INITIAL})
    general.put(
        "/api/v1/me/password",
        json={"current_password": INITIAL, "new_password": "chosen-pass-1"},
    )
    assert general.get("/api/v1/me").json()["must_change_password"] is False

    res = client.post(f"{USERS}/{user['id']}/password-reset", json={"new_password": "reset-pass-1"})
    assert res.status_code == 204

    assert general.get("/api/v1/me").status_code == 401  # ログアウトされる
    res = general.post(LOGIN, json={"email": "taro@example.com", "password": "reset-pass-1"})
    assert res.json()["must_change_password"] is True


def test_delete_user_removes_user_and_frees_seat(client, master, settings):
    user = _create(client)
    conn = connect(settings.database_path)
    with conn:
        org_id = master["organization"]["id"]
        floor_id = conn.execute(
            "INSERT INTO floors (organization_id, name) VALUES (?, '1F')", (org_id,)
        ).lastrowid
        room_id = conn.execute(
            "INSERT INTO rooms (organization_id, floor_id, name, width, height)"
            " VALUES (?, ?, '執務室', 20, 10)",
            (org_id, floor_id),
        ).lastrowid
        seat_id = conn.execute(
            "INSERT INTO furniture (organization_id, room_id, type, x, y, width, height)"
            " VALUES (?, ?, 'chair', 1, 1, 1, 1)",
            (org_id, room_id),
        ).lastrowid
        conn.execute(
            "UPDATE presence SET status = 'present', seat_id = ? WHERE user_id = ?",
            (seat_id, user["id"]),
        )

    assert client.delete(f"{USERS}/{user['id']}").status_code == 204

    assert conn.execute("SELECT COUNT(*) FROM users WHERE id = ?", (user["id"],)).fetchone()[0] == 0
    assert (
        conn.execute("SELECT COUNT(*) FROM presence WHERE seat_id = ?", (seat_id,)).fetchone()[0]
        == 0
    )
    conn.close()

    other = TestClient(client.app)
    res = other.post(LOGIN, json={"email": "taro@example.com", "password": INITIAL})
    assert res.status_code == 401


# ───────── 権限・組織の分離 ─────────


@pytest.mark.parametrize(
    ("method", "suffix", "payload"),
    [
        ("patch", "", {"email": "x@example.com"}),
        ("post", "/password-reset", {"new_password": "reset-pass-1"}),
        ("delete", "", None),
    ],
)
def test_cannot_touch_users_of_other_organization(
    client, master, other_client, method, suffix, payload
):
    victim = _create(other_client, "victim@example.com")
    kwargs = {"json": payload} if payload else {}
    res = getattr(client, method)(f"{USERS}/{victim['id']}{suffix}", **kwargs)
    assert res.status_code == 404

    # 他の組織のユーザーは変更されていない
    emails = [u["email"] for u in other_client.get(USERS).json()["items"]]
    assert "victim@example.com" in emails


def test_master_cannot_modify_self(client, master):
    res = client.delete(f"{USERS}/{master['id']}")
    assert res.status_code == 422
    assert res.json()["code"] == "CANNOT_MODIFY_SELF"


def test_unknown_user_is_404(client, master):
    assert client.delete(f"{USERS}/99999").status_code == 404


def test_general_user_cannot_use_user_management(client, master):
    _create(client)
    client.post(LOGOUT)
    client.post(LOGIN, json={"email": "taro@example.com", "password": INITIAL})
    client.put(
        "/api/v1/me/password",
        json={"current_password": INITIAL, "new_password": "chosen-pass-1"},
    )

    assert client.get(USERS).status_code == 403
    res = client.post(USERS, json={"email": "x@example.com", "initial_password": INITIAL})
    assert res.status_code == 403


def test_anonymous_cannot_use_user_management(client):
    assert client.get(USERS).status_code == 401


def test_master_password_is_unchanged_by_user_operations(client, master):
    """念のため: 一般ユーザーの操作でマスターのログインに影響がないこと。"""
    user = _create(client)
    client.delete(f"{USERS}/{user['id']}")
    client.post(LOGOUT)
    res = client.post(LOGIN, json={"email": "master@example.com", "password": MASTER_PASSWORD})
    assert res.status_code == 200
