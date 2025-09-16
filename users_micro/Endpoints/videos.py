"""
YouTube-Style Optimized Video API

This module provides YouTube-style video processing and streaming:

🎬 YOUTUBE-STYLE FEATURES:
- Multi-resolution transcoding (144p to 4K)
- Video segmentation for adaptive streaming  
- Binary storage (no external URLs)
- Automatic quality optimization
- Bandwidth-aware streaming
- Multiple thumbnail sizes
- Background processing pipeline

🔧 PROCESSING PIPELINE:
1. Upload video → Analyze source
2. Generate multi-size thumbnails
3. Transcode to multiple qualities (144p, 240p, 360p, 480p, 720p, 1080p, 4K)
4. Segment each quality for smooth streaming
5. Store all data as binary in database
6. Enable adaptive bitrate streaming

📺 STREAMING FEATURES:
- Adaptive quality switching
- Segment-based streaming (4-second chunks)
- HTTP range request support
- Bandwidth detection
- Mobile/desktop optimization
- Smooth playback without buffering

🗄️ STORAGE OPTIMIZATION:
- All media stored as binary data (thumbnails + video segments)
- No external dependencies (no Google Drive)
- Compressed and optimized for each quality
- Efficient database storage with proper indexing

API Usage:
POST /videos/ - Upload and process video (YouTube-style)
GET /videos/ - Browse processed videos  
GET /videos/{id}/stream - Get streaming manifest
GET /streaming/video/{id}/quality/{quality}/segment/{index} - Stream segments
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Video, VideoQuality, VideoSegment, VideoLike, VideoComment, SavedVideo
from schemas.social_schemas import (
    VideoCreate, VideoResponse, VideoCommentCreate, VideoCommentResponse,
    VideosResponse, SuccessResponse, UserProfile, VideoUpdateInfo
)
from utils.video_pipeline import video_pipeline
from utils.video_processor import video_processor
from utils.streaming_api import streaming_router
from typing import List, Optional
import base64
import json
import uuid

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
        followers_count=getattr(user, 'followers_count', 0),
        following_count=getattr(user, 'following_count', 0),
        posts_count=getattr(user, 'posts_count', 0),
        created_at=user.created_at
    )

router = APIRouter(prefix="/videos", tags=["Videos"])

@router.post("/", response_model=dict)
async def create_video_optimized(
    video_file: UploadFile = File(...),
    thumbnail: Optional[UploadFile] = File(None),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_public: bool = Form(True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """
    Create and process video with YouTube-style optimization
    
    This endpoint:
    1. Accepts video upload
    2. Generates multiple thumbnails (if not provided)
    3. Starts background processing for multiple qualities
    4. Returns immediately with processing status
    """
    try:
        print(f"🎬 Starting YouTube-style video upload for user {current_user.id}")
        
        # Validate input
        if not title.strip():
            raise HTTPException(status_code=400, detail="Video title is required")
        
        if len(title.strip()) > 255:
            raise HTTPException(status_code=400, detail="Video title too long")
        
        # Validate video file
        if not video_file.filename:
            raise HTTPException(status_code=400, detail="Video file is required")
        
        # Check file size (limit to 1GB for processing)
        video_content = await video_file.read()
        video_file.file.seek(0)  # Reset for processing
        
        if len(video_content) > 1024 * 1024 * 1024:  # 1GB
            raise HTTPException(
                status_code=413, 
                detail="Video file too large. Maximum size is 1GB"
            )
        
        # Parse tags
        parsed_tags = []
        if tags:
            try:
                if tags.startswith('[') and tags.endswith(']'):
                    parsed_tags = json.loads(tags)
                else:
                    parsed_tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            except:
                parsed_tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Prepare metadata
        video_metadata = {
            'title': title.strip(),
            'description': description.strip() if description else None,
            'category': category.strip() if category else None,
            'tags': parsed_tags,
            'is_public': is_public
        }
        
        # Use provided thumbnail or generate from video
        thumbnail_file = thumbnail
        if not thumbnail_file:
            print("📸 No thumbnail provided, will generate from video")
        
        # Start the complete processing pipeline
        print("🚀 Starting YouTube-style processing pipeline...")
        video_id = await video_pipeline.process_video_complete(
            video_file=video_file,
            thumbnail_file=thumbnail_file,
            video_metadata=video_metadata,
            user_id=current_user.id,
            db=db
        )
        
        print(f"✅ Video created with ID: {video_id}")
        
        # Return immediate response with processing info
        return {
            "success": True,
            "message": "Video upload successful! Processing multiple qualities...",
            "video_id": video_id,
            "processing_status": "processing",
            "estimated_completion": "2-5 minutes",
            "status_check_url": f"/videos/{video_id}/status",
            "streaming_available": "after_processing",
            "qualities_being_processed": [
                "144p", "240p", "360p", "480p", "720p", "1080p"
            ],
            "features": [
                "Multiple quality levels for adaptive streaming",
                "Automatic thumbnail generation", 
                "Segmented video for smooth playback",
                "Binary storage for fast delivery",
                "Mobile and desktop optimization"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Video upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video: {str(e)}"
        )

@router.get("/{video_id}/status")
async def get_video_processing_status(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get video processing status"""
    try:
        # Get video from database
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check permissions
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get processing status from pipeline
        processing_status = video_pipeline.get_processing_status(video_id)
        
        # Get available qualities from database
        qualities = db.query(VideoQuality).filter(
            VideoQuality.video_id == video_id
        ).all()
        
        available_qualities = []
        for quality in qualities:
            segment_count = db.query(VideoSegment).filter(
                VideoSegment.video_quality_id == quality.id
            ).count()
            
            available_qualities.append({
                "quality": quality.quality,
                "resolution": quality.resolution,
                "bitrate": quality.bitrate,
                "segments": segment_count,
                "total_size_mb": round((quality.total_size or 0) / 1024 / 1024, 2)
            })
        
        return {
            "video_id": video_id,
            "title": video.title,
            "processing_status": video.processing_status,
            "duration": video.duration,
            "original_resolution": video.original_resolution,
            "created_at": video.created_at,
            "pipeline_status": processing_status,
            "available_qualities": available_qualities,
            "streaming_ready": video.processing_status == "completed",
            "stream_manifest_url": f"/streaming/video/{video_id}/manifest" if video.processing_status == "completed" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )

@router.get("/{video_id}/stream")
async def get_video_streaming_info(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get video streaming information and manifest"""
    try:
        # Check if video exists and is ready
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if video.processing_status != "completed":
            return {
                "status": "processing",
                "message": "Video is still being processed",
                "processing_status": video.processing_status,
                "check_again_in": "30 seconds"
            }
        
        # Get available qualities
        qualities = db.query(VideoQuality).filter(
            VideoQuality.video_id == video_id
        ).all()
        
        if not qualities:
            raise HTTPException(status_code=404, detail="No video qualities available")
        
        # Build streaming response
        quality_info = []
        for quality in qualities:
            quality_info.append({
                "quality": quality.quality,
                "resolution": quality.resolution,
                "bitrate": quality.bitrate,
                "codec": quality.codec,
                "fps": quality.fps,
                "segments": quality.total_segments,
                "stream_url": f"/streaming/video/{video_id}/quality/{quality.quality}/segment/0"
            })
        
        return {
            "video_id": video_id,
            "title": video.title,
            "duration": video.duration,
            "streaming_ready": True,
            "adaptive_streaming": {
                "manifest_url": f"/streaming/video/{video_id}/manifest",
                "auto_quality_url": f"/streaming/video/{video_id}/auto"
            },
            "available_qualities": quality_info,
            "thumbnails": {
                "small": f"/streaming/video/{video_id}/thumbnail/small",
                "medium": f"/streaming/video/{video_id}/thumbnail/medium", 
                "large": f"/streaming/video/{video_id}/thumbnail/large"
            },
            "playback_features": [
                "Adaptive bitrate streaming",
                "Segment-based playback", 
                "HTTP range request support",
                "Mobile optimization",
                "Bandwidth detection"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get streaming info: {str(e)}"
        )
    
@router.get("/", response_model=VideosResponse)
async def get_videos(
    limit: int = Query(20, le=50, ge=1),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get all public videos with optional filtering"""
    try:
        # Base query - only public videos or user's own videos
        query = db.query(Video).options(
            joinedload(Video.user),
            joinedload(Video.likes),
            joinedload(Video.comments)
        )
        
        # Filter by visibility
        if current_user:
            query = query.filter(
                or_(
                    Video.is_public == True,
                    Video.user_id == current_user.id
                )
            )
        else:
            query = query.filter(Video.is_public == True)
        
        # Apply filters
        if category:
            query = query.filter(Video.category.ilike(f"%{category}%"))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Video.title.ilike(search_term),
                    Video.description.ilike(search_term)
                )
            )
        
        if tags:
            # Search in tags JSON field
            tag_search = f'%"{tags}"%'
            query = query.filter(Video.tags.ilike(tag_search))
        
        if user_id:
            query = query.filter(Video.user_id == user_id)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        videos = query.order_by(desc(Video.created_at)).offset(offset).limit(limit).all()
        
        # Convert to response format
        video_responses = []
        for video in videos:
            # Get counts
            likes_count = len(video.likes)
            comments_count = len(video.comments)
            
            # Check if current user liked/saved
            is_liked = False
            is_saved = False
            if current_user:
                is_liked = any(like.user_id == current_user.id for like in video.likes)
                is_saved = db.query(SavedVideo).filter(
                    and_(
                        SavedVideo.user_id == current_user.id,
                        SavedVideo.video_id == video.id
                    )
                ).first() is not None
            
            # Create user profile
            user_profile = create_user_profile(video.user)
            
            # Use YouTube-style thumbnails (use medium as default)
            thumbnail_data = video.thumbnail_medium_data or video.thumbnail_large_data or video.thumbnail_small_data
            thumbnail_b64 = base64.b64encode(thumbnail_data).decode('utf-8') if thumbnail_data else None
            
            # Get available qualities for this video
            available_qualities = db.query(VideoQuality.quality).filter(
                VideoQuality.video_id == video.id
            ).all()
            quality_list = [q[0] for q in available_qualities] if available_qualities else []
            
            video_response = VideoResponse(
                id=video.id,
                user_id=video.user_id,
                user=user_profile,
                title=video.title,
                description=video.description,
                thumbnail_data=thumbnail_b64,
                thumbnail_mime_type=video.thumbnail_mime_type,
                
                # YouTube-style metadata
                original_filename=video.original_filename,
                original_resolution=video.original_resolution,
                fps=video.fps,
                duration=video.duration,
                processing_status=video.processing_status,
                
                # Content
                category=video.category,
                tags=json.loads(video.tags) if video.tags else [],
                is_public=video.is_public,
                view_count=video.view_count or 0,
                
                # Timestamps
                created_at=video.created_at,
                updated_at=video.updated_at,
                
                # Streaming info
                streaming_url=f"/videos/{video.id}/stream" if quality_list else None,
                available_qualities=quality_list,
                likes_count=likes_count,
                comments_count=comments_count,
                is_liked=is_liked,
                is_saved=is_saved
            )
            
            video_responses.append(video_response)
        
        return VideosResponse(
            videos=video_responses,
            has_next=len(videos) == limit,
            total_count=total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos: {str(e)}"
        )

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get a specific video and increment view count"""
    try:
        # Get video with relationships
        video = db.query(Video).options(
            joinedload(Video.user),
            joinedload(Video.likes),
            joinedload(Video.comments)
        ).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail="Video not found"
            )
        
        # Check if video is accessible
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(
                status_code=403,
                detail="Video is private"
            )
        
        # Increment view count
        video.view_count = (video.view_count or 0) + 1
        db.commit()
        
        # Get counts
        likes_count = len(video.likes)
        comments_count = len(video.comments)
        
        # Check if current user liked/saved
        is_liked = False
        is_saved = False
        if current_user:
            is_liked = any(like.user_id == current_user.id for like in video.likes)
            is_saved = db.query(SavedVideo).filter(
                and_(
                    SavedVideo.user_id == current_user.id,
                    SavedVideo.video_id == video.id
                )
            ).first() is not None
        
        # Create user profile
        user_profile = create_user_profile(video.user)
        
        # Use YouTube-style thumbnails (use medium as default)
        thumbnail_data = video.thumbnail_medium_data or video.thumbnail_large_data or video.thumbnail_small_data
        thumbnail_b64 = base64.b64encode(thumbnail_data).decode('utf-8') if thumbnail_data else None
        
        # Get available qualities for this video
        available_qualities = db.query(VideoQuality.quality).filter(
            VideoQuality.video_id == video.id
        ).all()
        quality_list = [q[0] for q in available_qualities] if available_qualities else []
        
        return VideoResponse(
            id=video.id,
            user_id=video.user_id,
            user=user_profile,
            title=video.title,
            description=video.description,
            thumbnail_data=thumbnail_b64,
            thumbnail_mime_type=video.thumbnail_mime_type,
            
            # YouTube-style metadata
            original_filename=video.original_filename,
            original_resolution=video.original_resolution,
            fps=video.fps,
            duration=video.duration,
            processing_status=video.processing_status,
            
            # Content
            category=video.category,
            tags=json.loads(video.tags) if video.tags else [],
            is_public=video.is_public,
            view_count=video.view_count or 0,
            
            # Timestamps
            created_at=video.created_at,
            updated_at=video.updated_at,
            
            # Engagement
            likes_count=likes_count,
            comments_count=comments_count,
            is_liked=is_liked,
            is_saved=is_saved,
            
            # Streaming info
            streaming_url=f"/videos/{video.id}/stream" if quality_list else None,
            available_qualities=quality_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video: {str(e)}"
        )

@router.post("/{video_id}/like", response_model=SuccessResponse)
async def like_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Like or unlike a video"""
    try:
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if user already liked this video
        existing_like = db.query(VideoLike).filter(
            and_(
                VideoLike.user_id == current_user.id,
                VideoLike.video_id == video_id
            )
        ).first()
        
        if existing_like:
            # Unlike - remove the like
            db.delete(existing_like)
            db.commit()
            return SuccessResponse(message="Video unliked successfully")
        else:
            # Like - add the like
            new_like = VideoLike(
                user_id=current_user.id,
                video_id=video_id
            )
            db.add(new_like)
            db.commit()
            return SuccessResponse(message="Video liked successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like/unlike video: {str(e)}"
        )

@router.post("/{video_id}/save", response_model=SuccessResponse)
async def save_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Save or unsave a video to user's watchlist"""
    try:
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if user already saved this video
        existing_save = db.query(SavedVideo).filter(
            and_(
                SavedVideo.user_id == current_user.id,
                SavedVideo.video_id == video_id
            )
        ).first()
        
        if existing_save:
            # Unsave - remove from watchlist
            db.delete(existing_save)
            db.commit()
            return SuccessResponse(message="Video removed from watchlist")
        else:
            # Save - add to watchlist
            new_save = SavedVideo(
                user_id=current_user.id,
                video_id=video_id
            )
            db.add(new_save)
            db.commit()
            return SuccessResponse(message="Video saved to watchlist")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save/unsave video: {str(e)}"
        )

@router.post("/{video_id}/comments", response_model=VideoCommentResponse)
async def create_video_comment(
    video_id: str,
    comment_data: VideoCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a comment on a video"""
    try:
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create comment
        new_comment = VideoComment(
            video_id=video_id,
            user_id=current_user.id,
            text=comment_data.text,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        # Create user profile for response
        user_profile = create_user_profile(current_user)
        
        return VideoCommentResponse(
            id=new_comment.id,
            video_id=new_comment.video_id,
            user_id=new_comment.user_id,
            user=user_profile,
            text=new_comment.text,
            parent_comment_id=new_comment.parent_comment_id,
            created_at=new_comment.created_at,
            replies_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comment: {str(e)}"
        )

@router.get("/{video_id}/comments", response_model=List[VideoCommentResponse])
async def get_video_comments(
    video_id: str,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get comments for a video"""
    try:
        # Get comments with user info
        comments = db.query(VideoComment).options(
            joinedload(VideoComment.user)
        ).filter(VideoComment.video_id == video_id).order_by(
            VideoComment.created_at
        ).offset(offset).limit(limit).all()
        
        comment_responses = []
        for comment in comments:
            user_profile = create_user_profile(comment.user)
            
            comment_response = VideoCommentResponse(
                id=comment.id,
                video_id=comment.video_id,
                user_id=comment.user_id,
                user=user_profile,
                text=comment.text,
                parent_comment_id=comment.parent_comment_id,
                created_at=comment.created_at,
                replies_count=0  # TODO: implement replies count
            )
            comment_responses.append(comment_response)
        
        return comment_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comments: {str(e)}"
        )

@router.patch("/{video_id}", response_model=SuccessResponse)
async def update_video_info(
    video_id: str,
    video_update: VideoUpdateInfo,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Update video information (creator only)"""
    try:
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check ownership
        if video.user_id != current_user.id:
            raise HTTPException(
                status_code=403, 
                detail="Only video creator can update video info"
            )
        
        # Update fields
        if video_update.title is not None:
            video.title = video_update.title
        if video_update.description is not None:
            video.description = video_update.description
        if video_update.category is not None:
            video.category = video_update.category
        if video_update.is_public is not None:
            video.is_public = video_update.is_public
        if video_update.tags is not None:
            video.tags = json.dumps(video_update.tags)
        
        db.commit()
        
        return SuccessResponse(message="Video updated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update video: {str(e)}"
        )

@router.delete("/{video_id}", response_model=SuccessResponse)
async def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Delete a video (creator only)"""
    try:
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check ownership
        if video.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only video creator can delete video"
            )
        
        # Delete all video segments and qualities (YouTube-style cleanup)
        try:
            # Delete video segments for all qualities
            qualities = db.query(VideoQuality).filter(VideoQuality.video_id == video_id).all()
            for quality in qualities:
                db.query(VideoSegment).filter(VideoSegment.video_quality_id == quality.id).delete()
            
            # Delete video qualities
            db.query(VideoQuality).filter(VideoQuality.video_id == video_id).delete()
            
            print(f"🗑️ Cleaned up all video segments and qualities for video {video_id}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to cleanup video segments: {e}")
            # Continue with deletion even if cleanup fails
        
        # Delete from database (cascades to likes, comments, saves)
        db.delete(video)
        db.commit()
        
        return SuccessResponse(message="Video deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete video: {str(e)}"
        )

@router.get("/media/thumbnail/{video_id}")
async def serve_video_thumbnail(
    video_id: str,
    db: Session = Depends(get_db)
):
    """Serve video thumbnail from database"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Use YouTube-style thumbnails (prefer medium, fallback to others)
        thumbnail_data = video.thumbnail_medium_data or video.thumbnail_large_data or video.thumbnail_small_data
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return Response(
            content=thumbnail_data,
            media_type=video.thumbnail_mime_type or "image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(thumbnail_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve thumbnail: {str(e)}"
        )