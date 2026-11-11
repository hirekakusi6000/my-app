from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """アプリ全体の設定。環境変数（接頭辞 APP_）または .env から読み込む。

    公開するときに変える項目は my-app-docs の design/07-deployment.md を参照。
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # ───────── データの保存先 ─────────
    database_path: Path = BASE_DIR / "data" / "app.db"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    backup_dir: Path = BASE_DIR / "data" / "backups"
    backup_keep: int = 14  # 残しておくバックアップの数（古いものから削除）
    migrations_dir: Path = BASE_DIR / "migrations"

    # ───────── セッション・セキュリティ ─────────
    session_expire_hours: int = 24 * 7
    # HTTPS で公開するときは true にする（Cookie に Secure を付け、HSTS ヘッダーを送る）
    cookie_secure: bool = False
    # API 仕様書（/docs）を公開するか。公開環境では false を推奨
    enable_api_docs: bool = True

    # ───────── ログ ─────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # 指定するとファイルにも出力する（10MB ごとに切り替え、5世代まで残す）
    log_file: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
