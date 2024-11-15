import logging
from uuid import UUID
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status

from backend import db
from utils.encoder import adapt_json
from backend.core.auth import get_current_user
from backend.schemas import User, CheckList, CheckListUpdate, CheckListCreate
from backend.services.checklist import (
    get_checklists_by_owner_id,
    get_single_checklist,
    insert_checklist,
)
from backend.core.dependencies import DatabaseSessionDependency
from backend.utils.shortcuts import model_to_dict, models_to_dict, raise_404

checklist_router = APIRouter(tags=["Checklist"])


@checklist_router.get("/checklists")
def get_list_of_checklists(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    checklists = get_checklists_by_owner_id(db_session, current_user.id)

    if not checklists:
        return checklists

    response_content = models_to_dict(CheckList, checklists)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_content,
    )


@checklist_router.get("/checklists/{checklist_id}")
def retrieve_checklist(
    db_session: DatabaseSessionDependency,
    checklist_id: UUID,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    checklist = get_single_checklist(db_session, current_user.id, checklist_id)

    if not checklist:
        return raise_404("Checklist is not found")

    response_content = model_to_dict(CheckList, checklist)

    return JSONResponse(status_code=status.HTTP_200_OK, content=response_content)


@checklist_router.post("/checklist")
def create_checklist(
    db_session: DatabaseSessionDependency,
    new_checklist: CheckListCreate,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    checklist = {"owner_id": current_user.id, **new_checklist.model_dump()}

    new_checklist = insert_checklist(db_session, checklist)
    response_content = model_to_dict(CheckList, new_checklist)

    return JSONResponse(status_code=status.HTTP_200_OK, content=response_content)


@checklist_router.patch("/checklist/{checklist_id}")
def update_checklist(
    checklist_id: str,
    data: CheckListUpdate,
    current_user: User = Depends(get_current_user),
):
    existing = db.get_checklist_by_id(checklist_id, owner_id=str(current_user.id))

    if not existing:
        return raise_404("Checklist is not found")

    update_data = {
        "title": data.title or existing["title"],
        "payload": data.payload if data.payload else existing["payload"],
        "active": data.active if data.active is not None else existing["active"],
        "deleted_at": (
            datetime.fromisoformat(data.deleted_at.rstrip("Z"))
            if data.deleted_at
            else existing["deleted_at"]
        ),
    }

    result = db.update_checklist(checklist_id, update_data)

    if result:
        logging.warning(f"Updated checklist: {result}")
        response = adapt_json(result)
        return JSONResponse(status_code=status.HTTP_200_OK, content=response)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Update failed"}
    )


@checklist_router.post("/activate_checklist")
def activate_checklist(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    result = db.activate_checklist(checklist_id, owner_id=str(current_user.id))

    if result:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})

    return raise_404("Checklist is not found")
