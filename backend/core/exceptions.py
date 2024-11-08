import logging

from fastapi import status, FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from sqlalchemy.exc import IntegrityError


async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": [
                {"loc": [], "msg": str(exc), "type": "IntegrityError"},
            ],
            "success": False,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    exceptions_table = {IntegrityError: integrity_error_handler}

    for exc, handler in exceptions_table.items():
        logging.info(f"Registering exc. handler({handler}) for {exc}")
        app.add_exception_handler(exc, handler)
