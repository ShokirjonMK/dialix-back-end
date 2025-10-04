import httpx
import logging
import typing as t
from uuid import UUID

from sqlalchemy.orm import Session

from backend.services.pbx import update_bitrix_results_by_phone_number

DEAL_LIST_URL: str = "{}/crm.deal.list"
STAGE_LIST_URL: str = "{}/crm.status.list"
CONTACT_LIST_URL: str = "{}/crm.contact.list"


BITRIX_DEAL_CREATED_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"


def update_bulk_deals_by_phones(
    webhook_url: str, phone_numbers: list[str], db_session: Session, owner_id: UUID
) -> None:
    with httpx.Client(timeout=30) as client:
        for phone_number in phone_numbers:
            result = None

            contact_info = get_contact_info_by_phone(webhook_url, client, phone_number)

            if not contact_info:
                logging.info(f"No contact found for phone number: {phone_number}")
            else:
                contact_id = contact_info["ID"]
                contact_name = contact_info["NAME"]

                logging.info(
                    f"Retrieved contact: {contact_name=} ({contact_id=}) for {phone_number=}"
                )

                deals = get_deals_by_contact_id(webhook_url, client, contact_id)

                if not deals:
                    logging.warning(f"No deals found for contact ID: {contact_id}")
                else:
                    result = [
                        {
                            "contact_name": contact_name,
                            "deal_id": deal["ID"],
                            "title": deal["TITLE"],
                            "status": deal["STAGE_ID"].lower(),
                            "date_created": deal["DATE_CREATE"],
                            "date_closed": deal.get("CLOSEDATE"),
                        }
                        for deal in sorted(deals, key=lambda d: d["DATE_CREATE"])
                    ]
                    logging.info(f"Deal for {phone_number=} => {result}")

            update_bitrix_results_by_phone_number(
                db_session, owner_id, phone_number, result
            )


def get_deals_by_contact_id(
    webhook_url: str, client: httpx.Client, contact_id: str
) -> list[dict]:
    stage_mapping = get_stage_mapping(webhook_url, client)

    response = client.get(
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


def get_contact_info_by_phone(
    webhook_url: str, client: httpx.Client, phone_number: str
) -> t.Optional[dict]:
    response = client.get(
        CONTACT_LIST_URL.format(webhook_url),
        params={
            "filter[PHONE]": phone_number,
            "select[0]": "ID",
            "select[1]": "NAME",
        },
    )

    contacts = response.json().get("result", [])
    if not contacts:
        return None

    return contacts[0]


def get_stage_mapping(webhook_url: str, client: httpx.Client) -> dict:
    response = client.get(STAGE_LIST_URL.format(webhook_url))
    statuses = response.json().get("result", [])
    return {status["STATUS_ID"]: status["NAME"] for status in statuses}
