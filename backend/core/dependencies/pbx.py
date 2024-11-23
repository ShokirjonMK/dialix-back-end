import logging
import requests
import typing as t


from fastapi import Depends, status
from sqlalchemy import select

from backend.core import settings
from backend.utils.shortcuts import raise_401
from backend.utils.pbx import test_pbx_credentials
from backend.schemas import PbxCredentialsFull, User
from backend.database.models import PbxCredentials as PbxCredentialsDb
from backend.core.dependencies.user import get_current_user
from backend.services.credentials import update_pbx_credentials
from backend.core.dependencies.database import DatabaseSessionDependency


def get_pbx_keys(
    domain: str, api_key: str
) -> tuple[t.Union[str, None], t.Union[str, None]]:
    url = f"{settings.PBX_API_URL.format(domain=domain)}/auth.json"

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"auth_key": api_key},
            timeout=60,
        )

        response_content = response.json()
        if (
            response.status_code == status.HTTP_200_OK
            and response_content["status"] == "1"
        ):
            return response_content["data"]["key_id"], response_content["data"]["key"]

        return None, None

    except Exception as exc:
        logging.info(f"Could not get pbx keys: {exc=}")
        return None, None


def get_pbx_credentials(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> PbxCredentialsFull:
    logging.info("PBX cred works!")
    pbx_credentials = db_session.scalar(
        select(PbxCredentialsDb).where(PbxCredentialsDb.owner_id == current_user.id)
    )

    if not pbx_credentials:
        raise_401("No pbx credentials found")

    if pbx_credentials.key is None or pbx_credentials.key_id is None:
        logging.info("Pbx key and key_id is NULL, getting new keys")

        key_id, key = get_pbx_keys(pbx_credentials.domain, pbx_credentials.api_key)

        logging.info(f"New {key=} and {key_id=}, updating pbx credentials on db")

        update_pbx_credentials(db_session, current_user.id, key, key_id)

        db_session.commit()
        logging.info(f"Refreshing {pbx_credentials=}")
        db_session.refresh(pbx_credentials)

    if not (
        test_pbx_credentials(
            pbx_credentials.domain, pbx_credentials.key, pbx_credentials.key_id
        )
    ):
        logging.info("Updating pbx keys, they are not valid")
        update_pbx_credentials(db_session, current_user.id, None, None)
        raise_401("Pbx keys are not valid!")

    pbx_credentials_full = PbxCredentialsFull(
        domain=pbx_credentials.domain,
        key=pbx_credentials.key,
        key_id=pbx_credentials.key_id,
    )
    logging.info(f"{pbx_credentials_full=}")

    return pbx_credentials_full


PbxCredentialsDependency = t.Annotated[PbxCredentialsFull, Depends(get_pbx_credentials)]
