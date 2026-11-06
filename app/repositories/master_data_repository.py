"""役職・職種・スキルの候補の一覧。すべて organization_id で絞り込む。"""

import sqlite3

from app.entities.master_data import JobType, Position, Skill, SkillCategory


class PositionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, organization_id: int) -> list[Position]:
        rows = self.conn.execute(
            "SELECT id, name FROM positions WHERE organization_id = ? ORDER BY id",
            (organization_id,),
        ).fetchall()
        return [Position.from_row(r) for r in rows]

    def get(self, item_id: int, organization_id: int) -> Position | None:
        row = self.conn.execute(
            "SELECT id, name FROM positions WHERE id = ? AND organization_id = ?",
            (item_id, organization_id),
        ).fetchone()
        return Position.from_row(row) if row else None

    def create(self, organization_id: int, name: str) -> Position:
        cur = self.conn.execute(
            "INSERT INTO positions (organization_id, name) VALUES (?, ?)", (organization_id, name)
        )
        return Position(id=cur.lastrowid, name=name)

    def rename(self, item_id: int, organization_id: int, name: str) -> None:
        self.conn.execute(
            "UPDATE positions SET name = ? WHERE id = ? AND organization_id = ?",
            (name, item_id, organization_id),
        )

    def delete(self, item_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM positions WHERE id = ? AND organization_id = ?", (item_id, organization_id)
        )

    def get_or_create(self, organization_id: int, name: str) -> int:
        """名前（大文字・小文字は区別しない）で探し、なければ追加して id を返す。"""
        self.conn.execute(
            "INSERT OR IGNORE INTO positions (organization_id, name) VALUES (?, ?)",
            (organization_id, name),
        )
        return self.conn.execute(
            "SELECT id FROM positions WHERE organization_id = ? AND name = ?",
            (organization_id, name),
        ).fetchone()[0]


class JobTypeRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, organization_id: int) -> list[JobType]:
        rows = self.conn.execute(
            "SELECT id, name, is_engineer FROM job_types WHERE organization_id = ? ORDER BY id",
            (organization_id,),
        ).fetchall()
        return [JobType.from_row(r) for r in rows]

    def get(self, item_id: int, organization_id: int) -> JobType | None:
        row = self.conn.execute(
            "SELECT id, name, is_engineer FROM job_types WHERE id = ? AND organization_id = ?",
            (item_id, organization_id),
        ).fetchone()
        return JobType.from_row(row) if row else None

    def create(self, organization_id: int, name: str, is_engineer: bool) -> JobType:
        cur = self.conn.execute(
            "INSERT INTO job_types (organization_id, name, is_engineer) VALUES (?, ?, ?)",
            (organization_id, name, int(is_engineer)),
        )
        return JobType(id=cur.lastrowid, name=name, is_engineer=is_engineer)

    def update(self, item_id: int, organization_id: int, name: str, is_engineer: bool) -> None:
        self.conn.execute(
            "UPDATE job_types SET name = ?, is_engineer = ? WHERE id = ? AND organization_id = ?",
            (name, int(is_engineer), item_id, organization_id),
        )

    def delete(self, item_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM job_types WHERE id = ? AND organization_id = ?", (item_id, organization_id)
        )

    def get_or_create(self, organization_id: int, name: str) -> JobType:
        self.conn.execute(
            "INSERT OR IGNORE INTO job_types (organization_id, name) VALUES (?, ?)",
            (organization_id, name),
        )
        row = self.conn.execute(
            "SELECT id, name, is_engineer FROM job_types WHERE organization_id = ? AND name = ?",
            (organization_id, name),
        ).fetchone()
        return JobType.from_row(row)


class SkillRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, organization_id: int, category: SkillCategory | None = None) -> list[Skill]:
        rows = self.conn.execute(
            "SELECT id, category, name FROM skills"
            " WHERE organization_id = ? AND (? IS NULL OR category = ?)"
            " ORDER BY CASE category WHEN 'language' THEN 1 WHEN 'framework' THEN 2"
            "          WHEN 'database' THEN 3 ELSE 4 END, id",
            (organization_id, category, category),
        ).fetchall()
        return [Skill.from_row(r) for r in rows]

    def get(self, item_id: int, organization_id: int) -> Skill | None:
        row = self.conn.execute(
            "SELECT id, category, name FROM skills WHERE id = ? AND organization_id = ?",
            (item_id, organization_id),
        ).fetchone()
        return Skill.from_row(row) if row else None

    def create(self, organization_id: int, category: SkillCategory, name: str) -> Skill:
        cur = self.conn.execute(
            "INSERT INTO skills (organization_id, category, name) VALUES (?, ?, ?)",
            (organization_id, category.value, name),
        )
        return Skill(id=cur.lastrowid, category=category, name=name)

    def rename(self, item_id: int, organization_id: int, name: str) -> None:
        self.conn.execute(
            "UPDATE skills SET name = ? WHERE id = ? AND organization_id = ?",
            (name, item_id, organization_id),
        )

    def delete(self, item_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM skills WHERE id = ? AND organization_id = ?", (item_id, organization_id)
        )

    def get_or_create(self, organization_id: int, category: SkillCategory, name: str) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO skills (organization_id, category, name) VALUES (?, ?, ?)",
            (organization_id, category.value, name),
        )
        return self.conn.execute(
            "SELECT id FROM skills WHERE organization_id = ? AND category = ? AND name = ?",
            (organization_id, category.value, name),
        ).fetchone()[0]
