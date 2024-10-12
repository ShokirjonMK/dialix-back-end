import os
import asyncio
import secrets
import logging
import datetime
from functools import wraps
from typing import Annotated
from platform import node as get_hostname

from starlette import status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import FastAPI, Depends, HTTPException, status, Body

import backend.db as db
from backend.database import user_service

from backend.auth import (
    create_access_token,
    get_current_user,
    authenticate_user,
)
from backend.sockets import sio_app
from backend.core.lifespan import lifespan_handler
from backend.schemas import UserCreate, User


app = FastAPI(lifespan=lifespan_handler)
app.mount("/ws/", app=sio_app)

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


origins: list[str] = [
    "http://localhost:3000",
    "https://dialix.org",
    "https://dev.dialix.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()


def authenticate_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    # Encode the credentials to compare
    input_user_name = credentials.username.encode("utf-8")
    input_password = credentials.password.encode("utf-8")

    # Retrieve stored credentials securely from environment variables
    stored_username = os.getenv("BASIC_AUTH_USERNAME").encode("utf-8")
    stored_password = os.getenv("BASIC_AUTH_PASSWORD").encode("utf-8")

    # Compare credentials securely
    is_username = secrets.compare_digest(input_user_name, stored_username)
    is_password = secrets.compare_digest(input_password, stored_password)

    if is_username and is_password:
        return True

    # If credentials are invalid, raise an HTTP Exception
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def auth_wrapper(endpoint):
    @wraps(endpoint)
    async def secured_endpoint(*args, **kwargs):
        credentials: HTTPBasicCredentials = kwargs.get("credentials", None)
        if not credentials or not authenticate_basic_auth(credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        # Check if the endpoint is a coroutine (asynchronous function)
        if callable(endpoint):
            if asyncio.iscoroutinefunction(endpoint):
                return await endpoint(*args, **kwargs)
            else:
                return endpoint(*args, **kwargs)
        else:
            raise TypeError("Endpoint must be a callable function")

    return secured_endpoint


@app.post("/signup")
# @auth_wrapper
async def signup(
    user: UserCreate,
    credentials: HTTPBasicCredentials = Depends(security),
):
    registered_user = await user_service.create_user(user.model_dump())

    access_token = create_access_token(data={"user_id": str(registered_user["id"])})

    response = JSONResponse({"success": True}, status_code=status.HTTP_201_CREATED)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
    )

    return response


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"user_id": str(user.id)})
    user_json = user.json()
    response = JSONResponse(
        status_code=200, content={"user": user_json, "token_type": "bearer"}
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
    )
    return response


@app.post("/logout")
def logout():
    response = JSONResponse({"success": True})

    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=1
    )

    response.set_cookie(
        key="access_token",
        httponly=True,
        samesite="none",
        secure=True,
        value="",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )
    return response


@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    logging.info(f"Current_user is {current_user}")
    return {"user": current_user}


@app.get("/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0)
    logging.warning("balance: %s", balance)
    return {"balance": balance}


@app.post("/topup")
@auth_wrapper
def topup(
    amount: Annotated[int, Body(...)],
    email: Annotated[str, Body(...)],
    credentials: HTTPBasicCredentials = Depends(security),
):
    try:
        user = db.get_user_by_email(email)
        db.create_topup_transaction(
            owner_id=user["id"],
            amount=amount,
            type="topup",
        )
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        logging.error(f"Error occurred while topping up: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/healthz")
def healthz():
    # db.migrate_up()
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "time": datetime.now().isoformat(),
            "hostname": get_hostname(),
        },
    )
