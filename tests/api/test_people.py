"""メンバー検索。お試し用のサンプルデータ（従業員6人）を使って確認する。

サンプルの主な内容:
  山田 太郎  在席中  Python 10年 / FastAPI 4年 / PostgreSQL 8年 / AWS 6年
  佐藤 花子  在席中  （デザイナー・スキルなし）
  鈴木 一郎  離席中  TypeScript 3年 / React 3年 / Vue.js 1年 / AWS 1年
  高橋 美咲  リモート Go 2年 / Python 4年 / MySQL 3年 / Google Cloud 2年
  田中 健太  在席中  （営業）
  伊藤 さくら 未出勤  （事務）
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import login_general, signup

API = "/api/v1"
PEOPLE = f"{API}/people"


@pytest.fixture
def org(client) -> TestClient:
    signup(client)
    assert client.post(f"{API}/organization/sample-data").status_code == 201
    return client


def _names(c: TestClient, params=None) -> list[str]:
    res = c.get(PEOPLE, params=params)
    assert res.status_code == 200, res.text
    return [p["name"] for p in res.json()]


def test_lists_everyone_with_office_people_first(org):
    names = _names(org)
    assert len(names) == 6
    assert names[-1] == "伊藤 さくら"  # 未出勤の人は最後
    assert names.index("高橋 美咲") > names.index("鈴木 一郎")  # 離席中 → リモートの順


def test_search_by_name(org):
    assert _names(org, {"q": "田"}) == ["山田 太郎", "田中 健太"]
    assert _names(org, {"q": "  佐藤 "}) == ["佐藤 花子"]


@pytest.mark.parametrize("q", ["%", "_", "\\"])
def test_like_wildcards_are_treated_as_text(org, q):
    assert _names(org, {"q": q}) == []


def test_search_by_skill_case_insensitive(org):
    assert sorted(_names(org, {"skill": "python"})) == ["山田 太郎", "高橋 美咲"]


def test_min_years(org):
    assert _names(org, {"skill": "Python", "min_years": 5}) == ["山田 太郎"]
    assert _names(org, {"skill": "AWS", "min_years": 1}) == ["山田 太郎", "鈴木 一郎"]


def test_multiple_skills_mean_and(org):
    assert _names(org, [("skill", "Python"), ("skill", "AWS")]) == ["山田 太郎"]
    assert _names(org, [("skill", "Python"), ("skill", "React")]) == []


def test_filter_by_status(org):
    assert _names(org, {"status": "remote"}) == ["高橋 美咲"]
    office = _names(org, [("status", "present"), ("status", "away")])
    assert sorted(office) == ["佐藤 花子", "山田 太郎", "田中 健太", "鈴木 一郎"]


def test_result_contains_seat_and_skills(org):
    person = org.get(PEOPLE, params={"q": "山田"}).json()[0]
    assert person["status"] == "present"
    assert person["seat"]["label"] == "A-1"
    assert person["seat"]["room_name"] == "執務室"
    assert person["skills"][0] == {"category": "language", "name": "Python", "years": 10}
    assert person["position"] == "課長"


@pytest.mark.parametrize(
    "params",
    [
        {"min_years": -1},
        {"min_years": 51},
        {"status": "sleeping"},
        {"q": "あ" * 51},
        [("skill", f"s{i}") for i in range(6)],
    ],
)
def test_invalid_conditions(org, params):
    assert org.get(PEOPLE, params=params).status_code == 422


def test_general_user_can_search(org):
    general = login_general(org, "searcher@example.com")
    general.put(
        f"{API}/me/profile",
        json={"name": "検索 する人", "birth_date": "1990-01-01", "job_type_name": "営業"},
    )
    assert "山田 太郎" in _names(general, {"skill": "Python"})


def test_requires_completed_setup(org):
    newcomer = login_general(org, "newcomer@example.com")
    res = newcomer.get(PEOPLE)
    assert res.json()["code"] == "SETUP_REQUIRED"


def test_people_of_other_organization_are_not_found(org):
    other = TestClient(org.app)
    signup(other, email="b@example.com", org="組織B")
    assert _names(other) == []
    assert _names(other, {"skill": "Python"}) == []
