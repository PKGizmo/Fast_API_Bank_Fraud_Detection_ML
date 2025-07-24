from enum import Enum
from sqlmodel import SQLModel, Field
from datetime import date
from pydantic_extra_types.country import CountryShortName
from pydantic_extra_types.phone_numbers import PhoneNumber

# from pydantic import field_validator

# from backend.app.user_profile import validate_id_dates


class SalutationSchema(str, Enum):
    Mr = "Mr"
    Mrs = "Mrs"
    Miss = "Miss"


class GenerSchema(str, Enum):
    Male = "Male"
    Female = "Female"


class MaritalStatusSchema(str, Enum):
    Married = "Married"
    Divorced = "Divorced"
    Single = "Single"
    Widowed = "Widowed"


class IdentificationTypeSchema(str, Enum):
    Passport = "Passport"
    Drivers_License = "Drivers_License"
    National_ID = "National_ID"


class EmployementStatusSchema(str, Enum):
    Employed = "Employed"
    Unemployed = "Unemployed"
    Self_Employed = "Self_Employed"
    Student = "Student"
    Retired = "Retired"


class ProfileBaseSchema(SQLModel):
    title: SalutationSchema
    gender: GenerSchema
    date_of_birth: date
    country_of_birth: CountryShortName
    place_of_birth: str
    marital_status: MaritalStatusSchema
    means_of_identification: IdentificationTypeSchema
    id_issue_date: date
    id_expiry_date: date
    passport_number: str
    nationality: str
    phone_number: PhoneNumber
    address: str
    city: str
    country: str
    employement_status: EmployementStatusSchema
    employer_name: str
    employer_address: str
    employer_country: CountryShortName
    annual_income: float
    date_of_employement: date
    profile_photo_url: str | None = Field(default=None)
    id_photo_url: str | None = Field(default=None)
    signature_photo_url: str | None = Field(default=None)
