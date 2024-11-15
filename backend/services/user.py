from sqlalchemy.orm import Session
from sqlalchemy import select, exists

from backend.utils.auth import hashify
from backend.database.models import Account
from backend.utils.shortcuts import raise_400


def create_user(db_session: Session, user_data: dict) -> Account:
    if user_exists(db_session, user_data["username"], user_data["email"]):
        return raise_400("User already exists with these credentials")

    hashed_password = hashify(user_data.pop("password"))
    new_user = Account(password=hashed_password, **user_data)

    db_session.add(new_user)
    db_session.commit()

    return {"id": new_user.id, **user_data}


def user_exists(db_session: Session, username: str, email: str) -> bool:
    return db_session.query(
        exists(Account.id).where(Account.email == email or Account.username == username)
    ).scalar()


def get_user_by_username(db_session: Session, username: str) -> Account:
    return db_session.scalar(select(Account).where(Account.username == username))


def get_user_by_id(db_session: Session, user_id: str) -> Account:
    return db_session.scalar(select(Account).where(Account.id == user_id))
