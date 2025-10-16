from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, constr


class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8) = Field(..., description="Password, at least 8 characters")
# можно заменить на Annotated[str, StringConstraints(min_length=8)]


class UserOut(BaseModel):
    id: str
    email: EmailStr


class UserLogin(BaseModel):
    username: EmailStr = Field(..., description="Email пользователя для входа")
    password: str = Field(..., min_length=1, description="Пароль пользователя")
    
    class Config:
        # Позволяет использовать с form-data
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
