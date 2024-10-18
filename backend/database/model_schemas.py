from tortoise.contrib.pydantic import pydantic_model_creator, pydantic_queryset_creator

from backend.database.models import (
    Account,
    Record,
    Transaction,
    Checklist,
    Result,
    OperatorData,
)

AccountPydantic = pydantic_model_creator(Account)
AccountPydanticList = pydantic_queryset_creator(Account)

RecordPydantic = pydantic_model_creator(Record)
RecordPydanticList = pydantic_queryset_creator(Record)

TransactionPydantic = pydantic_model_creator(Transaction)
RecordPydanticList = pydantic_queryset_creator(Record)

ChecklistPydantic = pydantic_model_creator(Checklist)
ChecklistPydanticList = pydantic_queryset_creator(Checklist)

ResultPydantic = pydantic_model_creator(Result)
ResultPydanticList = pydantic_queryset_creator(Result)

OperatorDataPydantic = pydantic_model_creator(OperatorData)
OperatorDataPydanticList = pydantic_queryset_creator(OperatorData)
