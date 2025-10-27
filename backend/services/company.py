"""
Company Management Service

CRUD operations va Company management uchun service layer
"""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, and_

from backend.database.models import (
    Company,
    Account,
    CompanyAdministrator,
    UserCompanyHistory,
)


def create_company(db: Session, company_data: dict) -> Company:
    """Yangi kompaniya yaratish"""
    new_company = Company(**company_data)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    logging.info(f"New company created: {new_company.id}")
    return new_company


def get_company_by_id(db: Session, company_id: UUID) -> Optional[Company]:
    """Kompaniya ma'lumotini olish"""
    return db.query(Company).filter(Company.id == company_id).first()


def get_all_companies(
    db: Session, skip: int = 0, limit: int = 50, is_active: Optional[bool] = None
) -> list[Company]:
    """Barcha kompaniyalarni olish"""
    query = select(Company).where(Company.deleted_at.is_(None))

    if is_active is not None:
        query = query.where(Company.is_active == is_active)

    query = query.offset(skip).limit(limit)

    result = db.execute(query).scalars().all()
    return list(result)


def update_company(
    db: Session, company_id: UUID, update_data: dict
) -> Optional[Company]:
    """Kompaniya ma'lumotini yangilash"""
    db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(**update_data, updated_at=func.now())
    )
    db.commit()
    return get_company_by_id(db, company_id)


def deactivate_company(db: Session, company_id: UUID):
    """Kompaniyani bloklash - barcha userlar ham bloklanadi"""
    # Update company
    db.execute(update(Company).where(Company.id == company_id).values(is_active=False))

    # Block all users under this company
    db.execute(
        update(Account).where(Account.company_id == company_id).values(is_blocked=True)
    )

    db.commit()
    logging.info(f"Company {company_id} deactivated and all users blocked")


def topup_company_balance(db: Session, company_id: UUID, amount: int):
    """Kompaniya balansini to'ldirish"""
    # Get current balance
    company = get_company_by_id(db, company_id)
    if not company:
        raise ValueError("Company not found")

    new_balance = company.balance + amount

    db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(balance=new_balance, updated_at=func.now())
    )
    db.commit()
    logging.info(f"Company {company_id} balance updated: {new_balance}")


def get_company_statistics(db: Session, company_id: UUID) -> dict:
    """Kompaniya statistikasi"""
    # Users count
    users_count = (
        db.query(Account)
        .filter(Account.company_id == company_id, Account.is_active == True)
        .count()
    )

    # Balance
    company = get_company_by_id(db, company_id)

    # Total records processed
    records_count = db.query(func.count()).select_from(db.query(func.count())).scalar()

    return {
        "users_count": users_count,
        "balance": company.balance if company else 0,
        "company_name": company.name if company else "",
        "is_active": company.is_active if company else False,
    }


def transfer_user_between_companies(
    db: Session, user_id: UUID, from_company_id: UUID, to_company_id: UUID
):
    """User'ni boshqa kompaniyaga o'tkazish"""
    # Get user's current balance
    user = db.query(Account).filter(Account.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    # Get user's balance from transactions
    balance_query = db.execute(select(func.sum()).where(Account.id == user_id))
    current_balance = balance_query.scalar() or 0

    # Save history
    history = UserCompanyHistory(
        user_id=user_id,
        company_id=from_company_id,
        action="transferred",
        balance_at_time=current_balance,
    )
    db.add(history)

    # Update user
    db.execute(
        update(Account).where(Account.id == user_id).values(company_id=to_company_id)
    )

    db.commit()
    logging.info(
        f"User {user_id} transferred from {from_company_id} to {to_company_id}"
    )


def add_company_administrator(
    db: Session, company_id: UUID, user_id: UUID, permissions: dict = None
) -> CompanyAdministrator:
    """Kompaniyaga admin qo'shish"""
    admin = CompanyAdministrator(
        company_id=company_id, user_id=user_id, permissions=permissions or {}
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_company_users(
    db: Session, company_id: UUID, skip: int = 0, limit: int = 50
) -> list[Account]:
    """Kompaniya userlarini olish"""
    return (
        db.query(Account)
        .filter(Account.company_id == company_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
