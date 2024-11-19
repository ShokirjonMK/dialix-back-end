from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.database.models import PbxCredentials


def update_pbx_credentials(
    db_session: Session,
    owner_id: UUID,
    pbx_credential_id: UUID,
    new_key: str,
    new_key_id: str,
) -> None:
    db_session.execute(
        update(PbxCredentials)
        .where(
            (PbxCredentials.owner_id == owner_id)
            & (PbxCredentials.id == pbx_credential_id)
        )
        .values(key=new_key, key_id=new_key_id)
    )
    db_session.commit()
