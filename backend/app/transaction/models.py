import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Column, Relationship, SQLModel
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func

from backend.app.transaction.schema import TransactionBaseSchema
from sqlalchemy.dialects.postgresql import JSONB

# To avoid circular imports
if TYPE_CHECKING:
    from backend.app.auth.models import User
    from backend.app.bank_account.models import BankAccount


class Transaction(TransactionBaseSchema, table=True):
    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
        ),
        default_factory=uuid.uuid4,
    )
    sender_account_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="bankaccount.id",
    )
    receiver_account_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="bankaccount.id",
    )

    sender_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    receiver_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    processed_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=True,
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

    transaction_metadata: dict | None = Field(default=None, sa_column=Column(JSONB))

    sender_account: "BankAccount" = Relationship(
        back_populates="sent_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.sender_account_id"},
    )
    receiver_account: "BankAccount" = Relationship(
        back_populates="received_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.receiver_account_id"},
    )

    sender: "User" = Relationship(
        back_populates="sent_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.sender_id"},
    )
    receiver: "User" = Relationship(
        back_populates="received_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.receiver_id"},
    )
    processor: "User" = Relationship(
        back_populates="processed_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.processed_by"},
    )


class IdempotencyKey(SQLModel, table=True):
    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
        ),
        default_factory=uuid.uuid4,
    )

    key: str = Field(index=True, unique=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")

    # This will help to identify which API call the key is related to
    endpoint: str

    # Will store the response code of the original request
    # so that the same response can be returned after duplicated call
    response_code: int

    # Will store the same response in the database
    # so that it can be returned after duplicated call without reprocessing the request
    response_body: dict = Field(sa_column=Column(JSONB))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    # Time at which Idempotency Key expires so that it cannot be reused indefinitely
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
        ),
    )
