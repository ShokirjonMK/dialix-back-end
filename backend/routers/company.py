"""
Company Management Router

Company management uchun API endpoints - Admin only
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body, status
from fastapi.responses import JSONResponse
from uuid import UUID

from backend.schemas import (
    CompanyCreate,
    CompanyUpdate,
    UserTransferRequest,
    Company,
    User,
)
from backend.services import company as company_service
from backend.core.dependencies.user import get_current_user, CurrentUser
from backend.core.dependencies.database import DatabaseSessionDependency
from backend.utils.shortcuts import model_to_dict


company_router = APIRouter(tags=["Company Management"])


def check_admin_access(current_user: CurrentUser):
    """Admin access check"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@company_router.post("/company")
def create_company(
    company_data: CompanyCreate,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Yangi kompaniya yaratish - Admin only"""
    check_admin_access(current_user)

    company = company_service.create_company(db_session, company_data.model_dump())
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"success": True, "company_id": str(company.id)},
    )


@company_router.get("/companies")
def list_companies(
    db_session: DatabaseSessionDependency,
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniyalar ro'yxatini olish"""
    companies = company_service.get_all_companies(db_session, skip, limit, is_active)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"companies": [model_to_dict(User, c) for c in companies], "total": len(companies)},
    )


@company_router.get("/company/{company_id}")
def get_company_details(
    company_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniya detallarini olish"""
    company = company_service.get_company_by_id(db_session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    statistics = company_service.get_company_statistics(db_session, company_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"company": model_to_dict(Company, company), "statistics": statistics},
    )


@company_router.patch("/company/{company_id}")
def update_company_info(
    company_id: UUID,
    update_data: CompanyUpdate,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniya ma'lumotini yangilash - Admin only"""
    check_admin_access(current_user)

    company = company_service.update_company(
        db_session, company_id, update_data.model_dump(exclude_none=True)
    )
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@company_router.post("/company/{company_id}/block")
def block_company(
    company_id: UUID,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniyani bloklash - Admin only"""
    check_admin_access(current_user)

    company_service.deactivate_company(db_session, company_id)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@company_router.post("/company/{company_id}/topup")
def topup_company_balance(
    company_id: UUID,
    amount: int = Body(...),
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniya balansini to'ldirish - Admin only"""
    check_admin_access(current_user)

    company_service.topup_company_balance(db_session, company_id, amount)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@company_router.post("/company/{company_id}/transfer-user")
def transfer_user(
    company_id: UUID,
    transfer_data: UserTransferRequest,
    db_session: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user),
):
    """User'ni boshqa kompaniyaga o'tkazish - Admin only"""
    check_admin_access(current_user)

    company_service.transfer_user_between_companies(
        db_session, transfer_data.user_id, transfer_data.from_company_id, company_id
    )
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})


@company_router.get("/company/{company_id}/users")
def get_company_users(
    company_id: UUID,
    db_session: DatabaseSessionDependency,
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Kompaniya userlarini olish"""
    users = company_service.get_company_users(db_session, company_id, skip, limit)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"users": [model_to_dict(User, u) for u in users]},
    )

