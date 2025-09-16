"""
YouTube-Style Video Optimization & Transcoding System

This system implements YouTube's approach to video storage and streaming:
1. Multiple resolutions (144p, 240p, 360p, 480p, 720p, 1080p, 4K)
2. Multiple codecs (H.264, VP9, AV1)
3. Video segmentation for adaptive streaming
4. Compression optimization
5. Binary storage in database (no external URLs)

Features:
- Automatic transcoding to multiple qualities
- Video segmentation for smooth streaming
- Adaptive bitrate streaming support
- Efficient compression with quality optimization
- Binary storage for complete control
- Metadata extraction and optimization
"""

import os
import io
import json
import tempfile
import subprocess
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import UploadFile, HTTPException

# Try to import video processing libraries
try:
    import ffmpeg
    HAS_FFMPEG_PYTHON = True
except ImportError:
    HAS_FFMPEG_PYTHON = False

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class VideoProcessor:
    """YouTube-style video processing and optimization"""
    
    # Video quality presets (YouTube-style)
    QUALITY_PRESETS = {
        "144p": {
            "resolution": "256x144",
            "bitrate": "100k",
            "fps": 15,
            "codec": "libx264",
            "profile": "baseline",
            "preset": "fast"
        },
        "240p": {
            "resolution": "426x240", 
            "bitrate": "300k",
            "fps": 24,
            "codec": "libx264",
            "profile": "baseline",
            "preset": "fast"
        },
        "360p": {
            "resolution": "640x360",
            "bitrate": "700k", 
            "fps": 30,
            "codec": "libx264",
            "profile": "main",
            "preset": "medium"
        },
        "480p": {
            "resolution": "854x480",
            "bitrate": "1500k",
            "fps": 30, 
            "codec": "libx264",
            "profile": "main",
            "preset": "medium"
        },
        "720p": {
            "resolution": "1280x720",
            "bitrate": "3000k",
            "fps": 30,
            "codec": "libx264", 
            "profile": "high",
            "preset": "slow"
        },
        "1080p": {
            "resolution": "1920x1080",
            "bitrate": "6000k",
            "fps": 30,
            "codec": "libx264",
            "profile": "high", 
            "preset": "slow"
        },
        "1440p": {
            "resolution": "2560x1440",
            "bitrate": "12000k",
            "fps": 30,
            "codec": "libx264",
            "profile": "high",
            "preset": "slower"
        },
        "2160p": {  # 4K
            "resolution": "3840x2160", 
            "bitrate": "25000k",
            "fps": 30,
            "codec": "libx264",
            "profile": "high",
            "preset": "slower"
        }
    }
    
    # Segment duration for adaptive streaming (seconds)
    SEGMENT_DURATION = 4  # 4-second chunks like YouTube
    
    def __init__(self):
        """Initialize video processor"""
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available"""
        # Check for FFmpeg binary
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.has_ffmpeg = True
                print("✅ FFmpeg found")
            else:
                self.has_ffmpeg = False
                print("❌ FFmpeg not found")
        except FileNotFoundError:
            self.has_ffmpeg = False
            print("❌ FFmpeg not installed")
        
        if not self.has_ffmpeg:
            raise Exception(
                "FFmpeg is required for video processing. "
                "Install from https://ffmpeg.org/"
            )
    
    async def analyze_video(self, video_file: UploadFile) -> Dict:
        """
        Analyze video file to determine optimal processing parameters
        
        Args:
            video_file: Uploaded video file
            
        Returns:
            Dictionary with video metadata and analysis
        """
        if not HAS_OPENCV:
            raise HTTPException(
                status_code=500,
                detail="Video analysis requires OpenCV. Install with: pip install opencv-python"
            )
        
        try:
            # Save video to temporary file
            video_content = await video_file.read()
            video_file.file.seek(0)  # Reset for later use
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_content)
                temp_file_path = temp_file.name
            
            # Analyze with OpenCV
            cap = cv2.VideoCapture(temp_file_path)
            
            if not cap.isOpened():
                os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=400,
                    detail="Could not analyze video file"
                )
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # Get file size
            file_size = len(video_content)
            
            # Determine optimal qualities based on source resolution
            optimal_qualities = self._determine_optimal_qualities(width, height)
            
            # Clean up
            os.unlink(temp_file_path)
            
            return {
                "original_resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "fps": fps,
                "duration": duration,
                "frame_count": frame_count,
                "file_size": file_size,
                "optimal_qualities": optimal_qualities,
                "estimated_processing_time": len(optimal_qualities) * 30  # Rough estimate
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Video analysis failed: {str(e)}"
            )
    
    def _determine_optimal_qualities(self, width: int, height: int) -> List[str]:
        """
        Determine which qualities to generate based on source resolution
        (Don't upscale - only downscale or maintain quality)
        """
        source_pixels = width * height
        optimal_qualities = []
        
        # Always include original quality if it's a standard resolution
        for quality_name, preset in self.QUALITY_PRESETS.items():
            target_width, target_height = map(int, preset["resolution"].split('x'))
            target_pixels = target_width * target_height
            
            # Only include qualities that don't upscale
            if target_pixels <= source_pixels:
                optimal_qualities.append(quality_name)
        
        # Ensure we have at least one quality
        if not optimal_qualities:
            optimal_qualities = ["360p"]  # Fallback
        
        return optimal_qualities
    
    async def process_video_optimized(
        self, 
        video_file: UploadFile,
        target_qualities: Optional[List[str]] = None,
        generate_segments: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Process video into multiple optimized formats (YouTube-style)
        
        Args:
            video_file: Uploaded video file
            target_qualities: List of qualities to generate (auto-detected if None)
            generate_segments: Whether to create segments for adaptive streaming
            
        Returns:
            Dictionary with processed video data for each quality
        """
        try:
            # Analyze video first
            analysis = await self.analyze_video(video_file)
            
            if target_qualities is None:
                target_qualities = analysis["optimal_qualities"]
            
            print(f"🎬 Processing video: {analysis['original_resolution']} -> {target_qualities}")
            
            # Read video content
            video_content = await video_file.read()
            
            # Save to temporary file for FFmpeg processing
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input:
                temp_input.write(video_content)
                input_path = temp_input.name
            
            # Process each quality
            processed_videos = {}
            
            for quality in target_qualities:
                print(f"🔄 Processing {quality}...")
                
                if generate_segments:
                    # Generate segmented video for adaptive streaming
                    segments = await self._process_quality_with_segments(
                        input_path, quality, analysis
                    )
                    processed_videos[quality] = segments
                else:
                    # Generate single file
                    video_data = await self._process_quality_single(
                        input_path, quality, analysis  
                    )
                    processed_videos[quality] = [video_data]
            
            # Clean up
            os.unlink(input_path)
            
            return processed_videos
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Video processing failed: {str(e)}"
            )
    
    async def _process_quality_with_segments(
        self, 
        input_path: str, 
        quality: str, 
        analysis: Dict
    ) -> List[Dict]:
        """
        Process video into segments for adaptive streaming
        
        Returns:
            List of segment dictionaries with binary data
        """
        preset = self.QUALITY_PRESETS[quality]
        
        # Create temporary directory for segments
        with tempfile.TemporaryDirectory() as temp_dir:
            segment_pattern = os.path.join(temp_dir, f"segment_{quality}_%03d.mp4")
            
            # FFmpeg command for segmentation
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', preset['codec'],
                '-b:v', preset['bitrate'],
                '-s', preset['resolution'],
                '-r', str(preset['fps']),
                '-profile:v', preset['profile'],
                '-preset', preset['preset'],
                '-f', 'segment',
                '-segment_time', str(self.SEGMENT_DURATION),
                '-segment_format', 'mp4',
                '-reset_timestamps', '1',
                segment_pattern,
                '-y'  # Overwrite output files
            ]
            
            # Run FFmpeg (using synchronous call for Windows compatibility)
            import subprocess
            
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode() if result.stderr else "Unknown FFmpeg error"
                    raise Exception(f"FFmpeg segmentation failed: {error_msg}")
                    
            except subprocess.TimeoutExpired:
                raise Exception("FFmpeg processing timed out (5 minutes)")
            except Exception as e:
                raise Exception(f"FFmpeg execution failed: {str(e)}")
            
            # Read all segment files
            segments = []
            segment_files = sorted([
                f for f in os.listdir(temp_dir) 
                if f.startswith(f'segment_{quality}_') and f.endswith('.mp4')
            ])
            
            for i, segment_file in enumerate(segment_files):
                segment_path = os.path.join(temp_dir, segment_file)
                
                with open(segment_path, 'rb') as f:
                    segment_data = f.read()
                
                segments.append({
                    "segment_index": i,
                    "segment_data": segment_data,
                    "segment_size": len(segment_data),
                    "duration": self.SEGMENT_DURATION,
                    "quality": quality,
                    "codec": preset['codec'],
                    "resolution": preset['resolution'],
                    "bitrate": preset['bitrate']
                })
            
            return segments
    
    async def _process_quality_single(
        self, 
        input_path: str, 
        quality: str, 
        analysis: Dict
    ) -> Dict:
        """
        Process video into single file for a specific quality
        
        Returns:
            Dictionary with video binary data and metadata
        """
        preset = self.QUALITY_PRESETS[quality]
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
            output_path = temp_output.name
        
        try:
            # FFmpeg command for single file processing
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', preset['codec'],
                '-b:v', preset['bitrate'],
                '-s', preset['resolution'],
                '-r', str(preset['fps']),
                '-profile:v', preset['profile'],
                '-preset', preset['preset'],
                '-movflags', '+faststart',  # Optimize for streaming
                output_path,
                '-y'  # Overwrite output
            ]
            
            # Run FFmpeg
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg processing failed: {stderr.decode()}")
            
            # Read processed video
            with open(output_path, 'rb') as f:
                video_data = f.read()
            
            return {
                "video_data": video_data,
                "video_size": len(video_data),
                "quality": quality,
                "codec": preset['codec'],
                "resolution": preset['resolution'],
                "bitrate": preset['bitrate'],
                "is_segmented": False
            }
            
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    async def generate_optimized_thumbnail(
        self, 
        video_file: UploadFile, 
        timestamp: float = 1.0,
        sizes: List[Tuple[int, int]] = [(320, 180), (480, 270), (640, 360)]
    ) -> List[Dict]:
        """
        Generate multiple thumbnail sizes (YouTube-style)
        
        Args:
            video_file: Video file
            timestamp: Time to capture thumbnail (seconds)
            sizes: List of (width, height) tuples for different sizes
            
        Returns:
            List of thumbnail data dictionaries
        """
        if not HAS_OPENCV:
            raise HTTPException(
                status_code=500,
                detail="Thumbnail generation requires OpenCV"
            )
        
        try:
            # Save video to temporary file
            video_content = await video_file.read()
            video_file.file.seek(0)  # Reset for later use
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_content)
                temp_file_path = temp_file.name
            
            # Open video with OpenCV
            cap = cv2.VideoCapture(temp_file_path)
            
            if not cap.isOpened():
                os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=400,
                    detail="Could not process video for thumbnail"
                )
            
            # Get frame at timestamp
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(timestamp * fps) if fps > 0 else 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            os.unlink(temp_file_path)
            
            if not ret:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract frame for thumbnail"
                )
            
            # Generate thumbnails in different sizes
            thumbnails = []
            
            from PIL import Image
            
            for width, height in sizes:
                # Convert OpenCV frame to PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                
                # Resize maintaining aspect ratio
                pil_image.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
                thumbnail_bytes = img_byte_arr.getvalue()
                
                thumbnails.append({
                    "thumbnail_data": thumbnail_bytes,
                    "thumbnail_size": len(thumbnail_bytes),
                    "width": width,
                    "height": height,
                    "mime_type": "image/jpeg",
                    "quality": "high" if width >= 640 else "medium" if width >= 480 else "low"
                })
            
            return thumbnails
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Thumbnail generation failed: {str(e)}"
            )

# Global processor instance
video_processor = VideoProcessor()