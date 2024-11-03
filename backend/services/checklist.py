from uuid import UUID

from backend.database.models import Checklist


def get_checklist_by(owner_id: UUID):
    queryset = Checklist.filter(owner_id=owner_id)
    return queryset


def get_single_checklist_by(owner_id: UUID, checklist_id: UUID):
    queryset = Checklist.filter(id=checklist_id, owner_id=owner_id).first()
    return queryset


async def create_checklist(): ...
