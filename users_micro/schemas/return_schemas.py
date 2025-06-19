from pydantic import BaseModel, EmailStr,validator,Field
from typing import List, Optional, Literal
from datetime import date,datetime

class ReturnUser(BaseModel):
    # Primary identifiers
    id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_google_account: Optional[bool] = None

    # Basic profile
    fname: Optional[str] = None
    lname: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    profile_image_url: Optional[str] = None
    website: Optional[str] = None

    # Account status
    is_active: Optional[bool] = None
    email_confirmed: Optional[bool] = None
    is_verified: Optional[bool] = None

    # Timestamps
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True
