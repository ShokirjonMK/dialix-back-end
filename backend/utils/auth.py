import logging
from passlib.context import CryptContext

from backend.database.models import BlackListToken

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def add_to_blacklist(username: str, access_token: str) -> None:
    blacklisted_token = await BlackListToken.create(value=access_token)
    logging.info(
        f"Added new token to blacklist: from {username},token={blacklisted_token.value[:20]}..."
    )


def hashify(password: str) -> str:
    return bcrypt_context.hash(password)
