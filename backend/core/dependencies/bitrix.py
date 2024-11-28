import logging
import typing as t
from uuid import UUID

from sqlalchemy import select

from fastapi import Depends

from backend.utils.shortcuts import raise_401
from backend.schemas import BitrixCredentials, User
from backend.database.models import BitrixCredentials as BitrixCredentialsDb
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency


def get_bitrix_credentials(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> BitrixCredentials:
    statement = select(BitrixCredentialsDb).where(
        BitrixCredentialsDb.owner_id == current_user.id
    )

    bitrix_credentials = db_session.scalar(statement)

    if not bitrix_credentials:
        raise_401("No bitrix credentials found")

    return BitrixCredentials(webhook_url=bitrix_credentials.webhook_url)


# celery implementation,
# which returns None instead of raising exception
def get_bitrix_credentials_celery(
    db_session: DatabaseSessionDependency, owner_id: UUID
) -> BitrixCredentials | None:
    statement = select(BitrixCredentialsDb).where(
        BitrixCredentialsDb.owner_id == owner_id
    )

    bitrix_credentials = db_session.scalar(statement)

    if not bitrix_credentials:
        logging.warning(f"No bitrix credentials found for {owner_id=}")
        return

    return BitrixCredentials(webhook_url=bitrix_credentials.webhook_url)


BitrixCredentialsDependency = t.Annotated[
    BitrixCredentials, Depends(get_bitrix_credentials)
]
