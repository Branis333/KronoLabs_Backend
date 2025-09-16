from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, LargeBinary
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
    media_data = Column(LargeBinary, nullable=True)  # Store image/video as binary data
    media_mime_type = Column(String(100), nullable=True)  # MIME type of the media
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
    media_data = Column(LargeBinary, nullable=False)  # Store media as binary data
    media_mime_type = Column(String(100), nullable=False)  # MIME type of the media
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
    media_data = Column(LargeBinary, nullable=True)  # Store media as binary data
    media_mime_type = Column(String(100), nullable=True)  # MIME type of the media
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
    media_data = Column(LargeBinary, nullable=True)  # Store media as binary data
    media_mime_type = Column(String(100), nullable=True)  # MIME type of the media
    
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

class Comic(Base):
    __tablename__ = "comics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_data = Column(LargeBinary, nullable=False)  # Thumbnail image as binary
    thumbnail_mime_type = Column(String(100), nullable=False)  # MIME type of thumbnail
    genre = Column(String(100), nullable=True)  # e.g., "Action", "Comedy", "Drama"
    status = Column(String(50), nullable=False, default="ongoing")  # "ongoing", "completed", "hiatus"
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="comics")
    pages = relationship("ComicPage", back_populates="comic", cascade="all, delete-orphan", order_by="ComicPage.page_number")
    likes = relationship("ComicLike", back_populates="comic", cascade="all, delete-orphan")
    comments = relationship("ComicComment", back_populates="comic", cascade="all, delete-orphan")
    saved_by = relationship("SavedComic", back_populates="comic", cascade="all, delete-orphan")

class ComicPage(Base):
    __tablename__ = "comic_pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comic_id = Column(UUID(as_uuid=True), ForeignKey('comics.id'), nullable=False)
    page_number = Column(Integer, nullable=False)  # Sequential page number
    page_data = Column(LargeBinary, nullable=False)  # Page image as binary data
    page_mime_type = Column(String(100), nullable=False)  # MIME type of the page image
    page_title = Column(String(255), nullable=True)  # Optional title for the page
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    comic = relationship("Comic", back_populates="pages")

class ComicLike(Base):
    __tablename__ = "comic_likes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    comic_id = Column(UUID(as_uuid=True), ForeignKey('comics.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="comic_likes")
    comic = relationship("Comic", back_populates="likes")

class ComicComment(Base):
    __tablename__ = "comic_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comic_id = Column(UUID(as_uuid=True), ForeignKey('comics.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey('comic_comments.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    comic = relationship("Comic", back_populates="comments")
    user = relationship("User", back_populates="comic_comments")
    parent_comment = relationship("ComicComment", remote_side=[id], backref="replies")

class SavedComic(Base):
    __tablename__ = "saved_comics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    comic_id = Column(UUID(as_uuid=True), ForeignKey('comics.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_comics")
    comic = relationship("Comic", back_populates="saved_by")

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Thumbnail storage (multiple sizes like YouTube)
    thumbnail_small_data = Column(LargeBinary, nullable=True)  # 320x180
    thumbnail_medium_data = Column(LargeBinary, nullable=True)  # 480x270  
    thumbnail_large_data = Column(LargeBinary, nullable=False)  # 640x360
    thumbnail_mime_type = Column(String(100), nullable=False, default="image/jpeg")
    
    # Video metadata
    original_filename = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    original_resolution = Column(String(50), nullable=True)  # e.g. "1920x1080"
    fps = Column(Integer, nullable=True)
    
    # Content metadata  
    category = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)  # JSON string of tags
    is_public = Column(Boolean, default=True)
    
    # Analytics
    view_count = Column(Integer, default=0)
    processing_status = Column(String(50), default="processing")  # processing, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="videos")
    video_qualities = relationship("VideoQuality", back_populates="video", cascade="all, delete-orphan")
    likes = relationship("VideoLike", back_populates="video", cascade="all, delete-orphan")
    comments = relationship("VideoComment", back_populates="video", cascade="all, delete-orphan")
    saved_by = relationship("SavedVideo", back_populates="video", cascade="all, delete-orphan")

class VideoQuality(Base):
    __tablename__ = "video_qualities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False)
    
    # Quality metadata
    quality = Column(String(10), nullable=False)  # 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p
    resolution = Column(String(20), nullable=False)  # 1920x1080
    bitrate = Column(String(20), nullable=False)  # 3000k
    codec = Column(String(50), nullable=False)  # libx264, libvp9
    fps = Column(Integer, nullable=False)
    
    # Segmentation info
    is_segmented = Column(Boolean, default=True)
    segment_duration = Column(Integer, default=4)  # seconds per segment
    total_segments = Column(Integer, nullable=True)
    
    # Storage info
    total_size = Column(Integer, nullable=True)  # Total size of all segments in bytes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="video_qualities")
    segments = relationship("VideoSegment", back_populates="video_quality", cascade="all, delete-orphan")

class VideoSegment(Base):
    __tablename__ = "video_segments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_quality_id = Column(UUID(as_uuid=True), ForeignKey('video_qualities.id'), nullable=False)
    
    # Segment info
    segment_index = Column(Integer, nullable=False)  # 0, 1, 2, 3...
    segment_data = Column(LargeBinary, nullable=False)  # Binary video segment
    segment_size = Column(Integer, nullable=False)  # Size in bytes
    duration = Column(Integer, nullable=False)  # Duration in seconds
    
    # Metadata for streaming
    start_time = Column(Integer, nullable=False)  # Start time in seconds
    end_time = Column(Integer, nullable=False)  # End time in seconds
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships  
    video_quality = relationship("VideoQuality", back_populates="segments")

class VideoLike(Base):
    __tablename__ = "video_likes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="video_likes")
    video = relationship("Video", back_populates="likes")

class VideoComment(Base):
    __tablename__ = "video_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey('video_comments.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="comments")
    user = relationship("User", back_populates="video_comments")
    parent_comment = relationship("VideoComment", remote_side=[id], backref="replies")

class SavedVideo(Base):
    __tablename__ = "saved_videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey('videos.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="saved_videos")
    video = relationship("Video", back_populates="saved_by")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reported_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=True)
    comic_id = Column(UUID(as_uuid=True), ForeignKey('comics.id'), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    post = relationship("Post")
    comic = relationship("Comic")
