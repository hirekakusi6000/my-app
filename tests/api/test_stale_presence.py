"""前日から状態を更新していない人の表示と、まとめて未出勤に戻す操作。

サンプルデータ（在席中3人・離席中1人・リモート1人・未出勤1人）を使い、
一部の人の更新日時を過去にずらして確認する。
"""

import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect
from tests.conftest import login_general, signup

API = "/api/v1"
LONG_AGO = "2000-01-01T00:00:00Z"


@pytest.fixture
def org(client) -> TestClient:
    signup(client)
    assert client.post(f"{API}/organization/sample-data").status_code == 201
    return client


def _age(settings, *names: str) -> None:
    """指定した人の在席状態の更新日時を、ずっと前にする。"""
    conn = connect(settings.database_path)
    with conn:
        for name in names:
            conn.execute(
                "UPDATE presence SET updated_at = ?"
                " WHERE user_id = (SELECT user_id FROM profiles WHERE name = ?)",
                (LONG_AGO, name),
            )
    conn.close()


def _by_name(c: TestClient) -> dict[str, dict]:
    return {e["name"]: e for e in c.get(f"{API}/presence").json()}


def test_fresh_states_are_not_stale(org):
    assert not any(e["is_stale"] for e in org.get(f"{API}/presence").json())


def test_old_working_states_are_stale_but_not_working_is_not(org, settings):
    # 在席中・離席中・リモート・未出勤の人をそれぞれ古くする
    _age(settings, "山田 太郎", "鈴木 一郎", "高橋 美咲", "伊藤 さくら")
    entries = _by_name(org)
    assert entries["山田 太郎"]["is_stale"] is True  # 在席中
    assert entries["鈴木 一郎"]["is_stale"] is True  # 離席中
    assert entries["高橋 美咲"]["is_stale"] is True  # リモート
    assert entries["伊藤 さくら"]["is_stale"] is False  # 未出勤は「古い」とはみなさない
    assert entries["佐藤 花子"]["is_stale"] is False  # 古くしていない人


def test_stale_flag_on_map_and_people_search(org, settings):
    _age(settings, "山田 太郎")
    room_id = org.get(f"{API}/floors").json()[0]["rooms"][0]["id"]
    occupants = {o["name"]: o for o in org.get(f"{API}/rooms/{room_id}/occupancy").json()}
    assert occupants["山田 太郎"]["is_stale"] is True
    assert occupants["山田 太郎"]["updated_at"] == LONG_AGO
    assert occupants["佐藤 花子"]["is_stale"] is False

    people = {p["name"]: p for p in org.get(f"{API}/people").json()}
    assert people["山田 太郎"]["is_stale"] is True
    assert people["田中 健太"]["is_stale"] is False


def test_updating_own_state_clears_stale(org, settings):
    general = login_general(org, "me@example.com")
    general.put(f"{API}/me/profile", json={"name": "自分", "birth_date": "1990-01-01"})
    general.put(f"{API}/me/presence", json={"status": "remote"})
    _age(settings, "自分")
    assert general.get(f"{API}/me/presence").json()["is_stale"] is True

    general.put(f"{API}/me/presence", json={"status": "remote", "comment": "今日もリモート"})
    assert general.get(f"{API}/me/presence").json()["is_stale"] is False


def test_reset_stale_resets_only_old_working_states(org, settings):
    _age(settings, "山田 太郎", "鈴木 一郎", "高橋 美咲", "伊藤 さくら")

    res = org.post(f"{API}/presence/reset-stale")
    assert res.json() == {"count": 3}  # 在席中・離席中・リモートの3人（未出勤の人は対象外）

    entries = _by_name(org)
    for name in ("山田 太郎", "鈴木 一郎", "高橋 美咲"):
        assert entries[name]["status"] == "not_working"
        assert entries[name]["seat"] is None
        assert entries[name]["is_stale"] is False
    # コメントは本人のものなので残す
    assert entries["山田 太郎"]["comment"] == "コードレビューはいつでもどうぞ"
    # 古くしていない人はそのまま
    assert entries["佐藤 花子"]["status"] == "present"
    assert entries["田中 健太"]["status"] == "present"

    # 空いた座席には他の人が座れる
    assert org.post(f"{API}/presence/reset-stale").json() == {"count": 0}


def test_reset_stale_is_master_only(org):
    general = login_general(org, "me@example.com")
    general.put(f"{API}/me/profile", json={"name": "自分", "birth_date": "1990-01-01"})
    assert general.post(f"{API}/presence/reset-stale").status_code == 403


def test_reset_stale_does_not_touch_other_organizations(org, settings):
    other = TestClient(org.app)
    signup(other, email="b@example.com", org="組織B")
    other.post(f"{API}/organization/sample-data")
    conn = connect(settings.database_path)
    with conn:
        conn.execute("UPDATE presence SET updated_at = ?", (LONG_AGO,))  # 両方の組織を古くする
    conn.close()

    assert org.post(f"{API}/presence/reset-stale").json() == {"count": 5}
    # 組織Bはそのまま（まだ前日からの状態が残っている）
    assert sum(e["is_stale"] for e in other.get(f"{API}/presence").json()) == 5
