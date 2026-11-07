import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.core.time import to_iso, utc_now
from app.db.connection import connect
from app.entities.user import Role
from app.repositories.user_repository import UserRepository
from app.services.user_service import MAX_GENERAL_USERS
from tests.conftest import login_general, signup

API = "/api/v1"
IMPORT = f"{API}/users/import"


@pytest.fixture
def master(client) -> dict:
    return signup(client)


def _import(c: TestClient, text: str, *, dry_run: bool = False, encoding: str = "utf-8"):
    return c.post(
        IMPORT,
        params={"dry_run": str(dry_run).lower()},
        files={"file": ("users.csv", text.encode(encoding), "text/csv")},
    )


def _emails(c: TestClient) -> list[str]:
    return [u["email"] for u in c.get(f"{API}/users").json()["items"] if u["role"] == "general"]


CSV_OK = "メールアドレス,初期パスワード\nTaro@Example.com,\nhanako@example.com,hanako-pass-1\n"


def test_dry_run_checks_without_creating(client, master):
    res = _import(client, CSV_OK, dry_run=True)
    body = res.json()
    assert res.status_code == 200
    assert body["created"] is False
    assert [(r["line"], r["email"], r["error"]) for r in body["rows"]] == [
        (2, "taro@example.com", None),
        (3, "hanako@example.com", None),
    ]
    # 確認だけのときはパスワードを返さない（CSV に書かれていたかどうかだけ返す）
    assert all(r["initial_password"] is None for r in body["rows"])
    assert [r["password_provided"] for r in body["rows"]] == [False, True]
    assert _emails(client) == []


def test_import_creates_users_and_returns_passwords(client, master):
    body = _import(client, CSV_OK).json()
    assert body["created"] is True
    passwords = {r["email"]: r["initial_password"] for r in body["rows"]}
    assert passwords["hanako@example.com"] == "hanako-pass-1"
    generated = passwords["taro@example.com"]
    assert len(generated) == 12

    assert sorted(_emails(client)) == ["hanako@example.com", "taro@example.com"]

    # 返された初期パスワードでログインでき、初回はパスワード変更が求められる
    other = TestClient(client.app)
    res = other.post(f"{API}/auth/login", json={"email": "taro@example.com", "password": generated})
    assert res.json()["must_change_password"] is True
    # 在席状態（未出勤）も用意されている
    other.put(f"{API}/me/password", json={"current_password": generated, "new_password": "x" * 8})
    other.put(f"{API}/me/profile", json={"name": "太郎", "birth_date": "1990-01-01"})
    assert other.get(f"{API}/me/presence").json()["status"] == "not_working"


@pytest.mark.parametrize(
    ("line", "error_part"),
    [
        ("not-an-email,", "形式"),
        # すべてのセルが空の行は「空行」として無視するので、パスワードだけある行で確認する
        (",only-password-1", "空欄"),
        ("a@example.com,short", "8〜128文字"),
    ],
)
def test_row_errors_prevent_any_creation(client, master, line, error_part):
    text = f"メールアドレス,初期パスワード\nok@example.com,\n{line}\n"
    body = _import(client, text).json()
    assert body["created"] is False
    bad = next(r for r in body["rows"] if r["line"] == 3)
    assert error_part in bad["error"]
    assert _emails(client) == []  # 正しい行も含めて、1人も作成されない


def test_duplicate_in_file(client, master):
    body = _import(client, "email\na@example.com\nA@example.com\n").json()
    assert body["rows"][0]["error"] is None
    assert "重複" in body["rows"][1]["error"]


def test_existing_email_including_other_organization(client, master):
    other = TestClient(client.app)
    signup(other, email="taken@example.com", org="組織B")
    body = _import(client, "email\ntaken@example.com\n").json()
    assert "既に登録" in body["rows"][0]["error"]


def test_user_limit(client, master, settings):
    conn = connect(settings.database_path)
    password_hash = hash_password("x" * 8)
    with conn:
        for i in range(MAX_GENERAL_USERS - 1):
            UserRepository(conn).create(
                organization_id=master["organization"]["id"],
                email=f"u{i}@example.com",
                password_hash=password_hash,
                role=Role.GENERAL,
                must_change_password=True,
                now=to_iso(utc_now()),
            )
    conn.close()

    body = _import(client, "email\na@example.com\nb@example.com\n").json()
    assert body["created"] is False
    assert "あと1名" in body["error"]
    assert _import(client, "email\na@example.com\n").json()["created"] is True


def test_shift_jis_file(client, master):
    text = "メールアドレス,初期パスワード\r\nsjis@example.com,\r\n"
    assert _import(client, text, encoding="cp932").json()["created"] is True


def test_broken_file_is_rejected(client, master):
    res = _import(client, "名前\n山田\n")
    assert res.status_code == 422
    assert res.json()["code"] == "CSV_INVALID"


def test_general_user_cannot_import(client, master):
    general = login_general(client)
    assert _import(general, CSV_OK).status_code == 403
