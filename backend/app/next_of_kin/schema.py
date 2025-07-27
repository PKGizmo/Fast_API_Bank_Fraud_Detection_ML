import uuid
from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from pydantic_extra_types.country import CountryShortName
from pydantic_extra_types.phone_numbers import PhoneNumber
from backend.app.next_of_kin.enums import RelationshipTypeEnum


class NextOfKinBaseSchema(SQLModel):
    full_name: str = Field(min_length=2, max_length=100)
    relationship: RelationshipTypeEnum
    email: EmailStr
    phone_number: PhoneNumber
    address: str
    city: str
    country: CountryShortName
    nationality: str
    id_number: str | None = None
    passport_number: str | None = None
    is_primary: bool = Field(default=False)


class NextOfKinCreateSchema(NextOfKinBaseSchema):
    pass


class NextOfKinReadSchema(NextOfKinBaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
