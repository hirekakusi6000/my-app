from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, master_data, me, profiles, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(users.router)
api_router.include_router(master_data.router)
api_router.include_router(profiles.router)
