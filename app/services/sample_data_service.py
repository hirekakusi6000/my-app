"""お試し用のサンプルデータ。

一般公開したアプリを試す人が、従業員の登録やマップ作りをしなくても全体像をつかめるように、
空の組織にオフィスマップと従業員（プロフィール・スキル・在席状態つき）をまとめて作成する。

- 既存のデータを壊さないよう、フロアも一般ユーザーもまだない組織でだけ作成できる
- サンプルの従業員はパスワードを知る人がいないためログインできない。
  試しにログインしたい場合は、マスターがユーザー管理からパスワードをリセットすればよい
"""

import secrets
import sqlite3
from dataclasses import dataclass

from app.core import security
from app.core.errors import BusinessRuleError
from app.core.time import to_iso, utc_now
from app.entities.master_data import SkillCategory
from app.entities.office import Furniture, FurnitureType
from app.entities.presence import PresenceStatus
from app.entities.user import Role, User
from app.repositories.furniture_repository import FurnitureRepository
from app.repositories.master_data_repository import (
    JobTypeRepository,
    PositionRepository,
    SkillRepository,
)
from app.repositories.office_repository import FloorRepository, RoomRepository
from app.repositories.presence_repository import PresenceRepository
from app.repositories.profile_repository import ProfileRepository, UserSkillRepository
from app.repositories.user_repository import UserRepository

ROOM_WIDTH = 26
ROOM_HEIGHT = 14

_L, _F, _D, _C = (
    SkillCategory.LANGUAGE,
    SkillCategory.FRAMEWORK,
    SkillCategory.DATABASE,
    SkillCategory.CLOUD,
)


@dataclass(frozen=True)
class SampleEmployee:
    name: str
    birth_date: str
    position: str
    job_type: str
    skills: tuple[tuple[SkillCategory, str, int], ...]
    status: PresenceStatus
    seat: str | None  # 座席のラベル（在席中・離席中の人だけ）
    default_seat: str | None
    comment: str | None


SAMPLE_EMPLOYEES = (
    SampleEmployee(
        "山田 太郎",
        "1985-06-12",
        "課長",
        "エンジニア",
        ((_L, "Python", 10), (_F, "FastAPI", 4), (_D, "PostgreSQL", 8), (_C, "AWS", 6)),
        PresenceStatus.PRESENT,
        "A-1",
        "A-1",
        "コードレビューはいつでもどうぞ",
    ),
    SampleEmployee(
        "佐藤 花子",
        "1992-11-03",
        "主任",
        "デザイナー",
        (),
        PresenceStatus.PRESENT,
        "A-2",
        "A-2",
        "Figma のことなら聞いてください",
    ),
    SampleEmployee(
        "鈴木 一郎",
        "1996-02-20",
        "メンバー",
        "エンジニア",
        ((_L, "TypeScript", 3), (_F, "React", 3), (_F, "Vue.js", 1), (_C, "AWS", 1)),
        PresenceStatus.AWAY,
        "A-4",
        "A-4",
        "14時まで会議です",
    ),
    SampleEmployee(
        "高橋 美咲",
        "1994-08-08",
        "メンバー",
        "エンジニア",
        ((_L, "Go", 2), (_L, "Python", 4), (_D, "MySQL", 3), (_C, "Google Cloud", 2)),
        PresenceStatus.REMOTE,
        None,
        "B-2",
        "在宅です。Slack で連絡ください",
    ),
    SampleEmployee(
        "田中 健太",
        "1988-04-01",
        "係長",
        "営業",
        (),
        PresenceStatus.PRESENT,
        "B-1",
        "B-1",
        None,
    ),
    SampleEmployee(
        "伊藤 さくら",
        "1999-12-24",
        "メンバー",
        "事務",
        (),
        PresenceStatus.NOT_WORKING,
        None,
        "B-4",
        None,
    ),
)


def _sample_layout() -> list[Furniture]:
    """机の島2つ（それぞれ椅子6脚）と会議テーブルのある執務室。"""

    def item(type_: FurnitureType, x: int, y: int, w: int, h: int, label=None, rotation=0):
        return Furniture(
            id=None, type=type_, label=label, x=x, y=y, width=w, height=h, rotation=rotation
        )

    furniture = [
        item(FurnitureType.WALL, 0, 0, ROOM_WIDTH, 1),
        item(FurnitureType.DOOR, 22, 13, 3, 1, rotation=180),
        item(FurnitureType.OTHER, 18, 3, 6, 4, label="会議テーブル"),
        item(FurnitureType.OTHER, 1, 11, 4, 2, label="複合機"),
    ]
    for island, left in (("A", 2), ("B", 10)):
        furniture.append(item(FurnitureType.DESK, left, 4, 6, 2, label=f"島{island}"))
        for i in range(3):
            # 机の上側の椅子は背もたれを上に、下側の椅子は背もたれを下にして机に向かわせる
            furniture.append(
                item(FurnitureType.CHAIR, left + 1 + i * 2, 3, 1, 1, f"{island}-{i + 1}")
            )
            furniture.append(
                item(FurnitureType.CHAIR, left + 1 + i * 2, 6, 1, 1, f"{island}-{i + 4}", 180)
            )
    return furniture


class SampleDataService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.floors = FloorRepository(conn)
        self.rooms = RoomRepository(conn)
        self.furniture = FurnitureRepository(conn)
        self.users = UserRepository(conn)
        self.profiles = ProfileRepository(conn)
        self.user_skills = UserSkillRepository(conn)
        self.presence = PresenceRepository(conn)
        self.positions = PositionRepository(conn)
        self.job_types = JobTypeRepository(conn)
        self.skills = SkillRepository(conn)

    def is_available(self, master: User) -> bool:
        """サンプルを作成できる（まだフロアも一般ユーザーもない）か。"""
        org = master.organization_id
        return self.floors.count(org) == 0 and self.users.count_by_role(org, Role.GENERAL) == 0

    def create(self, master: User) -> None:
        if not self.is_available(master):
            raise BusinessRuleError(
                "サンプルデータは、フロアも従業員もまだない組織でだけ作成できます",
                code="ORGANIZATION_NOT_EMPTY",
            )
        org = master.organization_id
        now = to_iso(utc_now())
        # サンプルの従業員は誰もパスワードを知らない（ログインできない）状態にする
        unusable_hash = security.hash_password(secrets.token_urlsafe(32))

        with self.conn:
            floor = self.floors.create(org, "1F（サンプル）", 0)
            room = self.rooms.create(
                organization_id=org,
                floor_id=floor.id,
                name="執務室",
                width=ROOM_WIDTH,
                height=ROOM_HEIGHT,
                sort_order=0,
            )
            seats: dict[str, int] = {}
            for f in _sample_layout():
                fid = self.furniture.create(organization_id=org, room_id=room.id, item=f)
                if f.type is FurnitureType.CHAIR and f.label:
                    seats[f.label] = fid

            for i, e in enumerate(SAMPLE_EMPLOYEES, start=1):
                user = self.users.create(
                    organization_id=org,
                    # メールアドレスはシステム全体で一意なので、組織の id を含める
                    email=f"sample{i}.org{org}@example.com",
                    password_hash=unusable_hash,
                    role=Role.GENERAL,
                    # 初回設定が済んだ「利用中」の従業員として作る（パスワードをリセットすれば
                    # 通常どおり「次のログインで変更が必要」になる）
                    must_change_password=False,
                    now=now,
                )
                job_type = self.job_types.get_or_create(org, e.job_type)
                self.profiles.upsert(
                    user_id=user.id,
                    name=e.name,
                    birth_date=e.birth_date,
                    position_id=self.positions.get_or_create(org, e.position),
                    job_type_id=job_type.id,
                    default_seat_id=seats.get(e.default_seat) if e.default_seat else None,
                    now=now,
                )
                if e.skills and job_type.is_engineer:
                    self.user_skills.replace(
                        user.id,
                        [
                            (self.skills.get_or_create(org, category, name), years)
                            for category, name, years in e.skills
                        ],
                    )
                self.presence.create_initial(user_id=user.id, organization_id=org, now=now)
                self.presence.update(
                    user_id=user.id,
                    organization_id=org,
                    status=e.status,
                    seat_id=seats[e.seat] if e.seat else None,
                    comment=e.comment,
                    now=now,
                )
