from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "blacklisttoken" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "value" TEXT NOT NULL
);
        DROP TABLE IF EXISTS "token";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "blacklisttoken";"""
