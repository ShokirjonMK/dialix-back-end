import logging  # noqa: F401

import typing as t
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import (
    Field,
    EmailStr,
    BaseModel,
    validator,
    ConfigDict,
    model_validator,
    StringConstraints,
    SecretStr,
)

ChecklistPayload = t.Union[t.List[str], t.Dict[str, t.List[str]]]


class PbxCredentials(BaseModel):
    domain: str
    api_key: str


class PbxCredentialsFull(BaseModel):
    domain: t.Optional[str] = None

    api_key: t.Optional[str] = None

    key: t.Optional[str] = None
    key_id: t.Optional[str] = None


class BitrixCredentials(BaseModel):
    webhook_url: str


class AmoCRMCredentials(BaseModel):
    base_url: str
    access_token: str
    refresh_token: t.Optional[str] = None
    client_id: t.Optional[str] = None
    client_secret: t.Optional[str] = None
    redirect_uri: t.Optional[str] = None


class PutCredentials(BaseModel):
    owner_id: UUID

    pbx_credentials: t.Optional[PbxCredentialsFull] = None
    bitrix_credentials: t.Optional[BitrixCredentials] = None
    amocrm_credentials: t.Optional[AmoCRMCredentials] = None


class UserCreate(BaseModel):
    role: str
    password: str
    email: EmailStr
    company_name: str
    id: UUID = Field(default_factory=uuid4)
    username: t.Annotated[str, StringConstraints(min_length=3, max_length=255)]

    # optional credentials
    pbx_credentials: t.Optional[PbxCredentials] = None
    bitrix_credentials: t.Optional[BitrixCredentials] = None
    amocrm_credentials: t.Optional[AmoCRMCredentials] = None


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    username: str
    email: EmailStr
    company_name: str
    created_at: t.Optional[datetime] = None
    updated_at: t.Optional[datetime] = None


class UserPrivate(User):
    password: str


class CheckListBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    active: bool = False


class CheckListCreate(CheckListBase):
    payload: ChecklistPayload

    @model_validator(mode="before")
    @classmethod
    def check_whether_segmented_or_not(cls, values: t.Any) -> t.Any:
        payload = values.get("payload")

        if isinstance(payload, list):
            values["payload"] = {"segment_1": payload}

        elif isinstance(payload, dict):
            for key, segment in payload.items():
                if not isinstance(segment, list) or not all(
                    isinstance(i, str) for i in segment
                ):
                    raise ValueError(f"Segment {key=} must be a list of strings")

        return values


class CheckList(CheckListBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: t.Optional[datetime]
    payload: ChecklistPayload


class CheckListUpdate(BaseModel):
    title: t.Optional[str] = None
    payload: t.Optional[t.Union[t.List[str], t.Dict[str, t.List[str]]]] = None
    active: t.Optional[bool] = None
    deleted_at: t.Optional[str] = None


class Record(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
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
    deleted_at: t.Optional[datetime] = None


class ReprocessRecord(BaseModel):
    record_id: str
    checklist_id: str = None
    general: bool = False


class OperatorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: int
    name: str


class CreateOperatorData(OperatorBase): ...


class ListOperatorData(OperatorBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: t.Optional[datetime] = None


class UpdateOperatorData(BaseModel):
    code: t.Optional[int] = None
    name: t.Optional[str] = None


class PBXCallHistoryRequest(BaseModel):
    checklist_id: t.Optional[str] = Field(
        default=None,
        description="Unique identifier for the checklist, e.g., '213e4567-e89b-12d3-a456-426614174000'",
    )

    general: t.Optional[bool] = Field(
        default=False, description="Whether you want general checker or not"
    )

    uuid: UUID = Field(
        description="Unique identifier for the call, e.g., '123e4567-e89b-12d3-a456-426614174000'",
    )

    download: t.Optional[str] = Field(
        default="yes",
        description="Whether to download call recordings (empty or '1'), e.g., '1' for yes",
    )

    # start_stamp_from: t.Optional[str] = Field(
    #     default=None,
    #     description="Start timestamp from which to filter the calls (Unix Timestamp), e.g., '1622547800'",
    # )

    # end_stamp_to: t.Optional[str] = Field(
    #     default=None,
    #     description="End timestamp to which to filter the calls (Unix Timestamp), e.g., '1622549600'",
    # )

    # start_stamp_from: t.Optional[str] = Field(
    #     default=None,
    #     description="Start timestamp from which to filter the calls (Unix Timestamp), e.g., '1622547800'",
    # )

    # end_stamp_to: t.Optional[str] = Field(
    #     default=None,
    #     description="End timestamp to which to filter the calls (Unix Timestamp), e.g., '1622549600'",
    # )

    # uuid_array: t.Optional[t.List[str]] = Field(
    #     default=None,
    #     description="Array of UUIDs for filtering multiple calls, e.g., ['123e4567-e89b-12d3-a456-426614174000']",
    # )

    # Extra

    # phone_numbers: t.Optional[t.List[str]] = Field(
    #     default=None,
    #     description="t.List of phone numbers to filter the call history, e.g., ['+1234567890', '+0987654321']",
    # )
    # sub_phone_numbers: t.Optional[t.List[str]] = Field(
    #     default=None,
    #     description="t.List of sub phone numbers to filter the call history, e.g., ['+1234567890-ext123', '+0987654321-ext456']",
    # )
    # from_host: t.Optional[str] = Field(
    #     default=None,
    #     description="The host or source of the call, e.g., 'host1.example.com'",
    # )
    # caller_id_number: t.Optional[str] = Field(
    #     default=None, description="Caller ID number, e.g., '+1234567890'"
    # )
    # caller_id_name: t.Optional[str] = Field(
    #     default=None, description="Caller ID name, e.g., 'John Doe'"
    # )
    # to_host: t.Optional[str] = Field(
    #     default=None,
    #     description="The destination host of the call, e.g., 'host2.example.com'",
    # )
    # destination_number: t.Optional[str] = Field(
    #     default=None,
    #     description="The number the call is directed to, e.g., '+0987654321'",
    # )

    # start_stamp_to: t.Optional[str] = Field(
    #     default=None,
    #     description="End timestamp to which to filter the calls (Unix Timestamp), e.g., '1622548400'",
    # )
    # end_stamp_from: t.Optional[str] = Field(
    #     default=None,
    #     description="Start end timestamp from which to filter the calls (Unix Timestamp), e.g., '1622549000'",
    # )

    # duration_from: t.Optional[int] = Field(
    #     default=None, description="Minimum call duration (in seconds), e.g., 10"
    # )
    # duration_to: t.Optional[int] = Field(
    #     default=None, description="Maximum call duration (in seconds), e.g., 300"
    # )
    # user_talk_time_from: t.Optional[int] = Field(
    #     default=None, description="Minimum user talk time (in seconds), e.g., 5"
    # )
    # user_talk_time_to: t.Optional[int] = Field(
    #     default=None, description="Maximum user talk time (in seconds), e.g., 200"
    # )
    # accountcode: t.Optional[str] = Field(
    #     default=None, description="Account code for the call, e.g., 'ACC123456'"
    # )


class RecordQueryParams(BaseModel):
    duration: t.Optional[int] = None
    operator_code: t.Union[str, int, None] = None
    operator_name: t.Optional[str] = None
    call_type: t.Optional[str] = None
    call_status: t.Optional[str] = None
    client_phone_number: t.Optional[str] = None
    transcript_contains: t.Optional[str] = None


class RecordOrderQueries(BaseModel):
    # Ordering stuff, god forgive me.
    duration_asc: t.Optional[bool | None] = None
    duration_desc: t.Optional[bool | None] = None

    operator_code_asc: t.Union[bool | None] = None
    operator_code_desc: t.Union[bool | None] = None

    operator_name_asc: t.Optional[bool | None] = None
    operator_name_desc: t.Optional[bool | None] = None

    call_type_asc: t.Optional[bool | None] = None
    call_type_desc: t.Optional[bool | None] = None

    call_status_asc: t.Optional[bool | None] = None
    call_status_desc: t.Optional[bool | None] = None

    client_phone_number_asc: t.Optional[bool | None] = None
    client_phone_number_desc: t.Optional[bool | None] = None


class ResultQueryParams(BaseModel):
    is_conversation_over: t.Optional[bool] = None
    sentiment_analysis_of_conversation: t.Optional[str] = None
    sentiment_analysis_of_operator: t.Optional[str] = None
    sentiment_analysis_of_customer: t.Optional[str] = None
    is_customer_satisfied: t.Optional[bool] = None
    is_customer_agreed_to_buy: t.Optional[bool] = None
    is_customer_interested_to_product: t.Optional[bool] = None
    reason_for_customer_purchase: t.Optional[str] = None
    which_platform_customer_found_about_the_course: t.Optional[str] = None
    call_purpose: t.Optional[str] = None


class ResultOrderQueries(BaseModel):
    # Ordering stuff, god forgive me.
    is_conversation_over_asc: t.Optional[bool | None] = None
    is_conversation_over_desc: t.Optional[bool | None] = None

    sentiment_analysis_of_conversation_asc: t.Optional[bool | None] = None
    sentiment_analysis_of_conversation_desc: t.Optional[bool | None] = None

    sentiment_analysis_of_operator_asc: t.Optional[bool | None] = None
    sentiment_analysis_of_operator_desc: t.Optional[bool | None] = None

    sentiment_analysis_of_customer_asc: t.Optional[bool | None] = None
    sentiment_analysis_of_customer_desc: t.Optional[bool | None] = None

    is_customer_satisfied_asc: t.Optional[bool | None] = None
    is_customer_satisfied_desc: t.Optional[bool | None] = None

    is_customer_agreed_to_buy_asc: t.Optional[bool | None] = None
    is_customer_agreed_to_buy_desc: t.Optional[bool | None] = None

    is_customer_interested_to_product_asc: t.Optional[bool | None] = None
    is_customer_interested_to_product_desc: t.Optional[bool | None] = None

    reason_for_customer_purchase_asc: t.Optional[bool | None] = None
    reason_for_customer_purchase_desc: t.Optional[bool | None] = None

    which_platform_customer_found_about_the_course_asc: t.Optional[bool | None] = None
    which_platform_customer_found_about_the_course_desc: t.Optional[bool | None] = None

    call_purpose_asc: t.Optional[bool | None] = None
    call_purpose_desc: t.Optional[bool | None] = None


class FinalCallStatusRequest(BaseModel):
    client_phone_number: str

    @validator("client_phone_number", pre=True, always=True)
    def strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().replace(" ", "")

        return value


class FinalCallStatusResponse(BaseModel):
    class Deal(BaseModel):
        deal_id: str
        title: str
        status: str
        date_created: datetime
        date_closed: t.Optional[datetime]

        @validator("status", pre=True, always=True)
        def strip_whitespace(cls, value: str) -> str:
            if ":" in value:
                for part in value.split(":"):
                    # don't worry about this nested loop
                    for status in ["win", "won", "lost", "lose"]:
                        if status in part:
                            return part

            return value

    client_name: t.Optional[str] = None
    deals: t.Optional[list[Deal]] = []


# ========================================
# Company Management Schemas
# ========================================


class CompanyCreate(BaseModel):
    name: str
    description: t.Optional[str] = None
    parent_company_id: t.Optional[UUID] = None


class CompanyUpdate(BaseModel):
    name: t.Optional[str] = None
    description: t.Optional[str] = None
    is_active: t.Optional[bool] = None


class Company(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: t.Optional[str] = None
    is_active: bool
    parent_company_id: t.Optional[UUID] = None
    hierarchy_level: int
    settings: t.Optional[dict] = None
    balance: int
    created_at: datetime
    updated_at: datetime


class UserTransferRequest(BaseModel):
    user_id: UUID
    from_company_id: UUID


class CompanyAdministrator(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    permissions: t.Optional[dict] = None
    created_at: datetime


# ========================================
# User Management Enhancement Schemas
# ========================================


class UserUpdateRequest(BaseModel):
    email: t.Optional[str] = None
    username: t.Optional[str] = None
    role: t.Optional[str] = None
    company_id: t.Optional[UUID] = None
    is_active: t.Optional[bool] = None
    is_blocked: t.Optional[bool] = None
    preferred_language: t.Optional[str] = None


# ========================================
# Settings Schemas
# ========================================


class UserSettings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    language: str
    timezone: str
    auto_delete_records_after_days: int
    preferred_stt_model: str
    created_at: datetime
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    email_notifications: t.Optional[bool] = None
    sms_notifications: t.Optional[bool] = None
    push_notifications: t.Optional[bool] = None
    language: t.Optional[str] = None
    timezone: t.Optional[str] = None
    auto_delete_records_after_days: t.Optional[int] = None
    preferred_stt_model: t.Optional[str] = None


# ========================================
# AI Chat Schemas
# ========================================


class AIChatSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    record_id: UUID
    session_data: t.Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AIChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class AIChatMessageRequest(BaseModel):
    message: str


class ChatSessionResponse(BaseModel):
    session_id: str
    remaining_questions: int


# ========================================
# Activity Log Schemas
# ========================================


class ActivityLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    details: t.Optional[dict] = None
    ip_address: t.Optional[str] = None
    user_agent: t.Optional[str] = None
    created_at: datetime
