"""
Instagram-like Stories API

This module provides comprehensive story management functionality similar to Instagram:

Features:
- Create stories with uploaded media files (images/videos) from device
- 24-hour auto-expiry (like Instagram stories)
- View tracking and analytics
- Get stories feed from followed users
- View specific user's stories
- Delete own stories
- Story viewer lists

Media Requirements:
- Images: JPEG, PNG, GIF, WebP, BMP, TIFF (max 10MB)
- Videos: MP4, MPEG, QuickTime, AVI, WebM, OGG, 3GP (max 50MB for stories)
- Files are uploaded directly from user's device
- Automatic media type detection and validation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Story, StoryView, Follower
from schemas.social_schemas import (
    StoryCreate, StoryResponse, SuccessResponse, UserProfile, MediaType
)
from utils.media_utils import MediaUtils
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import base64

# Helper function to create user profile with binary data
def create_user_profile(user: User) -> UserProfile:
    """Create UserProfile with base64 encoded images from binary data"""
    profile_image = None
    if user.profile_image and user.profile_image_mime_type:
        profile_image = base64.b64encode(user.profile_image).decode('utf-8')
    
    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        bio=user.bio,
        profile_image=profile_image,
        profile_image_mime_type=user.profile_image_mime_type,
        website=user.website,
        is_verified=user.is_verified,
        followers_count=user.followers_count,
        following_count=user.following_count,
        posts_count=user.posts_count
    )

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("/", response_model=StoryResponse)
async def create_story(
    files: Optional[List[UploadFile]] = File(None),
    text: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a new story with text and/or uploaded media (Instagram-style)"""
    try:
        # Validate input: must have at least text or a file
        if (not files or len(files) == 0) and not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide either text or at least one media file for a story."
            )
        
        media_data = None
        media_mime_type = None
        media_type = None
        
        if files and len(files) > 0:
            # Process the first file (stories typically have one media item)
            file = files[0]
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must have a filename"
                )
            
            # Process media using MediaUtils - fix tuple access issue
            try:
                processed_media = await MediaUtils.process_story_media(file)
                # Handle both dict and tuple returns from MediaUtils
                if isinstance(processed_media, dict):
                    media_data = processed_media["media_data"]
                    media_mime_type = processed_media["media_mime_type"] 
                    media_type = processed_media.get("media_type", MediaType.image)
                else:
                    # Handle tuple format: (media_data, media_mime_type)
                    media_data, media_mime_type = processed_media
                    # Determine media type from MIME type
                    if media_mime_type.startswith('video/'):
                        media_type = MediaType.video
                    else:
                        media_type = MediaType.image
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process media file: {str(e)}"
                )
        
        # Create the story with binary media data
        new_story = Story(
            user_id=current_user.id,
            text=text,
            media_data=media_data,
            media_mime_type=media_mime_type,
            media_type=media_type
        )
        
        db.add(new_story)
        db.commit()
        db.refresh(new_story)
        
        # Convert user to UserProfile
        user_profile = create_user_profile(current_user)
        
        # Encode media data for response
        encoded_media_data = None
        if media_data:
            encoded_media_data = base64.b64encode(media_data).decode('utf-8')
        
        return StoryResponse(
            id=new_story.id,
            user_id=new_story.user_id,
            user=user_profile,
            text=new_story.text,
            media_data=encoded_media_data,
            media_mime_type=media_mime_type,
            media_type=media_type,
            created_at=new_story.created_at,
            expires_at=new_story.expires_at,
            views_count=0,
            is_viewed=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create story: {str(e)}")

@router.get("/feed", response_model=List[StoryResponse])
async def get_stories_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get stories from followed users"""
    try:
        # Get stories from followed users and own stories
        current_time = datetime.utcnow()
        
        stories = db.query(Story).options(
            joinedload(Story.user),
            joinedload(Story.views)
        ).join(
            User, Story.user_id == User.id
        ).outerjoin(
            Follower, and_(
                Follower.following_id == Story.user_id,
                Follower.follower_id == current_user.id
            )
        ).filter(
            and_(
                Story.expires_at > current_time,
                or_(
                    Story.user_id == current_user.id,  # Own stories
                    Follower.follower_id == current_user.id  # Followed users' stories
                )
            )
        ).order_by(desc(Story.created_at)).all()
        
        story_responses = []
        for story in stories:
            # Check if current user has viewed this story
            is_viewed = any(
                view.user_id == current_user.id for view in story.views
            )
            
            user_profile = create_user_profile(story.user)
            
            # Encode media data for response
            encoded_media_data = None
            if story.media_data:
                encoded_media_data = base64.b64encode(story.media_data).decode('utf-8')
            
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                text=story.text,
                media_data=encoded_media_data,
                media_mime_type=story.media_mime_type,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                views_count=len(story.views),
                is_viewed=is_viewed
            ))
        
        return story_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stories feed: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=List[StoryResponse])
async def get_user_stories(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get stories from a specific user"""
    try:
        current_time = datetime.utcnow()
        
        stories = db.query(Story).options(
            joinedload(Story.user),
            joinedload(Story.views)
        ).filter(
            and_(
                Story.user_id == user_id,
                Story.expires_at > current_time
            )
        ).order_by(desc(Story.created_at)).all()
        
        story_responses = []
        for story in stories:
            # Check if current user has viewed this story
            is_viewed = any(
                view.user_id == current_user.id for view in story.views
            )
            
            user_profile = create_user_profile(story.user)
            
            # Encode media data for response
            encoded_media_data = None
            if story.media_data:
                encoded_media_data = base64.b64encode(story.media_data).decode('utf-8')
            
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                text=story.text,
                media_data=encoded_media_data,
                media_mime_type=story.media_mime_type,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                views_count=len(story.views),
                is_viewed=is_viewed
            ))
        
        return story_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stories: {str(e)}"
        )

@router.post("/{story_id}/view", response_model=SuccessResponse)
async def view_story(
    story_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Mark a story as viewed"""
    try:
        # Check if story exists and is not expired
        current_time = datetime.utcnow()
        story = db.query(Story).filter(
            and_(
                Story.id == story_id,
                Story.expires_at > current_time
            )
        ).first()
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or expired"
            )
        
        # Check if already viewed by this user
        existing_view = db.query(StoryView).filter(
            and_(
                StoryView.story_id == story_id,
                StoryView.user_id == current_user.id
            )
        ).first()
        
        if not existing_view:
            # Create new view record
            new_view = StoryView(
                story_id=story_id,
                user_id=current_user.id
            )
            db.add(new_view)
            
            # Increment view count
            story.view_count += 1
            
            db.commit()
        
        return SuccessResponse(message="Story viewed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to view story: {str(e)}"
        )

@router.get("/{story_id}/viewers", response_model=List[UserProfile])
async def get_story_viewers(
    story_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get list of users who viewed the story (only for story owner)"""
    try:
        # Check if story exists and user owns it
        story = db.query(Story).filter(Story.id == story_id).first()
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        if story.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view viewers of your own stories"
            )
        
        # Get viewers
        viewers = db.query(User).join(
            StoryView, User.id == StoryView.user_id
        ).filter(
            StoryView.story_id == story_id
        ).order_by(desc(StoryView.viewed_at)).all()
        
        viewer_profiles = []
        for viewer in viewers:
            viewer_profiles.append(create_user_profile(viewer))
        
        return viewer_profiles
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get story viewers: {str(e)}"
        )

@router.delete("/{story_id}", response_model=SuccessResponse)
async def delete_story(
    story_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Delete a story (only by owner)"""
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        if story.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own stories"
            )
        
        db.delete(story)
        db.commit()
        
        return SuccessResponse(message="Story deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete story: {str(e)}"
        )

@router.get("/my-stories", response_model=List[StoryResponse])
async def get_my_stories(
    include_expired: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get current user's stories"""
    try:
        query = db.query(Story).options(
            joinedload(Story.views)
        ).filter(Story.user_id == current_user.id)
        
        if not include_expired:
            current_time = datetime.utcnow()
            query = query.filter(Story.expires_at > current_time)
        
        stories = query.order_by(desc(Story.created_at)).all()
        
        story_responses = []
        user_profile = create_user_profile(current_user)
        
        for story in stories:
            # Encode media data for response
            encoded_media_data = None
            if story.media_data:
                encoded_media_data = base64.b64encode(story.media_data).decode('utf-8')
                
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                text=story.text,
                media_data=encoded_media_data,
                media_mime_type=story.media_mime_type,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                views_count=len(story.views),
                is_viewed=True  # User always sees their own stories as viewed
            ))
        
        return story_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get my stories: {str(e)}"
        )
