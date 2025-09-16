"""
Adaptive Bitrate Streaming API

This module provides YouTube-style adaptive streaming functionality:
- Serves video segments based on client bandwidth/capability
- Dynamic quality switching during playback
- Efficient binary data streaming from database
- DASH-like streaming support
- Bandwidth-aware quality selection

Features:
- Multiple quality levels (144p to 4K)
- Segmented streaming for smooth playback
- Automatic quality detection based on client hints
- Progressive download support
- Bandwidth optimization
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_
from db.connection import get_db
from db.verify_token import verify_token
from models.users_models import User
from models.social_models import Video, VideoQuality, VideoSegment
from typing import Optional, List, Dict
import json
import io
from datetime import datetime, timedelta

streaming_router = APIRouter(prefix="/streaming", tags=["Video Streaming"])

class AdaptiveStreamingService:
    """Service for managing adaptive video streaming"""
    
    # Quality priorities (lower number = higher priority for auto-selection)
    QUALITY_PRIORITY = {
        "2160p": 0,  # 4K - highest quality
        "1440p": 1,  # 2K 
        "1080p": 2,  # Full HD
        "720p": 3,   # HD
        "480p": 4,   # SD
        "360p": 5,   # Low
        "240p": 6,   # Very low
        "144p": 7    # Ultra low
    }
    
    @staticmethod
    def detect_optimal_quality(
        user_agent: str = "",
        connection: str = "", 
        bandwidth_hint: Optional[int] = None,
        available_qualities: List[str] = None
    ) -> str:
        """
        Detect optimal video quality based on client capabilities
        
        Args:
            user_agent: Client user agent string
            connection: Network connection type hint
            bandwidth_hint: Estimated bandwidth in kbps
            available_qualities: List of available qualities for the video
            
        Returns:
            Recommended quality string
        """
        if not available_qualities:
            return "360p"  # Default fallback
        
        # Sort available qualities by priority
        sorted_qualities = sorted(
            available_qualities, 
            key=lambda q: AdaptiveStreamingService.QUALITY_PRIORITY.get(q, 999)
        )
        
        # Bandwidth-based selection
        if bandwidth_hint:
            if bandwidth_hint >= 25000:  # 25 Mbps+
                target = "2160p"
            elif bandwidth_hint >= 12000:  # 12 Mbps+  
                target = "1440p"
            elif bandwidth_hint >= 6000:   # 6 Mbps+
                target = "1080p"
            elif bandwidth_hint >= 3000:   # 3 Mbps+
                target = "720p"
            elif bandwidth_hint >= 1500:   # 1.5 Mbps+
                target = "480p"
            elif bandwidth_hint >= 700:    # 700 kbps+
                target = "360p"
            elif bandwidth_hint >= 300:    # 300 kbps+
                target = "240p"
            else:
                target = "144p"
            
            # Return highest available quality up to target
            for quality in sorted_qualities:
                if quality == target:
                    return quality
            
            # If target not available, find next best
            target_priority = AdaptiveStreamingService.QUALITY_PRIORITY.get(target, 999)
            for quality in sorted_qualities:
                if AdaptiveStreamingService.QUALITY_PRIORITY.get(quality, 999) >= target_priority:
                    return quality
        
        # Connection type-based fallback
        if "mobile" in user_agent.lower() or "android" in user_agent.lower():
            # Mobile devices - prefer lower bandwidth
            preferred = ["480p", "360p", "240p", "144p"]
            for quality in preferred:
                if quality in available_qualities:
                    return quality
        
        # Desktop/unknown - prefer higher quality
        preferred = ["720p", "1080p", "480p", "360p"]
        for quality in preferred:
            if quality in available_qualities:
                return quality
        
        # Ultimate fallback
        return sorted_qualities[0] if sorted_qualities else "360p"

@streaming_router.get("/video/{video_id}/manifest")
async def get_video_manifest(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """
    Get video streaming manifest (like DASH MPD)
    Returns available qualities and segment information
    """
    try:
        # Get video with all qualities and segments
        video = db.query(Video).options(
            joinedload(Video.video_qualities).joinedload(VideoQuality.segments),
            joinedload(Video.user)
        ).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check access permissions
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Video is private")
        
        # Build manifest
        qualities = []
        for quality in video.video_qualities:
            segments = []
            for segment in sorted(quality.segments, key=lambda s: s.segment_index):
                segments.append({
                    "index": segment.segment_index,
                    "duration": segment.duration,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "size": segment.segment_size,
                    "url": f"/streaming/video/{video_id}/quality/{quality.quality}/segment/{segment.segment_index}"
                })
            
            qualities.append({
                "quality": quality.quality,
                "resolution": quality.resolution,
                "bitrate": quality.bitrate,
                "codec": quality.codec,
                "fps": quality.fps,
                "segment_duration": quality.segment_duration,
                "total_segments": quality.total_segments,
                "total_size": quality.total_size,
                "segments": segments
            })
        
        manifest = {
            "video_id": video_id,
            "title": video.title,
            "duration": video.duration,
            "qualities": qualities,
            "available_quality_levels": [q["quality"] for q in qualities],
            "created_at": video.created_at.isoformat(),
            "manifest_type": "adaptive_streaming",
            "segment_base_url": f"/streaming/video/{video_id}"
        }
        
        return manifest
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get video manifest: {str(e)}"
        )

@streaming_router.get("/video/{video_id}/quality/{quality}/segment/{segment_index}")
async def stream_video_segment(
    video_id: str,
    quality: str,
    segment_index: int,
    request: Request,
    range: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """
    Stream a specific video segment for adaptive playback
    Supports HTTP range requests for efficient streaming
    """
    try:
        # Get the specific segment
        segment = db.query(VideoSegment).join(
            VideoQuality
        ).join(
            Video
        ).filter(
            and_(
                Video.id == video_id,
                VideoQuality.quality == quality,
                VideoSegment.segment_index == segment_index
            )
        ).first()
        
        if not segment:
            raise HTTPException(status_code=404, detail="Video segment not found")
        
        # Check video permissions
        video = segment.video_quality.video
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Video is private")
        
        # Get segment data
        segment_data = segment.segment_data
        segment_size = len(segment_data)
        
        # Handle range requests for efficient streaming
        if range:
            # Parse range header (e.g., "bytes=0-1023")
            try:
                range_match = range.replace('bytes=', '')
                start, end = range_match.split('-')
                start = int(start) if start else 0
                end = int(end) if end else segment_size - 1
                
                # Validate range
                if start >= segment_size or end >= segment_size or start > end:
                    raise HTTPException(
                        status_code=416, 
                        detail="Requested range not satisfiable"
                    )
                
                # Extract requested chunk
                chunk_data = segment_data[start:end + 1]
                chunk_size = len(chunk_data)
                
                # Return partial content
                headers = {
                    "Content-Range": f"bytes {start}-{end}/{segment_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(chunk_size),
                    "Content-Type": "video/mp4",
                    "Cache-Control": "public, max-age=3600"
                }
                
                return Response(
                    content=chunk_data,
                    status_code=206,  # Partial Content
                    headers=headers
                )
                
            except (ValueError, IndexError):
                # Invalid range header, serve full segment
                pass
        
        # Serve full segment
        headers = {
            "Content-Length": str(segment_size),
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "X-Segment-Index": str(segment_index),
            "X-Video-Quality": quality
        }
        
        return Response(
            content=segment_data,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stream segment: {str(e)}"
        )

@streaming_router.get("/video/{video_id}/auto")
async def stream_video_auto_quality(
    video_id: str,
    request: Request,
    bandwidth: Optional[int] = Query(None, description="Estimated bandwidth in kbps"),
    user_agent: Optional[str] = Header(None),
    connection: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """
    Automatically select and stream optimal video quality
    Based on client capabilities and network conditions
    """
    try:
        # Get video with available qualities
        video = db.query(Video).options(
            joinedload(Video.video_qualities)
        ).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check permissions
        if not video.is_public and (not current_user or video.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Video is private")
        
        # Get available qualities
        available_qualities = [q.quality for q in video.video_qualities]
        
        if not available_qualities:
            raise HTTPException(status_code=404, detail="No video qualities available")
        
        # Detect optimal quality
        service = AdaptiveStreamingService()
        optimal_quality = service.detect_optimal_quality(
            user_agent=user_agent or "",
            connection=connection or "",
            bandwidth_hint=bandwidth,
            available_qualities=available_qualities
        )
        
        # Redirect to the optimal quality stream
        return {
            "recommended_quality": optimal_quality,
            "available_qualities": available_qualities,
            "manifest_url": f"/streaming/video/{video_id}/manifest",
            "stream_url": f"/streaming/video/{video_id}/quality/{optimal_quality}/segment/0",
            "auto_detection": {
                "bandwidth_hint": bandwidth,
                "user_agent_mobile": "mobile" in (user_agent or "").lower(),
                "connection_type": connection
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to auto-select quality: {str(e)}"
        )

@streaming_router.get("/video/{video_id}/quality/{quality}")
async def get_quality_info(
    video_id: str,
    quality: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(verify_token)
):
    """
    Get information about a specific video quality
    """
    try:
        # Get quality info
        video_quality = db.query(VideoQuality).join(
            Video
        ).filter(
            and_(
                Video.id == video_id,
                VideoQuality.quality == quality
            )
        ).first()
        
        if not video_quality:
            raise HTTPException(status_code=404, detail="Video quality not found")
        
        # Check permissions
        if not video_quality.video.is_public and (
            not current_user or video_quality.video.user_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Video is private")
        
        # Get segment information
        segments = db.query(VideoSegment).filter(
            VideoSegment.video_quality_id == video_quality.id
        ).order_by(VideoSegment.segment_index).all()
        
        segment_info = []
        for segment in segments:
            segment_info.append({
                "index": segment.segment_index,
                "size": segment.segment_size,
                "duration": segment.duration,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "url": f"/streaming/video/{video_id}/quality/{quality}/segment/{segment.segment_index}"
            })
        
        return {
            "video_id": video_id,
            "quality": video_quality.quality,
            "resolution": video_quality.resolution,
            "bitrate": video_quality.bitrate,
            "codec": video_quality.codec,
            "fps": video_quality.fps,
            "total_segments": video_quality.total_segments,
            "segment_duration": video_quality.segment_duration,
            "total_size": video_quality.total_size,
            "segments": segment_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality info: {str(e)}"
        )

@streaming_router.get("/video/{video_id}/thumbnail/{size}")
async def serve_video_thumbnail(
    video_id: str,
    size: str,  # small, medium, large
    db: Session = Depends(get_db)
):
    """
    Serve video thumbnails in different sizes
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Select appropriate thumbnail size
        thumbnail_data = None
        if size == "small" and video.thumbnail_small_data:
            thumbnail_data = video.thumbnail_small_data
        elif size == "medium" and video.thumbnail_medium_data:
            thumbnail_data = video.thumbnail_medium_data
        elif size == "large" and video.thumbnail_large_data:
            thumbnail_data = video.thumbnail_large_data
        else:
            # Fallback to large thumbnail
            thumbnail_data = video.thumbnail_large_data
        
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return Response(
            content=thumbnail_data,
            media_type=video.thumbnail_mime_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 24 hours
                "Content-Length": str(len(thumbnail_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serve thumbnail: {str(e)}"
        )