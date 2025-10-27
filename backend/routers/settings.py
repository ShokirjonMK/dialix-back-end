"""
Settings Router

User sozlamalarini boshqarish uchun API endpoints
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.schemas import (
    UserSettingsUpdate,
    UserSettings as UserSettingsSchema,
)
from backend.services import settings
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.utils.shortcuts import model_to_dict

settings_router = APIRouter(tags=["Settings"])


@settings_router.get("/settings")
def get_settings(
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User sozlamalarini olish"""
    user_settings = settings.get_user_settings(db_session, current_user.id)
    return model_to_dict(UserSettingsSchema, user_settings)


@settings_router.patch("/settings")
def update_settings(
    settings_data: UserSettingsUpdate,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User sozlamalarini yangilash"""
    updated_settings = settings.update_user_settings(
        db_session, current_user.id, settings_data.model_dump(exclude_none=True)
    )
    return {
        "success": True,
        "settings": model_to_dict(UserSettingsSchema, updated_settings),
    }


@settings_router.get("/settings/notifications")
def get_notification_settings(
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Notification sozlamalarini olish"""
    notification_settings = settings.get_user_notification_settings(
        db_session, current_user.id
    )
    return notification_settings


@settings_router.patch("/settings/notifications")
def update_notification_settings(
    notification_data: dict,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Notification sozlamalarini yangilash"""
    updated = settings.update_notification_settings(
        db_session, current_user.id, notification_data
    )
    return {
        "success": True,
        "notification_settings": model_to_dict(UserSettingsSchema, updated),
    }
