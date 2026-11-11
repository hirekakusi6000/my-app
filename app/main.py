import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.log_config import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import RateLimiter
from app.db import migrate

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_file)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 起動時に未適用のマイグレーションを適用する
        applied = migrate.run(settings.database_path, settings.migrations_dir)
        if applied:
            logger.info(
                "マイグレーションを適用しました: %s", ", ".join(f"{v:04d}" for v in applied)
            )
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        if not settings.cookie_secure:
            logger.warning(
                "APP_COOKIE_SECURE が false です。HTTPS で公開する場合は true にしてください"
            )
        yield

    docs = settings.enable_api_docs
    app = FastAPI(
        title="オフィス座席・従業員管理システム",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.settings = settings
    app.state.rate_limiter = RateLimiter()

    register_exception_handlers(app)
    # 後から追加したものが外側になる。リクエストID とアクセスログはいちばん外側で扱う
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)
    app.add_middleware(RequestContextMiddleware)

    # 画面は別のリポジトリ（Vue）。公開時はリバースプロキシで /api だけをこのアプリに転送する
    app.include_router(api_router)
    return app


app = create_app()
