from sqlalchemy.orm import Session
from sqlalchemy import select, exists

from fastapi import HTTPException, status

from backend.utils.auth import hashify
from backend.database.models import Account


def create_user(db_session: Session, user_data: dict) -> Account:
    if user_exists(db_session, user_data["username"], user_data["email"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists with these credentials",
        )

    new_user = Account(
        id=user_data["id"],
        email=user_data["email"],
        username=user_data["username"],
        password=hashify(user_data["password"]),
        role=user_data["role"],
        company_name=user_data["company_name"],
    )

    db_session.add(new_user)
    db_session.commit()

    user_data.pop("password")

    return {"id": new_user.id, **user_data}


def user_exists(db_session: Session, username: str, email: str) -> bool:
    return db_session.query(
        exists(Account.id).where(Account.email == email or Account.username == username)
    ).scalar()


def get_user_by_username(db_session: Session, username: str) -> Account:
    return db_session.scalar(select(Account).where(Account.username == username))


def get_user_by_id(db_session: Session, user_id: str) -> Account:
    return db_session.scalar(select(Account).where(Account.id == user_id))
