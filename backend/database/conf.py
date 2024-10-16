import logging
from decouple import config
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

DATABASE_URL: str = config("DATABASE_URL").replace("postgresql", "postgres")


TORTOISE_CONFIG = {
    "connections": {
        "default": DATABASE_URL,
    },
    "apps": {
        "models": {
            "models": ["backend.database.models", "aerich.models"],
            "default_connection": "default",
        }
    },
}


@asynccontextmanager
async def init_tortoise(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    async with RegisterTortoise(
        app=fastapi_app,
        # generate_schemas=True,
        config=TORTOISE_CONFIG,
    ):
        logging.info("Tortoise ORM registered!")
        yield
