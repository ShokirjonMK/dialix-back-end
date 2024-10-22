from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "operatordata" RENAME TO "operator_data";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "operator_data" RENAME TO "operatordata";"""
