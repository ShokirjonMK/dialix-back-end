import typing as t
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import update, select
from sqlalchemy.dialects.postgresql import insert

from backend.database.models import PbxCredentials, BitrixCredentials, AmoCRMCredentials


def get_pbx_credential(db_session: Session, owner_id: UUID) -> PbxCredentials:
    return db_session.scalar(
        select(PbxCredentials).where(PbxCredentials.owner_id == owner_id)
    )


def get_bitrix_credential(db_session: Session, owner_id: UUID) -> BitrixCredentials:
    return db_session.scalar(
        select(BitrixCredentials).where(BitrixCredentials.owner_id == owner_id)
    )


def update_pbx_credentials(
    db_session: Session,
    owner_id: UUID,
    new_key: str,
    new_key_id: str,
) -> None:
    db_session.execute(
        update(PbxCredentials)
        .where(PbxCredentials.owner_id == owner_id)
        .values(key=new_key, key_id=new_key_id)
    )
    db_session.commit()


def insert_or_update_pbx_credential(
    db_session: Session,
    owner_id: UUID,
    domain: str,
    api_key: str,
    key: t.Optional[str] = None,
    key_id: t.Optional[str] = None,
) -> None:
    query = (
        insert(PbxCredentials)
        .values(
            owner_id=owner_id, domain=domain, key=key, key_id=key_id, api_key=api_key
        )
        .on_conflict_do_update(
            index_elements=["owner_id"],
            set_={
                key: val
                for key, val in (
                    ("key", key),
                    ("key_id", key_id),
                    ("domain", domain),
                    ("api_key", api_key),
                )
                if val is not None
            },
        )
    )
    db_session.execute(query)
    db_session.commit()


def insert_or_update_bitrix_credential(
    db_session: Session,
    owner_id: UUID,
    webhook_url: str,
) -> None:
    query = (
        insert(BitrixCredentials)
        .values(owner_id=owner_id, webhook_url=webhook_url)
        .on_conflict_do_update(
            index_elements=["owner_id"],
            set_={"webhook_url": webhook_url},
        )
    )

    db_session.execute(query)
    db_session.commit()


def insert_or_update_amocrm_credential(
    db_session: Session,
    owner_id: UUID,
    base_url: str,
    access_token: str,
    refresh_token: t.Optional[str] = None,
    client_id: t.Optional[str] = None,
    client_secret: t.Optional[str] = None,
    redirect_uri: t.Optional[str] = None,
) -> None:
    query = (
        insert(AmoCRMCredentials)
        .values(
            owner_id=owner_id,
            base_url=base_url,
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        .on_conflict_do_update(
            index_elements=["owner_id"],
            set_={
                key: val
                for key, val in (
                    ("base_url", base_url),
                    ("access_token", access_token),
                    ("refresh_token", refresh_token),
                    ("client_id", client_id),
                    ("client_secret", client_secret),
                    ("redirect_uri", redirect_uri),
                )
                if val is not None
            },
        )
    )

    db_session.execute(query)
    db_session.commit()
