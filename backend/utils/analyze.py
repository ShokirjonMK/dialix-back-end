import os
import uuid
import shutil
import logging
import typing as t  # noqa: F401

from decouple import config

from fastapi.responses import JSONResponse
from fastapi import UploadFile, Request, HTTPException, status as http_status

from celery.result import AsyncResult

from backend import db
from backend.schemas import User
from backend.core import settings
from workers.data import upsert_data
from utils.storage import upload_file
from utils.data_manipulation import (
    find_operator_code,
    find_call_type,
    get_phone_number_from_filename,
)
from workers.api import api_processing
from utils.audio import get_audio_duration
from backend.utils.pbx import load_call_from_pbx
from backend.utils.validators import validate_filename
from backend.services.checklist import get_single_checklist
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency


def generate_task_id(user_id) -> str:
    return f"{user_id}/{uuid.uuid4()}"


def get_object_storage_id(extension):
    return f"{uuid.uuid4()}.{extension}"


def analyze_data_handler(
    db_session: DatabaseSessionDependency,
    processed_data: t.Tuple[
        t.List[UploadFile], t.List[bool], t.List[t.Union[str, None]], t.List[dict]
    ],
    current_user: User,
    _operator_code: t.Optional[str] = None,
    _call_type: t.Optional[str] = None,
    _destination_number: t.Optional[str] = None,
):
    responses = []

    files, general, checklist_id, processed_files = processed_data

    logging.info(
        f"Received request: {files=} {general=} {checklist_id=} {processed_files=}"
    )

    for single_checklist_id in checklist_id:
        if single_checklist_id in ["", None, "null"]:
            continue

        if not get_single_checklist(
            db_session=db_session,
            owner_id=current_user.id,
            checklist_id=single_checklist_id,
        ):
            err_message = f"Checklist with {single_checklist_id=} is not found!"
            logging.warning(err_message)

            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail={"success": False, "detail": err_message},
            )

    for file, general, single_checklist_id, processed_file in zip(
        files, general, checklist_id, processed_files
    ):
        record_id = str(uuid.uuid4())
        owner_id = str(current_user.id)
        status = (
            "UPLOADED"
            if general is False and single_checklist_id is None
            else "PENDING"
        )
        storage_id = processed_file["file_path"].split("/")[-1]
        file_path = processed_file["file_path"]
        duration = processed_file["duration"]
        bucket = config("STORAGE_BUCKET_NAME", default="dialixai-production")

        folder_name = current_user.company_name.lower().replace(" ", "_")

        upload_file(bucket, f"{folder_name}/{storage_id}", file_path)
        logging.info(
            f"folder_name: {folder_name} storage_id: {storage_id}, bucket: {bucket}"
        )
        task_id = generate_task_id(user_id=current_user.id)

        is_filename_in_pbx_format: bool = validate_filename(file.filename)

        if is_filename_in_pbx_format:
            operator_code = find_operator_code(file.filename)
            call_type = find_call_type(file.filename)
            client_phone_number = get_phone_number_from_filename(file.filename)
        else:
            operator_code = None or _operator_code
            call_type = None or _call_type
            client_phone_number = None or _destination_number

        logging.info(
            f"Metadata: {is_filename_in_pbx_format=} {_operator_code=} {_call_type=} {_destination_number=}"
            f" => {operator_code=} {call_type=} {client_phone_number}"
        )
        operator_name: t.Optional[str] = None

        if is_filename_in_pbx_format:
            operator = (
                db.get_operator_name_by_code(owner_id=owner_id, code=operator_code)
                or {}
            )
            operator_name = operator.get("name", None)

        record = {
            "id": record_id,
            "owner_id": owner_id,
            "title": file.filename,
            "operator_code": operator_code,
            "operator_name": operator_name,
            "call_type": call_type,
            "status": status,
            "duration": duration * 1000,
            "storage_id": storage_id,
            "client_phone_number": client_phone_number,
        }

        audio_record = db.upsert_record(record=record)

        logging.warning(
            f"Audio record: {audio_record} with id: {record_id} and owner_id: {current_user.id}"
        )

        # audio_local_path = f"uploads/transcode_{storage_id}.mp3"
        # waveform_local_path = f"uploads/transcode_waveform_{storage_id}.dat"
        # generate_waveform(audio_local_path, waveform_local_path)

        if general is False and single_checklist_id is None:
            responses.append(
                {
                    "id": task_id,
                    "record_id": record_id,
                    "record_title": file.filename,
                    "status": status,
                    "duration": duration * 1000,
                    "storage_id": storage_id,
                }
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            continue

        task: AsyncResult = api_processing.apply_async(
            kwargs={
                "task": {
                    "audio_record": audio_record,
                    "checklist_id": single_checklist_id,
                    "general": general,
                    "folder_name": folder_name,
                    "client_phone_number": client_phone_number,
                },
            },
            link=upsert_data.s(
                task={
                    "task_id": task_id,
                    "owner_id": owner_id,
                    "record_id": audio_record["id"],
                    "checklist_id": single_checklist_id,
                    "storage_id": audio_record["storage_id"],
                    "is_success": True,
                }
            ).set(queue="data"),
            link_error=upsert_data.s(
                task={
                    "task_id": task_id,
                    "owner_id": owner_id,
                    "record_id": audio_record["id"],
                    "checklist_id": single_checklist_id,
                    "storage_id": audio_record["storage_id"],
                    "is_success": False,
                }
            ).set(queue="data"),
            queue="api",
            task_id=task_id,
        )

        responses.append(
            {
                "id": task.id,
                "record_id": record_id,
                "checklist_id": single_checklist_id,
                "record_title": file.filename,
                "status": status,
                "duration": duration * 1000,
                "storage_id": storage_id,
            }
        )

    return JSONResponse(status_code=http_status.HTTP_200_OK, content=responses)


def estimate_costs_from_pbx(
    request: Request,
    db_session: DatabaseSessionDependency,
    call_id: uuid.UUID,
    domain: str,
    key_id: str,
    key: str,
    general: bool,
    checklist_id: t.Optional[uuid.UUID] = None,
) -> dict[str, str]:
    pbx_url = settings.PBX_API_URL.format(domain=domain) + "/mongo_history/search.json"

    logging.info(f"{pbx_url=}")
    _files, _general, _checklist = load_call_from_pbx(
        call_id, pbx_url, key_id, key, general, checklist_id
    )

    logging.info(
        f"Routing {_files=} {_general=} {_checklist=} to estimate_costs_generic"
    )

    return estimate_costs_generic(
        request, db_session, _files, _general, _checklist, from_pbx=True
    )


async def estimate_costs_from_upload(
    request: Request, db_session: DatabaseSessionDependency
) -> dict[str, str]:
    form_data = await request.form()

    files = form_data.getlist("files")
    general = [gen == "true" for gen in form_data.getlist("general")]
    checklist_ids = [
        checklist if checklist not in ("null", "", None) else None
        for checklist in form_data.getlist("checklist_id")
    ]

    logging.info(
        f"Form data => {form_data.getlist('general')=} {form_data.getlist('checklist_id')=}"
    )

    return estimate_costs_generic(request, db_session, files, general, checklist_ids)


def estimate_costs_generic(
    request: Request,
    db_session: DatabaseSessionDependency,
    files: list[UploadFile],
    general: list[str],
    checklist_id: list[str],
    from_pbx: t.Optional[bool] = False,
) -> dict[str, str]:
    current_user = get_current_user(request, db_session)
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum") or 0

    processed_files = []

    total_price = 0
    total_mohirai_price = 0
    total_general_price = 0
    total_checklist_price = 0

    if len(files) != len(general) or len(files) != len(checklist_id):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mismatched lengths of arrays.",
        )

    cost_report = {}

    for file, gen, checklist in zip(files, general, checklist_id):
        file_path: str = None

        if not from_pbx:
            storage_id = get_object_storage_id(file.filename.split(".")[-1])
            file_path = os.path.join("uploads", storage_id)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as buffer:
                logging.info(f"SHUTIL: {file} => {file_path}")
                shutil.copyfileobj(file.file, buffer)

        else:
            file_path = f"./audios/{file.filename}"

        duration = get_audio_duration(file_path)

        if duration is None:
            if os.path.exists(file_path):
                os.remove(file_path)
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid audio file"},
            )

        duration *= 1_000

        processed_files.append({"file_path": file_path, "duration": duration})

        mohirai_price = (
            duration * settings.MOHIRAI_PRICE_PER_MS
            if gen is True or checklist is not None
            else 0
        )
        general_price = (
            duration * settings.GENERAL_PROMPT_PRICE_PER_MS if gen is True else 0
        )
        checklist_price = (
            duration * settings.CHECKLIST_PROMPT_PRICE_PER_MS
            if checklist is not None
            else 0
        )

        total_for_this_audio = mohirai_price + general_price + checklist_price
        total_mohirai_price += mohirai_price
        total_general_price += general_price
        total_checklist_price += checklist_price
        total_price += total_for_this_audio

        cost_report[file.filename] = {
            "duration": duration,
            "mohirai_price": mohirai_price,
            "general_price": general_price,
            "checklist_price": checklist_price,
            "total_for_this_audio": total_for_this_audio,
        }

    for file in processed_files:
        if os.path.exists(file["file_path"]):
            os.remove(file["file_path"])

    response_content = {
        "total_price": total_price,
        "current_balance": balance,
        "is_enough": balance >= total_price,
        "total_mohirai_price": total_mohirai_price,
        "total_general_price": total_general_price,
        "total_checklist_price": total_checklist_price,
        "detailed": cost_report,
    }

    if response_content["is_enough"]:
        response_content["balance_after"] = float(balance) - total_price

    return response_content
