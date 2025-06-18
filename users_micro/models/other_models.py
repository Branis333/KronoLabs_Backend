from sqlalchemy import Table, MetaData
from db.database import engine

# Import all models for KronoLabs Social Media App
from .users_models import User, Base
from .social_models import (
    Post, PostMedia, Comment, Like, Follower, Story, StoryView,
    DirectMessage, Notification, SavedPost, Tag, Hashtag, Report,
    MediaType, PostVisibility, NotificationType, ReportStatus
)

# Reflect the existing tables
metadata = MetaData()

# Import gamification tables to use in this micro service
Rank = Table('ranks', metadata, autoload_with=engine)
Achievement = Table('achievements', metadata, autoload_with=engine)
UserProgress = Table('user_progress', metadata, autoload_with=engine)
UserAchievement = Table('user_achievements', metadata, autoload_with=engine)
XPTransaction = Table('xp_transactions', metadata, autoload_with=engine)

# Export all tables
__all__ = [
    'User', 'Base', 'Rank', 'Achievement', 'UserProgress', 
    'UserAchievement', 'XPTransaction', 'metadata',
    'Post', 'PostMedia', 'Comment', 'Like', 'Follower', 'Story', 'StoryView',
    'DirectMessage', 'Notification', 'SavedPost', 'Tag', 'Hashtag', 'Report',
    'MediaType', 'PostVisibility', 'NotificationType', 'ReportStatus'
]