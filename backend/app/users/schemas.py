from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.common.enums import UserRole


class PermissionSchema(BaseModel):
    name: str
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class RoleSchema(BaseModel):
    name: UserRole
    permissions: list[PermissionSchema]
    model_config = ConfigDict(
        from_attributes=True, str_strip_whitespace=True, use_enum_values=True
    )


class UserBase(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    phone: str | None = None


class UserCreate(UserBase):
    """Schema for registration - requires a password."""

    password: str


class User(UserBase):
    """Schema for returning user data - excludes password."""

    id: int
    role: RoleSchema
    date_created: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class UserInDB(User):
    """Internal schema that includes the hashed password."""

    hashed_password: str
