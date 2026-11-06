"""役職・職種・スキルの候補の管理。"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from app.core.errors import ConflictError, NotFoundError
from app.entities.master_data import (
    DEFAULT_JOB_TYPES,
    DEFAULT_POSITIONS,
    DEFAULT_SKILLS,
    JobType,
    Position,
    Skill,
    SkillCategory,
)
from app.entities.user import User
from app.repositories.master_data_repository import (
    JobTypeRepository,
    PositionRepository,
    SkillRepository,
)


@dataclass(frozen=True)
class MasterData:
    positions: list[Position]
    job_types: list[JobType]
    skills: list[Skill]


class MasterDataService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.positions = PositionRepository(conn)
        self.job_types = JobTypeRepository(conn)
        self.skills = SkillRepository(conn)

    def seed_defaults(self, organization_id: int) -> None:
        """組織の作成時に既定の候補を登録する。呼び出し側のトランザクションの中で使う。"""
        for name in DEFAULT_POSITIONS:
            self.positions.create(organization_id, name)
        for name, is_engineer in DEFAULT_JOB_TYPES:
            self.job_types.create(organization_id, name, is_engineer)
        for category, names in DEFAULT_SKILLS.items():
            for name in names:
                self.skills.create(organization_id, category, name)

    def get_all(self, user: User) -> MasterData:
        org = user.organization_id
        return MasterData(
            positions=self.positions.list(org),
            job_types=self.job_types.list(org),
            skills=self.skills.list(org),
        )

    # ───────── 役職 ─────────

    def create_position(self, master: User, name: str) -> Position:
        with self.conn, _unique_name():
            return self.positions.create(master.organization_id, name)

    def rename_position(self, master: User, item_id: int, name: str) -> Position:
        self._require(self.positions.get(item_id, master.organization_id))
        with self.conn, _unique_name():
            self.positions.rename(item_id, master.organization_id, name)
        return Position(id=item_id, name=name)

    def delete_position(self, master: User, item_id: int) -> None:
        self._require(self.positions.get(item_id, master.organization_id))
        with self.conn:
            self.positions.delete(item_id, master.organization_id)

    # ───────── 職種 ─────────

    def create_job_type(self, master: User, name: str, is_engineer: bool) -> JobType:
        with self.conn, _unique_name():
            return self.job_types.create(master.organization_id, name, is_engineer)

    def update_job_type(self, master: User, item_id: int, name: str, is_engineer: bool) -> JobType:
        self._require(self.job_types.get(item_id, master.organization_id))
        with self.conn, _unique_name():
            self.job_types.update(item_id, master.organization_id, name, is_engineer)
        return JobType(id=item_id, name=name, is_engineer=is_engineer)

    def delete_job_type(self, master: User, item_id: int) -> None:
        self._require(self.job_types.get(item_id, master.organization_id))
        with self.conn:
            self.job_types.delete(item_id, master.organization_id)

    # ───────── スキル ─────────

    def create_skill(self, master: User, category: SkillCategory, name: str) -> Skill:
        with self.conn, _unique_name():
            return self.skills.create(master.organization_id, category, name)

    def rename_skill(self, master: User, item_id: int, name: str) -> Skill:
        skill = self._require(self.skills.get(item_id, master.organization_id))
        with self.conn, _unique_name():
            self.skills.rename(item_id, master.organization_id, name)
        return Skill(id=item_id, category=skill.category, name=name)

    def delete_skill(self, master: User, item_id: int) -> None:
        self._require(self.skills.get(item_id, master.organization_id))
        with self.conn:
            self.skills.delete(item_id, master.organization_id)

    @staticmethod
    def _require[T](item: T | None) -> T:
        if item is None:
            raise NotFoundError()
        return item


@contextmanager
def _unique_name() -> Iterator[None]:
    """名前の重複（UNIQUE 制約違反）を 409 に変換する。"""
    try:
        yield
    except sqlite3.IntegrityError as exc:
        raise ConflictError("同じ名前がすでに登録されています", code="NAME_TAKEN") from exc
