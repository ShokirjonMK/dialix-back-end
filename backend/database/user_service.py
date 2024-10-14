from backend.database.models import Account

from backend.core.auth import hash_password


async def create_user(user_data: dict) -> dict | None:
    user = await Account.create(
        id=user_data["id"],
        email=user_data["email"],
        username=user_data["username"],
        password=hash_password(user_data["password"]),
        role=user_data["role"],
        company_name=user_data["company_name"],
    )
    return {**user_data, "id": str(user.id)}


async def get_user_by_id(user_id: str) -> dict | None:
    user = await Account.get(id=user_id)
    return user.to_dict() if user else None


async def get_user_by_email(email: str) -> dict | None:
    user = await Account.get(email=email)
    return user.to_dict() if user else None
