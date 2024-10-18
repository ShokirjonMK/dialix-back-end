from uuid import UUID

from backend.database.models import Checklist


async def get_checklist_by(owner_id: UUID):
    queryset = Checklist.filter(owner_id=owner_id)
    return await queryset


async def get_single_checklist_by(owner_id: UUID, checklist_id: UUID):
    queryset = Checklist.filter(id=checklist_id, owner_id=owner_id).first()
    return await queryset


async def create_checklist(): ...
