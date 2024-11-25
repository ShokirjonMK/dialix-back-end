import uuid
import logging
import typing as t  # noqa: F401
from typing import List, Tuple, Union

from celery.result import AsyncResult

from fastapi.responses import JSONResponse
from fastapi import Depends, UploadFile, Request, APIRouter, status, HTTPException

from backend import db
from backend.schemas import (
    User,
    ReprocessRecord,
    RecordQueryParams,
    ResultQueryParams,
    PBXCallHistoryRequest,
)
from backend.core import settings
from workers.data import upsert_data
from utils.encoder import adapt_json
from workers.api import api_processing
from utils.storage import get_stream_url
from backend.utils.pbx import filter_calls
from backend.services.record import (
    get_all_record_titles,
    get_filterable_values_for_record,
)
from backend.services.result import get_filterable_values_for_result
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.pbx import get_pbx_credentials, PbxCredentialsDependency
from backend.utils.analyze import (
    analyze_data_handler,
    estimate_costs_from_pbx,
    estimate_costs_from_upload,
)
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.core.dependencies.audio_processing import process_form_data

import httpx

audio_router = APIRouter(tags=["Audios"])


def generate_task_id(user_id) -> str:
    return f"{user_id}/{uuid.uuid4()}"


@audio_router.get("/filterable-values")
def get_filterable_values(
    db_session: DatabaseSessionDependency, current_user: CurrentUser
):
    return {
        **get_filterable_values_for_record(db_session, current_user.id),
        **get_filterable_values_for_result(db_session, current_user.id),
    }


@audio_router.get("/audios_results")
async def get_audio_and_results(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
    record_query_params: RecordQueryParams = Depends(),
    result_query_params: ResultQueryParams = Depends(),
    start_stamp_from: t.Optional[str] = None,
    end_stamp_to: t.Optional[str] = None,
):
    record_filter_params = record_query_params.model_dump(
        mode="python", exclude_none=True
    )
    result_filter_params = result_query_params.model_dump(
        mode="python", exclude_none=True
    )
    logging.info(f"{record_filter_params=} {result_filter_params=}")

    recordings = db.get_records_v1(
        owner_id=str(current_user.id), filter_params=record_filter_params
    )
    recordings = adapt_json(recordings)

    full_audios = []
    just_audios = []
    general_audios = []
    audios_with_checklist = []

    folder_name = current_user.company_name.lower().replace(" ", "_")

    for record in recordings:
        result = db.get_result_by_record_id(
            record["id"],
            owner_id=str(current_user.id),
            filter_params=result_filter_params,
        )

        if result_filter_params:
            if result is None:
                """if filters are being applied, and 
                results is NONE then
                we don't include this recording
                """
                continue

        audio_url = get_stream_url(f"{folder_name}/{record['storage_id']}")
        record["audio_url"] = audio_url

        if result:
            result: dict

            summary, checklist_result = (
                result.get("summary"),
                result.get("checklist_result"),
            )

            if summary and checklist_result:
                record["result"] = adapt_json(result)
                full_audios.append(record)
            elif checklist_result:
                record["result"] = adapt_json(result)
                audios_with_checklist.append(record)
            else:
                record["result"] = adapt_json(result)
                general_audios.append(record)
        else:
            record["result"] = None
            just_audios.append(record)

    response = {
        "just_audios": just_audios,
        "audios_with_checklist": audios_with_checklist,
        "general_audios": general_audios,
        "full_audios": full_audios,
        "recordings": recordings,
    }

    if start_stamp_from and end_stamp_to:
        response["pbx_calls"] = get_pbx_call_history(
            db_session, current_user, start_stamp_from, end_stamp_to
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@audio_router.get("/v2/audios_results")
async def get_audio_and_results_v2(current_user: User = Depends(get_current_user)):
    recordings = db.get_records_v2(owner_id=str(current_user.id))

    recordings = adapt_json(recordings)
    folder_name = current_user.company_name.lower().replace(" ", "_")

    for record in recordings:
        result = db.get_result_by_record_id(record["id"], owner_id=str(current_user.id))
        audio_url = get_stream_url(f"{folder_name}/{record['storage_id']}")

        record["audio_url"] = audio_url

        if not result:
            record["type"] = "just_audio"
            record["result"] = None
        else:
            summary_exists: bool = result.get("summary") is not None
            checklist_result_exists: bool = result.get("checklist_result") is not None

            if summary_exists and checklist_result_exists:
                record["type"] = "full_audio"
            elif checklist_result_exists:
                record["type"] = "audio_with_checklist"
            else:
                record["type"] = "general_audio"

            record["result"] = adapt_json(result)

    return JSONResponse(status_code=status.HTTP_200_OK, content=recordings)


@audio_router.get("/audio/file/{storage_id}")
async def get_audio_file(request: Request, storage_id: str):
    # return url to audio file
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"url": f"{request.base_url}uploads/{storage_id}"},
    )
    # or file itself
    # return FileResponse(f"uploads/{storage_id}")


@audio_router.post("/audio", dependencies=[Depends(get_current_user)])
async def analyze_data(
    db_session: DatabaseSessionDependency,
    processed_data: Tuple[
        List[UploadFile], List[bool], List[Union[str, None]], List[dict]
    ] = Depends(process_form_data),
    current_user: User = Depends(get_current_user),
):
    return analyze_data_handler(db_session, processed_data, current_user)


@audio_router.post("/estimate", dependencies=[Depends(get_current_user)])
async def estimate_cost_before_process(
    request: Request, db_session: DatabaseSessionDependency
):
    return await estimate_costs_from_upload(request, db_session)


@audio_router.post("/estimate-from-pbx", dependencies=[Depends(get_current_user)])
def estimate_cost_before_process_from_pbx(
    data: PBXCallHistoryRequest,
    pbx_credentials: PbxCredentialsDependency,
    request: Request,
    db_session: DatabaseSessionDependency,
):
    return estimate_costs_from_pbx(
        request,
        db_session,
        data.uuid,
        pbx_credentials.domain,
        pbx_credentials.key_id,
        pbx_credentials.key,
        data.general,
        data.checklist_id,
    )


@audio_router.post("/reprocess")
async def reprocess_data(
    record: ReprocessRecord,
    current_user: User = Depends(get_current_user),
):
    record_id = record.record_id
    checklist_id = record.checklist_id
    general = record.general
    folder_name = current_user.company_name.lower().replace(" ", "_")
    existing_record = db.get_record_by_id(record_id, owner_id=str(current_user.id))
    if not existing_record:
        return JSONResponse(status_code=404, content={"error": "Record not found"})

    # count the price
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0) or 0
    balance = balance if balance is not None else 0
    total_price = 0
    duration = existing_record["duration"]
    mohirai_price = (
        duration * settings.MOHIRAI_PRICE_PER_MS
        if existing_record["payload"] is None
        else 0
    )
    general_price = (
        duration * settings.GENERAL_PROMPT_PRICE_PER_MS if general is True else 0
    )
    checklist_price = (
        duration * settings.CHECKLIST_PROMPT_PRICE_PER_MS
        if checklist_id is not None
        else 0
    )
    total_price += mohirai_price + general_price + checklist_price

    if total_price > balance:
        return JSONResponse(status_code=400, content={"error": "Not enough balance"})

    record = {
        **existing_record,
        "status": "PENDING",
    }
    db.upsert_record(record=record)

    task_id = generate_task_id(user_id=current_user.id)

    task: AsyncResult = api_processing.apply_async(
        kwargs={
            "task": {
                "audio_record": record,
                "checklist_id": checklist_id,
                "general": general,
                "folder_name": folder_name,
            },
        },
        link=upsert_data.s(
            task={
                "task_id": task_id,
                "owner_id": str(current_user.id),
                "record_id": record_id,
                "checklist_id": checklist_id,
                "storage_id": record["storage_id"],
                "is_success": True,
            }
        ).set(queue="data"),
        link_error=upsert_data.s(
            task={
                "task_id": task_id,
                "owner_id": str(current_user.id),
                "record_id": record_id,
                "checklist_id": checklist_id,
                "storage_id": record["storage_id"],
                "is_success": False,
            }
        ).set(queue="data"),
        queue="api",
        task_id=task_id,
    )

    response_data = {
        "id": task.id,
        "status": "PENDING",
    }

    return JSONResponse(status_code=200, content=response_data)


@audio_router.get("/audios/pending")
async def get_pending_audios(current_user: User = Depends(get_current_user)):
    data = db.get_pending_audios(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)


def get_pbx_call_history(db_session, current_user, start_stamp_from, end_stamp_to):
    pbx_credentials = get_pbx_credentials(db_session, current_user, raise_exc=False)

    if not pbx_credentials:
        logging.warning(f"No pbx credentials are found for {current_user.username=}")
        return []

    existing_record_titles: list[str] = get_all_record_titles(
        db_session, current_user.id
    )

    logging.info("Preparing and sending request ...")
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/mongo_history/search.json"

    with httpx.Client() as client:
        filter_data = {
            "start_stamp_from": start_stamp_from,
            "end_stamp_to": end_stamp_to,
        }

        response = client.post(
            url,
            headers={
                "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=filter_data,
            timeout=60,
        )
        logging.info(f"Response arrived: {response.status_code=}")

        json_response = response.json()

        if int(json_response["status"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=json_response["comment"],
            )

        logging.info(f"Total number of calls is {len(json_response['data'])}")
        filtered_calls = filter_calls(json_response["data"], existing_record_titles)
        logging.info(f"Filtering is done total number of calls={len(filtered_calls)}")

        return filtered_calls
