import logging
import typing as t  # noqa: F401

from fastapi import UploadFile

from backend.core import settings
from workers.common import celery as celery_app
from backend.api import analyze_data
from backend.utils.pbx import (
    sync_download_from,
    sync_get_call_info_by,
    sync_get_call_download_url,
)
from backend.core.dependencies import get_db_session
from backend.services.user import get_user_by_id


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

    current_user = get_user_by_id(next(get_db_session()), user_id)
    response = analyze_data(
        processed_data=processed_data,
        current_user=current_user,
        _operator_code=call_info["caller_id_number"],
        _call_type=call_info["accountcode"],
        _destination_number=call_info["destination_number"],
    )

    logging.info(f"Analysis endpoint's response: {response}")

    return {"success": True, "response": response.status_code}
