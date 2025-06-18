from pydantic import BaseModel, Field, UUID4
from typing import List, Optional, Union
from datetime import datetime
from enum import Enum

# Enums
class MediaType(str, Enum):
    image = "image"
    video = "video"
    carousel = "carousel"

class PostVisibility(str, Enum):
    public = "public"
    private = "private"
    followers_only = "followers_only"

class NotificationType(str, Enum):
    like = "like"
    comment = "comment"
    follow = "follow"
    mention = "mention"
    dm = "dm"

class ReportStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    action_taken = "action_taken"

# Base User Schemas
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    website: Optional[str] = None

class UserProfile(UserBase):
    id: int
    is_verified: bool = False
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    posts_count: Optional[int] = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

# Post Schemas
class PostMediaCreate(BaseModel):
    media_url: str
    media_type: MediaType
    order_index: int = 0

class PostCreate(BaseModel):
    caption: Optional[str] = None
    media_files: Optional[List[PostMediaCreate]] = []  # For multiple media files
    media_url: Optional[str] = None  # For backward compatibility
    media_type: MediaType = MediaType.image
    location: Optional[str] = None
    visibility: PostVisibility = PostVisibility.public
    hashtags: Optional[List[str]] = []
    tagged_users: Optional[List[int]] = []

class PostMediaSchema(BaseModel):
    id: UUID4
    media_url: str
    order_index: int
    media_type: MediaType
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    caption: Optional[str]
    media_url: Optional[str]
    media_type: MediaType
    location: Optional[str]
    visibility: PostVisibility
    created_at: datetime
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    is_liked: Optional[bool] = False
    is_saved: Optional[bool] = False
    post_media: Optional[List[PostMediaSchema]] = []
    hashtags: Optional[List[str]] = []
    
    class Config:
        from_attributes = True

# Comment Schemas
class CommentCreate(BaseModel):
    text: str
    parent_comment_id: Optional[UUID4] = None

class CommentResponse(BaseModel):
    id: UUID4
    post_id: UUID4
    user_id: int
    user: UserProfile
    text: str
    parent_comment_id: Optional[UUID4]
    created_at: datetime
    replies_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Story Schemas
class StoryCreate(BaseModel):
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[MediaType] = None

class StoryResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[MediaType] = None
    created_at: datetime
    expires_at: datetime
    view_count: int = 0
    is_viewed: Optional[bool] = False
    
    class Config:
        from_attributes = True

# Direct Message Schemas
class MessageCreate(BaseModel):
    receiver_id: int
    message_text: Optional[str] = None
    media_url: Optional[str] = None
    shared_post_id: Optional[UUID4] = None
    shared_story_id: Optional[UUID4] = None

class MessageResponse(BaseModel):
    id: UUID4
    sender_id: int
    receiver_id: int
    sender: UserProfile
    receiver: UserProfile
    message_text: Optional[str]
    media_url: Optional[str]
    shared_post_id: Optional[UUID4] = None
    shared_story_id: Optional[UUID4] = None
    shared_post: Optional["PostResponse"] = None
    shared_story: Optional["StoryResponse"] = None
    created_at: datetime
    is_read: bool
    
    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    user: UserProfile
    last_message: Optional[MessageResponse]
    unread_count: int = 0

# Notification Schemas
class NotificationResponse(BaseModel):
    id: UUID4
    user_id: int
    type: NotificationType
    from_user_id: Optional[int]
    from_user: Optional[UserProfile]
    entity_id: Optional[UUID4]
    created_at: datetime
    is_read: bool
    
    class Config:
        from_attributes = True

# Follow Schemas
class FollowResponse(BaseModel):
    id: UUID4
    follower_id: int
    following_id: int
    follower: UserProfile
    following: UserProfile
    created_at: datetime
    
    class Config:
        from_attributes = True

# Search and Discovery Schemas
class SearchResponse(BaseModel):
    users: List[UserProfile] = []
    posts: List[PostResponse] = []
    hashtags: List[str] = []

class HashtagResponse(BaseModel):
    hashtag: str
    posts_count: int
    posts: List[PostResponse] = []

# Report Schemas
class ReportCreate(BaseModel):
    reported_user_id: Optional[int] = None
    post_id: Optional[UUID4] = None
    reason: str

class ReportResponse(BaseModel):
    id: UUID4
    reporter_id: int
    reported_user_id: Optional[int]
    post_id: Optional[UUID4]
    reason: str
    status: ReportStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

# Feed Schemas
class FeedResponse(BaseModel):
    posts: List[PostResponse]
    has_next: bool = False
    next_cursor: Optional[str] = None

# Analytics Schemas (for future use)
class PostAnalytics(BaseModel):
    post_id: UUID4
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0

class UserAnalytics(BaseModel):
    user_id: int
    followers_gained: int = 0
    posts_created: int = 0
    total_likes: int = 0
    total_comments: int = 0
    profile_views: int = 0

# Response Schemas
class SuccessResponse(BaseModel):
    success: bool = True
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[str] = None
