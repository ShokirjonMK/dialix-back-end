import logging  # noqa: F401
import typing as t  # noqa: F401

from fastapi import APIRouter

from backend.utils.bitrix import get_deals_by_phone
from backend.schemas import FinalCallStatusRequest, FinalCallStatusResponse
from backend.core.dependencies import BitrixCredentialsDependency


bitrix_router = APIRouter(tags=["Bitrix Integration"])


@bitrix_router.post("/final-call-status", response_model=FinalCallStatusResponse)
async def final_call_status(
    data: FinalCallStatusRequest, bitrix_credentials: BitrixCredentialsDependency
):
    name, deals = await get_deals_by_phone(
        bitrix_credentials.webhook_url, data.client_phone_number
    )

    return FinalCallStatusResponse(client_name=name, deals=deals)
