from fastapi import status, FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from tortoise.exceptions import DoesNotExist, IntegrityError


async def does_not_exist_handler(request: Request, exc: DoesNotExist):
    exc_str = str(exc).replace('"', "")

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc_str, "success": False},
    )


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
    exceptions_table = {
        DoesNotExist: does_not_exist_handler,
        IntegrityError: integrity_error_handler,
    }

    for exc, handler in exceptions_table.items():
        app.add_exception_handler(exc, handler)
