import pytest
from fastapi.testclient import TestClient

from tests.conftest import login_general, signup

API = "/api/v1"
ME = f"{API}/me/presence"


def _profile(c: TestClient, name: str) -> dict:
    res = c.put(
        f"{API}/me/profile",
        json={"name": name, "birth_date": "1990-04-01", "job_type_name": "営業"},
    )
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def office(client) -> dict:
    """椅子2脚と机がある部屋と、プロフィール登録済みの一般ユーザー2人。"""
    signup(client)
    floor = client.post(f"{API}/floors", json={"name": "1F"}).json()
    room = client.post(f"{API}/floors/{floor['id']}/rooms", json={"name": "執務室"}).json()
    layout = client.put(
        f"{API}/rooms/{room['id']}/layout",
        json={
            "furniture": [
                {"type": "chair", "x": 0, "y": 0, "width": 1, "height": 1, "label": "A-1"},
                {"type": "chair", "x": 2, "y": 0, "width": 1, "height": 1, "label": "A-2"},
                {"type": "desk", "x": 0, "y": 2, "width": 4, "height": 2},
            ]
        },
    ).json()
    chair1, chair2, desk = (f["id"] for f in layout["furniture"])
    taro = login_general(client, "taro@example.com")
    hanako = login_general(client, "hanako@example.com")
    return {
        "room": room,
        "chair1": chair1,
        "chair2": chair2,
        "desk": desk,
        "taro": taro,
        "taro_id": _profile(taro, "山田 太郎")["user_id"],
        "hanako": hanako,
        "hanako_id": _profile(hanako, "佐藤 花子")["user_id"],
    }


def _put(c: TestClient, status: str, seat_id: int | None = None, **extra):
    return c.put(ME, json={"status": status, "seat_id": seat_id, **extra})


# ───────── 基本の流れ ─────────


def test_initial_status_is_not_working(office):
    body = office["taro"].get(ME).json()
    assert body["status"] == "not_working"
    assert body["seat"] is None
    assert body["name"] == "山田 太郎"


def test_check_in_away_back_and_check_out(office):
    taro, chair = office["taro"], office["chair1"]

    body = _put(taro, "present", chair).json()
    assert body["status"] == "present"
    assert body["seat"] == {
        "seat_id": chair,
        "label": "A-1",
        "room_id": office["room"]["id"],
        "room_name": "執務室",
        "floor_name": "1F",
    }

    away = _put(taro, "away").json()  # 座席は送らなくても、そのまま確保される
    assert away["status"] == "away"
    assert away["seat"]["seat_id"] == chair

    assert _put(taro, "present", chair).json()["status"] == "present"

    out = _put(taro, "not_working").json()
    assert (out["status"], out["seat"]) == ("not_working", None)


def test_remote_has_no_seat_even_if_sent(office):
    body = _put(office["taro"], "remote", office["chair1"]).json()
    assert (body["status"], body["seat"]) == ("remote", None)


def test_change_seat(office):
    taro = office["taro"]
    _put(taro, "present", office["chair1"])
    body = _put(taro, "present", office["chair2"]).json()
    assert body["seat"]["seat_id"] == office["chair2"]
    # 元の座席は空いたので、他の人が座れる
    assert _put(office["hanako"], "present", office["chair1"]).status_code == 200


# ───────── 入力チェック・状態の変わり方 ─────────


def test_present_requires_seat(office):
    res = _put(office["taro"], "present")
    assert res.json()["code"] == "SEAT_REQUIRED"


@pytest.mark.parametrize("seat_key", ["desk", None])
def test_seat_must_be_a_chair(office, seat_key):
    seat_id = office[seat_key] if seat_key else 99999
    res = _put(office["taro"], "present", seat_id)
    assert res.json()["code"] == "INVALID_SEAT"


@pytest.mark.parametrize("before", ["not_working", "remote"])
def test_cannot_be_away_without_checking_in(office, before):
    _put(office["taro"], before)
    res = _put(office["taro"], "away")
    assert res.json()["code"] == "INVALID_TRANSITION"


def test_invalid_status_is_rejected(office):
    assert _put(office["taro"], "sleeping").status_code == 422


# ───────── 座席の重複 ─────────


def test_seat_taken_by_someone_else(office):
    _put(office["taro"], "present", office["chair1"])
    res = _put(office["hanako"], "present", office["chair1"])
    assert res.status_code == 409
    assert res.json()["code"] == "SEAT_OCCUPIED"
    # 失敗した側の状態は変わっていない
    assert office["hanako"].get(ME).json()["status"] == "not_working"


def test_seat_held_while_away(office):
    _put(office["taro"], "present", office["chair1"])
    _put(office["taro"], "away")
    res = _put(office["hanako"], "present", office["chair1"])
    assert res.json()["code"] == "SEAT_OCCUPIED"


def test_reselecting_own_seat_is_ok(office):
    _put(office["taro"], "present", office["chair1"])
    assert _put(office["taro"], "present", office["chair1"]).status_code == 200


# ───────── ひとことコメント ─────────


def test_comment_is_kept_unless_sent(office):
    taro = office["taro"]
    _put(taro, "remote", comment="  14時まで会議  ")
    assert taro.get(ME).json()["comment"] == "14時まで会議"

    # コメントを送らずに状態だけ変えても、コメントは残る
    _put(taro, "not_working")
    assert taro.get(ME).json()["comment"] == "14時まで会議"

    # 空文字を送ると消える
    _put(taro, "not_working", comment="")
    assert taro.get(ME).json()["comment"] is None


def test_comment_length_limit(office):
    res = _put(office["taro"], "remote", comment="あ" * 101)
    assert res.status_code == 422


# ───────── 一覧・閲覧 ─────────


def test_list_presence_and_occupancy(client, office):
    _put(office["taro"], "present", office["chair1"])
    _put(office["hanako"], "remote", comment="在宅です")

    entries = {e["name"]: e for e in office["taro"].get(f"{API}/presence").json()}
    assert entries["山田 太郎"]["status"] == "present"
    assert entries["佐藤 花子"]["status"] == "remote"
    assert entries["佐藤 花子"]["comment"] == "在宅です"

    occupancy = client.get(f"{API}/rooms/{office['room']['id']}/occupancy").json()
    assert [(o["name"], o["status"]) for o in occupancy] == [("山田 太郎", "present")]

    # 他の人のプロフィールにも状態とコメントが出る
    profile = office["taro"].get(f"{API}/profiles/{office['hanako_id']}").json()
    assert profile["presence"] == {"status": "remote", "comment": "在宅です"}


def test_users_without_profile_are_not_listed(client, office):
    login_general(client, "newcomer@example.com")
    names = [e["name"] for e in client.get(f"{API}/presence").json()]
    assert sorted(names) == ["佐藤 花子", "山田 太郎"]


# ───────── 権限 ─────────


def test_master_has_no_own_presence(client, office):
    assert client.get(ME).status_code == 403
    assert _put(client, "remote").status_code == 403
    assert client.get(f"{API}/presence").status_code == 200


def test_user_without_profile_cannot_check_in(client, office):
    newcomer = login_general(client, "newcomer@example.com")
    res = _put(newcomer, "present", office["chair1"])
    assert res.json()["code"] == "SETUP_REQUIRED"


# ───────── マスターによる座席の解放 ─────────


def test_master_can_release_seat(client, office):
    _put(office["taro"], "present", office["chair1"], comment="作業中")
    assert client.delete(f"{API}/seats/{office['chair1']}/occupant").status_code == 204

    body = office["taro"].get(ME).json()
    assert (body["status"], body["seat"]) == ("not_working", None)
    assert body["comment"] == "作業中"  # コメントは残す
    assert _put(office["hanako"], "present", office["chair1"]).status_code == 200


def test_release_empty_seat_is_404(client, office):
    assert client.delete(f"{API}/seats/{office['chair1']}/occupant").status_code == 404


def test_general_user_cannot_release_seat(office):
    _put(office["taro"], "present", office["chair1"])
    res = office["hanako"].delete(f"{API}/seats/{office['chair1']}/occupant")
    assert res.status_code == 403


def test_presence_is_separated_by_organization(client, office):
    _put(office["taro"], "present", office["chair1"])
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")

    assert other.get(f"{API}/presence").json() == []
    assert other.delete(f"{API}/seats/{office['chair1']}/occupant").status_code == 404

    # 他の組織の椅子には座れない
    outsider = login_general(other, "b-user@example.com")
    _profile(outsider, "外部 太郎")
    assert _put(outsider, "present", office["chair2"]).json()["code"] == "INVALID_SEAT"
