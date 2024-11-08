from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import Checklist


def get_checklist_by(db_session: Session, owner_id: UUID):
    return db_session.scalar(select(Checklist).where(Checklist.owner_id == owner_id))


def get_single_checklist_by(
    db_session: Session,
    owner_id: UUID,
    checklist_id: UUID,
) -> list[Checklist]:
    return db_session.scalars(
        select(Checklist).where(
            Checklist.id == checklist_id, Checklist.owner_id == owner_id
        )
    ).all()


async def create_checklist(): ...
