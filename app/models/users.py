from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    PREMIUM = "premium"
    BASIC = "basic"
    AI_AGENT = "ai_agent"  # For AI identities

class SubscriptionTier(str, Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    subscription_tier: SubscriptionTier
    attributes: Dict[str, Any] = Field(default_factory=dict)

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str
    hashed_password: str
    
class User(UserBase):
    id: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 