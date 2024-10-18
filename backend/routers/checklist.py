import json
import logging
from uuid import UUID
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status

from backend import db
from utils.encoder import adapt_json
from backend.schemas import User, CheckList
from backend.core.auth import get_current_user

from backend.services.checklist import get_checklist_by, get_single_checklist_by
from backend.database.model_schemas import ChecklistPydantic, ChecklistPydanticList

checklist_router = APIRouter(tags=["Checklist"])


@checklist_router.get("/checklists")
async def list_checklist(current_user: User = Depends(get_current_user)):
    serialized_data = await ChecklistPydanticList.from_queryset(
        get_checklist_by(owner_id=current_user.id)
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=serialized_data.model_dump(mode="json"),
    )


@checklist_router.get("/checklists/{checklist_id}")
async def retrieve_checklist(
    checklist_id: UUID, current_user: User = Depends(get_current_user)
):
    data = get_single_checklist_by(owner_id=current_user.id, checklist_id=checklist_id)
    logging.info(f"{data=} {not data}")

    # if data is None:
    #     return JSONResponse(
    #         status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not found"}
    #     )

    serialized_data = await ChecklistPydantic.from_queryset_single(data)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=serialized_data.model_dump(mode="json"),
    )


@checklist_router.post("/checklists")
async def create_checklist(
    data: CheckList,
    current_user: User = Depends(get_current_user),
):
    logging.warning(f"Checklist data: {data}")

    if data.deleted_at and isinstance(data.deleted_at, str):
        logging.warning(f"Deleted at: {data.deleted_at}")
        deleted_at = datetime.fromisoformat(data.deleted_at.rstrip("Z"))
    else:
        deleted_at = None

    id = str(data.id)
    title = data.title
    payload = json.dumps(data.payload)
    active = data.active
    checklist = {
        "id": id,
        "title": title,
        "payload": payload,
        "active": active,
        "deleted_at": deleted_at,
        "owner_id": str(current_user.id),
    }
    result = db.upsert_checklist(checklist=checklist)
    logging.warning(f"Checklist result: {result}")
    response = adapt_json(result)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@checklist_router.post("/activate_checklist")
async def activate_checklist(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    result = db.activate_checklist(checklist_id, owner_id=str(current_user.id))
    if result:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"error": "Not found"}
    )
