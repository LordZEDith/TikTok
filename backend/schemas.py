from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class ModerationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class InteractionType(str, Enum):
    view = "view"
    like = "like"
    comment = "comment"
    share = "share"

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    profile_picture_url: Optional[HttpUrl] = None
    bio: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserOut(UserBase):
    user_id: str
    profile_picture_url: Optional[HttpUrl] = None
    bio: Optional[str] = None
    created_at: datetime
    is_active: bool
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None

class VideoCreate(VideoBase):
    pass

class VideoOut(VideoBase):
    video_id: str
    user_id: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime
    view_count: int
    like_count: int
    comment_count: int
    moderation_status: ModerationStatus

    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    content: str

class CommentCreate(BaseModel):
    content: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "content": "Great video!"
            }
        }

class CommentOut(CommentBase):
    comment_id: str
    video_id: str
    user_id: str
    created_at: datetime
    like_count: int
    moderation_status: ModerationStatus

    class Config:
        from_attributes = True

class LikeCreate(BaseModel):
    video_id: str

class LikeOut(BaseModel):
    like_id: str
    user_id: str
    video_id: str
    created_at: datetime

    class Config:
        from_attributes = True 