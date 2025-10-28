from fastapi import APIRouter

from backend.core.dependencies.amocrm import get_amocrm_credentials, AmoCredentials
from backend.utils.amocrm import get_leads_by_phone
from backend.schemas import FinalCallStatusRequest, FinalCallStatusResponse


amocrm_router = APIRouter(tags=["AmoCRM Integration"])


@amocrm_router.post("/amocrm/final-call-status", response_model=FinalCallStatusResponse)
async def final_call_status_amocrm(
    data: FinalCallStatusRequest, creds: AmoCredentials = get_amocrm_credentials
):
    name, leads = get_leads_by_phone(
        creds["base_url"], creds["access_token"], data.client_phone_number
    )
    return FinalCallStatusResponse(client_name=name, deals=leads)
