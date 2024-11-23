import logging
import typing as t  # noqa: F401

import httpx

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, status

from celery.result import AsyncResult

from backend.core import settings
from workers.common import celery as celery_app
from backend.schemas import User, PBXCallHistoryRequest

from backend.services.operator import create_operators
from backend.core.dependencies.pbx import PbxCredentialsDependency
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency

from backend.tasks.pbx import process_pbx_call_task

pbx_router = APIRouter(tags=["PBX Integration"])


@pbx_router.get("/pbx-operators")
async def get_users(pbx_credentials: PbxCredentialsDependency):
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/user/get.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        response_data = response.json()

        if response_data["status"] != "1":
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {exc}",
        )


@pbx_router.post("/sync-operators")
async def sync_operators(
    db_session: DatabaseSessionDependency,
    pbx_credentials: PbxCredentialsDependency,
    current_user: User = Depends(get_current_user),
):
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/user/get.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        response_data = response.json()

        if response_data["status"] != "1":
            raise HTTPException(status_code=response.status_code, detail=response.text)

        operators_data: list[dict] = [
            {
                "name": operator.get("name"),
                "code": int(operator.get("num")),
                "owner_id": current_user.id,
            }
            for operator in response_data["data"]
        ]

        create_operators(db_session, operators_data)

        return JSONResponse(
            content={
                "success": True,
                "message": f"Total {len(operators_data)} were added",
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing operators: {exc}",
        )


@pbx_router.post("/history")
async def process_from_call_history(
    request: PBXCallHistoryRequest,
    pbx_credentials: PbxCredentialsDependency,
    current_user: User = Depends(get_current_user),
):
    task = process_pbx_call_task.delay(
        uuid=request.uuid,
        checklist_id=request.checklist_id,
        domain=pbx_credentials.domain,
        key_id=pbx_credentials.key_id,
        key=pbx_credentials.key,
        user_id=current_user.id,
    )

    logging.info(f"Task {task} is routed to celery")
    return {
        "task_id": task.id,
        "message": "Processing started. Check status using task_id.",
    }


@pbx_router.get("/history/status/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"status": "Pending"}

    elif result.state == "SUCCESS":
        return {"status": "Success", "result": result.result}

    elif result.state == "FAILURE":
        return {"status": "Failure", "error": str(result.info)}

    return {"status": result.state}
