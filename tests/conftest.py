import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db import migrate
from app.db.connection import connect
from app.main import create_app


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
