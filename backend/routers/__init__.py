from fastapi import APIRouter

from backend.routers.pbx import pbx_router
from backend.routers.user import user_router
from backend.routers.audio import audio_router
from backend.routers.bitrix import bitrix_router
from backend.routers.operator import operator_router
from backend.routers.dashboard import dashboard_router
from backend.routers.checklist import checklist_router

__all__ = ["routers"]

routers: list[APIRouter] = [
    # core
    user_router,
    operator_router,
    checklist_router,
    audio_router,
    dashboard_router,
    # integrations
    pbx_router,
    bitrix_router,
]
