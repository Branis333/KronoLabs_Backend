from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, or_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Post, Hashtag, Follower, Like, Comment, SavedPost
from schemas.social_schemas import (
    SearchResponse, HashtagResponse, UserProfile, PostResponse, SuccessResponse
)
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/search", tags=["Search & Discovery"])

@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Search for users, posts, and hashtags"""
    try:
        search_term = f"%{q.lower()}%"
          # Search users
        users = db.query(User).filter(
            or_(
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
                User.bio.ilike(search_term)
            )
        ).filter(
            User.id != current_user.id,
            User.is_active == True
        ).limit(limit).all()
        
        user_profiles = []
        for user in users:
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
        
        # Search posts
        posts = db.query(Post).options(
            joinedload(Post.user)        ).filter(
            or_(
                Post.caption.ilike(search_term),
                Post.location.ilike(search_term)
            ),
            Post.visibility == 'public'
        ).order_by(desc(Post.created_at)).limit(limit).all()
        
        post_responses = []
        for post in posts:
            # Get post stats
            likes_count = db.query(Like).filter(Like.post_id == post.id).count()
            comments_count = db.query(Comment).filter(Comment.post_id == post.id).count()
            
            # Check if current user liked/saved the post
            is_liked = db.query(Like).filter(
                Like.post_id == post.id,
                Like.user_id == current_user.id
            ).first() is not None
            
            is_saved = db.query(SavedPost).filter(
                SavedPost.post_id == post.id,
                SavedPost.user_id == current_user.id
            ).first() is not None
            
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
                is_saved=is_saved            ))
        
        # Search hashtags
        hashtag_query = q.strip('#').lower()
        hashtags = db.query(Hashtag.hashtag).filter(
            Hashtag.hashtag.ilike(f"%{hashtag_query}%")
        ).distinct().limit(limit).all()
        
        hashtag_list = [f"#{tag[0]}" for tag in hashtags]
        
        return SearchResponse(
            users=user_profiles,
            posts=post_responses,
            hashtags=hashtag_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/hashtag/{hashtag_name}", response_model=HashtagResponse)
async def get_hashtag_posts(
    hashtag_name: str,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get posts for a specific hashtag"""
    try:
        hashtag_clean = hashtag_name.strip('#').lower()
        
        # Get posts with this hashtag
        posts = db.query(Post).options(
            joinedload(Post.user)
        ).join(
            Hashtag, Post.id == Hashtag.post_id
        ).filter(
            Hashtag.hashtag == hashtag_clean,
            Post.visibility == 'public'
        ).order_by(desc(Post.created_at)).offset(offset).limit(limit).all()
        
        # Get total count
        posts_count = db.query(Post).join(
            Hashtag, Post.id == Hashtag.post_id
        ).filter(
            Hashtag.hashtag == hashtag_clean,
            Post.visibility == 'public'
        ).count()
        
        post_responses = []
        for post in posts:
            # Get post stats
            likes_count = db.query(Like).filter(Like.post_id == post.id).count()
            comments_count = db.query(Comment).filter(Comment.post_id == post.id).count()
            
            # Check if current user liked/saved the post
            is_liked = db.query(Like).filter(
                Like.post_id == post.id,
                Like.user_id == current_user.id
            ).first() is not None
            
            is_saved = db.query(SavedPost).filter(
                SavedPost.post_id == post.id,
                SavedPost.user_id == current_user.id
            ).first() is not None
            
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
                is_saved=is_saved
            ))
        
        return HashtagResponse(
            hashtag=f"#{hashtag_clean}",
            posts_count=posts_count,
            posts=post_responses
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hashtag posts: {str(e)}"
        )

@router.get("/trending-hashtags", response_model=List[HashtagResponse])
async def get_trending_hashtags(
    limit: int = Query(10, le=20),
    days: int = Query(7, le=30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get trending hashtags"""
    try:
        from datetime import timedelta
        
        # Calculate date threshold
        date_threshold = datetime.utcnow() - timedelta(days=days)
        
        # Get hashtags with post counts from recent posts
        trending = db.query(
            Hashtag.hashtag,
            func.count(Hashtag.post_id).label('post_count')
        ).join(
            Post, Hashtag.post_id == Post.id
        ).filter(
            Post.created_at >= date_threshold,
            Post.visibility == 'public'
        ).group_by(
            Hashtag.hashtag
        ).order_by(
            desc('post_count')
        ).limit(limit).all()
        
        trending_responses = []
        for hashtag, count in trending:
            trending_responses.append(HashtagResponse(
                hashtag=f"#{hashtag}",
                posts_count=count,
                posts=[]  # Don't include posts in trending list for performance
            ))
        
        return trending_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending hashtags: {str(e)}"
        )

@router.get("/explore", response_model=List[PostResponse])
async def explore_posts(
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get explore posts (popular/trending posts)"""
    try:
        # Get posts not from followed users, ordered by engagement
        following_ids = db.query(Follower.following_id).filter(
            Follower.follower_id == current_user.id
        ).subquery()
        
        posts = db.query(Post).options(
            joinedload(Post.user)
        ).filter(
            Post.visibility == 'public',
            Post.user_id != current_user.id,
            Post.user_id.notin_(following_ids)
        ).order_by(desc(Post.created_at)).offset(offset).limit(limit).all()
        
        post_responses = []
        for post in posts:
            # Get post stats
            likes_count = db.query(Like).filter(Like.post_id == post.id).count()
            comments_count = db.query(Comment).filter(Comment.post_id == post.id).count()
            
            # Check if current user liked/saved the post
            is_liked = db.query(Like).filter(
                Like.post_id == post.id,
                Like.user_id == current_user.id
            ).first() is not None
            
            is_saved = db.query(SavedPost).filter(
                SavedPost.post_id == post.id,
                SavedPost.user_id == current_user.id
            ).first() is not None
            
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
                is_saved=is_saved
            ))
        
        return post_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get explore posts: {str(e)}"
        )

@router.get("/saved-posts", response_model=List[PostResponse])
async def get_saved_posts(
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Get user's saved posts"""
    try:
        posts = db.query(Post).options(
            joinedload(Post.user)
        ).join(
            SavedPost, Post.id == SavedPost.post_id
        ).filter(
            SavedPost.user_id == current_user.id
        ).order_by(desc(SavedPost.created_at)).offset(offset).limit(limit).all()
        
        post_responses = []
        for post in posts:
            # Get post stats
            likes_count = db.query(Like).filter(Like.post_id == post.id).count()
            comments_count = db.query(Comment).filter(Comment.post_id == post.id).count()
            
            # Check if current user liked the post
            is_liked = db.query(Like).filter(
                Like.post_id == post.id,
                Like.user_id == current_user.id
            ).first() is not None
            
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
                is_saved=True  # All posts in this list are saved
            ))
        
        return post_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved posts: {str(e)}"
        )
