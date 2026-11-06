import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Request


def connect(db_path: Path) -> sqlite3.Connection:
    """SQLite に接続し、このアプリで必須の PRAGMA を設定する。

    - foreign_keys: SQLite では既定で無効なので、接続ごとに有効にする
    - journal_mode=WAL: 読み込みと書き込みが同時に起きても待ちを減らす
    - busy_timeout: 書き込みが重なったとき、すぐにエラーにせず待つ
    check_same_thread=False は、FastAPI が依存関数とエンドポイントを
    別スレッドで実行することがあるため。接続はリクエストごとに作るので共有はされない。
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """リクエストごとに接続を作り、終わったら閉じる（FastAPI の Depends 用）。"""
    conn = connect(request.app.state.settings.database_path)
    try:
        yield conn
    finally:
        conn.close()
