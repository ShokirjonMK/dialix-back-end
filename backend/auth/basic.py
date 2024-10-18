# basic auth related stuff utils, decorators

import logging
import secrets

from decouple import config

from functools import wraps
from asyncio import iscoroutinefunction

from fastapi import status, Depends
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic


basic_auth_security = HTTPBasic()

SUDO_USERNAME: str = config("BASIC_AUTH_USERNAME").encode("utf-8")
SUDO_PASSWORD: str = config("BASIC_AUTH_PASSWORD").encode("utf-8")


def basic_auth_wrapper(endpoint):
    @wraps(endpoint)
    async def decorator(*args, **kwargs):
        credentials: HTTPBasicCredentials = kwargs.get("credentials", None)
        basic_auth_status = perform_basic_authentication(credentials)

        if not credentials or not basic_auth_status:
            logging.info(f"{credentials=} {basic_auth_status=}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )

        if callable(endpoint):
            if iscoroutinefunction(endpoint):
                return await endpoint(*args, **kwargs)

            return endpoint(*args, **kwargs)

        raise TypeError("Endpoint must be a callable function")

    return decorator


def perform_basic_authentication(
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
):
    received_username = credentials.username.encode("utf-8")
    received_password = credentials.password.encode("utf-8")

    return all(
        [
            secrets.compare_digest(received_username, SUDO_USERNAME),
            secrets.compare_digest(received_password, SUDO_PASSWORD),
        ]
    )
