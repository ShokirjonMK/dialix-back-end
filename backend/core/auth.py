import typing as t
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from backend.database.models import Account
from backend.core.settings import ALGORITHM, SECRET_KEY
from backend.services.user import get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def authenticate_user(db_session: Session, username: str, password: str):
    account: Account = get_user_by_username(db_session, username)

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
