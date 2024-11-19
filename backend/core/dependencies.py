import logging
import typing as t

from jose import jwt, JWTError

from fastapi import Depends, Request

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.utils.shortcuts import raise_401
from backend.database.session_manager import sessionmanager
from backend.schemas import BitrixCredentials, PbxCredentialsFull, User
from backend.database.models import (
    PbxCredentials as PbxCredentialsDb,
    BitrixCredentials as BitrixCredentialsDb,
    Account,
)
from backend.utils.pbx import test_pbx_credentials, get_pbx_keys
from backend.services.user import get_user_by_id
from backend.utils.auth import is_token_blacklisted
from backend.core.settings import ALGORITHM, SECRET_KEY
from backend.services.credentials import update_pbx_credentials


def get_db_session() -> t.Generator[Session, t.Any, None]:
    with sessionmanager.session() as session:
        yield session


DatabaseSessionDependency = t.Annotated[Session, Depends(get_db_session)]


def get_current_user(
    request: Request, db_session: DatabaseSessionDependency
) -> Account:
    token = request.cookies.get("access_token")

    if not token:
        raise_401()

    if is_token_blacklisted(db_session, token):
        logging.info(f"Received blacklisted token: {token[:15]}...")
        raise_401()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")

        if user_id is None:
            raise_401("Invalid token")

    except JWTError:
        raise_401("Invalid token")

    account = get_user_by_id(db_session, user_id)

    if not account:
        raise_401("User does not exist, you probably gave hard coded user_id")

    return account


def get_current_user_websocket(
    token: str, db_session: DatabaseSessionDependency
) -> Account:
    if not token:
        return None

    if is_token_blacklisted(db_session, token):
        logging.info(f"Received blacklisted token: {token[:15]}...")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
    except JWTError:
        return None

    account = get_user_by_id(db_session, user_id)

    if not account:
        return None

    return account


def get_pbx_credentials(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> PbxCredentialsFull:
    logging.info("PBX cred works!")
    pbx_credentials = db_session.scalar(
        select(PbxCredentialsDb).where(PbxCredentialsDb.owner_id == current_user.id)
    )

    if not pbx_credentials:
        raise_401("No pbx credentials found")

    if pbx_credentials.key is None or pbx_credentials.key_id is None:
        logging.info("Pbx key and key_id is NULL, getting new keys")

        key_id, key = get_pbx_keys(pbx_credentials.domain, pbx_credentials.api_key)

        logging.info(f"New {key=} and {key_id=}, updating pbx credentials on db")

        update_pbx_credentials(db_session, current_user.id, key, key_id)

        db_session.commit()
        logging.info(f"Refreshing {pbx_credentials=}")
        db_session.refresh(pbx_credentials)

    if not (
        test_pbx_credentials(
            pbx_credentials.domain, pbx_credentials.key, pbx_credentials.key_id
        )
    ):
        logging.info("Updating pbx keys, they are not valid")
        update_pbx_credentials(db_session, current_user.id, None, None)
        raise_401("Pbx keys are not valid!")

    pbx_credentials_full = PbxCredentialsFull(
        domain=pbx_credentials.domain,
        key=pbx_credentials.key,
        key_id=pbx_credentials.key_id,
    )
    logging.info(f"{pbx_credentials_full=}")

    return pbx_credentials_full


def get_bitrix_credentials(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> BitrixCredentials:
    query = select(BitrixCredentialsDb).where(
        BitrixCredentialsDb.owner_id == current_user.id
    )
    bitrix_credentials = db_session.scalar(query)

    if not bitrix_credentials:
        raise_401("No bitrix credentials found")

    return BitrixCredentials(webhook_url=bitrix_credentials.webhook_url)


PbxCredentialsDependency = t.Annotated[PbxCredentialsFull, Depends(get_pbx_credentials)]
BitrixCredentialsDependency = t.Annotated[
    BitrixCredentials, Depends(get_bitrix_credentials)
]
