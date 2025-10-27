# Backend Development Strategy - Dialix Project

## Kirish

Hujjat Dialix loyihasida ToR talablariga muvofiq qilmagan va chala ishlarni bajarish uchun backend development strategiyasini tavsiflaydi.

**Maqsad:** ToR'ning 40% implementation holatini 90%+ ga yetkazish

---

## Phаse 1: Database Architecture Enhancement (2-3 hafta)

### 1.1 Yangi Database Models Yaratish

#### Company Management Models

**File:** `backend/database/models.py`

```python
class Company(Base):
    __tablename__ = "company"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(TEXT)
    is_active = Column(Boolean, server_default="true")
    parent_company_id = Column(PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=True)
    hierarchy_level = Column(Integer, default=0)
    settings = Column(JSON)  # Company-specific settings
    balance = Column(BigInteger, default=0)
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"))
    deleted_at = Column(TIMESTAMP)
    
    # Relationships
    users = relationship("Account", back_populates="company")
    administrators = relationship("CompanyAdministrator", back_populates="company")


class CompanyAdministrator(Base):
    __tablename__ = "company_administrator"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    company_id = Column(PostgresUUID(as_uuid=True), ForeignKey("company.id"))
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("account.id"))
    permissions = Column(JSON)  # {"can_manage_users": true, ...}
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))


class UserCompanyHistory(Base):
    """User o'tkazilgan kompaniyalar tarixi"""
    __tablename__ = "user_company_history"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("account.id"))
    company_id = Column(PostgresUUID(as_uuid=True), ForeignKey("company.id"))
    action = Column(String)  # "transferred", "joined", "left"
    balance_at_time = Column(BigInteger)
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))
```

#### Activity & Audit Logging Models

```python
class ActivityLog(Base):
    """CRUD operations uchun audit log"""
    __tablename__ = "activity_log"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("account.id"))
    action = Column(String)  # "CREATE", "UPDATE", "DELETE", "VIEW"
    resource_type = Column(String)  # "record", "checklist", "operator"
    resource_id = Column(PostgresUUID(as_uuid=True))
    details = Column(JSON)  # {"field": "value", "old_value": "...", "new_value": "..."}
    ip_address = Column(String)
    user_agent = Column(TEXT)
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))


class AIChatSession(Base):
    """AI Chat interfacе uchun"""
    __tablename__ = "ai_chat_session"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("account.id"))
    record_id = Column(PostgresUUID(as_uuid=True), ForeignKey("record.id"))
    session_data = Column(JSON)  # {"questions_asked": 5, "context": {...}}
    is_active = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"))


class AIChatMessage(Base):
    """AI Chat xabarlar"""
    __tablename__ = "ai_chat_message"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    session_id = Column(PostgresUUID(as_uuid=True), ForeignKey("ai_chat_session.id"))
    role = Column(String)  # "user", "assistant"
    content = Column(TEXT)
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))
```

#### Settings Model

```python
class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("account.id"), unique=True)
    
    # Notification settings
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    
    # Language & localization
    language = Column(String, default="uz")
    timezone = Column(String, default="Asia/Tashkent")
    
    # Data retention
    auto_delete_records_after_days = Column(Integer, default=90)
    
    # STT Model preferences
    preferred_stt_model = Column(String, default="mohirai")
    
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"))
```

#### Account Model Yangilanish

```python
class Account(Base):
    __tablename__ = "account"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    company_name = Column(String, nullable=False)  # LEGACY - use company_id instead
    company_id = Column(PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=True)  # NEW
    is_active = Column(Boolean, server_default="true")  # NEW
    is_blocked = Column(Boolean, server_default="false")  # NEW
    last_activity = Column(TIMESTAMP)  # NEW
    preferred_language = Column(String, default="uz")  # NEW
    
    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="users")
```

**Migration:** `alembic revision --autogenerate -m "Add company management and activity logging models"`

---

### 1.2 Database Indexlar Qo'shish (Performance)

**File:** `alembic/versions/add_indexes.py`

```python
# Activity logs uchun
CREATE INDEX idx_activity_log_user_id ON activity_log(user_id);
CREATE INDEX idx_activity_log_created_at ON activity_log(created_at);
CREATE INDEX idx_activity_log_resource ON activity_log(resource_type, resource_id);

# User management uchun
CREATE INDEX idx_account_email ON account(email);
CREATE INDEX idx_account_company_id ON account(company_id);
CREATE INDEX idx_account_is_active ON account(is_active);

# Records uchun optimization
CREATE INDEX idx_record_owner_status ON record(owner_id, status);
CREATE INDEX idx_record_client_phone ON record(client_phone_number);

# Results uchun
CREATE INDEX idx_result_owner_created ON result(owner_id, created_at);
```

---

## Phase 2: Service Layer Development (3-4 hafta)

### 2.1 Company Service

**File:** `backend/services/company.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from backend.database.models import Company, Account, CompanyAdministrator

def create_company(db: Session, company_data: dict) -> Company:
    """Yangi kompaniya yaratish"""
    new_company = Company(**company_data)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company

def get_company_by_id(db: Session, company_id: UUID) -> Company:
    """Kompaniya ma'lumotini olish"""
    return db.query(Company).filter(Company.id == company_id).first()

def update_company(db: Session, company_id: UUID, update_data: dict) -> Company:
    """Kompaniya ma'lumotini yangilash"""
    db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(**update_data)
    )
    db.commit()
    return get_company_by_id(db, company_id)

def deactivate_company(db: Session, company_id: UUID):
    """Kompaniyani bloklash"""
    db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(is_active=False)
    )
    # All users under this company will be blocked
    db.execute(
        update(Account)
        .where(Account.company_id == company_id)
        .values(is_blocked=True)
    )
    db.commit()

def topup_company_balance(db: Session, company_id: UUID, amount: int):
    """Kompaniya balansini to'ldirish"""
    db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(balance=Company.balance + amount)
    )
    db.commit()

def get_company_statistics(db: Session, company_id: UUID) -> dict:
    """Kompaniya statistikasi"""
    # Users count
    users_count = db.query(Account).filter(Account.company_id == company_id).count()
    
    # Balance
    company = db.query(Company).filter(Company.id == company_id).first()
    
    # Total records processed
    # ... additional statistics
    
    return {
        "users_count": users_count,
        "balance": company.balance,
        # ...
    }

def transfer_user_between_companies(
    db: Session, 
    user_id: UUID, 
    from_company_id: UUID, 
    to_company_id: UUID
):
    """User'ni boshqa kompaniyaga o'tkazish"""
    # Save history
    # Transfer balance
    # Update user
    pass
```

---

### 2.2 Activity Logging Service

**File:** `backend/services/activity_log.py`

```python
from backend.database.models import ActivityLog
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from datetime import datetime
from typing import Optional

def log_activity(
    db: Session,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """CRUD operations uchun logging"""
    log_entry = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(log_entry)
    db.commit()

def get_user_activity_logs(
    db: Session,
    user_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None
) -> list:
    """User'ning faollik loglarini filter qilib olish"""
    query = select(ActivityLog).where(ActivityLog.user_id == user_id)
    
    if start_date:
        query = query.where(ActivityLog.created_at >= start_date)
    if end_date:
        query = query.where(ActivityLog.created_at <= end_date)
    if action:
        query = query.where(ActivityLog.action == action)
    if resource_type:
        query = query.where(ActivityLog.resource_type == resource_type)
    
    query = query.order_by(ActivityLog.created_at.desc())
    
    return db.execute(query).scalars().all()

def get_company_activity_logs(db: Session, company_id: UUID, filters: dict = None):
    """Company bo'yicha activity logs"""
    # Get all users in company
    # Filter their activity logs
    pass

def get_audit_trail_for_resource(
    db: Session,
    resource_type: str,
    resource_id: UUID
) -> list:
    """Muayyan resource uchun audit trail"""
    query = select(ActivityLog).where(
        and_(
            ActivityLog.resource_type == resource_type,
            ActivityLog.resource_id == resource_id
        )
    ).order_by(ActivityLog.created_at.desc())
    
    return db.execute(query).scalars().all()
```

---

### 2.3 User Management Service Enhancement

**File:** `backend/services/user.py` (Yangilanish)

```python
def update_user_info(db: Session, user_id: UUID, update_data: dict):
    """User ma'lumotini yangilash"""
    db.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(**update_data, updated_at=text("now()"))
    )
    db.commit()

def delete_user(db: Session, user_id: UUID):
    """User'ni o'chirish (soft delete)"""
    db.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(is_active=False)
    )
    db.commit()

def search_users(
    db: Session,
    query: str = None,
    role: str = None,
    company_id: UUID = None,
    is_active: bool = None,
    limit: int = 50,
    offset: int = 0
) -> list:
    """User'lar ichida qidirish"""
    search_query = select(Account)
    
    if query:
        search_query = search_query.where(
            or_(
                Account.username.ilike(f"%{query}%"),
                Account.email.ilike(f"%{query}%"),
                Account.company_name.ilike(f"%{query}%")
            )
        )
    
    if role:
        search_query = search_query.where(Account.role == role)
    if company_id:
        search_query = search_query.where(Account.company_id == company_id)
    if is_active is not None:
        search_query = search_query.where(Account.is_active == is_active)
    
    search_query = search_query.limit(limit).offset(offset)
    
    return db.execute(search_query).scalars().all()

def reset_user_password(db: Session, user_id: UUID, new_password: str):
    """User parolini qayta tiklash"""
    hashed = hashify(new_password)
    db.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(password=hashed, updated_at=text("now()"))
    )
    db.commit()

def block_user(db: Session, user_id: UUID):
    """User'ni bloklash"""
    db.execute(
        update(Account)
        .where(Account.id == user_id)
        .values(is_blocked=True)
    )
    db.commit()

def get_user_transaction_history(
    db: Session,
    user_id: UUID,
    limit: int = 100
) -> list:
    """User'ning transaction tarixini olish"""
    query = select(Transaction).where(
        Transaction.owner_id == user_id
    ).order_by(Transaction.created_at.desc()).limit(limit)
    
    return db.execute(query).scalars().all()
```

---

### 2.4 AI Chat Service

**File:** `backend/services/ai_chat.py`

```python
from backend.database.models import AIChatSession, AIChatMessage
import openai

MAX_QUESTIONS_PER_SESSION = 10

def create_chat_session(db: Session, user_id: UUID, record_id: UUID) -> AIChatSession:
    """Yangi AI chat session yaratish"""
    session = AIChatSession(
        user_id=user_id,
        record_id=record_id,
        session_data={
            "questions_asked": 0,
            "context": {}
        }
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def send_message_to_ai(
    db: Session,
    session_id: UUID,
    user_message: str,
    record_context: dict
) -> dict:
    """AI'ga xabar yuborish va javob olish"""
    # Get session
    session = db.query(AIChatSession).filter(AIChatSession.id == session_id).first()
    
    # Check question limit
    if session.session_data["questions_asked"] >= MAX_QUESTIONS_PER_SESSION:
        raise HTTPException(400, "Question limit reached")
    
    # Get conversation context from record
    conversation_text = record_context.get("conversation_text", "")
    
    # Prepare GPT prompt with context
    context_prompt = f"""
    You are an AI assistant helping to analyze a phone call conversation.
    
    Full conversation transcript:
    {conversation_text}
    
    User's question: {user_message}
    
    Provide a helpful answer based on the conversation.
    """
    
    # Call OpenAI
    response = openai.ChatCompletion.create(
        deployment_id=config("DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    assistant_response = response.choices[0].message.content
    
    # Save message to database
    user_msg = AIChatMessage(
        session_id=session_id,
        role="user",
        content=user_message
    )
    
    ai_msg = AIChatMessage(
        session_id=session_id,
        role="assistant",
        content=assistant_response
    )
    
    db.add_all([user_msg, ai_msg])
    
    # Update session data
    session.session_data["questions_asked"] += 1
    session.session_data["context"]["last_question"] = user_message
    
    db.commit()
    
    return {
        "response": assistant_response,
        "remaining_questions": MAX_QUESTIONS_PER_SESSION - session.session_data["questions_asked"]
    }

def get_suggested_questions(record_context: dict) -> list:
    """Context'ga asoslangan taklif etilgan savollar"""
    return [
        "Qo'ng'iroqda qanday asosiy mavzular muhokama qilindi?",
        "Mijozning asosiy ehtiyoji nima edi?",
        "Operator qanday savollar berdi?",
        "Suhbatning umumiy sentiment holati qanday?",
        "Qaysi kurslar haqida gapirildi?"
    ]
```

---

### 2.5 Call Grouping Service

**File:** `backend/services/call_grouping.py`

```python
from sqlalchemy import select, func
from backend.database.models import Record

def group_calls_by_phone_number(
    db: Session,
    owner_id: UUID,
    time_window_hours: int = 24
) -> list:
    """Raqam bo'yicha qo'ng'iroqlarni guruhlash"""
    
    query = select(
        Record.client_phone_number,
        func.count(Record.id).label("call_count"),
        func.avg(Record.duration).label("avg_duration"),
        func.min(Record.created_at).label("first_call"),
        func.max(Record.created_at).label("last_call")
    ).where(
        Record.owner_id == owner_id,
        Record.client_phone_number.isnot(None)
    ).group_by(
        Record.client_phone_number
    ).having(
        func.count(Record.id) > 1  # Only show repeated calls
    )
    
    groups = db.execute(query).all()
    
    result = []
    for group in groups:
        phone = group.client_phone_number
        
        # Get all records for this phone
        records = db.query(Record).filter(
            Record.owner_id == owner_id,
            Record.client_phone_number == phone
        ).order_by(Record.created_at).all()
        
        # Sentiment analysis
        sentiments = [r.result.sentiment_analysis_of_conversation for r in records if r.result]
        
        result.append({
            "phone_number": phone,
            "call_count": group.call_count,
            "avg_duration": group.avg_duration,
            "first_call": group.first_call,
            "last_call": group.last_call,
            "sentiment_distribution": {
                "positive": sentiments.count("positive"),
                "negative": sentiments.count("negative"),
                "neutral": sentiments.count("neutral")
            },
            "records": [record.id for record in records]
        })
    
    return result

def get_similar_calls(db: Session, record_id: UUID, owner_id: UUID) -> list:
    """O'xshash qo'ng'iroqlarni topish"""
    # Get current record
    current_record = db.query(Record).filter(Record.id == record_id).first()
    
    if not current_record or not current_record.client_phone_number:
        return []
    
    # Find similar calls (same phone number with similar duration/sentiment)
    similar_calls = db.query(Record).filter(
        Record.owner_id == owner_id,
        Record.client_phone_number == current_record.client_phone_number,
        Record.id != record_id
    ).order_by(Record.created_at.desc()).limit(10).all()
    
    return similar_calls
```

---

### 2.6 Settings Service

**File:** `backend/services/settings.py`

```python
from backend.database.models import UserSettings

def get_user_settings(db: Session, user_id: UUID) -> UserSettings:
    """User'ning sozlashlarini olish"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == user_id
    ).first()
    
    if not settings:
        # Create default settings
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        db.commit()
    
    return settings

def update_user_settings(db: Session, user_id: UUID, settings_data: dict):
    """User'ning sozlashlarini yangilash"""
    db.execute(
        update(UserSettings)
        .where(UserSettings.user_id == user_id)
        .values(**settings_data, updated_at=text("now()"))
    )
    db.commit()
```

---

## Phase 3: API Endpoints Development (3-4 hafta)

### 3.1 Company Router

**File:** `backend/routers/company.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from uuid import UUID

company_router = APIRouter(tags=["Company Management"])

@company_router.post("/company")
def create_company(
    company_data: CompanyCreate,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)  # Admin only
):
    """Yangi kompaniya yaratish"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    company = create_company(db, company_data.model_dump())
    return JSONResponse(
        content={"success": True, "company_id": str(company.id)},
        status_code=status.HTTP_201_CREATED
    )

@company_router.get("/companies")
def list_companies(
    db: DatabaseSessionDependency,
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Kompaniyalar ro'yxatini olish"""
    companies = get_all_companies(db, skip, limit)
    return {"companies": companies, "total": len(companies)}

@company_router.get("/company/{company_id}")
def get_company_details(
    company_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Kompaniya detallarini olish"""
    company = get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    
    statistics = get_company_statistics(db, company_id)
    
    return {
        "company": company,
        "statistics": statistics
    }

@company_router.patch("/company/{company_id}")
def update_company_info(
    company_id: UUID,
    update_data: CompanyUpdate,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Kompaniya ma'lumotini yangilash"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    company = update_company(db, company_id, update_data.model_dump(exclude_none=True))
    return {"success": True, "company": company}

@company_router.post("/company/{company_id}/block")
def block_company(
    company_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Kompaniyani bloklash"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    deactivate_company(db, company_id)
    return {"success": True}

@company_router.post("/company/{company_id}/topup")
def topup_company_balance(
    company_id: UUID,
    amount: int,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Kompaniya balansini to'ldirish"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    topup_company_balance(db, company_id, amount)
    return {"success": True}

@company_router.post("/company/{company_id}/transfer-user")
def transfer_user(
    company_id: UUID,
    transfer_data: UserTransferRequest,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User'ni boshqa kompaniyaga o'tkazish"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    transfer_user_between_companies(
        db,
        transfer_data.user_id,
        transfer_data.from_company_id,
        company_id
    )
    return {"success": True}
```

---

### 3.2 User Management Router Enhancement

**File:** `backend/routers/user.py` (Qo'shimchalar)

```python
@user_router.get("/admin/users")  # Admin only
def list_all_users(
    db: DatabaseSessionDependency,
    search: str = None,
    role: str = None,
    company_id: UUID = None,
    is_active: bool = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Admin uchun user'lar ro'yxati"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    users = search_users(db, search, role, company_id, is_active)
    return {"users": users}

@user_router.get("/admin/user/{user_id}")
def get_user_details(
    user_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User detallarini olish"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    user = db.query(Account).filter(Account.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    activity_logs = get_user_activity_logs(db, user_id, limit=100)
    transaction_history = get_user_transaction_history(db, user_id)
    
    return {
        "user": user,
        "activity_logs": activity_logs,
        "transaction_history": transaction_history
    }

@user_router.patch("/admin/user/{user_id}")
def update_user_by_admin(
    user_id: UUID,
    update_data: UserUpdateRequest,
    db: DatabaseSessionDependency,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Admin tomonidan user ma'lumotini yangilash"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    update_user_info(db, user_id, update_data.model_dump(exclude_none=True))
    
    # Log activity
    log_activity(
        db,
        current_user.id,
        "UPDATE",
        "account",
        user_id,
        details={"updated_fields": list(update_data.model_dump(exclude_none=True).keys())},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"success": True}

@user_router.delete("/admin/user/{user_id}")
def delete_user_by_admin(
    user_id: UUID,
    db: DatabaseSessionDependency,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Admin tomonidan user'ni o'chirish"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    delete_user(db, user_id)
    
    # Log activity
    log_activity(
        db,
        current_user.id,
        "DELETE",
        "account",
        user_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"success": True}

@user_router.post("/admin/user/{user_id}/reset-password")
def reset_user_password_by_admin(
    user_id: UUID,
    new_password: str,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Admin tomonidan password qayta tiklash"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    reset_user_password(db, user_id, new_password)
    return {"success": True}

@user_router.post("/admin/user/{user_id}/block")
def block_user_by_admin(
    user_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User'ni bloklash"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    block_user(db, user_id)
    return {"success": True}
```

---

### 3.3 AI Chat Router

**File:** `backend/routers/ai_chat.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID

ai_chat_router = APIRouter(tags=["AI Chat"])

@ai_chat_router.post("/chat/session")
def create_chat_session(
    record_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Yangi AI chat session yaratish"""
    session = create_chat_session(db, current_user.id, record_id)
    
    return {
        "session_id": str(session.id),
        "remaining_questions": MAX_QUESTIONS_PER_SESSION
    }

@ai_chat_router.post("/chat/{session_id}/message")
def send_message(
    session_id: UUID,
    message: str,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """AI'ga xabar yuborish"""
    # Get record context
    # session = get_session_by_id(db, session_id)
    # record = get_record_by_id(db, session.record_id, current_user.id)
    
    # record_context = extract_context_from_record(record)
    
    # response = send_message_to_ai(db, session_id, message, record_context)
    
    return response

@ai_chat_router.get("/chat/suggested-questions/{record_id}")
def get_suggested_questions(
    record_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Context'ga asoslangan savollarni olish"""
    record = get_record_by_id(db, record_id, current_user.id)
    
    if not record or not record.payload:
        raise HTTPException(404, "Record not found or no payload")
    
    record_context = extract_context_from_record(record)
    questions = get_suggested_questions(record_context)
    
    return {"questions": questions}

@ai_chat_router.get("/chat/session/{session_id}/messages")
def get_chat_history(
    session_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Chat tarixini olish"""
    session = get_session_by_id(db, session_id)
    
    if session.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    messages = db.query(AIChatMessage).filter(
        AIChatMessage.session_id == session_id
    ).order_by(AIChatMessage.created_at).all()
    
    return {"messages": messages}
```

---

### 3.4 Activity Logs Router

**File:** `backend/routers/activity_log.py`

```python
activity_log_router = APIRouter(tags=["Activity Logs"])

@activity_log_router.get("/activity-logs")
def get_user_activity_logs(
    start_date: datetime = None,
    end_date: datetime = None,
    action: str = None,
    resource_type: str = None,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User o'zining activity loglarini ko'rish"""
    logs = get_user_activity_logs(
        db,
        current_user.id,
        start_date,
        end_date,
        action,
        resource_type
    )
    return {"logs": logs}

@activity_log_router.get("/activity-logs/{resource_type}/{resource_id}")
def get_resource_audit_trail(
    resource_type: str,
    resource_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Resource uchun audit trail"""
    trail = get_audit_trail_for_resource(db, resource_type, resource_id)
    return {"audit_trail": trail}

@activity_log_router.get("/admin/company/{company_id}/activity-logs")
def get_company_activity_logs(
    company_id: UUID,
    filters: dict = None,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Admin uchun company activity logs"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    
    logs = get_company_activity_logs(db, company_id, filters)
    return {"logs": logs}
```

---

### 3.5 Settings Router

**File:** `backend/routers/settings.py`

```python
settings_router = APIRouter(tags=["Settings"])

@settings_router.get("/settings")
def get_settings(
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User sozlamalarini olish"""
    settings = get_user_settings(db, current_user.id)
    return {"settings": settings}

@settings_router.patch("/settings")
def update_settings(
    settings_data: UserSettingsUpdate,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """User sozlamalarini yangilash"""
    update_user_settings(db, current_user.id, settings_data.model_dump(exclude_none=True))
    return {"success": True}
```

---

### 3.6 Call Grouping Router

**File:** `backend/routers/call_grouping.py`

```python
call_grouping_router = APIRouter(tags=["Call Grouping"])

@call_grouping_router.get("/calls/grouped")
def get_grouped_calls(
    time_window_hours: int = 24,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Telefon raqam bo'yicha guruhlangan qo'ng'iroqlar"""
    grouped = group_calls_by_phone_number(db, current_user.id, time_window_hours)
    return {"grouped_calls": grouped}

@call_grouping_router.get("/calls/similar/{record_id}")
def get_similar_calls(
    record_id: UUID,
    db: DatabaseSessionDependency,
    current_user: CurrentUser = Depends(get_current_user)
):
    """O'xshash qo'ng'iroqlarni topish"""
    similar = get_similar_calls(db, record_id, current_user.id)
    return {"similar_calls": similar}
```

---

### 3.7 Router Registration

**File:** `backend/routers/__init__.py`

```python
from .user import user_router
from .company import company_router
from .ai_chat import ai_chat_router
from .activity_log import activity_log_router
from .settings import settings_router
from .call_grouping import call_grouping_router
from .audio import audio_router
from .checklist import checklist_router
from .dashboard import dashboard_router
from .operator import operator_router
from .pbx import pbx_router
from .bitrix import bitrix_router

routers = [
    user_router,
    company_router,
    ai_chat_router,
    activity_log_router,
    settings_router,
    call_grouping_router,
    audio_router,
    checklist_router,
    dashboard_router,
    operator_router,
    pbx_router,
    bitrix_router,
]
```

---

## Phase 4: Middleware & Dependency Updates (1 hafta)

### 4.1 Activity Logging Middleware

**File:** `backend/core/middleware/activity_logging.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.activity_log import log_activity

class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip health check, static files
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        response = await call_next(request)
        
        # Extract user info from request
        current_user = request.state.current_user if hasattr(request.state, "current_user") else None
        
        # If it's a CRUD operation, log it
        if current_user and request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                # Extract action and resource info from URL
                action = request.method
                # ...
                
                # Log activity
                await log_activity(...)
            except:
                pass  # Don't break the request
        
        return response
```

### 4.2 Update Dependencies

**File:** `backend/core/dependencies/user.py`

```python
def get_current_user_admin_only(
    request: Request, db_session: DatabaseSessionDependency
) -> Account:
    """Admin uchun cheklangan dependency"""
    user = get_current_user(request, db_session)
    
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    
    return user
```

---

## Phase 5: Schemas Update (1 hafta)

**File:** `backend/schemas.py` (Qo'shimchalar)

```python
class CompanyCreate(BaseModel):
    name: str
    description: str = None
    parent_company_id: UUID = None

class CompanyUpdate(BaseModel):
    name: str = None
    description: str = None
    is_active: bool = None

class UserSettingsUpdate(BaseModel):
    email_notifications: bool = None
    sms_notifications: bool = None
    language: str = None
    timezone: str = None
    preferred_stt_model: str = None

class UserUpdateRequest(BaseModel):
    email: str = None
    username: str = None
    role: str = None
    company_id: UUID = None
    is_active: bool = None

class UserTransferRequest(BaseModel):
    user_id: UUID
    from_company_id: UUID

class AIChatMessageRequest(BaseModel):
    message: str
```

---

## Phase 6: Testing & Documentation (2 hafta)

### 6.1 Unit Tests
- Service layer testlari
- Utils testlari

### 6.2 Integration Tests
- API endpoint testlari
- Database integration testlari

### 6.3 Documentation
- API documentation (Swagger) to'ldirish
- Architecture documentation

---

## Vaqt Rejası

| Phase | Vazifa | Vaqt | Developer |
|-------|--------|------|-----------|
| 1 | Database Models & Migrations | 2 hafta | Backend dev |
| 2 | Service Layer | 3 hafta | Backend dev |
| 3 | API Endpoints | 3 hafta | Backend dev |
| 4 | Middleware & Dependencies | 1 hafta | Backend dev |
| 5 | Schemas Update | 1 hafta | Backend dev |
| 6 | Testing & Docs | 2 hafta | Backend dev |

**Jami:** 12 hafta (3 oy)

---

## Natija

Ushbu strategiyani amalga oshirishdan keyin:

✅ Company Management System
✅ Activity Logging
✅ Full User Management
✅ AI Chat Interface
✅ Call Grouping
✅ Settings Management
✅ Usage Statistics API
✅ Compliance Dashboard

**ToR Bajarilganlik:** 40% → 90%+

