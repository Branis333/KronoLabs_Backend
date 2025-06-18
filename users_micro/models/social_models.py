from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import enum
from .users_models import Base

# Enums for different field types
class MediaType(enum.Enum):
    image = "image"
    video = "video"
    carousel = "carousel"

class PostVisibility(enum.Enum):
    public = "public"
    private = "private"
    followers_only = "followers_only"

class NotificationType(enum.Enum):
    like = "like"
    comment = "comment"
    follow = "follow"
    mention = "mention"
    dm = "dm"

class ReportStatus(enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    action_taken = "action_taken"

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    caption = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    media_type = Column(SQLEnum(MediaType), nullable=False, default=MediaType.image)
    location = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    visibility = Column(SQLEnum(PostVisibility), default=PostVisibility.public)
    
    # Relationships
    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    post_media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")
    saved_by = relationship("SavedPost", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="post", cascade="all, delete-orphan")
    hashtags = relationship("Hashtag", back_populates="post", cascade="all, delete-orphan")

class PostMedia(Base):
    __tablename__ = "post_media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    media_url = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False)
    
    # Relationships
    post = relationship("Post", back_populates="post_media")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey('comments.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id], backref="replies")

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

class Follower(Base):
    __tablename__ = "followers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    following_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    follower_user = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following_user = relationship("User", foreign_keys=[following_id], back_populates="followers")

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=True)  # For text-only stories or text with media
    media_url = Column(Text, nullable=True)  # Now nullable since stories can be text-only
    media_type = Column(SQLEnum(MediaType), nullable=True)  # Now nullable since stories can be text-only
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    view_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    views = relationship("StoryView", back_populates="story", cascade="all, delete-orphan")

class StoryView(Base):
    __tablename__ = "story_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey('stories.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    story = relationship("Story", back_populates="views")
    user = relationship("User", back_populates="story_views")

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_text = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)  # For uploaded images/videos
    
    # For sharing posts and stories
    shared_post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=True)
    shared_story_id = Column(UUID(as_uuid=True), ForeignKey('stories.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    shared_post = relationship("Post", foreign_keys=[shared_post_id])
    shared_story = relationship("Story", foreign_keys=[shared_story_id])

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(SQLEnum(NotificationType), nullable=False)
    from_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)  # Can reference post, comment, message, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    from_user = relationship("User", foreign_keys=[from_user_id])

class SavedPost(Base):
    __tablename__ = "saved_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_posts")
    post = relationship("Post", back_populates="saved_by")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    tagged_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="tags")
    tagged_user = relationship("User", back_populates="tags")

class Hashtag(Base):
    __tablename__ = "hashtags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False)
    hashtag = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="hashtags")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reported_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    post = relationship("Post")
