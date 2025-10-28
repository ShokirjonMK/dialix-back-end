import typing as t
from uuid import UUID

from sqlalchemy import select
from fastapi import Depends

from backend.database.models import AmoCRMCredentials as AmoCRMCredentialsDb
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.utils.shortcuts import raise_401
from backend.schemas import User


class AmoCredentials(t.TypedDict):
    base_url: str
    access_token: str


def get_amocrm_credentials(
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> AmoCredentials:
    stmt = select(AmoCRMCredentialsDb).where(
        AmoCRMCredentialsDb.owner_id == current_user.id
    )
    cred = db_session.scalar(stmt)
    if not cred:
        raise_401("No amocrm credentials found")
    return AmoCredentials(base_url=cred.base_url, access_token=cred.access_token)


def get_amocrm_credentials_celery(
    db_session: DatabaseSessionDependency, owner_id: UUID
) -> t.Optional[AmoCredentials]:
    stmt = select(AmoCRMCredentialsDb).where(AmoCRMCredentialsDb.owner_id == owner_id)
    cred = db_session.scalar(stmt)
    if not cred:
        return None
    return AmoCredentials(base_url=cred.base_url, access_token=cred.access_token)
