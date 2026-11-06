from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """アプリ全体の設定。環境変数（接頭辞 APP_）または .env から読み込む。"""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    database_path: Path = BASE_DIR / "data" / "app.db"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    migrations_dir: Path = BASE_DIR / "migrations"
    frontend_dir: Path = BASE_DIR / "frontend"
    session_expire_hours: int = 24 * 7
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
