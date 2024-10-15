import logging

from backend.database.models import BlackListToken


async def add_to_blacklist(access_token: str) -> None:
    blacklisted_token = await BlackListToken.create(value=access_token)
    logging.info(f"Added new token to blacklist: {blacklisted_token.value[:15]}...")
