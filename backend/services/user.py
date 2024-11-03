from backend.database.models import Account

from backend.utils.auth import hashify


async def create_user(user_data: dict) -> dict:
    user = await Account.create(
        id=user_data["id"],
        email=user_data["email"],
        username=user_data["username"],
        password=hashify(user_data["password"]),
        role=user_data["role"],
        company_name=user_data["company_name"],
    )

    return {"id": str(user.id), **user_data}
