import uuid
from tortoise import fields
from tortoise.models import Model


class Account(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    email = fields.CharField(max_length=255, unique=True)
    username = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)
    role = fields.CharField(max_length=255)
    company_name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class PydanticMeta:
        exclude = ("password",)


class Record(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    owner = fields.ForeignKeyField("models.Account", related_name="records")
    title = fields.CharField(max_length=255)
    duration = fields.BigIntField(null=True)
    payload = fields.JSONField(null=True)
    operator_code = fields.CharField(max_length=255, null=True)
    operator_name = fields.CharField(max_length=255, null=True)
    call_type = fields.CharField(max_length=255, null=True)
    source = fields.CharField(max_length=255, null=True)
    status = fields.CharField(max_length=255, null=True)
    storage_id = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)


class Transaction(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    owner = fields.ForeignKeyField("models.Account", related_name="transactions")
    amount = fields.BigIntField()
    type = fields.CharField(max_length=255)
    record = fields.ForeignKeyField(
        "models.Record", related_name="transactions", null=True
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Checklist(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    owner = fields.ForeignKeyField("models.Account", related_name="checklists")
    title = fields.CharField(max_length=255)
    payload = fields.JSONField(null=True)
    active = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)


class Result(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    owner = fields.ForeignKeyField("models.Account", related_name="results")
    record = fields.ForeignKeyField("models.Record", related_name="results")
    checklist = fields.ForeignKeyField(
        "models.Checklist", related_name="results", null=True
    )
    operator_answer_delay = fields.BigIntField(null=True)
    operator_speech_duration = fields.BigIntField(null=True)
    customer_speech_duration = fields.BigIntField(null=True)
    is_conversation_over = fields.BooleanField(null=True)
    sentiment_analysis_of_conversation = fields.CharField(max_length=255, null=True)
    sentiment_analysis_of_operator = fields.CharField(max_length=255, null=True)
    sentiment_analysis_of_customer = fields.CharField(max_length=255, null=True)
    is_customer_satisfied = fields.BooleanField(null=True)
    is_customer_agreed_to_buy = fields.BooleanField(null=True)
    is_customer_interested_to_product = fields.BooleanField(null=True)
    which_course_customer_interested = fields.CharField(max_length=255, null=True)
    summary = fields.CharField(max_length=255, null=True)
    customer_gender = fields.CharField(max_length=255, null=True)
    checklist_result = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)


class OperatorData(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    owner = fields.ForeignKeyField("models.Account", related_name="operator_data")
    code = fields.IntField()
    name = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)
