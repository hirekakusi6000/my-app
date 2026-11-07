"""メンバー検索（名前・技術スキル・在席状態で探す）。"""

import sqlite3

from app.entities.person import PeopleQuery, Person
from app.entities.user import User
from app.repositories.people_repository import PeopleRepository


class PeopleService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.people = PeopleRepository(conn)

    def search(self, viewer: User, query: PeopleQuery) -> list[Person]:
        # 同じスキルを2回指定しても結果は変わらないので、重複は取り除いておく
        unique_skills = tuple(dict.fromkeys(s.strip() for s in query.skills if s.strip()))
        normalized = PeopleQuery(
            name=query.name.strip() if query.name and query.name.strip() else None,
            skills=unique_skills,
            min_years=query.min_years,
            statuses=query.statuses,
        )
        return self.people.search(viewer.organization_id, normalized)
