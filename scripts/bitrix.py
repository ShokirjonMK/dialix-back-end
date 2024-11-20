import json
import httpx
import random
import asyncio
import argparse
from decouple import config
from typing import Optional


BITRIX_WEBHOOK_URL: str = config("DEFAULT_BITRIX_WEBHOOK_URL")
CONTACT_LIST_URL = BITRIX_WEBHOOK_URL + "crm.contact.list"


async def get_random_contact(generate_random: Optional[bool] = False) -> None:
    params = {"select[0]": "ID", "select[1]": "PHONE", "limit": 100}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            CONTACT_LIST_URL,
            params=params,
        )
        response.raise_for_status()

        contacts = response.json().get("result", [])
        if not contacts:
            print("No contacts found in Bitrix24.")
            return None

        contacts_with_phones = [
            {
                "ID": contact["ID"],
                "PHONE": [phone["VALUE"] for phone in contact.get("PHONE", [])],
            }
            for contact in contacts
            if contact.get("PHONE")
        ]

        if not contacts_with_phones:
            print("No contacts with phone numbers found.")
            return None

        result = (
            random.choice(contacts_with_phones)
            if generate_random
            else contacts_with_phones
        )
        print(json.dumps(result))

        return


async def main() -> int:
    parser = argparse.ArgumentParser(
        prog="Bitrix  - contacts",
        description="Prints list of 50 contacts or gives random one",
    )
    parser.add_argument("-r", "--random", action="store_true")

    args = parser.parse_args()

    await get_random_contact(args.random)

    return 0


if __name__ == "__main__":
    asyncio.run(main())
