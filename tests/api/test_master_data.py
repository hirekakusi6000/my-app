import pytest
from fastapi.testclient import TestClient

from app.entities.master_data import DEFAULT_JOB_TYPES, DEFAULT_POSITIONS
from tests.conftest import GENERAL_PASSWORD, login_general, signup

API = "/api/v1"


@pytest.fixture
def master(client) -> dict:
    return signup(client)


def test_signup_seeds_default_candidates(client, master):
    positions = [p["name"] for p in client.get(f"{API}/positions").json()]
    job_types = {j["name"]: j["is_engineer"] for j in client.get(f"{API}/job-types").json()}
    languages = client.get(f"{API}/skills", params={"category": "language"}).json()

    assert positions == DEFAULT_POSITIONS
    assert job_types == dict(DEFAULT_JOB_TYPES)
    assert languages and all(s["category"] == "language" for s in languages)


def test_master_can_manage_positions(client, master):
    created = client.post(f"{API}/positions", json={"name": "  執行役員  "}).json()
    assert created["name"] == "執行役員"

    res = client.patch(f"{API}/positions/{created['id']}", json={"name": "取締役"})
    assert res.json()["name"] == "取締役"

    assert client.delete(f"{API}/positions/{created['id']}").status_code == 204
    names = [p["name"] for p in client.get(f"{API}/positions").json()]
    assert "取締役" not in names


def test_job_type_engineer_flag_can_be_changed(client, master):
    designer = next(j for j in client.get(f"{API}/job-types").json() if j["name"] == "デザイナー")
    res = client.patch(
        f"{API}/job-types/{designer['id']}", json={"name": "デザイナー", "is_engineer": True}
    )
    assert res.json()["is_engineer"] is True


def test_skill_create_and_duplicate(client, master):
    res = client.post(f"{API}/skills", json={"category": "language", "name": "Rust"})
    assert res.status_code == 201
    dup = client.post(f"{API}/skills", json={"category": "language", "name": "rust"})
    assert dup.status_code == 409
    assert dup.json()["code"] == "NAME_TAKEN"
    # 分類が違えば同じ名前でもよい
    other = client.post(f"{API}/skills", json={"category": "cloud", "name": "Rust"})
    assert other.status_code == 201


def test_rename_to_existing_name_is_conflict(client, master):
    first = client.get(f"{API}/positions").json()[0]
    res = client.patch(f"{API}/positions/{first['id']}", json={"name": "課長"})
    assert res.status_code == 409


def test_invalid_category_is_rejected(client, master):
    res = client.post(f"{API}/skills", json={"category": "hardware", "name": "x"})
    assert res.status_code == 422


def test_general_user_can_read_but_not_modify(client, master):
    general = login_general(client)
    assert general.get(f"{API}/positions").status_code == 200
    assert general.post(f"{API}/positions", json={"name": "x"}).status_code == 403


def test_candidates_readable_before_profile_but_not_before_password_change(client, master):
    client.post(
        f"{API}/users", json={"email": "new@example.com", "initial_password": GENERAL_PASSWORD}
    )
    fresh = TestClient(client.app)
    fresh.post(f"{API}/auth/login", json={"email": "new@example.com", "password": GENERAL_PASSWORD})
    res = fresh.get(f"{API}/positions")
    assert res.status_code == 403
    assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_candidates_are_separated_by_organization(client, master):
    client.post(f"{API}/positions", json={"name": "組織Aだけの役職"})
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")

    names = [p["name"] for p in other.get(f"{API}/positions").json()]
    assert "組織Aだけの役職" not in names

    own = next(p for p in client.get(f"{API}/positions").json() if p["name"] == "組織Aだけの役職")
    assert other.patch(f"{API}/positions/{own['id']}", json={"name": "x"}).status_code == 404
    assert other.delete(f"{API}/positions/{own['id']}").status_code == 404
