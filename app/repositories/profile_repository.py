# UserSkillRepository には list というメソッドがあるため、クラスの中の型注釈の
# list[...] が組み込みの list ではなくそのメソッドを指してしまい、
# Python 3.12・3.13 では読み込み時にエラーになる。
# 型注釈を実行時に評価しないようにして、3.12 以上のどの版でも動くようにする。
from __future__ import annotations

import sqlite3

from app.entities.profile import Profile, UserSkill


class ProfileRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, user_id: int, organization_id: int) -> Profile | None:
        row = self.conn.execute(
            "SELECT p.user_id, p.name, p.birth_date, p.avatar_path, p.default_seat_id,"
            "       p.updated_at, pos.name AS position_name, jt.name AS job_type_name,"
            "       COALESCE(jt.is_engineer, 0) AS is_engineer"
            " FROM profiles p"
            " JOIN users u ON u.id = p.user_id"
            " LEFT JOIN positions pos ON pos.id = p.position_id"
            " LEFT JOIN job_types jt ON jt.id = p.job_type_id"
            " WHERE p.user_id = ? AND u.organization_id = ?",
            (user_id, organization_id),
        ).fetchone()
        return Profile.from_row(row) if row else None

    def upsert(
        self,
        *,
        user_id: int,
        name: str,
        birth_date: str,
        position_id: int | None,
        job_type_id: int | None,
        default_seat_id: int | None,
        now: str,
    ) -> None:
        """登録または更新する。プロフィール画像は別の操作で変更するので触らない。"""
        self.conn.execute(
            "INSERT INTO profiles"
            " (user_id, name, birth_date, position_id, job_type_id, default_seat_id, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id) DO UPDATE SET"
            "   name = excluded.name, birth_date = excluded.birth_date,"
            "   position_id = excluded.position_id, job_type_id = excluded.job_type_id,"
            "   default_seat_id = excluded.default_seat_id, updated_at = excluded.updated_at",
            (user_id, name, birth_date, position_id, job_type_id, default_seat_id, now),
        )

    def set_avatar(self, user_id: int, avatar_path: str | None, now: str) -> None:
        self.conn.execute(
            "UPDATE profiles SET avatar_path = ?, updated_at = ? WHERE user_id = ?",
            (avatar_path, now, user_id),
        )


class UserSkillRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, user_id: int) -> list[UserSkill]:
        rows = self.conn.execute(
            "SELECT s.category, s.name, us.years"
            " FROM user_skills us JOIN skills s ON s.id = us.skill_id"
            " WHERE us.user_id = ?"
            " ORDER BY CASE s.category WHEN 'language' THEN 1 WHEN 'framework' THEN 2"
            "          WHEN 'database' THEN 3 ELSE 4 END, us.years DESC, s.name",
            (user_id,),
        ).fetchall()
        return [UserSkill.from_row(r) for r in rows]

    def replace(self, user_id: int, items: list[tuple[int, int]]) -> None:
        """(skill_id, years) の一覧で、そのユーザーのスキルをまとめて置き換える。"""
        self.clear(user_id)
        self.conn.executemany(
            "INSERT INTO user_skills (user_id, skill_id, years) VALUES (?, ?, ?)",
            [(user_id, skill_id, years) for skill_id, years in items],
        )

    def clear(self, user_id: int) -> None:
        self.conn.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
