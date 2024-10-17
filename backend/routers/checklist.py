import json
import logging
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status

from backend import db
from utils.encoder import adapt_json
from backend.schemas import User, CheckList
from backend.core.auth import get_current_user

checklist_router = APIRouter()


@checklist_router.post("/checklist")
async def upsert_checklist(
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


@checklist_router.get("/checklists")
async def get_list_of_checklists(current_user: User = Depends(get_current_user)):
    data = db.get_checklists(owner_id=str(current_user.id))
    data = adapt_json(data)

    return JSONResponse(status_code=status.HTTP_200_OK, content=data)


@checklist_router.get("/checklist/{checklist_id}")
async def get_checklist_by_id(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    data = db.get_checklist_by_id(checklist_id, owner_id=str(current_user.id))
    if data:
        data = adapt_json(data)
        return JSONResponse(status_code=status.HTTP_200_OK, content=data)

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"error": "Not found"}
    )
