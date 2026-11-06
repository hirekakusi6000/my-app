from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.db import migrate


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 起動時に未適用のマイグレーションを適用する
        migrate.run(settings.database_path, settings.migrations_dir)
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(title="オフィス座席・従業員管理システム", lifespan=lifespan)
    app.state.settings = settings

    register_exception_handlers(app)
    # API を先に登録し、残りのパスを画面ファイルの配信に回す
    app.include_router(api_router)
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
