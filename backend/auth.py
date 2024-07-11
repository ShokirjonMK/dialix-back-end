import logging
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from psycopg2.extras import RealDictCursor

from . import db
from .schemas import User
from .db import ConnectionWrapper

# Configuration
SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.get_user_by_id(user_id)
        user = User.parse_obj(dict(user))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user.hide_password()


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


@db.db_connection_wrapper
def authenticate_user(connection, username: str, password: str):
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM account WHERE username = %s", (username,))
            user_record = cursor.fetchone()
            if user_record and bcrypt.checkpw(
                password.encode("utf-8"), user_record["password"].encode("utf-8")
            ):
                user = User.parse_obj(user_record)
                return user.hide_password()
    except Exception as e:
        print(f"Authentication error: {e}")
        return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # No expiration time
        expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
