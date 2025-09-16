"""
Simplified Video Processor (No FFmpeg Required)
This is a fallback processor for testing without external dependencies
"""

import io
from PIL import Image
import uuid
from typing import Dict, List, Tuple, Optional
import json

class SimpleVideoProcessor:
    """Simplified video processor that works without FFmpeg"""
    
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    
    async def analyze_video(self, video_content: bytes, filename: str) -> Dict:
        """Basic video analysis without FFmpeg"""
        return {
            'duration': 30,  # Default duration
            'width': 1280,
            'height': 720,
            'fps': 30,
            'size': len(video_content),
            'format': filename.split('.')[-1].lower() if '.' in filename else 'mp4'
        }
    
    async def generate_thumbnails(self, video_content: bytes, filename: str) -> Dict[str, bytes]:
        """Generate simple placeholder thumbnails"""
        # Create simple colored thumbnails as placeholders
        thumbnails = {}
        
        sizes = {
            'small': (320, 180),
            'medium': (480, 270), 
            'large': (640, 360)
        }
        
        colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]  # Red, Green, Blue
        
        for i, (size_name, (width, height)) in enumerate(sizes.items()):
            # Create a colored rectangle as thumbnail
            img = Image.new('RGB', (width, height), colors[i % len(colors)])
            
            # Add text overlay
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                text = f"{size_name.upper()}\n{width}x{height}"
                
                # Try to use a default font, fall back to basic if not available
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Calculate text position (center)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                
                draw.text((x, y), text, fill=(255, 255, 255), font=font)
            except Exception:
                # If text drawing fails, just use the colored rectangle
                pass
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            thumbnails[size_name] = img_byte_arr.getvalue()
        
        return thumbnails
    
    async def process_video_qualities(self, video_content: bytes, video_metadata: Dict) -> List[Dict]:
        """Simulate video quality processing"""
        # For now, just create metadata for different qualities
        # In a real implementation, this would use FFmpeg to transcode
        
        qualities = [
            {'quality': '360p', 'width': 640, 'height': 360, 'bitrate': 300000},
            {'quality': '480p', 'width': 854, 'height': 480, 'bitrate': 500000},
            {'quality': '720p', 'width': 1280, 'height': 720, 'bitrate': 1000000}
        ]
        
        processed_qualities = []
        
        for quality_info in qualities:
            # For now, we'll store the original video data for each quality
            # In production, this would be transcoded video data
            processed_qualities.append({
                'quality': quality_info['quality'],
                'resolution': f"{quality_info['width']}x{quality_info['height']}",
                'bitrate': quality_info['bitrate'],
                'segments': await self.create_video_segments(video_content, quality_info),
                'total_size': len(video_content)
            })
        
        return processed_qualities
    
    async def create_video_segments(self, video_content: bytes, quality_info: Dict) -> List[Dict]:
        """Create video segments (simulated)"""
        # For now, create 4-second segments by splitting the video data
        segment_size = len(video_content) // 8  # Create 8 segments
        segments = []
        
        for i in range(8):
            start_pos = i * segment_size
            end_pos = start_pos + segment_size if i < 7 else len(video_content)
            segment_data = video_content[start_pos:end_pos]
            
            segments.append({
                'segment_index': i,
                'segment_data': segment_data,
                'segment_size': len(segment_data),
                'start_time': i * 4.0,  # 4 seconds per segment
                'end_time': (i + 1) * 4.0
            })
        
        return segments

# Create a global instance
simple_video_processor = SimpleVideoProcessor()