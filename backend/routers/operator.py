import logging  # noqa: F401
from uuid import UUID

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status


from backend.services import operator as operator_service
from backend.core.dependencies import DatabaseSessionDependency, get_current_user
from backend.utils.shortcuts import model_to_dict, models_to_dict, raise_404
from backend.schemas import (
    User,
    ListOperatorData,
    CreateOperatorData,
    UpdateOperatorData,
)

operator_router = APIRouter(tags=["Operator"])


@operator_router.get("/operators")
def list_operators(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
):
    operators = operator_service.get_operators(db_session, current_user.id)
    response_content = models_to_dict(ListOperatorData, operators) if operators else []
    return JSONResponse(status_code=status.HTTP_200_OK, content=response_content)


@operator_router.post("/operators")
def create_operator(
    db_session: DatabaseSessionDependency,
    data: CreateOperatorData,
    current_user: User = Depends(get_current_user),
):
    new_operator = operator_service.create_operator(
        db_session, current_user.id, data.model_dump()
    )
    response_content = model_to_dict(ListOperatorData, new_operator)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response_content)


@operator_router.patch("/operators/{operator_id}")
def update_operator(
    db_session: DatabaseSessionDependency,
    update_operator_data: UpdateOperatorData,
    operator_id: UUID,
    current_user: User = Depends(get_current_user),
):
    was_operator_updated: bool = operator_service.update_operator(
        db_session,
        current_user.id,
        operator_id,
        update_operator_data.model_dump(exclude_none=True),
    )
    if not was_operator_updated:
        raise_404(f"Operator with {operator_id} not found & was NOT updated")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Operator with {operator_id} was updated",
        },
    )


@operator_router.delete("/operators/{operator_id}")
def delete_operator(
    db_session: DatabaseSessionDependency,
    operator_id: UUID,
    current_user: User = Depends(get_current_user),
):
    was_operator_deleted: bool = operator_service.delete_operator(
        db_session, current_user.id, operator_id
    )
    if not was_operator_deleted:
        raise_404(f"Operator with {operator_id} not found & was NOT deleted")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": f"Operator with {operator_id} was deleted",
        },
    )
