import uuid
from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import Field, Column, Relationship

from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func
from backend.app.bank_account.schema import BankAccountBaseSchema


if TYPE_CHECKING:
    from backend.app.auth.models import User
    from backend.app.transaction.models import Transaction


class BankAccount(BankAccountBaseSchema, table=True):
    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
        ),
        default_factory=uuid.uuid4,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=func.current_timestamp(),
        ),
    )

    kyc_verified_on: datetime | None = Field(
        default=None,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")

    user: "User" = Relationship(back_populates="bank_accounts")

    sent_transactions: list["Transaction"] = Relationship(
        back_populates="sender_account",
        sa_relationship_kwargs={"foreign_keys": "Transaction.sender_account_id"},
    )

    received_transactions: list["Transaction"] = Relationship(
        back_populates="receiver_account",
        sa_relationship_kwargs={"foreign_keys": "Transaction.receiver_account_id"},
    )
