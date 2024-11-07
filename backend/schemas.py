import typing as t
from uuid import UUID, uuid4
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StringConstraints,
    root_validator,
    ConfigDict,
)


class UserCreate(BaseModel):
    role: str
    password: str
    email: EmailStr
    company_name: str
    id: UUID = Field(default_factory=uuid4)
    username: t.Annotated[str, StringConstraints(min_length=3, max_length=255)]


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    role: str
    company_name: str
    created_at: datetime
    updated_at: datetime


class UserPrivate(User):
    password: str


class CheckList(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    payload: t.Union[t.List[str], t.Dict[str, t.List[str]]] = []
    active: bool = False
    deleted_at: str = ""

    @root_validator(pre=True)
    def validate_payload(cls, values):
        payload = values.get("payload")
        # title = values.get("title")

        if isinstance(payload, list):
            values["payload"] = {"segment_1": payload}

        elif isinstance(payload, dict):
            for key, segment in payload.items():
                if not isinstance(segment, list) or not all(
                    isinstance(i, str) for i in segment
                ):
                    raise ValueError(f"Segment {key=} must be a list of strings")

        return values


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
    deleted_at: datetime = None


class ReprocessRecord(BaseModel):
    record_id: str
    checklist_id: str = None
    general: bool = False


class OperatorData(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    code: int
    name: str
    deleted_at: datetime = None


class PBXCallHistoryRequest(BaseModel):
    checklist_id: t.Optional[str] = Field(
        default=None,
        description="Unique identifier for the checklist, e.g., '213e4567-e89b-12d3-a456-426614174000'",
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
    title: t.Optional[str] = None
    duration: t.Optional[int] = None
    operator_code: t.Union[str, int, None] = None
    operator_name: t.Optional[str] = None
    call_type: t.Optional[str] = None
    call_status: t.Optional[str] = None
    client_phone_number: t.Optional[str] = None


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
