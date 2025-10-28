import httpx
import typing as t


class AmoAuth(httpx.Auth):
    def __init__(self, access_token: str):
        self.access_token = access_token

    def auth_flow(
        self, request: httpx.Request
    ) -> t.Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        yield request


def normalize_phone(phone: str) -> str:
    return phone.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")


def get_leads_by_phone(
    base_url: str,
    access_token: str,
    phone_number: str,
) -> tuple[t.Optional[str], list[dict]]:
    phone = normalize_phone(phone_number)

    with httpx.Client(
        base_url=base_url, auth=AmoAuth(access_token), timeout=30
    ) as client:
        contacts_resp = client.get(
            "/api/v4/contacts",
            params={"query": phone, "with": "leads"},
        )
        contacts_resp.raise_for_status()
        embedded = contacts_resp.json().get("_embedded", {})
        contacts = embedded.get("contacts", [])

        if not contacts:
            return None, []

        contact = contacts[0]
        contact_name = contact.get("name")

        leads_links = contact.get("_links", {}).get("leads", {})
        leads_href = leads_links.get("href")

        leads: list[dict] = []
        if leads_href:
            leads_resp = client.get(leads_href)
            leads_resp.raise_for_status()
            leads_embedded = leads_resp.json().get("_embedded", {})
            for lead in leads_embedded.get("leads", []):
                leads.append(
                    {
                        "deal_id": str(lead.get("id")),
                        "title": lead.get("name"),
                        "status": str(lead.get("status_id")),
                        "date_created": lead.get("created_at"),
                        "date_closed": lead.get("closed_at"),
                    }
                )

        return contact_name, leads
