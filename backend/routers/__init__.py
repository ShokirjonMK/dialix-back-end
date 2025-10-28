from fastapi import APIRouter

from backend.routers.pbx import pbx_router
from backend.routers.user import user_router
from backend.routers.audio import audio_router
from backend.routers.bitrix import bitrix_router
from backend.routers.amocrm import amocrm_router
from backend.routers.operator import operator_router
from backend.routers.dashboard import dashboard_router
from backend.routers.checklist import checklist_router
from backend.routers.settings import settings_router
from backend.routers.ai_chat import ai_chat_router
from backend.routers.activity_log import activity_log_router
from backend.routers.company import company_router
from backend.routers.health import health_router

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
    amocrm_router,
    # new features
    settings_router,
    ai_chat_router,
    activity_log_router,
    company_router,
    # monitoring
    health_router,
]
