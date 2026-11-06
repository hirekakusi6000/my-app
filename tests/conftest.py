import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import hash_password
from app.core.time import to_iso, utc_now
from app.db import migrate
from app.db.connection import connect
from app.entities.user import Role
from app.main import create_app
from app.repositories.user_repository import UserRepository


@pytest.fixture
def settings(tmp_path) -> Settings:
    """テストごとに一時フォルダの DB を使う設定。ローカルの .env は読み込まない。"""
    return Settings(
        _env_file=None,
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
    )


@pytest.fixture
def db(settings: Settings) -> Iterator[sqlite3.Connection]:
    """マイグレーション済みの DB への接続。"""
    migrate.run(settings.database_path, settings.migrations_dir)
    conn = connect(settings.database_path)
    yield conn
    conn.close()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """起動処理（マイグレーション）まで実行したアプリのテスト用クライアント。"""
    with TestClient(create_app(settings)) as c:
        yield c


MASTER_PASSWORD = "master-pass-123"
GENERAL_PASSWORD = "initial-pass-123"


def signup(client: TestClient, email: str = "master@example.com", org: str = "組織A") -> dict:
    """マスターとして新規登録し、ログインした状態にする。"""
    res = client.post(
        "/api/v1/auth/signup",
        json={"organization_name": org, "email": email, "password": MASTER_PASSWORD},
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_general_user(
    settings: Settings, organization_id: int, email: str = "general@example.com"
) -> int:
    """一般ユーザーを DB に直接作成する（ユーザー管理 API を実装するまでのテスト用）。"""
    conn = connect(settings.database_path)
    try:
        with conn:
            user = UserRepository(conn).create(
                organization_id=organization_id,
                email=email,
                password_hash=hash_password(GENERAL_PASSWORD),
                role=Role.GENERAL,
                must_change_password=True,
                now=to_iso(utc_now()),
            )
        return user.id
    finally:
        conn.close()
