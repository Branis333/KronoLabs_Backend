from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    # Primary identifiers
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    is_google_account = Column(Boolean, default=False)    
    
    # Authentication
    password_hash = Column(String(255), nullable=False)
    
    # Basic profile
    fname = Column(String(50), nullable=True, default="")
    lname = Column(String(50), nullable=True, default="")
    full_name = Column(String(255), nullable=True)  # Display name for social media
    bio = Column(Text, nullable=True)  # User bio
    avatar = Column(LargeBinary, nullable=True)  # Profile image as binary data
    profile_image = Column(LargeBinary, nullable=True)  # Additional profile image as binary data
    profile_image_mime_type = Column(String(100), nullable=True)  # MIME type for profile image
    website = Column(Text, nullable=True)  # Optional external link
    
    # Account status
    is_active = Column(Boolean, default=True)
    email_confirmed = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # Verified badge
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Social Media Relationships
    posts = relationship("Post", back_populates="user", lazy="dynamic")
    comments = relationship("Comment", back_populates="user", lazy="dynamic")
    likes = relationship("Like", back_populates="user", lazy="dynamic")
    stories = relationship("Story", back_populates="user", lazy="dynamic")
    story_views = relationship("StoryView", back_populates="user", lazy="dynamic")
    
    # Following/Followers relationships
    following = relationship("Follower", foreign_keys="Follower.follower_id", back_populates="follower_user", lazy="dynamic")
    followers = relationship("Follower", foreign_keys="Follower.following_id", back_populates="following_user", lazy="dynamic")
    
    # Messages
    sent_messages = relationship("DirectMessage", foreign_keys="DirectMessage.sender_id", back_populates="sender", lazy="dynamic")
    received_messages = relationship("DirectMessage", foreign_keys="DirectMessage.receiver_id", back_populates="receiver", lazy="dynamic")
    
    # Notifications and other features
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user", lazy="dynamic")
    saved_posts = relationship("SavedPost", back_populates="user", lazy="dynamic")
    tags = relationship("Tag", back_populates="tagged_user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(username={self.username}, email={self.email})>"