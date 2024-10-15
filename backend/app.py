import os
import logging
import datetime
from typing import Annotated
from platform import node as get_hostname

from fastapi import status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security import HTTPBasicCredentials
from fastapi import FastAPI, Depends, HTTPException, Body

from backend import db
from backend.database import user_service
from backend.core.auth import (
    generate_access_token,
    get_current_user,
    authenticate_user,
)
from backend.sockets import sio_app
from backend.schemas import UserCreate, User
from backend.core.lifespan import lifespan_handler
from backend.core.logging import configure_logging
from backend.core.exceptions import register_exception_handlers  # noqa: F401
from backend.auth.utils import add_to_blacklist
from backend.auth.basic import basic_auth_security, basic_auth_wrapper

app = FastAPI(lifespan=lifespan_handler)

configure_logging()
register_exception_handlers(app)

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


@app.post("/signup")
@basic_auth_wrapper
async def signup(
    user: UserCreate,
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
) -> JSONResponse:
    registered_user = await user_service.create_user(user.model_dump(mode="json"))

    access_token = generate_access_token(data={"user_id": str(registered_user["id"])})

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
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> JSONResponse:
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )

    access_token = generate_access_token(data={"user_id": str(user.id)})

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"user": user.model_dump(mode="json"), "token_type": "bearer"},
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
async def logout(
    request: Request, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    access_token: str | None = request.cookies.get("access_token")
    
    if access_token is not None:
        await add_to_blacklist(access_token)

    response = JSONResponse({"success": True})
    response.delete_cookie(key="access_token")

    return response


@app.get("/me")
def retrieve_current_user(current_user: User = Depends(get_current_user)):
    return {"user": current_user}


@app.get("/balance")
def retrieve_current_user_balance(current_user: User = Depends(get_current_user)):
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0)
    logging.warning("balance: %s", balance)
    return {"balance": balance}


@app.post("/topup")
@basic_auth_wrapper
def topup(
    amount: Annotated[int, Body(...)],
    email: Annotated[str, Body(...)],
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
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


@app.get("/health")
def health():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "hostname": get_hostname(),
            "time": datetime.datetime.now().isoformat(),
        },
    )
