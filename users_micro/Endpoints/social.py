from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Follower, Notification, Post
from schemas.social_schemas import (
    UserProfile, FollowResponse, NotificationResponse, 
    SuccessResponse, NotificationType
)
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/social", tags=["Social"])

@router.post("/follow/{user_id}", response_model=SuccessResponse)
async def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Follow or unfollow a user"""
    try:
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot follow yourself"
            )
        
        # Check if target user exists
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already following
        existing_follow = db.query(Follower).filter(
            Follower.follower_id == current_user.id,
            Follower.following_id == user_id
        ).first()
        
        if existing_follow:
            # Unfollow
            db.delete(existing_follow)
            message = f"Unfollowed {target_user.username}"
        else:
            # Follow
            new_follow = Follower(
                follower_id=current_user.id,
                following_id=user_id
            )
            db.add(new_follow)
            
            # Create notification for the followed user
            notification = Notification(
                user_id=user_id,
                type=NotificationType.follow,
                from_user_id=current_user.id
            )
            db.add(notification)
            
            message = f"Now following {target_user.username}"
        
        db.commit()
        return SuccessResponse(message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to follow/unfollow user: {str(e)}"
        )

@router.get("/followers/{user_id}", response_model=List[UserProfile])
async def get_followers(
    user_id: int,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get followers of a user"""
    try:
        followers = db.query(User).join(
            Follower, User.id == Follower.follower_id
        ).filter(
            Follower.following_id == user_id
        ).offset(offset).limit(limit).all()
        
        # Convert to UserProfile format
        follower_profiles = []
        for follower in followers:
            # Get counts for each follower
            followers_count = db.query(Follower).filter(
                Follower.following_id == follower.id
            ).count()
            
            following_count = db.query(Follower).filter(
                Follower.follower_id == follower.id
            ).count()
            
            posts_count = db.query(Post).filter(
                Post.user_id == follower.id
            ).count()
            
            follower_profiles.append(UserProfile(
                id=follower.id,
                username=follower.username,
                email=follower.email,
                full_name=follower.full_name,
                bio=follower.bio,
                profile_image_url=follower.profile_image_url,
                website=follower.website,
                is_verified=follower.is_verified,
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                created_at=follower.created_at
            ))
        
        return follower_profiles
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get followers: {str(e)}"
        )

@router.get("/following/{user_id}", response_model=List[UserProfile])
async def get_following(
    user_id: int,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get users that a user is following"""
    try:
        following = db.query(User).join(
            Follower, User.id == Follower.following_id
        ).filter(
            Follower.follower_id == user_id
        ).offset(offset).limit(limit).all()
        
        # Convert to UserProfile format
        following_profiles = []
        for user in following:
            # Get counts for each user
            followers_count = db.query(Follower).filter(
                Follower.following_id == user.id
            ).count()
            
            following_count = db.query(Follower).filter(
                Follower.follower_id == user.id
            ).count()
            
            posts_count = db.query(Post).filter(
                Post.user_id == user.id
            ).count()
            
            following_profiles.append(UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                profile_image_url=user.profile_image_url,
                website=user.website,
                is_verified=user.is_verified,
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                created_at=user.created_at
            ))
        
        return following_profiles
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get following: {str(e)}"
        )

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get user's notifications"""
    try:
        query = db.query(Notification).options(
            joinedload(Notification.from_user)
        ).filter(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        notifications = query.order_by(
            desc(Notification.created_at)
        ).offset(offset).limit(limit).all()
        
        notification_responses = []
        for notification in notifications:
            from_user_profile = None
            if notification.from_user:
                from_user_profile = UserProfile(
                    id=notification.from_user.id,
                    username=notification.from_user.username,
                    email=notification.from_user.email,
                    full_name=notification.from_user.full_name,
                    bio=notification.from_user.bio,
                    profile_image_url=notification.from_user.profile_image_url,
                    website=notification.from_user.website,
                    is_verified=notification.from_user.is_verified,
                    created_at=notification.from_user.created_at
                )
            
            notification_responses.append(NotificationResponse(
                id=notification.id,
                user_id=notification.user_id,
                type=notification.type,
                from_user_id=notification.from_user_id,
                from_user=from_user_profile,
                entity_id=notification.entity_id,
                created_at=notification.created_at,
                is_read=notification.is_read
            ))
        
        return notification_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )

@router.put("/notifications/{notification_id}/read", response_model=SuccessResponse)
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Mark a notification as read"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification.is_read = True
        db.commit()
        
        return SuccessResponse(message="Notification marked as read")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )

@router.put("/notifications/read-all", response_model=SuccessResponse)
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Mark all notifications as read"""
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).update({"is_read": True})
        
        db.commit()
        
        return SuccessResponse(message="All notifications marked as read")
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )

@router.get("/check-follow/{user_id}", response_model=dict)
async def check_follow_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Check if current user is following another user"""
    try:
        is_following = db.query(Follower).filter(
            Follower.follower_id == current_user.id,
            Follower.following_id == user_id
        ).first() is not None
        
        is_followed_by = db.query(Follower).filter(
            Follower.follower_id == user_id,
            Follower.following_id == current_user.id
        ).first() is not None
        
        return {
            "is_following": is_following,
            "is_followed_by": is_followed_by,
            "is_mutual": is_following and is_followed_by
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check follow status: {str(e)}"
        )

@router.get("/suggested-users", response_model=List[UserProfile])
async def get_suggested_users(
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get suggested users to follow"""
    try:
        # Get users that current user is not following
        following_ids = db.query(Follower.following_id).filter(
            Follower.follower_id == current_user.id
        ).subquery()
        
        suggested_users = db.query(User).filter(
            User.id != current_user.id,
            User.id.notin_(following_ids),
            User.is_active == True
        ).order_by(desc(User.created_at)).limit(limit).all()
        
        # Convert to UserProfile format
        user_profiles = []
        for user in suggested_users:
            followers_count = db.query(Follower).filter(
                Follower.following_id == user.id
            ).count()
            
            following_count = db.query(Follower).filter(
                Follower.follower_id == user.id
            ).count()
            
            posts_count = db.query(Post).filter(
                Post.user_id == user.id
            ).count()
            
            user_profiles.append(UserProfile(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                profile_image_url=user.profile_image_url,
                website=user.website,
                is_verified=user.is_verified,
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                created_at=user.created_at
            ))
        
        return user_profiles
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggested users: {str(e)}"
        )
