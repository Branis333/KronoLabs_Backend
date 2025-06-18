"""
Instagram-like Posts API

This module provides comprehensive post management functionality similar to Instagram:

Features:
- Create posts with uploaded media files (images/videos) - REQUIRED like Instagram
- Support for carousel posts (multiple media files)
- Direct file upload from user's device
- Get user's feed with posts from followed users
- View individual posts with full media support
- Get posts by specific user (profile view)
- Like/unlike posts
- Save/unsave posts
- Comment on posts with threaded replies
- Delete posts (owner only)
- Hashtag support
- User tagging
- Privacy controls (public, private, followers_only)

Media Requirements (like Instagram):
- At least one media file is REQUIRED to create a post
- Images: JPEG, PNG, GIF, WebP, BMP, TIFF (max 10MB each)
- Videos: MP4, MPEG, QuickTime, AVI, WebM, OGG, 3GP (max 100MB each)
- Maximum 10 media files per post (Instagram standard)
- Automatic media type detection and validation
- Files are stored locally and served through the API

API Usage:
POST /posts/ - Upload files and create post in one request
- Use multipart/form-data with files
- Include caption, location, visibility, hashtags, tagged_users as form fields
- Files are automatically saved and organized by user
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Post, PostMedia, Like, Comment, SavedPost, Hashtag, Tag, Follower
from schemas.social_schemas import (
    PostCreate, PostResponse, CommentCreate, CommentResponse, 
    FeedResponse, SuccessResponse, UserProfile, PostMediaSchema, MediaType, PostVisibility
)
from typing import List, Optional
import uuid
import os
import shutil
from pathlib import Path
from datetime import datetime
import mimetypes

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=PostResponse)
async def create_post_with_upload(
    files: List[UploadFile] = File(...),
    caption: Optional[str] = None,
    location: Optional[str] = None,
    visibility: str = "public",
    hashtags: Optional[str] = None,  # JSON string or comma-separated
    tagged_users: Optional[str] = None,  # JSON string or comma-separated
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a new post with uploaded files from device (like Instagram)"""
    try:
        import json
        
        # Validate that files are provided (required like Instagram)
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one media file is required to create a post"
            )
        
        if len(files) > 10:  # Instagram allows up to 10 media files
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 media files allowed per post"
            )
        
        # Parse hashtags and tagged users if provided
        parsed_hashtags = []
        parsed_tagged_users = []
        
        if hashtags:
            try:
                parsed_hashtags = json.loads(hashtags)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated string
                parsed_hashtags = [tag.strip() for tag in hashtags.split(',') if tag.strip()]
        
        if tagged_users:
            try:
                parsed_tagged_users = json.loads(tagged_users)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated string
                parsed_tagged_users = [int(uid.strip()) for uid in tagged_users.split(',') if uid.strip().isdigit()]
        
        # Create uploads directory if it doesn't exist
        base_upload_dir = Path("uploads")
        user_upload_dir = base_upload_dir / "posts" / str(current_user.id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_files = []
        
        # Process and upload each file
        for index, file in enumerate(files):
            # Validate file has content
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must have a filename"
                )
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            if file_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} is empty"
                )
            
            # Detect file type from content and filename
            file_extension = Path(file.filename).suffix.lower()
            detected_mime_type = mimetypes.guess_type(file.filename)[0]
            
            # Use detected mime type if available, otherwise use provided content_type
            content_type = detected_mime_type or file.content_type
            
            # Validate file type
            allowed_image_types = {
                "image/jpeg", "image/jpg", "image/png", "image/gif", 
                "image/webp", "image/bmp", "image/tiff"
            }
            allowed_video_types = {
                "video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo",
                "video/webm", "video/ogg", "video/3gpp"
            }
            
            allowed_extensions = {
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff',
                '.mp4', '.mpeg', '.mov', '.avi', '.webm', '.ogg', '.3gp'
            }
            
            if (content_type not in allowed_image_types and 
                content_type not in allowed_video_types and 
                file_extension not in allowed_extensions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {content_type} or extension: {file_extension}"
                )
            
            # Determine if it's image or video
            is_image = (content_type in allowed_image_types or 
                       file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'})
            is_video = (content_type in allowed_video_types or 
                       file_extension in {'.mp4', '.mpeg', '.mov', '.avi', '.webm', '.ogg', '.3gp'})
            
            # Validate file size
            max_image_size = 10 * 1024 * 1024  # 10MB
            max_video_size = 100 * 1024 * 1024  # 100MB
            
            if is_image and file_size > max_image_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image file {file.filename} size ({file_size / 1024 / 1024:.1f}MB) exceeds 10MB limit"
                )
            elif is_video and file_size > max_video_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video file {file.filename} size ({file_size / 1024 / 1024:.1f}MB) exceeds 100MB limit"
                )
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            safe_filename = f"{timestamp}_{unique_id}_{index}{file_extension}"
            
            # Create full file path
            file_path = user_upload_dir / safe_filename
            
            # Save file to disk
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # Create relative URL for serving files
            media_url = f"/posts/uploads/{current_user.id}/{safe_filename}"
            
            # Determine media type
            media_type = MediaType.image if is_image else MediaType.video
            
            uploaded_files.append({
                "media_url": media_url,
                "media_type": media_type,
                "order_index": index,
                "original_filename": file.filename,
                "file_size": file_size,
                "content_type": content_type
            })
            
            # Reset file position for potential future reads
            await file.seek(0)
        
        # Determine post media type
        if len(uploaded_files) > 1:
            post_media_type = MediaType.carousel
        else:
            post_media_type = uploaded_files[0]["media_type"]
        
        # Convert visibility string to enum
        try:
            post_visibility = PostVisibility(visibility)
        except ValueError:
            post_visibility = PostVisibility.public
        
        # Create the post
        new_post = Post(
            user_id=current_user.id,
            caption=caption,
            media_url=uploaded_files[0]["media_url"],  # Primary media URL
            media_type=post_media_type,
            location=location,
            visibility=post_visibility
        )
        
        db.add(new_post)
        db.flush()  # Get the post ID
        
        # Add multiple media files to PostMedia table
        post_media_list = []
        for file_info in uploaded_files:
            post_media = PostMedia(
                post_id=new_post.id,
                media_url=file_info["media_url"],
                media_type=file_info["media_type"],
                order_index=file_info["order_index"]
            )
            db.add(post_media)
            post_media_list.append(post_media)
        
        # Add hashtags if provided
        if parsed_hashtags:
            for hashtag_text in parsed_hashtags:
                hashtag = Hashtag(
                    post_id=new_post.id,
                    hashtag=hashtag_text.lower().strip('#')
                )
                db.add(hashtag)
        
        # Tag users if provided
        if parsed_tagged_users:
            for user_id in parsed_tagged_users:
                tag = Tag(
                    post_id=new_post.id,
                    tagged_user_id=user_id
                )
                db.add(tag)
        
        db.commit()
        db.refresh(new_post)
        
        # Get user profile for response
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
        
        # Convert post media to schema format
        media_schemas = []
        for media in post_media_list:
            media_schemas.append(PostMediaSchema(
                id=media.id,
                media_url=media.media_url,
                order_index=media.order_index,
                media_type=media.media_type
            ))
        
        # Return the created post with user info
        return PostResponse(
            id=new_post.id,
            user_id=new_post.user_id,
            user=user_profile,
            caption=new_post.caption,
            media_url=new_post.media_url,
            media_type=new_post.media_type,
            location=new_post.location,
            visibility=new_post.visibility,
            created_at=new_post.created_at,
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_saved=False,
            post_media=media_schemas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}"
        )

@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get user's personalized feed"""
    try:        # Get posts from followed users and own posts
        posts_query = db.query(Post).options(
            joinedload(Post.user),
            joinedload(Post.likes),
            joinedload(Post.comments),
            joinedload(Post.post_media)
        ).filter(
            or_(
                Post.user_id == current_user.id,
                Post.user_id.in_(
                    db.query(Follower.following_id).filter(
                        Follower.follower_id == current_user.id
                    )
                )
            )
        ).filter(
            or_(
                Post.visibility == 'public',
                Post.user_id == current_user.id
            )
        ).order_by(desc(Post.created_at))
        
        posts = posts_query.offset(offset).limit(limit + 1).all()
        
        has_next = len(posts) > limit
        if has_next:
            posts = posts[:-1]
        
        # Convert to response format
        post_responses = []
        for post in posts:
            # Check if current user liked the post
            is_liked = db.query(Like).filter(
                Like.post_id == post.id,
                Like.user_id == current_user.id
            ).first() is not None
            
            # Check if current user saved the post
            is_saved = db.query(SavedPost).filter(
                SavedPost.post_id == post.id,
                SavedPost.user_id == current_user.id
            ).first() is not None
              # Get counts
            likes_count = len(post.likes)
            comments_count = len(post.comments)
            
            # Convert user to UserProfile
            user_profile = UserProfile(
                id=post.user.id,
                username=post.user.username,
                email=post.user.email,
                full_name=post.user.full_name,
                bio=post.user.bio,
                profile_image_url=post.user.profile_image_url,
                website=post.user.website,
                is_verified=post.user.is_verified,
                created_at=post.user.created_at
            )
            
            # Convert post media to schema format
            media_schemas = []
            if post.post_media:
                for media in sorted(post.post_media, key=lambda x: x.order_index):
                    media_schemas.append(PostMediaSchema(
                        id=media.id,
                        media_url=media.media_url,
                        order_index=media.order_index,
                        media_type=media.media_type
                    ))
            
            post_responses.append(PostResponse(
                id=post.id,
                user_id=post.user_id,
                user=user_profile,
                caption=post.caption,
                media_url=post.media_url,
                media_type=post.media_type,
                location=post.location,
                visibility=post.visibility,
                created_at=post.created_at,
                likes_count=likes_count,
                comments_count=comments_count,
                is_liked=is_liked,
                is_saved=is_saved,
                post_media=media_schemas
            ))
        
        return FeedResponse(
            posts=post_responses,
            has_next=has_next
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feed: {str(e)}"
        )

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get a specific post"""
    try:
        post = db.query(Post).options(
            joinedload(Post.user),
            joinedload(Post.likes),
            joinedload(Post.comments),
            joinedload(Post.post_media)
        ).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if current user can view this post
        if post.visibility == 'private' and post.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if current user liked the post
        is_liked = db.query(Like).filter(
            Like.post_id == post.id,
            Like.user_id == current_user.id
        ).first() is not None
        
        # Check if current user saved the post
        is_saved = db.query(SavedPost).filter(
            SavedPost.post_id == post.id,
            SavedPost.user_id == current_user.id
        ).first() is not None
        
        # Convert user to UserProfile
        user_profile = UserProfile(
            id=post.user.id,
            username=post.user.username,
            email=post.user.email,
            full_name=post.user.full_name,
            bio=post.user.bio,
            profile_image_url=post.user.profile_image_url,
            website=post.user.website,
            is_verified=post.user.is_verified,
            created_at=post.user.created_at
        )
        
        # Convert post media to schema format
        media_schemas = []
        if post.post_media:
            for media in sorted(post.post_media, key=lambda x: x.order_index):
                media_schemas.append(PostMediaSchema(
                    id=media.id,
                    media_url=media.media_url,
                    order_index=media.order_index,
                    media_type=media.media_type
                ))
        
        return PostResponse(
            id=post.id,
            user_id=post.user_id,
            user=user_profile,
            caption=post.caption,
            media_url=post.media_url,
            media_type=post.media_type,
            location=post.location,
            visibility=post.visibility,
            created_at=post.created_at,
            likes_count=len(post.likes),
            comments_count=len(post.comments),
            is_liked=is_liked,
            is_saved=is_saved,
            post_media=media_schemas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get post: {str(e)}"
        )

@router.post("/{post_id}/like", response_model=SuccessResponse)
async def like_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Like or unlike a post"""
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if already liked
        existing_like = db.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == current_user.id
        ).first()
        
        if existing_like:
            # Unlike the post
            db.delete(existing_like)
            message = "Post unliked successfully"
        else:
            # Like the post
            new_like = Like(
                post_id=post_id,
                user_id=current_user.id
            )
            db.add(new_like)
            message = "Post liked successfully"
        
        db.commit()
        return SuccessResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like/unlike post: {str(e)}"
        )

@router.post("/{post_id}/save", response_model=SuccessResponse)
async def save_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Save or unsave a post"""
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Check if already saved
        existing_save = db.query(SavedPost).filter(
            SavedPost.post_id == post_id,
            SavedPost.user_id == current_user.id
        ).first()
        
        if existing_save:
            # Unsave the post
            db.delete(existing_save)
            message = "Post unsaved successfully"
        else:
            # Save the post
            new_save = SavedPost(
                post_id=post_id,
                user_id=current_user.id
            )
            db.add(new_save)
            message = "Post saved successfully"
        
        db.commit()
        return SuccessResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save/unsave post: {str(e)}"
        )

@router.post("/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: str,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a comment on a post"""
    try:
        # Check if post exists
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Create the comment
        new_comment = Comment(
            post_id=post_id,
            user_id=current_user.id,
            text=comment_data.text,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return CommentResponse(
            id=new_comment.id,
            post_id=new_comment.post_id,
            user_id=new_comment.user_id,
            user=current_user,
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

@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_post_comments(
    post_id: str,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get comments for a post"""
    try:
        comments = db.query(Comment).options(
            joinedload(Comment.user)
        ).filter(
            Comment.post_id == post_id,
            Comment.parent_comment_id.is_(None)  # Only top-level comments
        ).order_by(
            desc(Comment.created_at)
        ).offset(offset).limit(limit).all()
        
        comment_responses = []
        for comment in comments:
            # Count replies
            replies_count = db.query(Comment).filter(
                Comment.parent_comment_id == comment.id
            ).count()
            
            comment_responses.append(CommentResponse(
                id=comment.id,
                post_id=comment.post_id,
                user_id=comment.user_id,
                user=comment.user,
                text=comment.text,
                parent_comment_id=comment.parent_comment_id,
                created_at=comment.created_at,
                replies_count=replies_count
            ))
        
        return comment_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comments: {str(e)}"
        )

@router.delete("/{post_id}", response_model=SuccessResponse)
async def delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Delete a post (only by the owner)"""
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if post.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own posts"
            )
        
        db.delete(post)
        db.commit()
        
        return SuccessResponse(message="Post deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )

@router.get("/uploads/{user_id}/{filename}")
async def serve_uploaded_file(
    user_id: int,
    filename: str,
    db: Session = Depends(get_db)
):
    """Serve uploaded media files"""
    try:
        # Construct file path
        file_path = Path("uploads") / "posts" / str(user_id) / filename
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Get file info
        file_size = file_path.stat().st_size
        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        
        # Return file
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
            headers={
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=31536000"  # Cache for 1 year
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve file: {str(e)}"
        )

@router.get("/test-upload")
async def test_upload_endpoint():
    """Test endpoint to verify upload functionality"""
    uploads_dir = Path("uploads") / "posts"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "message": "Upload system ready",
        "uploads_directory": str(uploads_dir.absolute()),
        "directory_exists": uploads_dir.exists(),
        "permissions": {
            "readable": os.access(uploads_dir, os.R_OK),
            "writable": os.access(uploads_dir, os.W_OK)
        },
        "info": "Use POST /posts/ with file uploads to create posts like Instagram"
    }
