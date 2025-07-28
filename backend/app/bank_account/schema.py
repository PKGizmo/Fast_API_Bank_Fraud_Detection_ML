from datetime import datetime
from uuid import UUID

from backend.app.bank_account.enums import (
    AccountCurrencyEnum,
    BankAccountStatusEnum,
    AccountTypeEnum,
)

from sqlmodel import Field, SQLModel


class BankAccountBaseSchema(SQLModel):
    account_type: AccountTypeEnum
    currency: AccountCurrencyEnum
    account_status: BankAccountStatusEnum = Field(default=BankAccountStatusEnum.Pending)
    account_number: str | None = Field(default=None, unique=True, index=True)
    account_name: str
    account_balance: float = Field(default=0.0)
    is_primary: bool = Field(default=False)
    kyc_submitted: bool = Field(default=False)
    kyc_verified: bool = Field(default=False)
    kyc_verified_by: UUID | None = Field(default=None)
    interest_rate: float = Field(default=0.0)


class BankAccountCreateSchema(BankAccountBaseSchema):
    account_number: str | None = None


class BankAccountReadSchema(BankAccountBaseSchema):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class BankAccountUpdateSchema(BankAccountBaseSchema):
    account_name: str | None = None
    is_primary: bool | None = None
    account_status: BankAccountStatusEnum | None = None
