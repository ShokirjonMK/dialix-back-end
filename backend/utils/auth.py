import logging
from passlib.context import CryptContext

from sqlalchemy import exists
from sqlalchemy.orm import Session

from backend.database.models import BlackListToken


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def add_to_blacklist(db_session: Session, username: str, access_token: str) -> None:
    blacklisted_token = BlackListToken(value=access_token)
    db_session.add(blacklisted_token)
    db_session.commit()

    logging.info(
        f"Added new token to blacklist: from {username},token={blacklisted_token.value[:20]}..."
    )


def is_token_blacklisted(db_session: Session, access_token: str) -> None:
    return db_session.query(
        exists(BlackListToken.id).where(BlackListToken.value == access_token)
    ).scalar()


def hashify(password: str) -> str:
    return bcrypt_context.hash(password)
