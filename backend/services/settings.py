"""
User Settings Service

User sozlamalarini boshqarish uchun service layer
"""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func
from backend.database.models import UserSettings, Account


def get_user_settings(db: Session, user_id: UUID) -> UserSettings:
    """User'ning sozlashlarini olish"""
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    if not settings:
        # Create default settings
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logging.info(f"Default settings created for user {user_id}")

    return settings


def update_user_settings(
    db: Session, user_id: UUID, settings_data: dict
) -> UserSettings:
    """User'ning sozlashlarini yangilash"""
    db.execute(
        update(UserSettings)
        .where(UserSettings.user_id == user_id)
        .values(**settings_data, updated_at=func.now())
    )
    db.commit()

    return get_user_settings(db, user_id)


def get_user_notification_settings(db: Session, user_id: UUID) -> dict:
    """User'ning notification sozlamalarini olish"""
    settings = get_user_settings(db, user_id)

    return {
        "email_notifications": settings.email_notifications,
        "sms_notifications": settings.sms_notifications,
        "push_notifications": settings.push_notifications,
    }


def update_notification_settings(
    db: Session, user_id: UUID, notification_settings: dict
) -> UserSettings:
    """Notification sozlamalarini yangilash"""
    update_data = {
        "email_notifications": notification_settings.get("email_notifications"),
        "sms_notifications": notification_settings.get("sms_notifications"),
        "push_notifications": notification_settings.get("push_notifications"),
    }

    return update_user_settings(
        db, user_id, {k: v for k, v in update_data.items() if v is not None}
    )


def get_user_language(db: Session, user_id: UUID) -> str:
    """User'ning tili"""
    settings = get_user_settings(db, user_id)
    return settings.language


def update_user_language(db: Session, user_id: UUID, language: str) -> UserSettings:
    """User tili va timezone ni yangilash"""
    # Update settings
    db.execute(
        update(UserSettings)
        .where(UserSettings.user_id == user_id)
        .values(language=language, updated_at=func.now())
    )

    # Update account preferred language
    db.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(preferred_language=language, updated_at=func.now())
    )

    db.commit()

    return get_user_settings(db, user_id)
