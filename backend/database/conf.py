import logging
from decouple import config
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise


@asynccontextmanager
async def init_tortoise(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    DATABASE_URL: str = config("DATABASE_URL").replace("postgresql", "postgres")

    async with RegisterTortoise(
        app=fastapi_app,
        db_url=DATABASE_URL,
        modules={"models": ["database.models"]},
        add_exception_handlers=True,
        generate_schemas=True,
    ):
        logging.info("Tortoise ORM registered!")
        yield
