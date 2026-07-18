from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class UserCreate(ORMModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(ORMModel):
    is_active: bool | None = None


class UserRead(ORMModel):
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime
