import json
import logging
from uuid import UUID
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status, HTTPException

from backend import db
from utils.encoder import adapt_json
from backend.core.auth import get_current_user
from backend.schemas import User, CheckList, CheckListUpdate

checklist_router = APIRouter(tags=["Checklist"])


@checklist_router.get("/checklists")
async def get_list_of_checklists(current_user: User = Depends(get_current_user)):
    data = db.get_checklists(owner_id=str(current_user.id))

    for item in data:
        if isinstance(item.get("payload"), str):
            item["payload"] = json.loads(item["payload"])

    data = adapt_json(data)

    return JSONResponse(status_code=status.HTTP_200_OK, content=data)


@checklist_router.get("/checklists/{checklist_id}")
async def retrieve_checklist(
    checklist_id: UUID, current_user: User = Depends(get_current_user)
):
    data = db.get_checklist_by_id(str(checklist_id), owner_id=str(current_user.id))

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist is not found"
        )
    data = adapt_json(data)

    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])

    return JSONResponse(status_code=status.HTTP_200_OK, content=data)


@checklist_router.post("/checklist")
async def create_checklist(
    data: CheckList, current_user: User = Depends(get_current_user)
):
    logging.warning(f"Checklist data: {data}")

    deleted_at = (
        datetime.fromisoformat(data.deleted_at.rstrip("Z")) if data.deleted_at else None
    )

    checklist = {
        "id": str(data.id),
        "title": data.title,
        "payload": json.dumps(data.payload),
        "active": data.active,
        "deleted_at": deleted_at,
        "owner_id": str(current_user.id),
    }

    result = db.upsert_checklist(checklist=checklist)
    logging.warning(f"Checklist result: {result}")

    response = adapt_json(result)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@checklist_router.patch("/checklist/{checklist_id}")
async def update_checklist(
    checklist_id: str,
    data: CheckListUpdate,
    current_user: User = Depends(get_current_user),
):
    existing = db.get_checklist_by_id(checklist_id, owner_id=str(current_user.id))
    if not existing:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"error": "Not found"}
        )

    update_data = {
        "title": data.title or existing["title"],
        "payload": json.dumps(data.payload) if data.payload else existing["payload"],
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
async def activate_checklist(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    result = db.activate_checklist(checklist_id, owner_id=str(current_user.id))
    if result:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"error": "Not found"}
    )
