import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.connection import get_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health(conn: sqlite3.Connection = Depends(get_db)) -> HealthResponse:
    conn.execute("SELECT 1").fetchone()
    return HealthResponse(status="ok", database="ok")
