import logging
import typing as t
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from sqlalchemy.orm import Session

from fastapi import status
from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from backend.database.models import Account
from backend.utils.auth import is_token_blacklisted
from backend.core.settings import ALGORITHM, SECRET_KEY
from backend.core.dependencies import DatabaseSessionDependency
from backend.services.user import get_user_by_id, get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(
    request: Request, db_session: DatabaseSessionDependency
) -> Account:
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if is_token_blacklisted(db_session, token):
        logging.info(f"Received blacklisted token: {token[:15]}...")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated*",  # * means blacklisted ;)
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid"
        )

    account = get_user_by_id(db_session, user_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist, you probably gave hard coded user_id",
        )

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


def authenticate_user(db_session: Session, username: str, password: str):
    account: Account | None = get_user_by_username(db_session, username)

    if account is None:
        return

    password_matches: bool = bcrypt.checkpw(
        password=password.encode("utf-8"),
        hashed_password=account.password.encode("utf-8"),
    )

    if account and password_matches:
        return account

    return


def generate_access_token(
    data: dict, expires_delta: t.Optional[timedelta] = None
) -> str:
    expires_at = datetime.now(timezone.utc)
    expires_at += timedelta(days=1) if expires_delta is None else expires_delta

    to_encode = data.copy()
    to_encode.update({"exp": expires_at})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
