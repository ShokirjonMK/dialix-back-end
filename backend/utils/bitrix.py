import httpx
import logging
import typing as t
from datetime import datetime

DEAL_LIST_URL: str = "{}/crm.deal.list"
CONTACT_LIST_URL: str = "{}/crm.contact.list"

BITRIX_DEAL_CREATED_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"


async def get_deals_by_phone(webhook_url: str, phone_number: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        contact_info = await get_contact_info_by_phone(
            webhook_url, client, phone_number
        )

        if not contact_info:
            logging.info(f"No contact found for phone number: {phone_number}")
            return None, []

        contact_id = contact_info["ID"]
        contact_name = contact_info["NAME"]

        logging.info(
            f"Retrieved contact: {contact_name} ({contact_id}) for {phone_number=}"
        )

        deals = await get_deals_by_contact_id(webhook_url, client, contact_id)

        if not deals:
            logging.info(f"No deals found for contact ID: {contact_id}")
            return contact_name, []

        result: list[dict] = []

        for deal in deals:
            logging.info(f"{deal=}")
            deal_stage: str = deal.get("STAGE_ID", "Unknown")

            logging.info(
                f"Deal ID: {deal['ID']}, Title: {deal['TITLE']}, "
                f"Status: {deal_stage}, Created: {deal['DATE_CREATE']}, "
                f"Closed: {deal.get('CLOSEDATE', 'N/A')}"
            )

            date_created = deal["DATE_CREATE"]
            date_closed = deal.get("CLOSEDATE")

            result.append(
                {
                    "deal_id": deal["ID"],
                    "title": deal["TITLE"],
                    "status": deal_stage.lower(),
                    "date_created": datetime.strptime(
                        date_created, BITRIX_DEAL_CREATED_TIME_FORMAT
                    ),
                    "date_closed": datetime.strptime(
                        date_closed, BITRIX_DEAL_CREATED_TIME_FORMAT
                    )
                    if date_closed
                    else None,
                }
            )

        result.sort(key=lambda deal: deal.get("date_created"))

        return contact_name, result


async def get_deals_by_contact_id(
    webhook_url: str, client: httpx.AsyncClient, contact_id: str
) -> list[dict]:
    response = await client.get(
        DEAL_LIST_URL.format(webhook_url),
        params={
            "filter[CONTACT_ID]": contact_id,
            "select[0]": "ID",
            "select[1]": "TITLE",
            "select[2]": "STAGE_ID",
            "select[3]": "DATE_CREATE",
            "select[4]": "CLOSEDATE",
        },
    )
    response.raise_for_status()
    return response.json().get("result", [])


async def get_contact_info_by_phone(
    webhook_url: str, client: httpx.AsyncClient, phone_number: str
) -> t.Optional[dict]:
    response = await client.get(
        CONTACT_LIST_URL.format(webhook_url),
        params={
            "filter[PHONE]": phone_number,
            "select[0]": "ID",
            "select[1]": "NAME",
        },
    )
    response.raise_for_status()
    contacts = response.json().get("result", [])
    if not contacts:
        return None
    return contacts[0]
