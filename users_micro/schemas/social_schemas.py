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
    profile_image: Optional[str] = None  # Base64 encoded image data
    profile_image_mime_type: Optional[str] = None
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
    media_data: str  # Base64 encoded media data
    media_mime_type: str
    media_type: MediaType
    order_index: int = 0

class PostCreate(BaseModel):
    caption: Optional[str] = None
    media_files: Optional[List[PostMediaCreate]] = []  # For multiple media files
    media_data: Optional[str] = None  # Base64 encoded media data
    media_mime_type: Optional[str] = None
    media_type: MediaType = MediaType.image
    location: Optional[str] = None
    visibility: PostVisibility = PostVisibility.public
    hashtags: Optional[List[str]] = []
    tagged_users: Optional[List[int]] = []

class PostMediaSchema(BaseModel):
    id: UUID4
    media_data: str  # Base64 encoded media data
    media_mime_type: str
    order_index: int
    media_type: MediaType
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    caption: Optional[str]
    media_data: Optional[str]  # Base64 encoded media data
    media_mime_type: Optional[str]
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
    media_data: Optional[str] = None  # Base64 encoded media data
    media_mime_type: Optional[str] = None
    media_type: Optional[MediaType] = None

class StoryResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    text: Optional[str] = None
    media_data: Optional[str] = None  # Base64 encoded media data
    media_mime_type: Optional[str] = None
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
    media_data: Optional[str] = None  # Base64 encoded media data
    media_mime_type: Optional[str] = None
    shared_post_id: Optional[UUID4] = None
    shared_story_id: Optional[UUID4] = None

class MessageResponse(BaseModel):
    id: UUID4
    sender_id: int
    receiver_id: int
    sender: UserProfile
    receiver: UserProfile
    message_text: Optional[str]
    media_data: Optional[str]  # Base64 encoded media data
    media_mime_type: Optional[str]
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

# Comic Schemas
class ComicPageCreate(BaseModel):
    page_data: str  # Base64 encoded page image
    page_mime_type: str
    page_title: Optional[str] = None

class ComicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    thumbnail_data: str  # Base64 encoded thumbnail image
    thumbnail_mime_type: str
    genre: Optional[str] = None
    status: str = "ongoing"  # "ongoing", "completed", "hiatus"
    is_public: bool = True
    pages: List[ComicPageCreate] = []

class ComicPageResponse(BaseModel):
    id: UUID4
    page_number: int
    page_data: str  # Base64 encoded page image
    page_mime_type: str
    page_title: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ComicResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    title: str
    description: Optional[str]
    thumbnail_data: str  # Base64 encoded thumbnail
    thumbnail_mime_type: str
    genre: Optional[str]
    status: str
    is_public: bool
    created_at: datetime
    updated_at: datetime
    pages_count: Optional[int] = 0
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    is_liked: Optional[bool] = False
    is_saved: Optional[bool] = False
    pages: Optional[List[ComicPageResponse]] = []
    
    class Config:
        from_attributes = True

class ComicCommentCreate(BaseModel):
    text: str
    parent_comment_id: Optional[UUID4] = None

class ComicCommentResponse(BaseModel):
    id: UUID4
    comic_id: UUID4
    user_id: int
    user: UserProfile
    text: str
    parent_comment_id: Optional[UUID4]
    created_at: datetime
    replies_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ComicUpdateStatus(BaseModel):
    status: str = Field(..., pattern="^(ongoing|completed|hiatus)$")

class ComicUpdateInfo(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = None
    is_public: Optional[bool] = None

class ComicsResponse(BaseModel):
    comics: List[ComicResponse]
    has_next: bool = False
    total_count: Optional[int] = None

# Video Schemas
class VideoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    thumbnail_data: str  # Base64 encoded thumbnail image
    thumbnail_mime_type: str
    video_url: str  # Google Drive URL
    video_filename: Optional[str] = None
    duration: Optional[int] = None  # Duration in seconds
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    is_public: bool = True

class VideoResponse(BaseModel):
    id: UUID4
    user_id: int
    user: UserProfile
    title: str
    description: Optional[str]
    thumbnail_data: Optional[str]  # Base64 encoded thumbnail
    thumbnail_mime_type: Optional[str] = "image/jpeg"
    
    # YouTube-style metadata  
    original_filename: Optional[str]
    original_resolution: Optional[str]
    fps: Optional[int]
    duration: Optional[int]
    processing_status: Optional[str] = "completed"
    
    # Content metadata
    category: Optional[str]
    tags: Optional[List[str]] = []
    is_public: bool = True
    view_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Engagement
    likes_count: Optional[int] = 0
    comments_count: Optional[int] = 0
    is_liked: Optional[bool] = False
    is_saved: Optional[bool] = False
    
    # YouTube-style streaming info
    streaming_url: Optional[str] = None
    available_qualities: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

class VideoCommentCreate(BaseModel):
    text: str
    parent_comment_id: Optional[UUID4] = None

class VideoCommentResponse(BaseModel):
    id: UUID4
    video_id: UUID4
    user_id: int
    user: UserProfile
    text: str
    parent_comment_id: Optional[UUID4]
    created_at: datetime
    replies_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class VideoUpdateInfo(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None

class VideosResponse(BaseModel):
    videos: List[VideoResponse]
    has_next: bool = False
    total_count: Optional[int] = None

# Response Schemas
class SuccessResponse(BaseModel):
    success: bool = True
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[str] = None
