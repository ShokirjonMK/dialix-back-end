import os

import logging
import typing as t  # noqa: F401

from httpx import HTTPStatusError

from fastapi import UploadFile

from backend.core import settings
from workers.common import celery as celery_app
from backend.utils.pbx import (
    sync_download_from,
    sync_get_call_info_by,
    sync_get_call_download_url,
)
from backend.services.user import get_user_by_id
from backend.utils.analyze import analyze_data_handler
from backend.services.pbx import (
    get_no_bitrix_processed_calls,
    get_bitrix_result_by_call_id,
)
from backend.core.dependencies.database import get_db_session
from backend.utils.bitrix import update_bulk_deals_by_phones


@celery_app.task(autoretry_for=[HTTPStatusError], max_retries=10, retry_backoff=True)
def update_bitrix_results(*args, **kwargs):
    logging.info(f"{args=} {kwargs=}")

    owner_id = kwargs.get("owner_id")
    webhook_url = kwargs.get("webhook_url")
    logging.info(f"{webhook_url=}")
    db_session = next(get_db_session())

    phone_numbers = get_no_bitrix_processed_calls(db_session, owner_id)

    logging.info(
        f"Total number of loaded phone numbers for this task: {len(phone_numbers)}"
    )

    if phone_numbers is None or len(phone_numbers) == 0:
        return {"success": True}

    phone_numbers_formatted = [row[0] for row in phone_numbers]

    update_bulk_deals_by_phones(
        webhook_url, phone_numbers_formatted, db_session, owner_id
    )

    return {"success": True}


@celery_app.task
def process_pbx_call_task(*args, **kwargs):
    logging.info(f"{args=} {kwargs=}")

    user_id = kwargs.get("user_id")
    uuid = kwargs.get("uuid")
    key = kwargs.get("key")
    domain = kwargs.get("domain")
    key_id = kwargs.get("key_id")
    checklist_id = kwargs.get("checklist_id")

    url = f"{settings.PBX_API_URL.format(domain=domain)}/mongo_history/search.json"

    try:
        call_info_response = sync_get_call_info_by(uuid, url, key_id, key)

        if int(call_info_response["status"]) == 0:
            logging.error("Invalid credentials.")
            return {"error": call_info_response["comment"]}

        call_info = call_info_response["data"][0]

        if call_info["user_talk_time"] == 0:
            logging.error("Call has no user talk time.")
            return {"error": "User did not say any word, and we need to analyze that?"}

        download_url_response = sync_get_call_download_url(
            {"uuid": uuid, "download": "1"},
            url,
            key_id,
            key,
        )
        download_url = download_url_response.get("data")
        filename = f"call-{uuid}.mp3"
        download_file_path = f"./audios/{filename}"

        downloaded_file = sync_download_from(download_url, download_file_path)
        logging.info(f"Downloaded file path: {downloaded_file}")

        with open(downloaded_file, "rb") as audio_file:
            upload_file = UploadFile(audio_file, filename=filename)

            processed_data = (
                [upload_file],
                [True],
                [checklist_id],
                [{"file_path": download_file_path, "duration": call_info["duration"]}],
            )

            db_session = next(get_db_session())
            current_user = get_user_by_id(db_session, user_id)

            bitrix_result = get_bitrix_result_by_call_id(
                db_session, current_user.id, uuid
            )
            logging.info(f"Processing call from pbx({uuid=}): {bitrix_result=}")

            response = analyze_data_handler(
                db_session=db_session,
                processed_data=processed_data,
                current_user=current_user,
                _operator_code=call_info["caller_id_number"],
                _call_type=call_info["accountcode"],
                _destination_number=call_info["destination_number"],
                _bitrix_result=bitrix_result,
            )

            logging.info(f"Analysis endpoint's response: {response}")

        # cleanup
        if os.path.exists(download_file_path):
            try:
                os.remove(download_file_path)
                logging.info(f"Deleted file: {download_file_path}")
            except Exception as exc:
                logging.error(
                    f"Failed to delete file: {download_file_path}. Error: {exc}"
                )

        return {"success": True, "response": response.status_code}
    except Exception as exc:
        logging.error(f"Unexpected exception occurred: {exc=}")
