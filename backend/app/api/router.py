from fastapi import APIRouter

from app.api.routes import agents, chats, runs, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users.router)
api_router.include_router(agents.router)
api_router.include_router(chats.router)
api_router.include_router(runs.router)
