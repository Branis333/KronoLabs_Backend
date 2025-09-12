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
from fastapi.responses import Response, FileResponse
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
from utils.media_utils import MediaUtils
from typing import List, Optional
from datetime import datetime
from pathlib import Path
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
        followers_count=getattr(user, 'followers_count', 0),
        following_count=getattr(user, 'following_count', 0),
        posts_count=getattr(user, 'posts_count', 0),
        created_at=user.created_at
    )

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
        media_data = None
        media_mime_type = None
        if file and file.filename:
            # Process media using MediaUtils
            media_data, media_mime_type = await MediaUtils.process_message_media(file)
        
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
        
        # Create the message with binary media data
        new_message = DirectMessage(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            message_text=message_text,
            media_data=media_data,
            media_mime_type=media_mime_type,
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
            post_user_profile = create_user_profile(shared_post.user)
            
            # Encode shared post media data
            shared_post_media_data = None
            if shared_post.media_data:
                shared_post_media_data = base64.b64encode(shared_post.media_data).decode('utf-8')
            
            shared_post_response = PostResponse(
                id=shared_post.id,
                user_id=shared_post.user_id,
                user=post_user_profile,
                caption=shared_post.caption,
                media_data=shared_post_media_data,
                media_mime_type=shared_post.media_mime_type,
                media_type=shared_post.media_type,
                location=shared_post.location,
                visibility=shared_post.visibility,
                created_at=shared_post.created_at,
                likes_count=0,  # Simplified for shared content
                comments_count=0,
                is_liked=False,
                is_saved=False,
                post_media=[]
            )
        
        if shared_story:
            # Create StoryResponse for shared story
            story_user_profile = create_user_profile(shared_story.user)
            
            # Encode shared story media data
            shared_story_media_data = None
            if shared_story.media_data:
                shared_story_media_data = base64.b64encode(shared_story.media_data).decode('utf-8')
            
            shared_story_response = StoryResponse(
                id=shared_story.id,
                user_id=shared_story.user_id,
                user=story_user_profile,
                text=shared_story.text,
                media_data=shared_story_media_data,
                media_mime_type=shared_story.media_mime_type,
                media_type=shared_story.media_type,
                created_at=shared_story.created_at,
                expires_at=shared_story.expires_at,
                views_count=0,  # Simplified for shared content
                is_viewed=False
            )
        
        # Convert users to UserProfile format
        sender_profile = create_user_profile(current_user)
        receiver_profile = create_user_profile(receiver)
        
        # Encode message media data for response
        encoded_media_data = None
        if media_data:
            encoded_media_data = base64.b64encode(media_data).decode('utf-8')
        
        return MessageResponse(
            id=new_message.id,
            sender_id=new_message.sender_id,
            receiver_id=new_message.receiver_id,
            sender=sender_profile,
            receiver=receiver_profile,
            message_text=new_message.message_text,
            media_data=encoded_media_data,
            media_mime_type=media_mime_type,
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
            
            # Convert to response format with Base64 encoded images
            user_profile = create_user_profile(user)
            
            # Get sender and receiver for last message
            sender = current_user if last_message.sender_id == current_user.id else user
            receiver = user if last_message.sender_id == current_user.id else current_user
            
            sender_profile = create_user_profile(sender)
            receiver_profile = create_user_profile(receiver)
            
            # Encode last message media data for response
            last_message_media_data = None
            if last_message.media_data:
                last_message_media_data = base64.b64encode(last_message.media_data).decode('utf-8')

            last_message_response = MessageResponse(
                id=last_message.id,
                sender_id=last_message.sender_id,
                receiver_id=last_message.receiver_id,
                sender=sender_profile,
                receiver=receiver_profile,
                message_text=last_message.message_text,
                media_data=last_message_media_data,
                media_mime_type=last_message.media_mime_type,
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
            
            sender_profile = create_user_profile(sender)
            receiver_profile = create_user_profile(receiver)
            
            # Encode message media data for response
            message_media_data = None
            if message.media_data:
                message_media_data = base64.b64encode(message.media_data).decode('utf-8')
            
            message_responses.append(MessageResponse(
                id=message.id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                sender=sender_profile,
                receiver=receiver_profile,
                message_text=message.message_text,
                media_data=message_media_data,
                media_mime_type=message.media_mime_type,
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
