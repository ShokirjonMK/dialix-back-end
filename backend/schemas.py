from datetime import datetime
from pydantic import BaseModel, EmailStr, constr, Field
import uuid


class UserCreate(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr
    username: constr(min_length=3, max_length=255)
    password: str
    # TODO: Add role default to role to user.
    role: str
    company_name: str


class User(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    username: str
    password: str
    email: EmailStr
    role: str
    company_name: str
    created_at: datetime
    updated_at: datetime

    def hide_password(self):
        return self.model_copy(exclude={"password": ...})


class CheckList(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    payload: list = []
    active: bool = False
    deleted_at: str = ""


class Record(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID
    title: str
    duration: float
    payload: dict = {}
    operator_code: int = None
    operator_name: str = None
    call_type: str = None
    source: str = None
    status: str = None
    storage_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime = None


class ReprocessRecord(BaseModel):
    record_id: str
    checklist_id: str = None
    general: bool = False


class OperatorData(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    code: int
    name: str
    deleted_at: datetime = None
