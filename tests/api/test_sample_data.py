import pytest
from fastapi.testclient import TestClient

from app.services.sample_data_service import SAMPLE_EMPLOYEES
from tests.conftest import login_general, signup

API = "/api/v1"
SAMPLE = f"{API}/organization/sample-data"


@pytest.fixture
def master(client) -> dict:
    return signup(client)


def test_available_only_for_empty_organization(client, master):
    assert client.get(SAMPLE).json() == {"available": True}
    assert client.post(SAMPLE).status_code == 201
    assert client.get(SAMPLE).json() == {"available": False}


def test_creates_map_and_employees(client, master):
    client.post(SAMPLE)

    floors = client.get(f"{API}/floors").json()
    assert len(floors) == 1
    room = floors[0]["rooms"][0]
    layout = client.get(f"{API}/rooms/{room['id']}/layout").json()
    chairs = [f for f in layout["furniture"] if f["type"] == "chair"]
    assert len(chairs) == 12

    users = client.get(f"{API}/users").json()
    assert users["general_user_count"] == len(SAMPLE_EMPLOYEES)
    generals = [u for u in users["items"] if u["role"] == "general"]
    # 初回設定が済んだ従業員として作られる（ユーザー管理では「利用中」と表示される）
    assert all(u["profile_completed"] and not u["must_change_password"] for u in generals)

    statuses = {e["name"]: e["status"] for e in client.get(f"{API}/presence").json()}
    assert statuses == {e.name: e.status.value for e in SAMPLE_EMPLOYEES}

    # 在席中・離席中の人はマップに表示される
    seated = {o["name"] for o in client.get(f"{API}/rooms/{room['id']}/occupancy").json()}
    assert seated == {e.name for e in SAMPLE_EMPLOYEES if e.seat}


def test_engineers_have_skills(client, master):
    client.post(SAMPLE)
    entries = {e["name"]: e["user_id"] for e in client.get(f"{API}/presence").json()}
    engineer = client.get(f"{API}/profiles/{entries['山田 太郎']}").json()
    assert engineer["is_engineer"] is True
    assert ("Python", 10) in {(s["name"], s["years"]) for s in engineer["skills"]}
    designer = client.get(f"{API}/profiles/{entries['佐藤 花子']}").json()
    assert designer["skills"] == []


def test_cannot_create_twice(client, master):
    client.post(SAMPLE)
    res = client.post(SAMPLE)
    assert res.status_code == 422
    assert res.json()["code"] == "ORGANIZATION_NOT_EMPTY"


@pytest.mark.parametrize("existing", ["floor", "user"])
def test_not_available_when_organization_has_data(client, master, existing):
    if existing == "floor":
        client.post(f"{API}/floors", json={"name": "1F"})
    else:
        client.post(f"{API}/users", json={"email": "a@example.com", "initial_password": "x" * 8})
    assert client.get(SAMPLE).json() == {"available": False}
    assert client.post(SAMPLE).json()["code"] == "ORGANIZATION_NOT_EMPTY"


def test_sample_users_cannot_log_in_until_password_reset(client, master):
    client.post(SAMPLE)
    sample = next(u for u in client.get(f"{API}/users").json()["items"] if u["role"] == "general")

    other = TestClient(client.app)
    res = other.post(f"{API}/auth/login", json={"email": sample["email"], "password": "anything"})
    assert res.status_code == 401

    client.post(f"{API}/users/{sample['id']}/password-reset", json={"new_password": "try-me-123"})
    res = other.post(f"{API}/auth/login", json={"email": sample["email"], "password": "try-me-123"})
    assert res.status_code == 200
    assert res.json()["profile_completed"] is True


def test_two_organizations_can_both_create_samples(client, master):
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")
    assert client.post(SAMPLE).status_code == 201
    assert other.post(SAMPLE).status_code == 201
    # お互いのサンプルは見えない
    assert len(other.get(f"{API}/presence").json()) == len(SAMPLE_EMPLOYEES)


def test_general_user_cannot_create_samples(client, master):
    general = login_general(client)
    assert general.get(SAMPLE).status_code == 403
    assert general.post(SAMPLE).status_code == 403
