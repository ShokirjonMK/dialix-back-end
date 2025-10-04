import uuid
import logging
import typing as t  # noqa: F401
from typing import List, Tuple, Union

import httpx

from redis import Redis
from decouple import config

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
    RecordOrderQueries,
    ResultOrderQueries,
    PbxCallSchema,
)
from backend.core import settings
from workers.data import upsert_data
from utils.encoder import adapt_json
from workers.api import api_processing
from utils.storage import get_stream_url
from backend.utils.pbx import filter_calls
from backend.tasks.pbx import update_bitrix_results
from backend.services.record import (
    get_all_record_titles,
    get_filterable_values_for_record,
)
from backend.services.pbx import (
    sync_pbx_calls,
    get_calls_between_interval,
    get_total_interval,
)
from backend.services.result import get_filterable_values_for_result
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.bitrix import BitrixCredentialsDependency
from backend.core.dependencies.pbx import get_pbx_credentials, PbxCredentialsDependency
from backend.utils.analyze import (
    analyze_data_handler,
    estimate_costs_from_pbx,
    estimate_costs_from_upload,
)
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.core.dependencies.audio_processing import process_form_data
from backend.utils.shortcuts import models_to_dict

audio_router = APIRouter(tags=["Audios"])
ONE_WEEK_SECONDS: int = 7 * 24 * 60 * 60
redis_conn = Redis().from_url(config("REDIS_URL"), decode_responses=True)


def generate_task_id(user_id: uuid.UUID) -> str:
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
async def get_audio_results(
    db_session: DatabaseSessionDependency,
    bitrix_credentials: BitrixCredentialsDependency,
    current_user: User = Depends(get_current_user),
    record_query_params: RecordQueryParams = Depends(),
    result_query_params: ResultQueryParams = Depends(),
    record_order_query_params: RecordOrderQueries = Depends(),
    result_order_query_params: ResultOrderQueries = Depends(),
    start_stamp_from: t.Optional[int] = None,
    end_stamp_to: t.Optional[int] = None,
    bitrix_result_should_exist: t.Optional[bool] = False,
) -> JSONResponse:
    if start_stamp_from > end_stamp_to or start_stamp_from == end_stamp_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Wrong interval, start should be less than end, interval length "
                "should be less than or equal 1 WEEK, refer to PBX docs"
            ),
        )

    record_filter_params = record_query_params.model_dump(
        mode="python", exclude_none=True
    )
    result_filter_params = result_query_params.model_dump(
        mode="python", exclude_none=True
    )

    logging.info(f"{record_filter_params=} {result_filter_params=}")

    full_audios = []
    just_audios = []
    general_audios = []
    audios_with_checklist = []

    folder_name = current_user.company_name.lower().replace(" ", "_")

    recordings = db.get_records_v3(
        owner_id=str(current_user.id),
        record_filter_params=record_filter_params,
        result_filter_params=result_filter_params,
        order_kwargs_record=record_order_query_params.model_dump(exclude_none=True),
        order_kwargs_result=result_order_query_params.model_dump(exclude_none=True),
    )

    for record in recordings:
        audio_url = get_stream_url(f"{folder_name}/{record['storage_id']}")
        record["audio_url"] = audio_url

        if result := record["result"]:
            result: dict

            summary, checklist_result = (
                result.get("summary"),
                result.get("checklist_result"),
            )

            if summary and checklist_result:
                full_audios.append(record)
            elif checklist_result:
                audios_with_checklist.append(record)
            else:
                general_audios.append(record)
        else:
            just_audios.append(record)

    response = {
        "just_audios": just_audios,
        "audios_with_checklist": audios_with_checklist,
        "general_audios": general_audios,
        "full_audios": full_audios,
        "recordings": recordings,
    }

    if start_stamp_from and end_stamp_to:
        existing_record_titles: list[str] = get_all_record_titles(
            db_session, current_user.id
        )
        response["pbx_calls"] = filter_calls(
            get_pbx_call_history(
                db_session, current_user, start_stamp_from, end_stamp_to
            ),
            existing_record_titles,
            bitrix_result_should_exist,
        )

        update_bitrix_results.delay(
            owner_id=current_user.id, webhook_url=bitrix_credentials.webhook_url
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=adapt_json(response))


@audio_router.get("/audio/file/{storage_id}")
async def get_audio_file(request: Request, storage_id: str):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"url": f"{request.base_url}uploads/{storage_id}"},
    )


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
    record: ReprocessRecord, current_user: User = Depends(get_current_user)
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

    response_data = {"id": task.id, "status": "PENDING"}

    return JSONResponse(status_code=200, content=response_data)


@audio_router.get("/audios/pending")
async def get_pending_audios(current_user: User = Depends(get_current_user)):
    data = db.get_pending_audios(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)


def get_pbx_call_history(
    db_session: DatabaseSessionDependency,
    current_user,
    start_stamp_from: int,
    end_stamp_to: int,
):
    pbx_credentials = get_pbx_credentials(db_session, current_user, raise_exc=False)

    if not pbx_credentials:
        logging.warning(f"No pbx credentials are found for {current_user.username=}")
        return []

    logging.info(f"Got pbx credentials: {pbx_credentials}")

    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/mongo_history/search.json"

    calls = load_pbx_calls(
        current_user.id,
        url,
        db_session,
        pbx_credentials,
        start_stamp_from,
        end_stamp_to,
    )
    logging.info(f"Number of calls loaded {len(calls)}")

    redis_conn.set(
        f"last_loaded_interval:{current_user.id}",
        f"{start_stamp_from}:{end_stamp_to}",
        ex=2 * 60,  # 2 minute
    )
    return models_to_dict(PbxCallSchema, calls)


def load_pbx_calls(
    owner_id: uuid.UUID,
    url: str,
    db_session: DatabaseSessionDependency,
    pbx_credentials: PbxCredentialsDependency,
    S: int,
    E: int,
):
    """
    I know, it is mess. But "CTO"(quote unquote),
    ignored my opinion. Proposed this (cutting uneccessary intervals).
    Forgive me if you are debugging this code, I have not have any choice.
    """
    global redis_conn

    def api(s: int, e: int):
        if (e - s) > ONE_WEEK_SECONDS:
            logging.warning(f"Difference of {s=} and {e=} is greater than one week.")
        calls = pbx_fetch(url, pbx_credentials, s, e)
        logging.info(f"Number of calls loaded from API {len(calls)} for {s=} {e=}")
        return calls

    def db(s: int, e: int):
        return get_calls_between_interval(db_session, owner_id, s, e)

    def sync(api_data):
        return sync_pbx_calls(db_session, owner_id, api_data)

    intervals_from_redis = redis_conn.get(f"last_loaded_interval:{owner_id}")
    logging.info(f"{type(intervals_from_redis)=}")

    if intervals_from_redis is not None:
        _S, _E = map(int, intervals_from_redis.split(":"))
        logging.info(f"Last loaded value is loaded from redis {_S=} {_E=}")

        if S == _S and E == _E:
            logging.info(f"Request was served just before, loading from db {S=} {E=}")
            return db(S, E)

    db_intervals = get_total_interval(db_session, owner_id)
    logging.info(f"Loaded {db_intervals=}")

    if db_intervals == (None, None):
        logging.info("[0] No interval found in db, cold start")
        api_data = api(S, E)
        sync(api_data)
        return db(S, E)

    MS, ME = db_intervals

    if MS <= S < E <= ME:
        logging.info(
            f"[1] {MS=} {ME=} {S=} {E=} Ideal interval overlap, loading all from db"
        )
        return db(S, E)

    if S < MS < E:
        logging.info(f"[2] {MS=} {ME=} {S=} {E=} Partial overlap, api+db loading")
        api_data = api(S, MS)
        sync(api_data)
        return db(S, E)

    if S < ME < E:
        logging.info(f"[3] {MS=} {ME=} {S=} {E=} Partial overlap, api+db loading")
        api_data = api(S, ME)
        sync(api_data)
        return db(S, ME)

    if ME < S:
        logging.info(
            f"[4] {MS=} {ME=} {S=} {E=} Did not match, extending contigious area"
        )
        args = (ME, E)
        if E - ME > ONE_WEEK_SECONDS:
            logging.info(
                f"Length of interval {E=} and {ME=} is greater than 1 WEEK, settings args {S=} {E=}"
            )
            args = (S, E)

        api_data = api(*args)
        sync(api_data)
        return db(S, E)

    if E < MS:
        logging.info(
            f"[5] {MS=} {ME=} {S=} {E=} Did not match, extending contigious area"
        )
        args = (S, MS)
        if MS - S > ONE_WEEK_SECONDS:
            logging.info(
                f"Length of interval {E=} and {ME=} is greater than 1 WEEK, settings args {S=} {E=}"
            )
            args = (S, E)
        api_data = api(*args)
        sync(api_data)
        return db(S, E)


def pbx_fetch(url: str, pbx_credentials: PbxCredentialsDependency, S: int, E: int):
    with httpx.Client() as client:
        filter_data = {"start_stamp_from": S, "end_stamp_to": E}

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

        return json_response["data"]
