import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect
from tests.conftest import MASTER_PASSWORD, login_general, signup

API = "/api/v1"
ORG = f"{API}/organization"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

# 組織のデータを持つテーブル（削除後に1行も残っていないことを確認する）
ORG_TABLES = [
    "users",
    "positions",
    "job_types",
    "skills",
    "floors",
    "rooms",
    "furniture",
    "presence",
]


@pytest.fixture
def org(client, settings) -> dict:
    """フロア・部屋・座席・従業員（画像・スキル・出社中）がそろった組織。"""
    master = signup(client)
    floor = client.post(f"{API}/floors", json={"name": "1F"}).json()
    room = client.post(f"{API}/floors/{floor['id']}/rooms", json={"name": "A"}).json()
    seat = client.put(
        f"{API}/rooms/{room['id']}/layout",
        json={"furniture": [{"type": "chair", "x": 0, "y": 0, "width": 1, "height": 1}]},
    ).json()["furniture"][0]

    general = login_general(client)
    general.put(
        f"{API}/me/profile",
        json={"name": "山田 太郎", "birth_date": "1990-04-01", "job_type_name": "エンジニア"},
    )
    general.put(
        f"{API}/me/skills", json={"skills": [{"category": "language", "name": "Go", "years": 3}]}
    )
    general.put(f"{API}/me/avatar", files={"file": ("a.png", PNG, "image/png")})
    general.put(f"{API}/me/presence", json={"status": "present", "seat_id": seat["id"]})
    return {"id": master["organization"]["id"], "general": general}


def _delete(c: TestClient, password: str = MASTER_PASSWORD, name: str = "組織A"):
    return c.request("DELETE", ORG, json={"password": password, "confirm_name": name})


def _count(settings, table: str, organization_id: int) -> int:
    conn = connect(settings.database_path)
    try:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE organization_id = ?", (organization_id,)
        ).fetchone()[0]
    finally:
        conn.close()


# ───────── 参照・名前の変更 ─────────


def test_read_and_rename(client, org):
    assert client.get(ORG).json()["name"] == "組織A"
    res = client.patch(ORG, json={"name": "  新しい組織名  "})
    assert res.json()["name"] == "新しい組織名"
    assert client.get(f"{API}/me").json()["organization"]["name"] == "新しい組織名"


@pytest.mark.parametrize("name", ["", "   ", "あ" * 101])
def test_rename_validation(client, org, name):
    assert client.patch(ORG, json={"name": name}).status_code == 422


# ───────── 削除 ─────────


def test_delete_removes_everything(client, org, settings):
    assert len(list(settings.upload_dir.iterdir())) == 1  # プロフィール画像

    res = _delete(client)
    assert res.status_code == 204
    assert 'session=""' in res.headers["set-cookie"] or "Max-Age=0" in res.headers["set-cookie"]

    for table in ORG_TABLES:
        assert _count(settings, table, org["id"]) == 0, table
    conn = connect(settings.database_path)
    assert conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM user_skills").fetchone()[0] == 0
    conn.close()
    assert list(settings.upload_dir.iterdir()) == []

    # 削除した組織のアカウントではログインできず、ログイン中だった人も締め出される
    assert client.get(f"{API}/me").status_code == 401
    assert org["general"].get(f"{API}/me").status_code == 401
    res = client.post(
        f"{API}/auth/login", json={"email": "master@example.com", "password": MASTER_PASSWORD}
    )
    assert res.status_code == 401


def test_same_email_can_sign_up_again_after_deletion(client, org):
    _delete(client)
    signup(client, email="master@example.com", org="作り直した組織")


def test_delete_requires_correct_password(client, org, settings):
    res = _delete(client, password="wrong-password")
    assert res.json()["code"] == "INVALID_PASSWORD"
    assert _count(settings, "users", org["id"]) > 0


@pytest.mark.parametrize("name", ["組織B", "組織", " 組織A x"])
def test_delete_requires_exact_organization_name(client, org, name):
    res = _delete(client, name=name)
    assert res.json()["code"] == "NAME_MISMATCH"


def test_other_organizations_are_not_affected(client, org, settings):
    other = TestClient(client.app)
    other_master = signup(other, email="b@example.com", org="組織B")
    other.post(f"{API}/floors", json={"name": "1F"})

    _delete(client)

    assert other.get(f"{API}/me").status_code == 200
    assert _count(settings, "floors", other_master["organization"]["id"]) == 1
    assert _count(settings, "positions", other_master["organization"]["id"]) > 0


# ───────── 権限 ─────────


def test_general_user_cannot_manage_organization(client, org):
    general = org["general"]
    assert general.get(ORG).status_code == 403
    assert general.patch(ORG, json={"name": "乗っ取り"}).status_code == 403
    assert _delete(general, password="general-pass-123").status_code == 403


def test_anonymous_cannot_manage_organization(client):
    assert client.get(ORG).status_code == 401
    assert _delete(client).status_code == 401
