from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(..., min_length=8)

class UserOAuthCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    oauth_provider: str
    oauth_id: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    is_verified: bool

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenPayload(BaseModel):
    sub: str
    exp: Optional[int] = None
    type: Optional[str] = None