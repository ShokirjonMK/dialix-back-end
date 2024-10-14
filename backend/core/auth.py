import os
import logging
import typing as t
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError
from passlib.context import CryptContext

from starlette import status
from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from tortoise.contrib.pydantic import pydantic_model_creator, pydantic_queryset_creator

from backend import db
from backend.schemas import User
from backend.database.models import Account

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

AccountPydantic = pydantic_model_creator(Account)


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
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

    account = await Account.get(id=user_id)
    logging.info(f"Fetched account: {account}")

    if await account.first() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist, you probably gave hard coded user_id",
        )

    return await AccountPydantic.from_tortoise_orm(account)


def get_current_user_websocket(token: str):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated") from None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token") from None
        user = db.get_user_by_id(user_id)
        user = User.parse_obj(dict(user))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found") from None
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    return user.hide_password()


async def authenticate_user(username: str, password: str):
    account = await Account.get(username=username)

    if account and bcrypt.checkpw(
        password=password.encode("utf-8"),
        hashed_password=account.password.encode("utf-8"),
    ):
        return await AccountPydantic.from_tortoise_orm(account)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_access_token(
    data: dict, expires_delta: t.Optional[timedelta] = None
) -> str:
    expires_at = datetime.now(timezone.utc)
    expires_at += timedelta(days=1) if expires_delta is None else expires_delta

    to_encode = data.copy()
    to_encode.update({"exp": expires_at})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
