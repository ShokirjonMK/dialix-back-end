import copy
import logging
import typing as t
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, exists, update, or_, func

from backend.utils.auth import hashify
from backend.utils.shortcuts import raise_400
from backend.database.models import (
    Account,
    PbxCredentials,
    BitrixCredentials,
    Transaction,
)

USER_CREDENTIALS: tuple[tuple[str, t.Any]] = (
    ("pbx_credentials", PbxCredentials),
    ("bitrix_credentials", BitrixCredentials),
)


def create_user(db_session: Session, user_data: dict) -> Account:
    if user_exists(db_session, user_data["username"], user_data["email"]):
        raise_400("User already exists with these credentials")

    hashed_password = hashify(user_data.pop("password"))
    user_data_with_credentials = copy.deepcopy(user_data)

    for credential_type, _ in USER_CREDENTIALS:
        user_data.pop(credential_type)

    new_user = Account(password=hashed_password, **user_data)

    db_session.add(new_user)
    user_credentials = create_user_credentials(user_data_with_credentials, new_user.id)

    if user_credentials:
        logging.info(f"User has some credentials {user_credentials}")
        db_session.add_all(user_credentials)
    else:
        logging.info("New user does not have any credentials")

    db_session.commit()

    return new_user


def create_user_credentials(user_data: dict, user_id: UUID) -> list[t.Any]:
    credentials: list[t.Any] = []

    for credential_type, Credential in USER_CREDENTIALS:
        if credentials_data := user_data.get(credential_type):
            credentials_data["owner_id"] = user_id
            credential = Credential(**credentials_data)
            credentials.append(credential)

    return credentials


def user_exists(db_session: Session, username: str, email: str) -> bool:
    return db_session.query(
        exists(Account.id).where(Account.email == email or Account.username == username)
    ).scalar()


def get_user_by_username(db_session: Session, username: str) -> Account:
    return db_session.scalar(select(Account).where(Account.username == username))


def get_user_by_id(db_session: Session, user_id: UUID) -> Account:
    return db_session.scalar(select(Account).where(Account.id == user_id))


def update_user_info(db_session: Session, user_id: UUID, update_data: dict) -> Account:
    """User ma'lumotini yangilash"""
    db_session.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(**update_data, updated_at=func.now())
    )
    db_session.commit()
    return get_user_by_id(db_session, user_id)


def delete_user(db_session: Session, user_id: UUID):
    """User'ni o'chirish (soft delete)"""
    db_session.execute(
        update(Account).where(Account.id == user_id).values(is_active=False)
    )
    db_session.commit()
    logging.info(f"User {user_id} deactivated")


def search_users(
    db_session: Session,
    query_str: str = None,
    role: str = None,
    company_id: UUID = None,
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Account]:
    """User'lar ichida qidirish"""
    search_query = select(Account)

    if query_str:
        search_query = search_query.where(
            or_(
                Account.username.ilike(f"%{query_str}%"),
                Account.email.ilike(f"%{query_str}%"),
                Account.company_name.ilike(f"%{query_str}%"),
            )
        )

    if role:
        search_query = search_query.where(Account.role == role)
    if company_id:
        search_query = search_query.where(Account.company_id == company_id)
    if is_active is not None:
        search_query = search_query.where(Account.is_active == is_active)

    search_query = search_query.limit(limit).offset(offset)

    result = db_session.execute(search_query)
    return list(result.scalars().all())


def reset_user_password(db_session: Session, user_id: UUID, new_password: str):
    """User parolini qayta tiklash"""
    hashed = hashify(new_password)
    db_session.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(password=hashed, updated_at=func.now())
    )
    db_session.commit()
    logging.info(f"Password reset for user {user_id}")


def block_user(db_session: Session, user_id: UUID):
    """User'ni bloklash"""
    db_session.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(is_blocked=True, updated_at=func.now())
    )
    db_session.commit()
    logging.info(f"User {user_id} blocked")


def unblock_user(db_session: Session, user_id: UUID):
    """User'ni blokdan ochirish"""
    db_session.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(is_blocked=False, updated_at=func.now())
    )
    db_session.commit()
    logging.info(f"User {user_id} unblocked")


def get_user_transaction_history(
    db_session: Session, user_id: UUID, limit: int = 100
) -> list[Transaction]:
    """User'ning transaction tarixini olish"""
    query = (
        select(Transaction)
        .where(Transaction.owner_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    result = db_session.execute(query)
    return list(result.scalars().all())
