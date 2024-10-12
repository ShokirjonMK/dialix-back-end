import logging
from fastapi import FastAPI

from backend.database.conf import init_tortoise


async def lifespan_handler(app: FastAPI):
    # handle startup/shutdown events
    logging.info("Executing lifespan handler (startup)")

    async with init_tortoise(app) as _:
        yield

    logging.info("Executing lifespan handler (shutdown)")
