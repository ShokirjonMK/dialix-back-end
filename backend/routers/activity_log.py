"""
Activity Logs Router

Activity logging va audit trail uchun API endpoints
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from uuid import UUID

from backend.schemas import ActivityLog
from backend.services import activity_log
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.utils.shortcuts import model_to_dict, models_to_dict

activity_log_router = APIRouter(tags=["Activity Logs"])


@activity_log_router.get("/activity-logs")
def get_user_activity_logs(
    db_session: DatabaseSessionDependency,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User o'zining activity loglarini ko'rish"""
    logs = activity_log.get_user_activity_logs(
        db_session, current_user.id, start_date, end_date, action, resource_type, limit
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"logs": [model_to_dict(ActivityLog, log) for log in logs]},
    )


@activity_log_router.get("/activity-logs/{resource_type}/{resource_id}")
def get_resource_audit_trail(
    resource_type: str,
    resource_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Resource uchun audit trail"""
    trail = activity_log.get_audit_trail_for_resource(
        db_session, resource_type, resource_id
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"audit_trail": [model_to_dict(ActivityLog, item) for item in trail]},
    )


@activity_log_router.get("/recent-activities")
def get_recent_activities(
    db_session: DatabaseSessionDependency,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Oxirgi faolliklarni olish"""
    logs = activity_log.get_recent_activities(db_session, current_user.id, limit)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"activities": [model_to_dict(ActivityLog, log) for log in logs]},
    )
