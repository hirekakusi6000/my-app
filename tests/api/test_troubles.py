import pytest
from fastapi.testclient import TestClient

from tests.conftest import login_general, signup

API = "/api/v1"
TROUBLES = f"{API}/troubles"


def _profile(c: TestClient, name: str) -> int:
    res = c.put(
        f"{API}/me/profile",
        json={"name": name, "birth_date": "1990-04-01", "job_type_name": "営業"},
    )
    assert res.status_code == 200, res.text
    return res.json()["user_id"]


@pytest.fixture
def team(client) -> dict:
    signup(client)
    taro = login_general(client, "taro@example.com")
    hanako = login_general(client, "hanako@example.com")
    return {
        "master": client,
        "taro": taro,
        "taro_id": _profile(taro, "山田 太郎"),
        "hanako": hanako,
        "hanako_id": _profile(hanako, "佐藤 花子"),
    }


def _create(c: TestClient, title: str = "Docker が動かない", body: str = "") -> dict:
    res = c.post(TROUBLES, json={"title": title, "body": body})
    assert res.status_code == 201, res.text
    return res.json()


# ───────── 登録・閲覧 ─────────


def test_create_and_list(team):
    created = _create(team["taro"], "  Docker が動かない  ", "ビルドで止まります")
    assert created["title"] == "Docker が動かない"
    assert created["status"] == "open"
    assert created["author_name"] == "山田 太郎"
    assert created["is_mine"] is True

    # 同じ組織の他の人・マスターも見られる
    seen_by_hanako = team["hanako"].get(TROUBLES).json()
    assert [t["title"] for t in seen_by_hanako] == ["Docker が動かない"]
    assert seen_by_hanako[0]["is_mine"] is False
    assert team["master"].get(TROUBLES).status_code == 200


def test_filter_by_status_and_user(team):
    a = _create(team["taro"], "A")
    _create(team["hanako"], "B")
    team["taro"].patch(f"{TROUBLES}/{a['id']}", json={"status": "resolved"})

    open_titles = [t["title"] for t in team["hanako"].get(f"{TROUBLES}?status=open").json()]
    assert open_titles == ["B"]
    by_taro = team["hanako"].get(f"{TROUBLES}?user_id={team['taro_id']}").json()
    assert [t["title"] for t in by_taro] == ["A"]


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "   "}, {"title": "あ" * 101}, {"title": "x", "body": "あ" * 2001}],
)
def test_validation(team, payload):
    assert team["taro"].post(TROUBLES, json=payload).status_code == 422


# ───────── 変更・削除の権限 ─────────


def test_owner_can_update_and_resolve(team):
    t = _create(team["taro"])
    res = team["taro"].patch(f"{TROUBLES}/{t['id']}", json={"body": "解決方法を探しています"})
    assert res.json()["body"] == "解決方法を探しています"
    assert res.json()["title"] == t["title"]  # 送らなかった項目はそのまま

    res = team["taro"].patch(f"{TROUBLES}/{t['id']}", json={"status": "resolved"})
    assert res.json()["status"] == "resolved"
    res = team["taro"].patch(f"{TROUBLES}/{t['id']}", json={"status": "open"})
    assert res.json()["status"] == "open"


def test_others_cannot_update(team):
    t = _create(team["taro"])
    res = team["hanako"].patch(f"{TROUBLES}/{t['id']}", json={"status": "resolved"})
    assert res.status_code == 403
    # マスターも内容は変えられない（削除だけできる）
    assert team["master"].patch(f"{TROUBLES}/{t['id']}", json={"title": "x"}).status_code == 403


def test_delete_by_owner_and_master_only(team):
    t1 = _create(team["taro"], "1")
    t2 = _create(team["taro"], "2")
    assert team["hanako"].delete(f"{TROUBLES}/{t1['id']}").status_code == 403
    assert team["taro"].delete(f"{TROUBLES}/{t1['id']}").status_code == 204
    assert team["master"].delete(f"{TROUBLES}/{t2['id']}").status_code == 204
    assert team["taro"].get(TROUBLES).json() == []


def test_master_cannot_create(team):
    assert team["master"].post(TROUBLES, json={"title": "x"}).status_code == 403


def test_user_without_profile_cannot_use(client, team):
    newcomer = login_general(client, "new@example.com")
    assert newcomer.get(TROUBLES).json()["code"] == "SETUP_REQUIRED"
    assert newcomer.post(TROUBLES, json={"title": "x"}).json()["code"] == "SETUP_REQUIRED"


def test_unknown_trouble_is_404(team):
    assert team["taro"].patch(f"{TROUBLES}/99999", json={"title": "x"}).status_code == 404


# ───────── 組織の分離・ユーザー削除 ─────────


def test_troubles_are_separated_by_organization(client, team):
    t = _create(team["taro"])
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")

    assert other.get(TROUBLES).json() == []
    assert other.delete(f"{TROUBLES}/{t['id']}").status_code == 404


def test_deleting_user_removes_their_troubles(team):
    _create(team["taro"])
    team["master"].delete(f"{API}/users/{team['taro_id']}")
    assert team["hanako"].get(TROUBLES).json() == []


# ───────── マップの目印 ─────────


def test_occupancy_shows_open_trouble_flag(team):
    m = team["master"]
    floor = m.post(f"{API}/floors", json={"name": "1F"}).json()
    room = m.post(f"{API}/floors/{floor['id']}/rooms", json={"name": "A"}).json()
    seat = m.put(
        f"{API}/rooms/{room['id']}/layout",
        json={"furniture": [{"type": "chair", "x": 0, "y": 0, "width": 1, "height": 1}]},
    ).json()["furniture"][0]
    team["taro"].put(f"{API}/me/presence", json={"status": "present", "seat_id": seat["id"]})

    def flag() -> bool:
        return m.get(f"{API}/rooms/{room['id']}/occupancy").json()[0]["has_open_trouble"]

    assert flag() is False
    t = _create(team["taro"])
    assert flag() is True
    team["taro"].patch(f"{TROUBLES}/{t['id']}", json={"status": "resolved"})
    assert flag() is False
