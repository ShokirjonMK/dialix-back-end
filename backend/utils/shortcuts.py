import typing as t
from uuid import UUID
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import HTTPException, status


def model_to_dict(
    PydanticModel: BaseModel,
    object: t.Any,
    dump_mode: t.Optional[str] = "json",
    exclude: list = None,
) -> dict[str, t.Any]:
    # validates & converts sqlalchemy(or any orm stuff) to dictionary
    return PydanticModel.model_validate(object).model_dump(
        mode=dump_mode, exclude=exclude
    )


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


def get_distinct_values(db_session: Session, column, owner_id: UUID):
    query = select(column).filter(column.isnot(None)).distinct()
    return db_session.execute(query).scalars().all()


def get_filterable_values_for(
    table_class, columns: list[str], db_session: Session, owner_id: UUID
) -> dict[str, list[str]]:
    result = dict()

    for column in [getattr(table_class, column) for column in columns]:
        result[column.name] = get_distinct_values(db_session, column, owner_id)

    return result
