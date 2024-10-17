import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise

from backend.core.settings import TORTOISE_CONFIG


@asynccontextmanager
async def init_tortoise(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    async with RegisterTortoise(
        app=fastapi_app,
        # generate_schemas=True,
        config=TORTOISE_CONFIG,
    ):
        logging.info("Tortoise ORM registered!")
        yield
