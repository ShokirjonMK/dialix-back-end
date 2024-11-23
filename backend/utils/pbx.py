import os
import httpx
import logging
import tarfile
import requests
import typing as t  # noqa: F401
from uuid import UUID

from fastapi import HTTPException, status

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
