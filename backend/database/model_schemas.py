from tortoise.contrib.pydantic import pydantic_model_creator

from backend.database.models import (
    Account,
    Record,
    Transaction,
    Checklist,
    Result,
    OperatorData,
)

AccountPydantic = pydantic_model_creator(Account)
RecordPydantic = pydantic_model_creator(Record)
TransactionPydantic = pydantic_model_creator(Transaction)
ChecklistPydantic = pydantic_model_creator(Checklist)
ResultPydantic = pydantic_model_creator(Result)
OperatorDataPydantic = pydantic_model_creator(OperatorData)
