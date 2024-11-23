import os
import httpx
import logging
import tarfile
import requests
import typing as t  # noqa: F401
from uuid import UUID

from fastapi import HTTPException, status, UploadFile

from backend.core import settings


def filter_calls(
    calls: list[dict], existing_record_ids: t.Optional[list[UUID]] = []
) -> list[dict]:
    logging.info(f"Filtering recordings: {len(calls)=} and {len(existing_record_ids)=}")
    return list(
        filter(
            lambda entry: entry["user_talk_time"] >= 10
            and f"call-{entry['uuid']}.mp3" not in existing_record_ids,
            calls,
        )
    )


def test_pbx_credentials(domain: str, key: str, key_id: str) -> bool:
    url = f"{settings.PBX_API_URL.format(domain=domain)}/user/get.json"

    try:
        response = requests.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=60,
        )

        if response.json()["status"] != "1":
            logging.error(
                f"Testing pbx credentials {domain=} {key=} {key_id=} failed: {response.json()=}"
            )
            return False

        return True

    except Exception as exc:
        logging.info(
            f"Testing pbx credentials {domain=} {key=} {key_id=} failed: {exc=}"
        )
        return False


def sync_download_from(url: str, file_path: str) -> str:
    with httpx.Client() as client:
        with client.stream("GET", url, timeout=120) as response:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
            logging.info(f"File downloaded successfully: {file_path}")
    return file_path


def sync_get_call_info_by(uuid: UUID, url: str, key_id: str, key: str) -> dict:
    with httpx.Client() as client:
        response = client.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"uuid": str(uuid)},
            timeout=120,
        )
        logging.info(f"Get call INFO: {response.status_code=} {response.json()=}")
        response.raise_for_status()
        return response.json()


def sync_get_call_download_url(data: dict, url: str, key_id: str, key: str) -> dict:
    with httpx.Client() as client:
        response = client.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
            timeout=120,
        )
        logging.info(f"Get download URL: {response.status_code=} {response.json()=}")
        response.raise_for_status()
        return response.json()


def extract_tar_file(tar_path: str, where: str) -> None:
    try:
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(path=where)
    except (tarfile.TarError, IOError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Couldn't extract tarball: {exc}",
        )


def load_call_from_pbx(
    call_id: UUID,
    pbx_url: str,
    key_id: str,
    key: str,
    general: bool,
    checklist_id: t.Optional[UUID] = None,
):
    call_info_response = sync_get_call_info_by(call_id, pbx_url, key_id, key)

    if int(call_info_response["status"]) == 0:
        logging.error("Invalid credentials.")
        return {"error": call_info_response["comment"]}

    call_info = call_info_response["data"][0]

    if call_info["user_talk_time"] == 0:
        logging.error("Call has no user talk time.")
        return {"error": "User did not say any word, and we need to analyze that?"}

    download_url_response = sync_get_call_download_url(
        {"uuid": call_id, "download": "1"}, pbx_url, key_id, key
    )
    filename = f"call-{call_id}.mp3"
    download_file_path = f"./audios/{filename}"
    download_url = download_url_response.get("data")

    downloaded_file = sync_download_from(download_url, download_file_path)
    logging.info(f"Downloaded file path: {downloaded_file}")

    with open(downloaded_file, "rb") as audio_file:
        upload_file = UploadFile(audio_file, filename=filename)

    processed_data = ([upload_file], [general], [checklist_id])

    return processed_data
