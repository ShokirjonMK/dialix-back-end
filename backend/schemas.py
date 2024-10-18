import uuid
import typing as t
from datetime import datetime

from pydantic import BaseModel, EmailStr, constr, Field


class UserCreate(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr
    username: constr(min_length=3, max_length=255)
    password: str
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
        return self.copy(exclude={"password": ...})


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


class CallHistoryRequest(BaseModel):
    # uuid: t.Optional[str] = Field(default=None,
    #                             description="Unique identifier for the call, e.g., '123e4567-e89b-12d3-a456-426614174000'")
    uuid_array: t.Optional[t.List[str]] = Field(
        default=None,
        description="Array of UUIDs for filtering multiple calls, e.g., ['123e4567-e89b-12d3-a456-426614174000']",
    )
    # phone_numbers: t.Optional[t.List[str]] = Field(default=None,
    #                                            description="t.List of phone numbers to filter the call history, e.g., ['+1234567890', '+0987654321']")
    # sub_phone_numbers: t.Optional[t.List[str]] = Field(default=None,
    #                                                description="t.List of sub phone numbers to filter the call history, e.g., ['+1234567890-ext123', '+0987654321-ext456']")
    # from_host: t.Optional[str] = Field(default=None,
    #                                  description="The host or source of the call, e.g., 'host1.example.com'")
    # caller_id_number: t.Optional[str] = Field(default=None, description="Caller ID number, e.g., '+1234567890'")
    # caller_id_name: t.Optional[str] = Field(default=None, description="Caller ID name, e.g., 'John Doe'")
    # to_host: t.Optional[str] = Field(default=None,
    #                                description="The destination host of the call, e.g., 'host2.example.com'")
    # destination_number: t.Optional[str] = Field(default=None,
    #                                           description="The number the call is directed to, e.g., '+0987654321'")
    start_stamp_from: t.Optional[str] = Field(
        default=None,
        description="Start timestamp from which to filter the calls (Unix Timestamp), e.g., '1622547800'",
    )
    # start_stamp_to: t.Optional[str] = Field(default=None,
    #                                       description="End timestamp to which to filter the calls (Unix Timestamp), e.g., '1622548400'")
    # end_stamp_from: t.Optional[str] = Field(default=None,
    #                                       description="Start end timestamp from which to filter the calls (Unix Timestamp), e.g., '1622549000'")
    end_stamp_to: t.Optional[str] = Field(
        default=None,
        description="End timestamp to which to filter the calls (Unix Timestamp), e.g., '1622549600'",
    )
    # duration_from: t.Optional[int] = Field(default=None, description="Minimum call duration (in seconds), e.g., 10")
    # duration_to: t.Optional[int] = Field(default=None, description="Maximum call duration (in seconds), e.g., 300")
    # user_talk_time_from: t.Optional[int] = Field(default=None, description="Minimum user talk time (in seconds), e.g., 5")
    # user_talk_time_to: t.Optional[int] = Field(default=None, description="Maximum user talk time (in seconds), e.g., 200")
    # accountcode: t.Optional[str] = Field(default=None, description="Account code for the call, e.g., 'ACC123456'")
    download: t.Optional[str] = Field(
        default=None,
        description="Whether to download call recordings (empty or '1'), e.g., '1' for yes",
    )
