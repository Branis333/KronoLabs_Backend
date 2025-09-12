"""
Comics API

This module provides comprehensive comic management functionality:

Features:
- Create comics with thumbnails and multiple pages
- Upload comic pages (JPEG/PNG images only)
- Browse and discover comics
- Like and save comics
- Comment on comics with threaded replies
- Update comic status (ongoing, completed, hiatus)
- Delete comics (creator only)
- Genre categorization
- Public/private visibility

Comic Structure:
- Each comic has a thumbnail and title
- Comics contain multiple pages in sequential order
- Pages are stored as binary data in the database
- Support for unlimited pages per comic

API Usage:
POST /comics/ - Create new comic with thumbnail and initial pages
POST /comics/{comic_id}/pages - Add more pages to existing comic
GET /comics/ - Browse all public comics
GET /comics/{comic_id} - Get specific comic with all pages
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_, and_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Comic, ComicPage, ComicLike, ComicComment, SavedComic
from schemas.social_schemas import (
    ComicCreate, ComicResponse, ComicCommentCreate, ComicCommentResponse,
    ComicsResponse, SuccessResponse, UserProfile, ComicUpdateStatus, ComicUpdateInfo
)
from utils.media_utils import MediaUtils
from typing import List, Optional
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

router = APIRouter(prefix="/comics", tags=["Comics"])

@router.post("/", response_model=ComicResponse)
async def create_comic(
    thumbnail: UploadFile = File(...),
    pages: List[UploadFile] = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    genre: Optional[str] = Form(None),
    status: str = Form("ongoing"),
    is_public: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a new comic with thumbnail and initial pages"""
    try:
        # Validate input
        if not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comic title is required"
            )
        
        if not pages or len(pages) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one comic page is required"
            )
        
        if len(pages) > 50:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 pages per comic allowed"
            )
        
        # Validate status
        if status not in ["ongoing", "completed", "hiatus"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'ongoing', 'completed', or 'hiatus'"
            )
        
        # Process thumbnail
        thumbnail_processed = await MediaUtils.process_comic_thumbnail(thumbnail)
        
        # Create the comic
        new_comic = Comic(
            user_id=current_user.id,
            title=title.strip(),
            description=description.strip() if description else None,
            thumbnail_data=thumbnail_processed["media_data"],
            thumbnail_mime_type=thumbnail_processed["media_mime_type"],
            genre=genre.strip() if genre else None,
            status=status,
            is_public=is_public
        )
        
        db.add(new_comic)
        db.flush()  # Get the comic ID
        
        # Process and add pages
        comic_pages = []
        for index, page_file in enumerate(pages):
            if not page_file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Page {index + 1} must have a filename"
                )
            
            # Process page
            page_processed = await MediaUtils.process_comic_page(page_file)
            
            comic_page = ComicPage(
                comic_id=new_comic.id,
                page_number=index + 1,
                page_data=page_processed["media_data"],
                page_mime_type=page_processed["media_mime_type"]
            )
            
            db.add(comic_page)
            comic_pages.append(comic_page)
        
        db.commit()
        db.refresh(new_comic)
        
        # Create response
        user_profile = create_user_profile(current_user)
        
        # Encode thumbnail for response
        thumbnail_b64 = base64.b64encode(new_comic.thumbnail_data).decode('utf-8')
        
        # Create page responses
        page_responses = []
        for page in comic_pages:
            page_data_b64 = base64.b64encode(page.page_data).decode('utf-8')
            page_responses.append({
                "id": page.id,
                "page_number": page.page_number,
                "page_data": page_data_b64,
                "page_mime_type": page.page_mime_type,
                "page_title": page.page_title,
                "created_at": page.created_at
            })
        
        return ComicResponse(
            id=new_comic.id,
            user_id=new_comic.user_id,
            user=user_profile,
            title=new_comic.title,
            description=new_comic.description,
            thumbnail_data=thumbnail_b64,
            thumbnail_mime_type=new_comic.thumbnail_mime_type,
            genre=new_comic.genre,
            status=new_comic.status,
            is_public=new_comic.is_public,
            created_at=new_comic.created_at,
            updated_at=new_comic.updated_at,
            pages_count=len(comic_pages),
            likes_count=0,
            comments_count=0,
            is_liked=False,
            is_saved=False,
            pages=page_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comic: {str(e)}"
        )

@router.get("/", response_model=ComicsResponse)
async def get_comics(
    limit: int = Query(20, le=50, ge=1),
    offset: int = Query(0, ge=0),
    genre: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get all public comics with optional filtering"""
    try:
        # Base query - only public comics or user's own comics
        query = db.query(Comic).options(
            joinedload(Comic.user),
            joinedload(Comic.likes),
            joinedload(Comic.comments),
            joinedload(Comic.pages)
        )
        
        if current_user:
            # Show public comics + user's own comics
            query = query.filter(
                or_(
                    Comic.is_public == True,
                    Comic.user_id == current_user.id
                )
            )
        else:
            # Only public comics for non-authenticated users
            query = query.filter(Comic.is_public == True)
        
        # Apply filters
        if genre:
            query = query.filter(Comic.genre.ilike(f"%{genre}%"))
        
        if status and status in ["ongoing", "completed", "hiatus"]:
            query = query.filter(Comic.status == status)
        
        if search:
            query = query.filter(
                or_(
                    Comic.title.ilike(f"%{search}%"),
                    Comic.description.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        comics = query.order_by(desc(Comic.updated_at)).offset(offset).limit(limit + 1).all()
        
        has_next = len(comics) > limit
        if has_next:
            comics = comics[:limit]
        
        # Convert to response format
        comic_responses = []
        for comic in comics:
            # Check if current user liked/saved this comic
            is_liked = False
            is_saved = False
            
            if current_user:
                is_liked = any(like.user_id == current_user.id for like in comic.likes)
                is_saved = any(saved.user_id == current_user.id for saved in comic.saved_by)
            
            user_profile = create_user_profile(comic.user)
            
            # Encode thumbnail
            thumbnail_b64 = base64.b64encode(comic.thumbnail_data).decode('utf-8')
            
            comic_responses.append(ComicResponse(
                id=comic.id,
                user_id=comic.user_id,
                user=user_profile,
                title=comic.title,
                description=comic.description,
                thumbnail_data=thumbnail_b64,
                thumbnail_mime_type=comic.thumbnail_mime_type,
                genre=comic.genre,
                status=comic.status,
                is_public=comic.is_public,
                created_at=comic.created_at,
                updated_at=comic.updated_at,
                pages_count=len(comic.pages),
                likes_count=len(comic.likes),
                comments_count=len(comic.comments),
                is_liked=is_liked,
                is_saved=is_saved,
                pages=[]  # Don't include full pages in list view for performance
            ))
        
        return ComicsResponse(
            comics=comic_responses,
            has_next=has_next,
            total_count=total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comics: {str(e)}"
        )

@router.get("/{comic_id}", response_model=ComicResponse)
async def get_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """Get a specific comic with all pages"""
    try:
        comic = db.query(Comic).options(
            joinedload(Comic.user),
            joinedload(Comic.likes),
            joinedload(Comic.comments),
            joinedload(Comic.pages),
            joinedload(Comic.saved_by)
        ).filter(Comic.id == comic_id).first()
        
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        # Check if user can access this comic
        if not comic.is_public and (not current_user or comic.user_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This comic is private"
            )
        
        # Check if current user liked/saved this comic
        is_liked = False
        is_saved = False
        
        if current_user:
            is_liked = any(like.user_id == current_user.id for like in comic.likes)
            is_saved = any(saved.user_id == current_user.id for saved in comic.saved_by)
        
        user_profile = create_user_profile(comic.user)
        
        # Encode thumbnail
        thumbnail_b64 = base64.b64encode(comic.thumbnail_data).decode('utf-8')
        
        # Create page responses with full data
        page_responses = []
        sorted_pages = sorted(comic.pages, key=lambda x: x.page_number)
        
        for page in sorted_pages:
            page_data_b64 = base64.b64encode(page.page_data).decode('utf-8')
            page_responses.append({
                "id": page.id,
                "page_number": page.page_number,
                "page_data": page_data_b64,
                "page_mime_type": page.page_mime_type,
                "page_title": page.page_title,
                "created_at": page.created_at
            })
        
        return ComicResponse(
            id=comic.id,
            user_id=comic.user_id,
            user=user_profile,
            title=comic.title,
            description=comic.description,
            thumbnail_data=thumbnail_b64,
            thumbnail_mime_type=comic.thumbnail_mime_type,
            genre=comic.genre,
            status=comic.status,
            is_public=comic.is_public,
            created_at=comic.created_at,
            updated_at=comic.updated_at,
            pages_count=len(comic.pages),
            likes_count=len(comic.likes),
            comments_count=len(comic.comments),
            is_liked=is_liked,
            is_saved=is_saved,
            pages=page_responses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comic: {str(e)}"
        )

@router.post("/{comic_id}/pages", response_model=SuccessResponse)
async def add_comic_pages(
    comic_id: str,
    pages: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Add more pages to an existing comic"""
    try:
        # Get the comic
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        # Check if user owns this comic
        if comic.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add pages to your own comics"
            )
        
        # Validate pages
        if not pages or len(pages) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one page is required"
            )
        
        # Get current highest page number
        highest_page = db.query(func.max(ComicPage.page_number)).filter(
            ComicPage.comic_id == comic.id
        ).scalar() or 0
        
        # Check total pages limit
        current_page_count = db.query(ComicPage).filter(ComicPage.comic_id == comic.id).count()
        if current_page_count + len(pages) > 100:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 pages per comic allowed"
            )
        
        # Process and add new pages
        new_pages = []
        for index, page_file in enumerate(pages):
            if not page_file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Page {index + 1} must have a filename"
                )
            
            # Process page
            page_processed = await MediaUtils.process_comic_page(page_file)
            
            comic_page = ComicPage(
                comic_id=comic.id,
                page_number=highest_page + index + 1,
                page_data=page_processed["media_data"],
                page_mime_type=page_processed["media_mime_type"]
            )
            
            db.add(comic_page)
            new_pages.append(comic_page)
        
        # Update comic's updated_at timestamp
        comic.updated_at = func.now()
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=f"Successfully added {len(new_pages)} pages to comic"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add pages: {str(e)}"
        )

@router.post("/{comic_id}/like", response_model=SuccessResponse)
async def like_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Like or unlike a comic"""
    try:
        # Check if comic exists
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        # Check if already liked
        existing_like = db.query(ComicLike).filter(
            ComicLike.comic_id == comic_id,
            ComicLike.user_id == current_user.id
        ).first()
        
        if existing_like:
            # Unlike
            db.delete(existing_like)
            message = "Comic unliked successfully"
        else:
            # Like
            new_like = ComicLike(
                comic_id=comic.id,
                user_id=current_user.id
            )
            db.add(new_like)
            message = "Comic liked successfully"
        
        db.commit()
        
        return SuccessResponse(success=True, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process like: {str(e)}"
        )

@router.post("/{comic_id}/save", response_model=SuccessResponse)
async def save_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Save or unsave a comic"""
    try:
        # Check if comic exists
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        # Check if already saved
        existing_save = db.query(SavedComic).filter(
            SavedComic.comic_id == comic_id,
            SavedComic.user_id == current_user.id
        ).first()
        
        if existing_save:
            # Unsave
            db.delete(existing_save)
            message = "Comic removed from saved list"
        else:
            # Save
            new_save = SavedComic(
                comic_id=comic.id,
                user_id=current_user.id
            )
            db.add(new_save)
            message = "Comic saved successfully"
        
        db.commit()
        
        return SuccessResponse(success=True, message=message)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process save: {str(e)}"
        )

@router.post("/{comic_id}/comments", response_model=ComicCommentResponse)
async def create_comic_comment(
    comic_id: str,
    comment_data: ComicCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Create a comment on a comic"""
    try:
        # Check if comic exists
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        # Create comment
        new_comment = ComicComment(
            comic_id=comic.id,
            user_id=current_user.id,
            text=comment_data.text,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        user_profile = create_user_profile(current_user)
        
        return ComicCommentResponse(
            id=new_comment.id,
            comic_id=new_comment.comic_id,
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

@router.get("/{comic_id}/comments", response_model=List[ComicCommentResponse])
async def get_comic_comments(
    comic_id: str,
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get comments for a comic"""
    try:
        comments = db.query(ComicComment).options(
            joinedload(ComicComment.user)
        ).filter(
            ComicComment.comic_id == comic_id
        ).order_by(desc(ComicComment.created_at)).offset(offset).limit(limit).all()
        
        comment_responses = []
        for comment in comments:
            user_profile = create_user_profile(comment.user)
            
            # Count replies
            replies_count = db.query(ComicComment).filter(
                ComicComment.parent_comment_id == comment.id
            ).count()
            
            comment_responses.append(ComicCommentResponse(
                id=comment.id,
                comic_id=comment.comic_id,
                user_id=comment.user_id,
                user=user_profile,
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

@router.patch("/{comic_id}/status", response_model=SuccessResponse)
async def update_comic_status(
    comic_id: str,
    status_update: ComicUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Update comic status (ongoing, completed, hiatus)"""
    try:
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        if comic.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own comics"
            )
        
        comic.status = status_update.status
        comic.updated_at = func.now()
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=f"Comic status updated to '{status_update.status}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )

@router.patch("/{comic_id}", response_model=SuccessResponse)
async def update_comic_info(
    comic_id: str,
    comic_update: ComicUpdateInfo,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Update comic information"""
    try:
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        if comic.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own comics"
            )
        
        # Update fields if provided
        if comic_update.title is not None:
            comic.title = comic_update.title.strip()
        
        if comic_update.description is not None:
            comic.description = comic_update.description.strip() if comic_update.description else None
        
        if comic_update.genre is not None:
            comic.genre = comic_update.genre.strip() if comic_update.genre else None
        
        if comic_update.is_public is not None:
            comic.is_public = comic_update.is_public
        
        comic.updated_at = func.now()
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Comic information updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update comic: {str(e)}"
        )

@router.delete("/{comic_id}", response_model=SuccessResponse)
async def delete_comic(
    comic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token)
):
    """Delete a comic (creator only)"""
    try:
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        
        if not comic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comic not found"
            )
        
        if comic.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comics"
            )
        
        # Delete comic (cascade will handle pages, likes, comments, saves)
        db.delete(comic)
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Comic deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comic: {str(e)}"
        )

@router.get("/media/thumbnail/{comic_id}")
async def serve_comic_thumbnail(
    comic_id: str,
    db: Session = Depends(get_db)
):
    """Serve comic thumbnail from database"""
    try:
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        
        if not comic or not comic.thumbnail_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found"
            )
        
        return Response(
            content=comic.thumbnail_data,
            media_type=comic.thumbnail_mime_type or "image/jpeg",
            headers={
                "Cache-Control": "public, max-age=31536000"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve thumbnail: {str(e)}"
        )

@router.get("/media/page/{page_id}")
async def serve_comic_page(
    page_id: str,
    db: Session = Depends(get_db)
):
    """Serve comic page from database"""
    try:
        page = db.query(ComicPage).filter(ComicPage.id == page_id).first()
        
        if not page or not page.page_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Page not found"
            )
        
        return Response(
            content=page.page_data,
            media_type=page.page_mime_type or "image/jpeg",
            headers={
                "Cache-Control": "public, max-age=31536000"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve page: {str(e)}"
        )
