import logging
import typing as t

from jose import jwt, JWTError

from fastapi import Depends, Request


from backend.core.settings import ALGORITHM, SECRET_KEY

from backend.database.models import Account
from backend.services.user import get_user_by_id

from backend.utils.shortcuts import raise_401
from backend.utils.auth import is_token_blacklisted
from backend.core.dependencies.database import DatabaseSessionDependency


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


CurrentUser = t.Annotated[Account, Depends(get_current_user)]
WebsocketCurrentUser = t.Annotated[Account, Depends(get_current_user_websocket)]
