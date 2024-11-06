import logging
from fastapi import FastAPI

from backend.database.session_manager import sessionmanager


async def lifespan_handler(app: FastAPI):
    # handle startup/shutdown events
    logging.info("Executing lifespan handler (startup)")
    yield

    if sessionmanager._engine is not None:
        sessionmanager.close()
        logging.info("Database session is closed")

    logging.info("Executing lifespan handler (shutdown)")
