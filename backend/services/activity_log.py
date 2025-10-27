"""
Activity Logging Service

CRUD operations uchun audit log va activity tracking
"""

import logging
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc

from backend.database.models import ActivityLog


def log_activity(
    db: Session,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None,
) -> ActivityLog:
    """
    CRUD operations uchun logging

    Args:
        db: Database session
        user_id: User ID who performed the action
        action: Action type (CREATE, UPDATE, DELETE, VIEW)
        resource_type: Resource type (record, checklist, operator, account)
        resource_id: Resource ID
        details: Additional details as dict
        ip_address: User IP address
        user_agent: User agent string

    Returns:
        Created ActivityLog object
    """
    log_entry = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    logging.info(
        f"Activity logged: {action} on {resource_type}/{resource_id} by {user_id}"
    )
    return log_entry


def get_user_activity_logs(
    db: Session,
    user_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
) -> list[ActivityLog]:
    """
    User'ning faollik loglarini filter qilib olish

    Args:
        db: Database session
        user_id: User ID
        start_date: Start date filter
        end_date: End date filter
        action: Action type filter
        resource_type: Resource type filter
        limit: Maximum records to return

    Returns:
        List of ActivityLog objects
    """
    query = select(ActivityLog).where(ActivityLog.user_id == user_id)

    if start_date:
        query = query.where(ActivityLog.created_at >= start_date)
    if end_date:
        query = query.where(ActivityLog.created_at <= end_date)
    if action:
        query = query.where(ActivityLog.action == action)
    if resource_type:
        query = query.where(ActivityLog.resource_type == resource_type)

    query = query.order_by(desc(ActivityLog.created_at)).limit(limit)

    result = db.execute(query)
    return list(result.scalars().all())


def get_company_activity_logs(
    db: Session, company_id: UUID, filters: dict = None, limit: int = 100
) -> list[ActivityLog]:
    """
    Company bo'yicha activity logs

    Args:
        db: Database session
        company_id: Company ID
        filters: Additional filters
        limit: Maximum records to return

    Returns:
        List of ActivityLog objects
    """
    # Get all users in company first
    from backend.database.models import Account

    user_ids = db.query(Account.id).filter(Account.company_id == company_id).all()
    user_ids = [uid[0] for uid in user_ids]

    if not user_ids:
        return []

    # Filter activity logs for these users
    query = select(ActivityLog).where(ActivityLog.user_id.in_(user_ids))

    if filters:
        if "start_date" in filters:
            query = query.where(ActivityLog.created_at >= filters["start_date"])
        if "end_date" in filters:
            query = query.where(ActivityLog.created_at <= filters["end_date"])
        if "action" in filters:
            query = query.where(ActivityLog.action == filters["action"])
        if "resource_type" in filters:
            query = query.where(ActivityLog.resource_type == filters["resource_type"])

    query = query.order_by(desc(ActivityLog.created_at)).limit(limit)

    result = db.execute(query)
    return list(result.scalars().all())


def get_audit_trail_for_resource(
    db: Session, resource_type: str, resource_id: UUID
) -> list[ActivityLog]:
    """
    Muayyan resource uchun audit trail

    Args:
        db: Database session
        resource_type: Resource type
        resource_id: Resource ID

    Returns:
        List of ActivityLog objects for this resource
    """
    query = (
        select(ActivityLog)
        .where(
            and_(
                ActivityLog.resource_type == resource_type,
                ActivityLog.resource_id == resource_id,
            )
        )
        .order_by(desc(ActivityLog.created_at))
    )

    result = db.execute(query)
    return list(result.scalars().all())


def get_recent_activities(
    db: Session, user_id: Optional[UUID] = None, limit: int = 50
) -> list[ActivityLog]:
    """Oxirgi faolliklarni olish"""
    query = select(ActivityLog)

    if user_id:
        query = query.where(ActivityLog.user_id == user_id)

    query = query.order_by(desc(ActivityLog.created_at)).limit(limit)

    result = db.execute(query)
    return list(result.scalars().all())
