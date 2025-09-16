"""
Video Processing Pipeline

YouTube-style video processing pipeline that handles:
1. Video upload and validation
2. Multi-resolution transcoding (144p to 4K)
3. Video segmentation for adaptive streaming
4. Thumbnail generation in multiple sizes
5. Binary storage in database
6. Asynchronous processing with status updates
7. Compression optimization
8. Quality selection based on source resolution

This pipeline processes videos similar to YouTube's backend:
- Accepts upload
- Analyzes source video
- Generates multiple quality versions
- Segments each quality for smooth streaming
- Stores everything as binary data in database
- Provides real-time processing status
"""

import asyncio
from typing import Dict, List, Tuple, Optional
from fastapi import UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models.social_models import Video, VideoQuality, VideoSegment
try:
    from utils.video_processor import video_processor
    FFMPEG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ FFmpeg dependencies not available: {e}")
    print("🔧 Please install: pip install ffmpeg-python opencv-python numpy")
    video_processor = None
    FFMPEG_AVAILABLE = False
import json
from datetime import datetime, timedelta

class VideoProcessingPipeline:
    """Complete video processing pipeline"""
    
    def __init__(self):
        self.processing_status = {}  # Track processing jobs
    
    async def process_video_complete(
        self,
        video_file: UploadFile,
        thumbnail_file: UploadFile,
        video_metadata: Dict,
        user_id: int,
        db: Session
    ) -> str:
        """
        Complete video processing pipeline
        
        Args:
            video_file: Uploaded video file
            thumbnail_file: Uploaded thumbnail file  
            video_metadata: Video title, description, etc.
            user_id: ID of uploading user
            db: Database session
            
        Returns:
            Video ID for tracking processing status
        """
        try:
            # Check if FFmpeg is available
            if not FFMPEG_AVAILABLE or video_processor is None:
                raise HTTPException(
                    status_code=500,
                    detail="🎬 YouTube-style video processing requires FFmpeg dependencies. "
                           "Please install: pip install ffmpeg-python opencv-python numpy pillow"
                )
            
            print("🚀 Starting YouTube-style video processing pipeline...")
            
            # Step 1: Analyze source video
            print("📊 Analyzing source video...")
            analysis = await video_processor.analyze_video(video_file)
            
            print(f"📺 Source: {analysis['original_resolution']} | "
                  f"Duration: {analysis['duration']:.1f}s | "
                  f"Size: {analysis['file_size'] / 1024 / 1024:.1f}MB")
            
            # Step 2: Generate optimized thumbnails
            print("🖼️ Generating multi-size thumbnails...")
            thumbnails = await video_processor.generate_optimized_thumbnail(
                video_file, 
                timestamp=1.0,
                sizes=[(320, 180), (480, 270), (640, 360)]
            )
            
            # Step 3: Create video record with processing status
            new_video = Video(
                user_id=user_id,
                title=video_metadata.get('title', 'Untitled Video'),
                description=video_metadata.get('description'),
                category=video_metadata.get('category'),
                tags=json.dumps(video_metadata.get('tags', [])) if video_metadata.get('tags') else None,
                is_public=video_metadata.get('is_public', True),
                
                # Source video metadata
                original_filename=video_file.filename,
                duration=int(analysis['duration']),
                original_resolution=analysis['original_resolution'],
                fps=int(analysis['fps']),
                
                # Thumbnails (multiple sizes)
                thumbnail_small_data=thumbnails[0]['thumbnail_data'],   # 320x180
                thumbnail_medium_data=thumbnails[1]['thumbnail_data'],  # 480x270
                thumbnail_large_data=thumbnails[2]['thumbnail_data'],   # 640x360
                thumbnail_mime_type="image/jpeg",
                
                processing_status="processing"
            )
            
            db.add(new_video)
            db.flush()  # Get video ID
            video_id = str(new_video.id)
            
            # Step 4: Start async processing
            self.processing_status[video_id] = {
                "status": "processing",
                "progress": 0,
                "current_step": "Starting transcoding...",
                "qualities_completed": [],
                "total_qualities": len(analysis['optimal_qualities']),
                "start_time": datetime.utcnow()
            }
            
            print(f"🎬 Processing {len(analysis['optimal_qualities'])} quality levels: {analysis['optimal_qualities']}")
            
            # Step 5: Process each quality level
            for i, quality in enumerate(analysis['optimal_qualities']):
                print(f"🔄 Processing {quality} ({i+1}/{len(analysis['optimal_qualities'])})...")
                
                # Update status
                self.processing_status[video_id].update({
                    "current_step": f"Processing {quality}...",
                    "progress": int((i / len(analysis['optimal_qualities'])) * 100)
                })
                
                # Create temporary file from video content
                import tempfile
                video_file.file.seek(0)  # Reset to beginning
                video_content = video_file.file.read()
                
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                    temp_file.write(video_content)
                    temp_input_path = temp_file.name
                
                try:
                    # Process quality with segmentation
                    segments = await video_processor._process_quality_with_segments(
                        temp_input_path,
                        quality,
                        analysis
                    )
                finally:
                    # Cleanup temporary file
                    import os
                    try:
                        os.unlink(temp_input_path)
                    except:
                        pass
                
                # Create VideoQuality record
                video_quality = VideoQuality(
                    video_id=new_video.id,
                    quality=quality,
                    resolution=video_processor.QUALITY_PRESETS[quality]['resolution'],
                    bitrate=video_processor.QUALITY_PRESETS[quality]['bitrate'],
                    codec=video_processor.QUALITY_PRESETS[quality]['codec'],
                    fps=video_processor.QUALITY_PRESETS[quality]['fps'],
                    is_segmented=True,
                    segment_duration=video_processor.SEGMENT_DURATION,
                    total_segments=len(segments),
                    total_size=sum(seg['segment_size'] for seg in segments)
                )
                
                db.add(video_quality)
                db.flush()  # Get quality ID
                
                # Store segments
                for segment_data in segments:
                    video_segment = VideoSegment(
                        video_quality_id=video_quality.id,
                        segment_index=segment_data['segment_index'],
                        segment_data=segment_data['segment_data'],
                        segment_size=segment_data['segment_size'],
                        duration=segment_data['duration'],
                        start_time=segment_data['segment_index'] * video_processor.SEGMENT_DURATION,
                        end_time=(segment_data['segment_index'] + 1) * video_processor.SEGMENT_DURATION
                    )
                    db.add(video_segment)
                
                # Update progress
                self.processing_status[video_id]['qualities_completed'].append(quality)
                
                print(f"✅ {quality} completed: {len(segments)} segments, "
                      f"{sum(seg['segment_size'] for seg in segments) / 1024 / 1024:.1f}MB")
            
            # Step 6: Mark as completed
            new_video.processing_status = "completed"
            
            # Final status update
            self.processing_status[video_id].update({
                "status": "completed",
                "progress": 100,
                "current_step": "Processing complete!",
                "end_time": datetime.utcnow()
            })
            
            db.commit()
            
            print(f"🎉 Video processing completed! Video ID: {video_id}")
            print(f"📊 Generated {len(analysis['optimal_qualities'])} quality levels")
            print(f"🎬 Total segments: {sum(len(segments) for segments in [])}")
            
            return video_id
            
        except Exception as e:
            # Mark as failed
            if 'new_video' in locals():
                new_video.processing_status = "failed"
                db.commit()
            
            if video_id in self.processing_status:
                self.processing_status[video_id].update({
                    "status": "failed",
                    "error": str(e),
                    "end_time": datetime.utcnow()
                })
            
            print(f"❌ Video processing failed: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Video processing failed: {str(e)}"
            )
    
    async def process_video_background(
        self,
        video_file: UploadFile,
        video_id: str,
        optimal_qualities: List[str],
        db: Session
    ):
        """
        Background processing of video qualities
        This runs asynchronously after the initial video record is created
        """
        try:
            print(f"🔄 Background processing for video {video_id}...")
            
            # Read video content once
            video_content = await video_file.read()
            
            # Create temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_content)
                temp_input_path = temp_file.name
            
            # Analyze video for processing
            video_file.file.seek(0)
            analysis = await video_processor.analyze_video(video_file)
            
            # Process each quality
            for i, quality in enumerate(optimal_qualities):
                print(f"🎯 Background processing {quality}...")
                
                # Update status
                if video_id in self.processing_status:
                    self.processing_status[video_id].update({
                        "current_step": f"Processing {quality}...",
                        "progress": int((i / len(optimal_qualities)) * 100)
                    })
                
                # Process with segments
                segments = await video_processor._process_quality_with_segments(
                    temp_input_path, quality, analysis
                )
                
                # Get video record
                video = db.query(Video).filter(Video.id == video_id).first()
                if not video:
                    raise Exception("Video record not found")
                
                # Create quality record
                video_quality = VideoQuality(
                    video_id=video.id,
                    quality=quality,
                    resolution=video_processor.QUALITY_PRESETS[quality]['resolution'],
                    bitrate=video_processor.QUALITY_PRESETS[quality]['bitrate'],
                    codec=video_processor.QUALITY_PRESETS[quality]['codec'],
                    fps=video_processor.QUALITY_PRESETS[quality]['fps'],
                    is_segmented=True,
                    segment_duration=video_processor.SEGMENT_DURATION,
                    total_segments=len(segments),
                    total_size=sum(seg['segment_size'] for seg in segments)
                )
                
                db.add(video_quality)
                db.flush()
                
                # Add segments
                for segment_data in segments:
                    video_segment = VideoSegment(
                        video_quality_id=video_quality.id,
                        segment_index=segment_data['segment_index'],
                        segment_data=segment_data['segment_data'],
                        segment_size=segment_data['segment_size'],
                        duration=segment_data['duration'],
                        start_time=segment_data['segment_index'] * video_processor.SEGMENT_DURATION,
                        end_time=(segment_data['segment_index'] + 1) * video_processor.SEGMENT_DURATION
                    )
                    db.add(video_segment)
                
                db.commit()
                print(f"✅ {quality} stored: {len(segments)} segments")
            
            # Update video status to completed
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.processing_status = "completed"
                db.commit()
            
            # Update processing status
            if video_id in self.processing_status:
                self.processing_status[video_id].update({
                    "status": "completed",
                    "progress": 100,
                    "current_step": "All qualities processed!",
                    "end_time": datetime.utcnow()
                })
            
            # Cleanup
            import os
            os.unlink(temp_input_path)
            
            print(f"🎉 Background processing completed for video {video_id}")
            
        except Exception as e:
            print(f"❌ Background processing failed for {video_id}: {e}")
            
            # Update video status
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.processing_status = "failed"
                db.commit()
            
            # Update processing status
            if video_id in self.processing_status:
                self.processing_status[video_id].update({
                    "status": "failed",
                    "error": str(e),
                    "end_time": datetime.utcnow()
                })
    
    def get_processing_status(self, video_id: str) -> Dict:
        """Get current processing status for a video"""
        if video_id not in self.processing_status:
            return {"status": "unknown", "error": "Video ID not found in processing queue"}
        
        status = self.processing_status[video_id].copy()
        
        # Calculate elapsed time
        if "start_time" in status:
            elapsed = (datetime.utcnow() - status["start_time"]).total_seconds()
            status["elapsed_seconds"] = int(elapsed)
        
        return status
    
    def cleanup_old_status(self, max_age_hours: int = 24):
        """Clean up old processing status records"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for video_id, status in self.processing_status.items():
            if "end_time" in status and status["end_time"] < cutoff_time:
                to_remove.append(video_id)
        
        for video_id in to_remove:
            del self.processing_status[video_id]
        
        print(f"🧹 Cleaned up {len(to_remove)} old processing status records")

# Global pipeline instance
video_pipeline = VideoProcessingPipeline()