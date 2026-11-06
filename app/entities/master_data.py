import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class SkillCategory(StrEnum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"


@dataclass(frozen=True)
class Position:
    id: int
    name: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Position":
        return cls(id=row["id"], name=row["name"])


@dataclass(frozen=True)
class JobType:
    id: int
    name: str
    is_engineer: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobType":
        return cls(id=row["id"], name=row["name"], is_engineer=bool(row["is_engineer"]))


@dataclass(frozen=True)
class Skill:
    id: int
    category: SkillCategory
    name: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Skill":
        return cls(id=row["id"], category=SkillCategory(row["category"]), name=row["name"])


# 組織の作成時に用意しておく候補（マスターが後から自由に変更できる）
DEFAULT_POSITIONS = ["メンバー", "主任", "係長", "課長", "部長"]
DEFAULT_JOB_TYPES = [("エンジニア", True), ("デザイナー", False), ("営業", False), ("事務", False)]
DEFAULT_SKILLS = {
    SkillCategory.LANGUAGE: ["Python", "JavaScript", "TypeScript", "Java", "Go", "C#"],
    SkillCategory.FRAMEWORK: ["FastAPI", "Django", "React", "Vue.js", "Spring Boot", ".NET"],
    SkillCategory.DATABASE: ["SQLite", "MySQL", "PostgreSQL", "Oracle", "SQL Server", "MongoDB"],
    SkillCategory.CLOUD: ["AWS", "Azure", "Google Cloud"],
}
