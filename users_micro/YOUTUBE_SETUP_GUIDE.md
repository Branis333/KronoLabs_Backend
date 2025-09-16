# 🎬 YouTube-Style Video System Setup Guide

## Overview
This system implements complete YouTube-style video optimization with:
- Multi-resolution transcoding (144p to 4K)
- Video segmentation for adaptive streaming
- Binary storage (no external dependencies)
- Automatic thumbnail generation
- Background processing pipeline

## 📋 Prerequisites

### 1. Install FFmpeg
FFmpeg is required for video processing and transcoding.

**Windows:**
```powershell
# Download from https://ffmpeg.org/download.html#build-windows
# Or use Chocolatey:
choco install ffmpeg

# Or use winget:
winget install FFmpeg
```

**Verify FFmpeg installation:**
```powershell
ffmpeg -version
```

### 2. Install Python Dependencies
```powershell
pip install -r youtube_video_requirements.txt
```

### 3. Database Migration
The migration script has already been run successfully:
```powershell
python migrate_youtube_style.py
```

## 🚀 System Architecture

### Database Tables Created:
- `videos` - Main video metadata with thumbnails
- `video_qualities` - Multi-resolution video storage
- `video_segments` - Streaming segments for each quality

### Processing Pipeline:
1. **Upload** → Accept video file
2. **Analyze** → Extract metadata and validate
3. **Transcode** → Create multiple quality versions
4. **Segment** → Split into 4-second streaming chunks
5. **Store** → Save binary data to database
6. **Stream** → Serve adaptive bitrate content

## 📡 API Endpoints

### Video Upload (YouTube-style)
```http
POST /videos/
Content-Type: multipart/form-data

Parameters:
- video_file: Video file (max 1GB)
- thumbnail: Thumbnail image (optional - auto-generated if not provided)
- title: Video title (required)
- description: Video description
- category: Video category
- tags: Comma-separated tags or JSON array
- is_public: Boolean (default: true)
```

**Response:**
```json
{
  "success": true,
  "message": "Video upload successful! Processing multiple qualities...",
  "video_id": "uuid-here",
  "processing_status": "processing",
  "estimated_completion": "2-5 minutes",
  "status_check_url": "/videos/{video_id}/status",
  "qualities_being_processed": [
    "144p", "240p", "360p", "480p", "720p", "1080p"
  ]
}
```

### Processing Status
```http
GET /videos/{video_id}/status
```

### Streaming Manifest
```http
GET /videos/{video_id}/stream
```

### Video Segments
```http
GET /streaming/video/{video_id}/quality/{quality}/segment/{index}
```

## 🎯 Usage Examples

### 1. Upload a Video
```python
import requests

files = {
    'video_file': open('my_video.mp4', 'rb'),
    'thumbnail': open('thumb.jpg', 'rb')  # optional
}
data = {
    'title': 'My YouTube-Style Video',
    'description': 'Amazing video with adaptive streaming',
    'category': 'Entertainment',
    'tags': 'funny,viral,awesome',
    'is_public': True
}

response = requests.post('http://localhost:8000/videos/', files=files, data=data)
print(response.json())
```

### 2. Check Processing Status
```python
video_id = "your-video-id"
response = requests.get(f'http://localhost:8000/videos/{video_id}/status')
status = response.json()
print(f"Status: {status['processing_status']}")
print(f"Available qualities: {status['available_qualities']}")
```

### 3. Get Streaming Info
```python
response = requests.get(f'http://localhost:8000/videos/{video_id}/stream')
streaming_info = response.json()
print(f"Streaming URL: {streaming_info['streaming_url']}")
```

## 🛠️ Technical Features

### Multi-Resolution Processing
The system automatically creates these quality levels:
- **144p** (256x144) - Ultra low bandwidth
- **240p** (426x240) - Low bandwidth mobile
- **360p** (640x360) - Standard mobile
- **480p** (854x480) - Standard quality
- **720p** (1280x720) - HD quality
- **1080p** (1920x1080) - Full HD
- **1440p** (2560x1440) - 2K (for source videos ≥1440p)
- **2160p** (3840x2160) - 4K (for source videos ≥2160p)

### Adaptive Streaming
- **Segment Duration**: 4 seconds per segment
- **Format**: MP4/H.264 for maximum compatibility
- **Codec**: H.264 with optimized settings per quality
- **Audio**: AAC audio tracks preserved across all qualities

### Binary Storage Optimization
- **Thumbnails**: Stored as BYTEA (small, medium, large sizes)
- **Video Segments**: Each 4-second chunk stored as BYTEA
- **No External URLs**: Everything in database for reliability
- **Compression**: Optimized bitrates per quality level

### Background Processing
- **Asynchronous**: Video processing doesn't block upload response
- **Status Tracking**: Real-time processing progress
- **Error Handling**: Robust error recovery and reporting
- **Queue System**: Multiple videos can be processed simultaneously

## 🎮 Testing the System

### 1. Start the Server
```powershell
cd "c:\Users\user\Desktop\KronoLabs_Backend\users_micro"
uvicorn main:app --reload
```

### 2. Test Video Upload
Visit: http://localhost:8000/docs

Try the `/videos/` POST endpoint with:
- A small MP4 video file
- Title: "Test YouTube Video"
- Description: "Testing adaptive streaming"

### 3. Monitor Processing
Use the returned `video_id` to check status:
- GET `/videos/{video_id}/status`

### 4. Test Streaming
Once processing is complete:
- GET `/videos/{video_id}/stream` - Get streaming manifest
- GET `/streaming/video/{video_id}/quality/720p/segment/0` - Stream first segment

## 🔧 Configuration

### Processing Settings (in video_processor.py)
```python
QUALITY_SETTINGS = {
    '144p': {'width': 256, 'height': 144, 'bitrate': '96k'},
    '240p': {'width': 426, 'height': 240, 'bitrate': '150k'},
    '360p': {'width': 640, 'height': 360, 'bitrate': '300k'},
    '480p': {'width': 854, 'height': 480, 'bitrate': '500k'},
    '720p': {'width': 1280, 'height': 720, 'bitrate': '1000k'},
    '1080p': {'width': 1920, 'height': 1080, 'bitrate': '2500k'}
}
```

### Thumbnail Sizes (in video_processor.py)
```python
THUMBNAIL_SIZES = {
    'small': (160, 90),
    'medium': (320, 180),  
    'large': (640, 360)
}
```

## 🚨 Troubleshooting

### FFmpeg Not Found
```
Error: FFmpeg executable not found
```
**Solution**: Install FFmpeg and ensure it's in your PATH

### Memory Issues During Processing
```
Error: Out of memory during video processing
```
**Solution**: 
- Reduce video file size limits
- Process lower quality videos first
- Add more RAM or use disk-based processing

### Database Connection Issues
```
Error: Could not connect to database
```
**Solution**: Check your database connection settings in `.env`

### Processing Stuck
```
Status: processing (for >10 minutes)
```
**Solution**: 
- Check background task logs
- Restart the processing pipeline
- Verify FFmpeg is working properly

## 🎯 Performance Tips

1. **Use SSD storage** for faster video processing
2. **Increase worker processes** for multiple simultaneous uploads
3. **Monitor CPU usage** during transcoding
4. **Optimize database** with proper indexing (already included)
5. **Cache thumbnails** for faster loading
6. **Use CDN** for segment delivery in production

## 🎉 Success Indicators

✅ **Upload Success**: Video accepted and processing started  
✅ **Processing Complete**: All quality levels generated  
✅ **Streaming Ready**: Segments available for playback  
✅ **Adaptive Quality**: Multiple resolutions working  
✅ **Fast Loading**: Thumbnails and metadata responsive  

Your YouTube-style video system is now ready! 🚀