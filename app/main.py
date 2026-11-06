from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title="my-app")
    # API を先に登録し、残りのパスを静的ファイル配信に回す
    app.include_router(api_router)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
