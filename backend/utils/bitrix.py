import httpx
import logging
import typing as t
from datetime import datetime

STAGE_LIST_URL: str = "{}/crm.status.list"
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
    stage_mapping = await get_stage_mapping(webhook_url, client)

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
    deals = response.json().get("result", [])

    for deal in deals:
        deal["STAGE_ID"] = stage_mapping.get(deal["STAGE_ID"].upper(), "Unknown Stage")

    return deals


async def get_contact_info_by_phone(
    webhook_url: str, client: httpx.AsyncClient, phone_number: str
) -> t.Optional[dict]:
    async def make_contact_list_request(client_phone_number: str):
        response = await client.get(
            CONTACT_LIST_URL.format(webhook_url),
            params={
                "filter[PHONE]": client_phone_number,
                "select[0]": "ID",
                "select[1]": "NAME",
            },
        )

        contacts = response.json().get("result", [])

        if not contacts:
            return None

        return contacts[0]

    first_try = await make_contact_list_request(phone_number)

    if first_try:
        return first_try

    logging.warning(
        f"Looks like we got wrong phone number format here :{phone_number=}"
    )

    # second try, maybe operators made mistake with phone number format
    other_format_phone_number = None

    if (phone_number_digits := len(phone_number)) == 9:  # for cases like 944585845
        other_format_phone_number: str = f"+998{phone_number}"
    elif (phone_number_digits := len(phone_number)) == 12:
        other_format_phone_number: str = f"+{phone_number}"
    elif (
        phone_number_digits := len(phone_number)
    ) == 13:  # for cases like +998901133104
        other_format_phone_number: str = phone_number[4:]

    else:
        logging.info("Number of digits neither 9,12 or 13 ... returning NONE")
        return None

    logging.warning(
        f"Made request with {phone_number=}, it contains {phone_number_digits} digits. "
        f"Making SECOND request with {other_format_phone_number}"
    )
    second_try = await make_contact_list_request(other_format_phone_number)
    return second_try


async def get_stage_mapping(webhook_url: str, client: httpx.AsyncClient) -> dict:
    response = await client.get(STAGE_LIST_URL.format(webhook_url))
    statuses = response.json().get("result", [])
    return {status["STATUS_ID"]: status["NAME"] for status in statuses}
