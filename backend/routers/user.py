import logging
import typing as t

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.security import HTTPBasicCredentials, OAuth2PasswordRequestForm

from backend import db
from backend.utils.auth import add_to_blacklist
from backend.utils.shortcuts import model_to_dict, raise_404
from backend.schemas import (
    UserCreate,
    User,
    PutCredentials,
    UserUpdateRequest,
)
from backend.auth.basic import basic_auth_security, basic_auth_wrapper
from backend.core.auth import generate_access_token, authenticate_user

from backend.services import user as user_service
from backend.services.user import create_user, get_user_by_id
from backend.services.credentials import (
    insert_or_update_pbx_credential,
    insert_or_update_bitrix_credential,
    insert_or_update_amocrm_credential,
)

from backend.core.dependencies.database import DatabaseSessionDependency
from backend.core.dependencies.user import get_current_user, CurrentUser
from uuid import UUID


user_router = APIRouter(tags=["User"])


@user_router.post("/signup")
@basic_auth_wrapper
def signup(
    user: UserCreate,
    db_session: DatabaseSessionDependency,
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
) -> JSONResponse:
    account = create_user(db_session, user.model_dump(mode="json"))

    return JSONResponse(
        {"success": True, "user": model_to_dict(User, account)},
        status_code=status.HTTP_201_CREATED,
    )


@user_router.post("/login")
def login(
    db_session: DatabaseSessionDependency,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    user = authenticate_user(db_session, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = generate_access_token(data={"user_id": str(user.id)})

    response = JSONResponse(
        content={
            "user": User.model_validate(user).model_dump(mode="json"),
            "token_type": "bearer",
        },
        status_code=status.HTTP_200_OK,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
    )

    return response


@user_router.post("/logout")
async def logout(
    request: Request,
    db_session: DatabaseSessionDependency,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    access_token: str | None = request.cookies.get("access_token")

    if access_token is not None:
        add_to_blacklist(db_session, current_user.username, access_token)

    response = JSONResponse({"success": True}, status_code=status.HTTP_200_OK)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="none",
        secure=True,
    )

    return response


@user_router.get("/me")
def retrieve_current_user(current_user: CurrentUser):
    return {"user": model_to_dict(User, current_user)}


@user_router.get("/balance")
def retrieve_current_user_balance(current_user: User = Depends(get_current_user)):
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0) or 0
    return {"balance": balance}


@user_router.post("/topup")
@basic_auth_wrapper
def topup(
    amount: t.Annotated[int, Body(...)],
    email: t.Annotated[str, Body(...)],
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
):
    try:
        user = db.get_user_by_email(email)
        db.create_topup_transaction(
            owner_id=user["id"],
            amount=amount,
            type="topup",
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})

    except Exception as exc:
        logging.error(f"Error occurred while topping up: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(exc)}
        )


@user_router.put("/put-credentials")
@basic_auth_wrapper
def put_credentials(
    put_credentials: PutCredentials,
    db_session: DatabaseSessionDependency,
    credentials: HTTPBasicCredentials = Depends(basic_auth_security),
) -> JSONResponse:
    if not get_user_by_id(db_session, put_credentials.owner_id):
        raise_404("Account with this owner_id is not found")

    if put_credentials.pbx_credentials:
        insert_or_update_pbx_credential(
            db_session,
            put_credentials.owner_id,
            **put_credentials.model_dump()["pbx_credentials"],
        )

    if put_credentials.bitrix_credentials:
        insert_or_update_bitrix_credential(
            db_session,
            put_credentials.owner_id,
            **put_credentials.model_dump()["bitrix_credentials"],
        )

    if put_credentials.amocrm_credentials:
        insert_or_update_amocrm_credential(
            db_session,
            put_credentials.owner_id,
            **put_credentials.model_dump()["amocrm_credentials"],
        )

    return JSONResponse(content={"success": True}, status_code=status.HTTP_200_OK)


# ========================================
# Admin User Management Endpoints
# ========================================


@user_router.get("/admin/users")
def list_all_users(
    db_session: DatabaseSessionDependency,
    search: str = None,
    role: str = None,
    company_id: UUID = None,
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Admin uchun user'lar ro'yxati"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    users = user_service.search_users(
        db_session, search, role, company_id, is_active, limit, offset
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"users": [model_to_dict(User, u) for u in users]},
    )


@user_router.get("/admin/user/{user_id}")
def get_user_details(
    user_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User detallarini olish - Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user = user_service.get_user_by_id(db_session, user_id)
    if not user:
        raise_404("User not found")

    activity_logs = user_service.get_user_transaction_history(db_session, user_id)

    from backend.schemas import Transaction
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "user": model_to_dict(User, user),
            "transaction_history": [{"id": str(t.id), "amount": t.amount, "type": t.type, "created_at": str(t.created_at)} for t in activity_logs],
        },
    )


@user_router.patch("/admin/user/{user_id}")
def update_user_by_admin(
    user_id: UUID,
    update_data: UserUpdateRequest,
    db_session: DatabaseSessionDependency,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Admin tomonidan user ma'lumotini yangilash"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user_service.update_user_info(
        db_session, user_id, update_data.model_dump(exclude_none=True)
    )

    # Log activity
    from backend.services import activity_log as al_service  # noqa

    al_service.log_activity(
        db_session,
        current_user.id,
        "UPDATE",
        "account",
        user_id,
        details={"updated_fields": list(update_data.model_dump(exclude_none=True).keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@user_router.delete("/admin/user/{user_id}")
def delete_user_by_admin(
    user_id: UUID,
    db_session: DatabaseSessionDependency,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Admin tomonidan user'ni o'chirish"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user_service.delete_user(db_session, user_id)

    # Log activity
    from backend.services import activity_log as al_service  # noqa

    al_service.log_activity(
        db_session,
        current_user.id,
        "DELETE",
        "account",
        user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@user_router.post("/admin/user/{user_id}/reset-password")
def reset_user_password_by_admin(
    user_id: UUID,
    new_password: str = Body(...),
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Admin tomonidan password qayta tiklash"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user_service.reset_user_password(db_session, user_id, new_password)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@user_router.post("/admin/user/{user_id}/block")
def block_user_by_admin(
    user_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User'ni bloklash - Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user_service.block_user(db_session, user_id)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@user_router.post("/admin/user/{user_id}/unblock")
def unblock_user_by_admin(
    user_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User'ni blokdan ochirish - Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    user_service.unblock_user(db_session, user_id)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
