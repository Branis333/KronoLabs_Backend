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
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Story, StoryView, Follower
from schemas.social_schemas import (
    StoryCreate, StoryResponse, SuccessResponse, UserProfile, MediaType
)
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import os
import shutil
from pathlib import Path
import mimetypes

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
        
        # Prepare uploads directory
        base_upload_dir = Path("uploads")
        user_upload_dir = base_upload_dir / "stories" / str(current_user.id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        media_url = None
        media_type = None
        uploaded_files = []
        
        if files:
            for index, file in enumerate(files):
                if not file.filename:
                    raise HTTPException(status_code=400, detail="File must have a filename")
                content = await file.read()
                file_size = len(content)
                if file_size == 0:
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is empty")
                file_extension = Path(file.filename).suffix.lower()
                detected_mime_type = mimetypes.guess_type(file.filename)[0]
                content_type = detected_mime_type or file.content_type
                allowed_image_types = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff"}
                allowed_video_types = {"video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo", "video/webm", "video/ogg", "video/3gpp"}
                allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.mp4', '.mpeg', '.mov', '.avi', '.webm', '.ogg', '.3gp'}
                if (content_type not in allowed_image_types and content_type not in allowed_video_types and file_extension not in allowed_extensions):
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type} or extension: {file_extension}")
                is_image = (content_type in allowed_image_types or file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'})
                is_video = (content_type in allowed_video_types or file_extension in {'.mp4', '.mpeg', '.mov', '.avi', '.webm', '.ogg', '.3gp'})
                max_image_size = 10 * 1024 * 1024  # 10MB
                max_video_size = 50 * 1024 * 1024  # 50MB for stories
                if is_image and file_size > max_image_size:
                    raise HTTPException(status_code=400, detail=f"Image file {file.filename} exceeds 10MB limit")
                elif is_video and file_size > max_video_size:
                    raise HTTPException(status_code=400, detail=f"Video file {file.filename} exceeds 50MB limit")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                safe_filename = f"{timestamp}_{unique_id}_{index}{file_extension}"
                file_path = user_upload_dir / safe_filename
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                media_url = f"/stories/uploads/{current_user.id}/{safe_filename}"
                media_type = MediaType.image if is_image else MediaType.video
                uploaded_files.append({
                    "media_url": media_url,
                    "media_type": media_type,
                    "order_index": index,
                    "original_filename": file.filename
                })
                await file.seek(0)        # Use the first uploaded file as the main media for the story (if multiple)
        main_media_url = uploaded_files[0]["media_url"] if uploaded_files else None
        main_media_type = uploaded_files[0]["media_type"] if uploaded_files else None
        
        # Create the story
        new_story = Story(
            user_id=current_user.id,
            text=text,
            media_url=main_media_url,
            media_type=main_media_type
        )
        db.add(new_story)
        db.commit()
        db.refresh(new_story)
        # Convert user to UserProfile
        user_profile = UserProfile(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            bio=current_user.bio,
            profile_image_url=current_user.profile_image_url,
            website=current_user.website,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at
        )
        return StoryResponse(
            id=new_story.id,
            user_id=new_story.user_id,
            user=user_profile,
            media_url=new_story.media_url,
            media_type=new_story.media_type,
            text=new_story.text,
            created_at=new_story.created_at,
            expires_at=new_story.expires_at,
            view_count=new_story.view_count,
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
            
            user_profile = UserProfile(
                id=story.user.id,
                username=story.user.username,
                email=story.user.email,
                full_name=story.user.full_name,
                bio=story.user.bio,
                profile_image_url=story.user.profile_image_url,
                website=story.user.website,
                is_verified=story.user.is_verified,
                created_at=story.user.created_at
            )
            
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                view_count=story.view_count,
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
            
            user_profile = UserProfile(
                id=story.user.id,
                username=story.user.username,
                email=story.user.email,
                full_name=story.user.full_name,
                bio=story.user.bio,
                profile_image_url=story.user.profile_image_url,
                website=story.user.website,
                is_verified=story.user.is_verified,
                created_at=story.user.created_at
            )
            
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                view_count=story.view_count,
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
            viewer_profiles.append(UserProfile(
                id=viewer.id,
                username=viewer.username,
                email=viewer.email,
                full_name=viewer.full_name,
                bio=viewer.bio,
                profile_image_url=viewer.profile_image_url,
                website=viewer.website,
                is_verified=viewer.is_verified,
                created_at=viewer.created_at
            ))
        
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
        user_profile = UserProfile(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            bio=current_user.bio,
            profile_image_url=current_user.profile_image_url,
            website=current_user.website,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at
        )
        
        for story in stories:
            story_responses.append(StoryResponse(
                id=story.id,
                user_id=story.user_id,
                user=user_profile,
                media_url=story.media_url,
                media_type=story.media_type,
                created_at=story.created_at,
                expires_at=story.expires_at,
                view_count=story.view_count,
                is_viewed=True  # User always sees their own stories as viewed
            ))
        
        return story_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get my stories: {str(e)}"
        )
