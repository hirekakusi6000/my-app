"""メンバー検索。

条件の数に応じて SQL を組み立てるが、組み立てに使うのはこのファイルに書いた固定の文字列だけで、
利用者の入力は必ずプレースホルダー（?）で渡す。
"""

import sqlite3

from app.entities.office import SeatInfo
from app.entities.person import PeopleQuery, Person
from app.entities.presence import PresenceStatus
from app.entities.profile import UserSkill

# オフィスにいる人を先に、未出勤の人を最後に並べる
_STATUS_ORDER = (
    "CASE pr.status WHEN 'present' THEN 1 WHEN 'away' THEN 2 WHEN 'remote' THEN 3 ELSE 4 END"
)


def _escape_like(value: str) -> str:
    """LIKE の特殊文字（% と _）を、ただの文字として検索できるようにする。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PeopleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def search(self, organization_id: int, query: PeopleQuery) -> list[Person]:
        where = ["pr.organization_id = ?"]
        params: list[object] = [organization_id]

        if query.name:
            where.append("p.name LIKE ? ESCAPE '\\'")
            params.append(f"%{_escape_like(query.name)}%")
        if query.statuses:
            where.append(f"pr.status IN ({', '.join('?' for _ in query.statuses)})")
            params.extend(s.value for s in query.statuses)
        for skill in query.skills:
            where.append(
                "EXISTS (SELECT 1 FROM user_skills us JOIN skills s ON s.id = us.skill_id"
                " WHERE us.user_id = pr.user_id AND s.name = ? COLLATE NOCASE AND us.years >= ?)"
            )
            params.extend([skill, query.min_years])

        rows = self.conn.execute(
            "SELECT pr.user_id, pr.status, pr.comment, pr.seat_id, pr.updated_at,"
            "       p.name, p.avatar_path,"
            "       pos.name AS position_name, jt.name AS job_type_name,"
            "       f.label AS seat_label, r.id AS room_id, r.name AS room_name,"
            "       fl.id AS floor_id, fl.name AS floor_name"
            " FROM presence pr"
            " JOIN profiles p ON p.user_id = pr.user_id"
            " LEFT JOIN positions pos ON pos.id = p.position_id"
            " LEFT JOIN job_types jt ON jt.id = p.job_type_id"
            " LEFT JOIN furniture f ON f.id = pr.seat_id"
            " LEFT JOIN rooms r ON r.id = f.room_id"
            " LEFT JOIN floors fl ON fl.id = r.floor_id"
            f" WHERE {' AND '.join(where)}"
            f" ORDER BY {_STATUS_ORDER}, p.name, pr.user_id",
            params,
        ).fetchall()

        skills = self._skills_of([r["user_id"] for r in rows])
        return [
            Person(
                user_id=r["user_id"],
                name=r["name"],
                avatar_path=r["avatar_path"],
                position=r["position_name"],
                job_type=r["job_type_name"],
                status=PresenceStatus(r["status"]),
                comment=r["comment"],
                seat=(
                    SeatInfo(
                        seat_id=r["seat_id"],
                        label=r["seat_label"],
                        room_id=r["room_id"],
                        room_name=r["room_name"],
                        floor_id=r["floor_id"],
                        floor_name=r["floor_name"],
                    )
                    if r["seat_id"] is not None
                    else None
                ),
                skills=tuple(skills.get(r["user_id"], ())),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def _skills_of(self, user_ids: list[int]) -> dict[int, list[UserSkill]]:
        if not user_ids:
            return {}
        rows = self.conn.execute(
            "SELECT us.user_id, s.category, s.name, us.years"
            " FROM user_skills us JOIN skills s ON s.id = us.skill_id"
            f" WHERE us.user_id IN ({', '.join('?' for _ in user_ids)})"
            " ORDER BY us.years DESC, s.name",
            user_ids,
        ).fetchall()
        result: dict[int, list[UserSkill]] = {}
        for r in rows:
            result.setdefault(r["user_id"], []).append(UserSkill.from_row(r))
        return result
