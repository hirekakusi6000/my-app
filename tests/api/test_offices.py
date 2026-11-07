import pytest
from fastapi.testclient import TestClient

from app.db.connection import connect
from tests.conftest import login_general, signup

API = "/api/v1"
PROFILE = {"name": "山田 太郎", "birth_date": "1990-04-01", "job_type_name": "営業"}


@pytest.fixture
def master(client) -> dict:
    return signup(client)


def _floor(c: TestClient, name: str = "1F") -> dict:
    res = c.post(f"{API}/floors", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()


def _room(c: TestClient, floor_id: int, name: str = "執務室", **size) -> dict:
    res = c.post(f"{API}/floors/{floor_id}/rooms", json={"name": name, **size})
    assert res.status_code == 201, res.text
    return res.json()


def _save(c: TestClient, room_id: int, furniture: list[dict]):
    return c.put(f"{API}/rooms/{room_id}/layout", json={"furniture": furniture})


def _chair(x: int = 0, y: int = 0, **kw) -> dict:
    return {"type": "chair", "x": x, "y": y, "width": 1, "height": 1, **kw}


def _sit(settings, user_id: int, seat_id: int) -> None:
    """在席状態を直接設定する（出勤 API を実装するまでのテスト用）。"""
    conn = connect(settings.database_path)
    with conn:
        conn.execute(
            "UPDATE presence SET status = 'present', seat_id = ? WHERE user_id = ?",
            (seat_id, user_id),
        )
    conn.close()


def _presence(settings, user_id: int) -> tuple:
    conn = connect(settings.database_path)
    row = conn.execute(
        "SELECT status, seat_id FROM presence WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return tuple(row)


@pytest.fixture
def seated(client, master, settings):
    """椅子が1脚ある部屋と、そこに座っている一般ユーザー。"""
    floor = _floor(client)
    room = _room(client, floor["id"])
    layout = _save(client, room["id"], [_chair(2, 3, label="A-1")]).json()
    seat = layout["furniture"][0]
    general = login_general(client)
    profile = general.put(
        f"{API}/me/profile", json={**PROFILE, "default_seat_id": seat["id"]}
    ).json()
    _sit(settings, profile["user_id"], seat["id"])
    return {
        "floor": floor,
        "room": room,
        "seat": seat,
        "general": general,
        "user_id": profile["user_id"],
    }


# ───────── フロア ─────────


def test_floor_crud_and_order(client, master):
    a = _floor(client, "1F")
    b = _floor(client, "2F")
    assert [f["name"] for f in client.get(f"{API}/floors").json()] == ["1F", "2F"]

    client.patch(f"{API}/floors/{a['id']}", json={"sort_order": 5})
    client.patch(f"{API}/floors/{b['id']}", json={"name": "2階"})
    floors = client.get(f"{API}/floors").json()
    assert [f["name"] for f in floors] == ["2階", "1F"]

    assert client.delete(f"{API}/floors/{a['id']}").status_code == 204
    assert [f["name"] for f in client.get(f"{API}/floors").json()] == ["2階"]


def test_floor_limit_and_duplicate(client, master):
    for i in range(5):
        _floor(client, f"{i + 1}F")
    res = client.post(f"{API}/floors", json={"name": "6F"})
    assert res.json()["code"] == "LIMIT_EXCEEDED"

    client.delete(f"{API}/floors/{client.get(f'{API}/floors').json()[0]['id']}")
    dup = client.post(f"{API}/floors", json={"name": "2F"})
    assert dup.status_code == 409


# ───────── 部屋 ─────────


def test_room_defaults_and_limit(client, master):
    floor = _floor(client)
    room = _room(client, floor["id"])
    assert (room["width"], room["height"]) == (30, 20)
    for i in range(4):
        _room(client, floor["id"], f"部屋{i}")
    res = client.post(f"{API}/floors/{floor['id']}/rooms", json={"name": "6つ目"})
    assert res.json()["code"] == "LIMIT_EXCEEDED"
    # 別のフロアなら作れる
    _room(client, _floor(client, "2F")["id"], "6つ目")


@pytest.mark.parametrize("size", [{"width": 4}, {"height": 201}])
def test_room_size_is_validated(client, master, size):
    floor = _floor(client)
    res = client.post(f"{API}/floors/{floor['id']}/rooms", json={"name": "x", **size})
    assert res.status_code == 422


def test_room_cannot_shrink_below_furniture(client, master):
    room = _room(client, _floor(client)["id"])
    _save(client, room["id"], [_chair(25, 0)])
    res = client.patch(f"{API}/rooms/{room['id']}", json={"width": 20})
    assert res.json()["code"] == "ROOM_TOO_SMALL"
    assert client.patch(f"{API}/rooms/{room['id']}", json={"width": 26}).status_code == 200


# ───────── 配置 ─────────


def test_save_layout_creates_updates_and_deletes(client, master):
    room = _room(client, _floor(client)["id"])
    first = _save(
        client,
        room["id"],
        [
            {"type": "desk", "x": 1, "y": 1, "width": 4, "height": 2, "label": " 島A "},
            _chair(1, 3),
        ],
    ).json()
    desk, chair = first["furniture"]
    assert desk["label"] == "島A"
    assert first["floor_name"] == "1F"

    second = _save(
        client,
        room["id"],
        [{**desk, "x": 10}, {"type": "wall", "x": 0, "y": 0, "width": 6, "height": 1}],
    ).json()
    assert len(second["furniture"]) == 2
    assert second["furniture"][0]["id"] == desk["id"]
    assert second["furniture"][0]["x"] == 10
    assert chair["id"] not in [f["id"] for f in second["furniture"]]


def test_furniture_must_fit_in_room_considering_rotation(client, master):
    room = _room(client, _floor(client)["id"], width=30, height=20)
    desk = {"type": "desk", "x": 27, "y": 0, "width": 4, "height": 2}
    assert _save(client, room["id"], [desk]).json()["code"] == "FURNITURE_OUT_OF_ROOM"
    # 90度回転すると床に占める範囲は 2 × 4 になり、収まる
    assert _save(client, room["id"], [{**desk, "rotation": 90}]).status_code == 200


@pytest.mark.parametrize(
    "item",
    [
        {"type": "sofa", "x": 0, "y": 0, "width": 1, "height": 1},
        {"type": "desk", "x": 0, "y": 0, "width": 1, "height": 1, "rotation": 45},
        {"type": "desk", "x": -1, "y": 0, "width": 1, "height": 1},
        {"type": "desk", "x": 0, "y": 0, "width": 0, "height": 1},
    ],
)
def test_invalid_furniture_is_rejected(client, master, item):
    room = _room(client, _floor(client)["id"])
    assert _save(client, room["id"], [item]).status_code == 422


def test_furniture_ids_must_belong_to_the_room(client, master):
    floor = _floor(client)
    room_a = _room(client, floor["id"], "A")
    room_b = _room(client, floor["id"], "B")
    other_chair = _save(client, room_b["id"], [_chair()]).json()["furniture"][0]

    res = _save(client, room_a["id"], [other_chair])
    assert res.json()["code"] == "INVALID_FURNITURE"

    own = _save(client, room_a["id"], [_chair()]).json()["furniture"][0]
    dup = _save(client, room_a["id"], [own, {**own, "x": 3}])
    assert dup.json()["code"] == "INVALID_FURNITURE"


# ───────── 座っている人がいる座席の削除 ─────────


def test_removing_occupied_chair_releases_user(client, settings, seated):
    _save(client, seated["room"]["id"], [])

    assert _presence(settings, seated["user_id"]) == ("not_working", None)
    profile = seated["general"].get(f"{API}/me/profile").json()
    assert profile["default_seat_id"] is None
    assert profile["default_seat"] is None


def test_changing_chair_to_desk_releases_user(client, settings, seated):
    seat = seated["seat"]
    _save(client, seated["room"]["id"], [{**seat, "type": "desk"}])
    assert _presence(settings, seated["user_id"]) == ("not_working", None)
    assert seated["general"].get(f"{API}/me/profile").json()["default_seat_id"] is None


def test_moving_occupied_chair_keeps_user_seated(client, settings, seated):
    seat = seated["seat"]
    _save(client, seated["room"]["id"], [{**seat, "x": 10}])
    assert _presence(settings, seated["user_id"]) == ("present", seat["id"])


@pytest.mark.parametrize("target", ["room", "floor"])
def test_deleting_room_or_floor_releases_user(client, settings, seated, target):
    url = (
        f"{API}/rooms/{seated['room']['id']}"
        if target == "room"
        else (f"{API}/floors/{seated['floor']['id']}")
    )
    assert client.delete(url).status_code == 204
    assert _presence(settings, seated["user_id"]) == ("not_working", None)


# ───────── 閲覧 ─────────


def test_occupancy_lists_seated_users(client, seated):
    res = seated["general"].get(f"{API}/rooms/{seated['room']['id']}/occupancy")
    occupants = res.json()
    assert occupants[0].pop("updated_at")  # 更新日時（値はテストの実行時刻による）
    assert occupants == [
        {
            "seat_id": seated["seat"]["id"],
            "user_id": seated["user_id"],
            "name": "山田 太郎",
            "status": "present",
            "avatar_url": None,
            "is_stale": False,
        }
    ]
    # マスターも見られる
    assert client.get(f"{API}/rooms/{seated['room']['id']}/occupancy").status_code == 200


def test_profile_shows_default_seat_location(seated):
    profile = seated["general"].get(f"{API}/me/profile").json()
    assert profile["default_seat"] == {
        "seat_id": seated["seat"]["id"],
        "label": "A-1",
        "room_id": seated["room"]["id"],
        "room_name": "執務室",
        "floor_name": "1F",
    }


def test_general_user_can_read_layout_during_setup_but_not_edit(client, master):
    room = _room(client, _floor(client)["id"])
    newcomer = login_general(client)  # パスワード変更済み・プロフィール未登録

    assert newcomer.get(f"{API}/floors").status_code == 200
    assert newcomer.get(f"{API}/rooms/{room['id']}/layout").status_code == 200
    assert newcomer.get(f"{API}/rooms/{room['id']}/occupancy").json()["code"] == "SETUP_REQUIRED"
    assert _save(newcomer, room["id"], []).status_code == 403
    assert newcomer.post(f"{API}/floors", json={"name": "x"}).status_code == 403


def test_offices_are_separated_by_organization(client, seated):
    other = TestClient(client.app)
    signup(other, email="b@example.com", org="組織B")
    room_id = seated["room"]["id"]

    assert other.get(f"{API}/floors").json() == []
    assert other.get(f"{API}/rooms/{room_id}/layout").status_code == 404
    assert other.get(f"{API}/rooms/{room_id}/occupancy").status_code == 404
    assert _save(other, room_id, []).status_code == 404
    assert other.delete(f"{API}/floors/{seated['floor']['id']}").status_code == 404
    assert (
        other.post(f"{API}/floors/{seated['floor']['id']}/rooms", json={"name": "x"}).status_code
        == 404
    )

    # 他の組織の椅子はデフォルト座席にできない
    general_b = login_general(other, "b-user@example.com")
    res = general_b.put(
        f"{API}/me/profile", json={**PROFILE, "default_seat_id": seated["seat"]["id"]}
    )
    assert res.json()["code"] == "INVALID_SEAT"
