import copy
import logging
import typing as t
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, exists

from backend.utils.auth import hashify
from backend.utils.shortcuts import raise_400
from backend.database.models import Account, PbxCredentials, BitrixCredentials

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
