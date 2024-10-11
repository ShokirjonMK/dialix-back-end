import os
import asyncio
import logging
from typing import Annotated
from datetime import datetime
from platform import node as get_hostname

from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import JSONResponse

from backend.auth import (
    create_access_token,
    hash_password,
    get_current_user,
    authenticate_user,
)
from fastapi.security import OAuth2PasswordRequestForm

import backend.db as db
from backend.schemas import UserCreate, User
from fastapi.middleware.cors import CORSMiddleware
import secrets
from backend.sockets import sio_app
from functools import wraps
from backend.core.lifespan import lifespan_handler


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
@auth_wrapper
def signup(user: UserCreate, credentials: HTTPBasicCredentials = Depends(security)):
    user.password = hash_password(user.password)
    try:
        new_user = db.create_user(user.dict())
        access_token = create_access_token(data={"user_id": str(new_user["id"])})
        response = JSONResponse({"success": True})
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="none",
            secure=True,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sign up: {str(e)}")


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
    response.delete_cookie("access_token")
    return response


@app.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    logging.warning("current_user: %s", current_user)
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
