"""
Enhanced Direct Messages API

Features:
- Send text messages
- Upload and send images/videos in messages
- Share posts from the platform in messages
- Share stories from the platform in messages
- Mixed messages (text + media + shared content)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_, case
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import DirectMessage, Notification, Post, Story
from schemas.social_schemas import (
    MessageCreate, MessageResponse, ConversationResponse, 
    SuccessResponse, UserProfile, NotificationType, PostResponse, StoryResponse
)
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil
from pathlib import Path
import mimetypes

router = APIRouter(prefix="/messages", tags=["Direct Messages"])

@router.post("/", response_model=MessageResponse)
async def send_message(
    receiver_id: int = Form(...),
    message_text: Optional[str] = Form(None),
    shared_post_id: Optional[str] = Form(None),
    shared_story_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """
    Send a direct message with optional text, media upload, and/or shared content
    
    Supports:
    - Text messages
    - Image/video uploads
    - Sharing posts from the platform
    - Sharing stories from the platform
    - Mixed messages (combinations of the above)
    """
    try:
        # Validate that at least one content type is provided
        if not any([message_text, file, shared_post_id, shared_story_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message must contain at least text, media, or shared content"
            )
        
        # Check if receiver exists
        receiver = db.query(User).filter(User.id == receiver_id).first()
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiver not found"
            )
        
        if receiver.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send message to yourself"
            )
        
        # Handle file upload if provided
        media_url = None
        if file and file.filename:
            # Validate file
            content = await file.read()
            file_size = len(content)
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="File is empty")
            
            # Check file type and size
            file_extension = Path(file.filename).suffix.lower()
            detected_mime_type = mimetypes.guess_type(file.filename)[0]
            content_type = detected_mime_type or file.content_type
            
            # Allowed types for message media
            allowed_image_types = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"}
            allowed_video_types = {"video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo", "video/webm"}
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.mp4', '.mpeg', '.mov', '.avi', '.webm'}
            
            if (content_type not in allowed_image_types and 
                content_type not in allowed_video_types and 
                file_extension not in allowed_extensions):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {content_type} or extension: {file_extension}"
                )
            
            # Check file size limits
            max_image_size = 10 * 1024 * 1024  # 10MB
            max_video_size = 50 * 1024 * 1024  # 50MB
            
            is_image = (content_type in allowed_image_types or 
                       file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'})
            is_video = (content_type in allowed_video_types or 
                       file_extension in {'.mp4', '.mpeg', '.mov', '.avi', '.webm'})
            
            if is_image and file_size > max_image_size:
                raise HTTPException(status_code=400, detail="Image exceeds 10MB limit")
            elif is_video and file_size > max_video_size:
                raise HTTPException(status_code=400, detail="Video exceeds 50MB limit")
            
            # Save file
            base_upload_dir = Path("uploads")
            message_upload_dir = base_upload_dir / "messages" / str(current_user.id)
            message_upload_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            safe_filename = f"{timestamp}_{unique_id}{file_extension}"
            file_path = message_upload_dir / safe_filename
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            media_url = f"/messages/uploads/{current_user.id}/{safe_filename}"
            await file.seek(0)
        
        # Validate shared content if provided
        shared_post = None
        shared_story = None
        
        if shared_post_id:
            try:
                post_uuid = uuid.UUID(shared_post_id)
                shared_post = db.query(Post).filter(Post.id == post_uuid).first()
                if not shared_post:
                    raise HTTPException(status_code=404, detail="Shared post not found")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid post ID format")
        
        if shared_story_id:
            try:
                story_uuid = uuid.UUID(shared_story_id)
                shared_story = db.query(Story).filter(Story.id == story_uuid).first()
                if not shared_story:
                    raise HTTPException(status_code=404, detail="Shared story not found")
                # Check if story is still valid (not expired)
                if shared_story.expires_at < datetime.utcnow():
                    raise HTTPException(status_code=400, detail="Cannot share expired story")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid story ID format")
        
        # Create the message
        new_message = DirectMessage(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            message_text=message_text,
            media_url=media_url,
            shared_post_id=uuid.UUID(shared_post_id) if shared_post_id else None,
            shared_story_id=uuid.UUID(shared_story_id) if shared_story_id else None
        )
        
        db.add(new_message)
        db.flush()
        
        # Create notification for receiver
        notification = Notification(
            user_id=receiver_id,
            type=NotificationType.dm,
            from_user_id=current_user.id,
            entity_id=new_message.id
        )
        db.add(notification)
        
        db.commit()
        db.refresh(new_message)
        
        # Load shared content if exists
        shared_post_response = None
        shared_story_response = None
        
        if shared_post:
            # Create PostResponse for shared post
            post_user_profile = UserProfile(
                id=shared_post.user.id,
                username=shared_post.user.username,
                email=shared_post.user.email,
                full_name=shared_post.user.full_name,
                bio=shared_post.user.bio,
                profile_image_url=shared_post.user.profile_image_url,
                website=shared_post.user.website,
                is_verified=shared_post.user.is_verified,
                created_at=shared_post.user.created_at
            )
            
            shared_post_response = PostResponse(
                id=shared_post.id,
                user_id=shared_post.user_id,
                user=post_user_profile,
                caption=shared_post.caption,
                media_url=shared_post.media_url,
                media_type=shared_post.media_type,
                location=shared_post.location,
                visibility=shared_post.visibility,
                created_at=shared_post.created_at
            )
        
        if shared_story:
            # Create StoryResponse for shared story
            story_user_profile = UserProfile(
                id=shared_story.user.id,
                username=shared_story.user.username,
                email=shared_story.user.email,
                full_name=shared_story.user.full_name,
                bio=shared_story.user.bio,
                profile_image_url=shared_story.user.profile_image_url,
                website=shared_story.user.website,
                is_verified=shared_story.user.is_verified,
                created_at=shared_story.user.created_at
            )
            
            shared_story_response = StoryResponse(
                id=shared_story.id,
                user_id=shared_story.user_id,
                user=story_user_profile,
                text=shared_story.text,
                media_url=shared_story.media_url,
                media_type=shared_story.media_type,
                created_at=shared_story.created_at,
                expires_at=shared_story.expires_at,
                view_count=shared_story.view_count,
                is_viewed=False
            )
        
        # Convert users to UserProfile format
        sender_profile = UserProfile(
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
        
        receiver_profile = UserProfile(
            id=receiver.id,
            username=receiver.username,
            email=receiver.email,
            full_name=receiver.full_name,
            bio=receiver.bio,
            profile_image_url=receiver.profile_image_url,
            website=receiver.website,
            is_verified=receiver.is_verified,
            created_at=receiver.created_at
        )
        
        return MessageResponse(
            id=new_message.id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            sender=sender_profile,
            receiver=receiver_profile,
            message_text=new_message.message_text,
            media_url=new_message.media_url,
            shared_post_id=new_message.shared_post_id,
            shared_story_id=new_message.shared_story_id,
            shared_post=shared_post_response,
            shared_story=shared_story_response,
            created_at=new_message.created_at,
            is_read=new_message.is_read
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get user's conversations"""
    try:
        # Get latest message from each conversation
        subquery = db.query(
            case(
                (DirectMessage.sender_id == current_user.id, DirectMessage.receiver_id),
                else_=DirectMessage.sender_id
            ).label('other_user_id'),
            func.max(DirectMessage.created_at).label('last_message_time')
        ).filter(
            or_(
                DirectMessage.sender_id == current_user.id,
                DirectMessage.receiver_id == current_user.id
            )
        ).group_by(
            case(
                (DirectMessage.sender_id == current_user.id, DirectMessage.receiver_id),
                else_=DirectMessage.sender_id
            )
        ).subquery()
        
        # Get conversations with last message and user info
        conversations_data = db.query(
            User,
            DirectMessage,
            subquery.c.last_message_time
        ).join(
            subquery, User.id == subquery.c.other_user_id
        ).join(
            DirectMessage,
            and_(
                DirectMessage.created_at == subquery.c.last_message_time,
                or_(
                    and_(
                        DirectMessage.sender_id == current_user.id,
                        DirectMessage.receiver_id == User.id
                    ),
                    and_(
                        DirectMessage.sender_id == User.id,
                        DirectMessage.receiver_id == current_user.id
                    )
                )
            )
        ).order_by(desc(subquery.c.last_message_time)).all()
        
        conversations = []
        for user, last_message, _ in conversations_data:
            # Count unread messages from this user
            unread_count = db.query(DirectMessage).filter(
                and_(
                    DirectMessage.sender_id == user.id,
                    DirectMessage.receiver_id == current_user.id,
                    DirectMessage.is_read == False
                )
            ).count()
            
            # Convert to response format
            user_profile = UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                profile_image_url=user.profile_image_url,
                website=user.website,
                is_verified=user.is_verified,
                created_at=user.created_at
            )
            
            # Get sender and receiver for last message
            sender = current_user if last_message.sender_id == current_user.id else user
            receiver = user if last_message.sender_id == current_user.id else current_user
            
            sender_profile = UserProfile(
                id=sender.id,
                username=sender.username,
                email=sender.email,
                full_name=sender.full_name,
                bio=sender.bio,
                profile_image_url=sender.profile_image_url,
                website=sender.website,
                is_verified=sender.is_verified,
                created_at=sender.created_at
            )
            
            receiver_profile = UserProfile(
                id=receiver.id,
                username=receiver.username,
                email=receiver.email,
                full_name=receiver.full_name,
                bio=receiver.bio,
                profile_image_url=receiver.profile_image_url,
                website=receiver.website,
                is_verified=receiver.is_verified,
                created_at=receiver.created_at
            )
            
            last_message_response = MessageResponse(
                id=last_message.id,
                sender_id=last_message.sender_id,
                receiver_id=last_message.receiver_id,
                sender=sender_profile,
                receiver=receiver_profile,
                message_text=last_message.message_text,
                media_url=last_message.media_url,
                created_at=last_message.created_at,
                is_read=last_message.is_read
            )
            
            conversations.append(ConversationResponse(
                user=user_profile,
                last_message=last_message_response,
                unread_count=unread_count
            ))
        
        return conversations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.get("/conversation/{user_id}", response_model=List[MessageResponse])
async def get_conversation_messages(
    user_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get messages from a specific conversation"""
    try:
        # Check if other user exists
        other_user = db.query(User).filter(User.id == user_id).first()
        if not other_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get messages between these two users
        messages = db.query(DirectMessage).filter(
            or_(
                and_(
                    DirectMessage.sender_id == current_user.id,
                    DirectMessage.receiver_id == user_id
                ),
                and_(
                    DirectMessage.sender_id == user_id,
                    DirectMessage.receiver_id == current_user.id
                )
            )
        ).order_by(desc(DirectMessage.created_at)).offset(offset).limit(limit).all()
        
        # Mark messages from other user as read
        db.query(DirectMessage).filter(
            and_(
                DirectMessage.sender_id == user_id,
                DirectMessage.receiver_id == current_user.id,
                DirectMessage.is_read == False
            )
        ).update({"is_read": True})
        db.commit()
        
        # Convert to response format
        message_responses = []
        for message in reversed(messages):  # Reverse to show oldest first
            sender = current_user if message.sender_id == current_user.id else other_user
            receiver = other_user if message.sender_id == current_user.id else current_user
            
            sender_profile = UserProfile(
                id=sender.id,
                username=sender.username,
                email=sender.email,
                full_name=sender.full_name,
                bio=sender.bio,
                profile_image_url=sender.profile_image_url,
                website=sender.website,
                is_verified=sender.is_verified,
                created_at=sender.created_at
            )
            
            receiver_profile = UserProfile(
                id=receiver.id,
                username=receiver.username,
                email=receiver.email,
                full_name=receiver.full_name,
                bio=receiver.bio,
                profile_image_url=receiver.profile_image_url,
                website=receiver.website,
                is_verified=receiver.is_verified,
                created_at=receiver.created_at
            )
            
            message_responses.append(MessageResponse(
                id=message.id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                sender=sender_profile,
                receiver=receiver_profile,
                message_text=message.message_text,
                media_url=message.media_url,
                created_at=message.created_at,
                is_read=message.is_read
            ))
        
        return message_responses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation messages: {str(e)}"
        )

@router.put("/{message_id}/read", response_model=SuccessResponse)
async def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Mark a message as read"""
    try:
        message = db.query(DirectMessage).filter(
            and_(
                DirectMessage.id == message_id,
                DirectMessage.receiver_id == current_user.id
            )
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        message.is_read = True
        db.commit()
        
        return SuccessResponse(message="Message marked as read")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark message as read: {str(e)}"
        )

@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get total unread messages count"""
    try:
        unread_count = db.query(DirectMessage).filter(
            and_(
                DirectMessage.receiver_id == current_user.id,
                DirectMessage.is_read == False
            )
        ).count()
        
        return {"unread_count": unread_count}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unread count: {str(e)}"
        )

@router.delete("/{message_id}", response_model=SuccessResponse)
async def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Delete a message (only by sender)"""
    try:
        message = db.query(DirectMessage).filter(
            and_(
                DirectMessage.id == message_id,
                DirectMessage.sender_id == current_user.id
            )
        ).first()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or you don't have permission to delete it"
            )
        
        db.delete(message)
        db.commit()
        
        return SuccessResponse(message="Message deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete message: {str(e)}"
        )

@router.get("/uploads/{user_id}/{filename}")
async def serve_message_media(
    user_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Serve uploaded message media files"""
    try:
        # Security: Only allow users to access media from conversations they're part of
        file_path = Path("uploads") / "messages" / str(user_id) / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found"
            )
        
        # Check if current user has access to this file
        # (either they sent the file or received it)
        has_access = db.query(DirectMessage).filter(
            and_(
                DirectMessage.media_url.contains(f"/messages/uploads/{user_id}/{filename}"),
                or_(
                    DirectMessage.sender_id == current_user.id,
                    DirectMessage.receiver_id == current_user.id
                )
            )
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this media file"
            )
        
        return FileResponse(
            path=str(file_path),
            media_type="application/octet-stream",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve media: {str(e)}"
        )
