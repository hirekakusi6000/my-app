from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.time import calculate_age, today_jst
from app.db.connection import connect
from tests.conftest import login_general, signup

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64

PROFILE = {
    "name": "山田 太郎",
    "birth_date": "1990-04-01",
    "position_name": "課長",
    "job_type_name": "エンジニア",
}


@pytest.fixture
def master(client) -> dict:
    return signup(client)


@pytest.fixture
def general(client, master) -> TestClient:
    return login_general(client)


def _register(c: TestClient, **overrides) -> dict:
    res = c.put(f"{API}/me/profile", json={**PROFILE, **overrides})
    assert res.status_code == 200, res.text
    return res.json()


def _upload(c: TestClient, data: bytes = PNG, name: str = "a.png"):
    return c.put(f"{API}/me/avatar", files={"file": (name, data, "application/octet-stream")})


# ───────── 登録 ─────────


def test_profile_is_not_registered_initially(general):
    res = general.get(f"{API}/me/profile")
    assert res.status_code == 404
    assert res.json()["code"] == "PROFILE_NOT_REGISTERED"
    assert general.get(f"{API}/me").json()["profile_completed"] is False


def test_register_profile(general):
    body = _register(general)

    assert body["name"] == "山田 太郎"
    assert body["position"] == "課長"
    assert body["job_type"] == "エンジニア"
    assert body["is_engineer"] is True
    assert body["age"] == calculate_age(date(1990, 4, 1), today_jst())
    assert general.get(f"{API}/me").json()["profile_completed"] is True


def test_new_position_name_is_added_to_candidates(general):
    _register(general, position_name="テックリード", job_type_name="データ分析")
    positions = [p["name"] for p in general.get(f"{API}/positions").json()]
    job_types = {j["name"]: j["is_engineer"] for j in general.get(f"{API}/job-types").json()}
    assert "テックリード" in positions
    assert job_types["データ分析"] is False


def test_existing_name_is_reused_case_insensitive(client, general):
    _register(general, job_type_name="エンジニア")
    before = len(client.get(f"{API}/skills").json())
    _register(general, position_name="課長")
    assert len(client.get(f"{API}/positions").json()) == 5  # 既定の5件のまま
    assert len(client.get(f"{API}/skills").json()) == before


def test_blank_position_and_job_type_mean_none(general):
    body = _register(general, position_name="  ", job_type_name="")
    assert body["position"] is None
    assert body["job_type"] is None
    assert body["is_engineer"] is False


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"name": "  "}, 422, "VALIDATION_ERROR"),
        ({"birth_date": "1990/04/01"}, 422, "VALIDATION_ERROR"),
        ({"birth_date": "2999-01-01"}, 422, "INVALID_BIRTH_DATE"),
        ({"birth_date": "1899-12-31"}, 422, "INVALID_BIRTH_DATE"),
        ({"default_seat_id": 99999}, 422, "INVALID_SEAT"),
    ],
)
def test_profile_validation(general, overrides, status, code):
    res = general.put(f"{API}/me/profile", json={**PROFILE, **overrides})
    assert res.status_code == status
    assert res.json()["code"] == code


def test_default_seat_must_be_chair_of_own_organization(general, master, settings):
    org_id = master["organization"]["id"]
    conn = connect(settings.database_path)
    with conn:
        floor = conn.execute(
            "INSERT INTO floors (organization_id, name) VALUES (?, '1F')", (org_id,)
        ).lastrowid
        room = conn.execute(
            "INSERT INTO rooms (organization_id, floor_id, name, width, height)"
            " VALUES (?, ?, 'A', 20, 10)",
            (org_id, floor),
        ).lastrowid
        insert = (
            "INSERT INTO furniture (organization_id, room_id, type, x, y, width, height)"
            " VALUES (?, ?, ?, 1, 1, 1, 1)"
        )
        chair = conn.execute(insert, (org_id, room, "chair")).lastrowid
        desk = conn.execute(insert, (org_id, room, "desk")).lastrowid
    conn.close()

    assert _register(general, default_seat_id=chair)["default_seat_id"] == chair
    res = general.put(f"{API}/me/profile", json={**PROFILE, "default_seat_id": desk})
    assert res.json()["code"] == "INVALID_SEAT"


def test_master_has_no_profile(client, master):
    assert client.get(f"{API}/me/profile").status_code == 403
    assert client.put(f"{API}/me/profile", json=PROFILE).status_code == 403


# ───────── 技術スキル ─────────


def test_engineer_can_register_skills(general):
    _register(general)
    res = general.put(
        f"{API}/me/skills",
        json={
            "skills": [
                {"category": "language", "name": "Python", "years": 5},
                {"category": "language", "name": "Elixir", "years": 1},  # 候補にない名前
                {"category": "cloud", "name": "AWS", "years": 3},
            ]
        },
    )
    assert res.status_code == 200
    skills = general.get(f"{API}/me/profile").json()["skills"]
    assert [(s["category"], s["name"], s["years"]) for s in skills] == [
        ("language", "Python", 5),
        ("language", "Elixir", 1),
        ("cloud", "AWS", 3),
    ]
    languages = [s["name"] for s in general.get(f"{API}/skills?category=language").json()]
    assert "Elixir" in languages


def test_skills_replace_previous_ones(general):
    _register(general)
    general.put(
        f"{API}/me/skills", json={"skills": [{"category": "language", "name": "Go", "years": 2}]}
    )
    general.put(f"{API}/me/skills", json={"skills": []})
    assert general.get(f"{API}/me/profile").json()["skills"] == []


def test_duplicate_skill_is_rejected(general):
    _register(general)
    res = general.put(
        f"{API}/me/skills",
        json={
            "skills": [
                {"category": "language", "name": "Python", "years": 1},
                {"category": "language", "name": "python", "years": 2},
            ]
        },
    )
    assert res.json()["code"] == "DUPLICATE_SKILL"


@pytest.mark.parametrize("years", [-1, 51])
def test_skill_years_range(general, years):
    _register(general)
    res = general.put(
        f"{API}/me/skills",
        json={"skills": [{"category": "language", "name": "Python", "years": years}]},
    )
    assert res.status_code == 422


def test_non_engineer_cannot_register_skills(general):
    _register(general, job_type_name="営業")
    res = general.put(
        f"{API}/me/skills", json={"skills": [{"category": "language", "name": "Go", "years": 1}]}
    )
    assert res.json()["code"] == "SKILLS_NOT_ALLOWED"


def test_changing_to_non_engineer_clears_skills(general):
    _register(general)
    general.put(
        f"{API}/me/skills", json={"skills": [{"category": "language", "name": "Go", "years": 2}]}
    )
    body = _register(general, job_type_name="営業")
    assert body["skills"] == []


# ───────── プロフィール画像 ─────────


def test_avatar_requires_profile(general):
    res = _upload(general)
    assert res.status_code == 404


def test_upload_and_read_avatar(client, general, settings):
    _register(general)
    body = _upload(general).json()
    assert body["avatar_url"].startswith(f"/api/v1/users/{body['user_id']}/avatar?v=")

    res = client.get(body["avatar_url"])  # 同じ組織のマスターも見られる
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content == PNG
    assert len(list(settings.upload_dir.iterdir())) == 1


def test_replacing_avatar_removes_old_file(general, settings):
    _register(general)
    _upload(general, PNG)
    body = _upload(general, JPEG, "b.jpg").json()
    files = list(settings.upload_dir.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".jpg"
    assert body["avatar_url"]


def test_delete_avatar(general, settings):
    _register(general)
    _upload(general)
    assert general.delete(f"{API}/me/avatar").status_code == 204
    assert general.get(f"{API}/me/profile").json()["avatar_url"] is None
    assert list(settings.upload_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"GIF89a" + b"\x00" * 10, "UNSUPPORTED_FILE_TYPE"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "UNSUPPORTED_FILE_TYPE"),
        (PNG + b"\x00" * (2 * 1024 * 1024), "FILE_TOO_LARGE"),
    ],
)
def test_invalid_avatar_is_rejected(general, settings, data, code):
    _register(general)
    res = _upload(general, data, "evil.png")
    assert res.status_code == 422
    assert res.json()["code"] == code
    assert not settings.upload_dir.exists() or list(settings.upload_dir.iterdir()) == []


def test_deleting_user_removes_avatar_file(client, general, settings):
    profile = _register(general)
    _upload(general)
    client.delete(f"{API}/users/{profile['user_id']}")
    assert list(settings.upload_dir.iterdir()) == []


# ───────── 他の従業員のプロフィール ─────────


def test_colleague_can_view_profile_without_birth_date(client, general):
    me = _register(general)
    colleague = login_general(client, "hanako@example.com")
    colleague.put(f"{API}/me/profile", json={**PROFILE, "name": "佐藤 花子"})

    res = colleague.get(f"{API}/profiles/{me['user_id']}")
    body = res.json()
    assert res.status_code == 200
    assert body["name"] == "山田 太郎"
    assert body["age"] == me["age"]
    assert "birth_date" not in body
    assert body["presence"] == {"status": "not_working", "comment": None}


def test_viewing_profiles_requires_own_profile(client, general):
    me = _register(general)
    newcomer = login_general(client, "new@example.com")
    res = newcomer.get(f"{API}/profiles/{me['user_id']}")
    assert res.status_code == 403
    assert res.json()["code"] == "SETUP_REQUIRED"


def test_master_can_view_profiles(client, general):
    me = _register(general)
    assert client.get(f"{API}/profiles/{me['user_id']}").status_code == 200


def test_profiles_of_other_organization_are_hidden(client, general):
    me = _register(general)
    _upload(general)
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")

    assert other.get(f"{API}/profiles/{me['user_id']}").status_code == 404
    assert other.get(f"{API}/users/{me['user_id']}/avatar").status_code == 404


def test_master_profile_is_not_viewable(client, master, general):
    _register(general)
    assert general.get(f"{API}/profiles/{master['id']}").status_code == 404
