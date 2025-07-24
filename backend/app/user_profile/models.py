import uuid
from typing import TYPE_CHECKING

from datetime import datetime, timezone
from sqlmodel import Field, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func

from backend.app.user_profile.schema import ProfileBaseSchema

if TYPE_CHECKING:
    from backend.app.auth.models import User


class Profile(ProfileBaseSchema, table=True):
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

    # 1 to 1 relationship
    user_id: uuid.UUID = Field(foreign_key="user.id")

    # Profile instance can access it's user via the 'profile'
    # User instance can access it's profile via the 'user'
    user: "User" = Relationship(back_populates="profile")
