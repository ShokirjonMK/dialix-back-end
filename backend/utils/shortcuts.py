import typing as t
from pydantic import BaseModel
from fastapi import HTTPException, status


def model_to_dict(
    PydanticModel: BaseModel, object: t.Any, dump_mode: t.Optional[str] = "json"
) -> dict[str, t.Any]:
    # validates & converts sqlalchemy(or any orm stuff) to dictionary
    return PydanticModel.model_validate(object).model_dump(mode=dump_mode)


def models_to_dict(
    PydanticModel: BaseModel, objects: t.Any, dump_mode: t.Optional[str] = "json"
) -> list[dict[str, t.Any]]:
    for index, object in enumerate(objects):
        objects[index] = model_to_dict(PydanticModel, object, dump_mode)
    return objects


def raise_400(
    detail: t.Optional[t.Any] = "Bad request", headers: t.Optional[dict] = {}
) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers
    )


def raise_401(
    detail: t.Optional[t.Any] = "Unauthorized", headers: t.Optional[dict] = {}
) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers
    )


def raise_404(
    detail: t.Optional[t.Any] = "Not Found", headers: t.Optional[dict] = {}
) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers
    )
