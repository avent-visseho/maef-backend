# ===================================
# app/schemas/user.py
# ===================================
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from enum import Enum

from app.models.address import AddressType


class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        return v


class Role(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class Permission(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class User(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    roles: List[Role] = []
    
    class Config:
        from_attributes = True


class UserInDB(User):
    password_hash: str


# Schémas pour l'authentification
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    data: Token


class UserResponse(BaseModel):
    success: bool = True
    message: str
    data: User


class UsersListResponse(BaseModel):
    success: bool = True
    data: List[User]
    total: int
    page: int
    per_page: int


class UserRoleAssignment(BaseModel):
    role_ids: List[int]


# Schémas pour les adresses
class AddressBase(BaseModel):
    kind: AddressType = AddressType.BOTH
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str
    zip_code: str
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    kind: Optional[AddressType] = None
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    is_default: Optional[bool] = None


class Address(AddressBase):
    id: int
    user_id: int
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True