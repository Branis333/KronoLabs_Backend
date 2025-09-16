"""
Google Drive Utilities for Video Storage

This utility handles uploading videos to Google Drive and managing video files.
Videos are uploaded to a specific Google Drive folder and made publicly accessible.

Requirements:
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib

Setup:
1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create Service Account credentials
4. Download the JSON key file
5. Share your target folder with the service account email

Usage:
- Upload videos to Google Drive
- Get shareable links for videos
- Delete videos from Google Drive
- Generate thumbnail from video files
"""

import io
import os
import json
import tempfile
import time
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import mimetypes

# Try to import Google Drive API dependencies
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
    from google.oauth2.service_account import Credentials
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

# Try to import video processing for thumbnails
try:
    import cv2
    import numpy as np
    from PIL import Image
    HAS_VIDEO_PROCESSING = True
except ImportError:
    HAS_VIDEO_PROCESSING = False

class GoogleDriveUtils:
    """Utility class for Google Drive operations"""
    
    # Your Google Drive folder ID from the URL
    DRIVE_FOLDER_ID = "1FH-72iCDmnggCcJht_eJ6HCxRj70snIt"
    
    # Allowed video MIME types
    ALLOWED_VIDEO_TYPES = {
        'video/mp4', 'video/mpeg', 'video/quicktime', 
        'video/x-msvideo', 'video/webm', 'video/ogg', 'video/3gpp',
        'video/x-flv', 'video/x-ms-wmv'
    }
    
    # Maximum video size (500MB)
    MAX_VIDEO_SIZE = 500 * 1024 * 1024
    
    def __init__(self):
        """Initialize Google Drive service"""
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service"""
        if not HAS_GOOGLE_API:
            raise Exception("Google API client libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        
        # Look for service account credentials
        credentials_paths = [
            "credentials/google_drive_credentials.json",
            "google_drive_credentials.json",
            os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "")
        ]
        
        credentials_file = None
        for path in credentials_paths:
            if path and os.path.exists(path):
                credentials_file = path
                break
        
        if not credentials_file:
            # For development/demo, we'll create a placeholder
            print("Warning: Google Drive credentials not found. Video upload will be simulated.")
            self.service = None
            return
        
        try:
            # Define the scopes
            scopes = ['https://www.googleapis.com/auth/drive']
            
            # Create credentials from service account file
            self.credentials = Credentials.from_service_account_file(
                credentials_file, scopes=scopes
            )
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            print(f"Failed to initialize Google Drive service: {e}")
            self.service = None
    
    async def upload_video(
        self, 
        video_file: UploadFile, 
        filename: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """
        Upload video to Google Drive and return shareable URL
        
        Args:
            video_file: The video file to upload
            filename: Optional custom filename
        
        Returns:
            Tuple of (file_id, shareable_url, file_size)
        """
        if not filename:
            filename = video_file.filename or f"video_{int(time.time())}.mp4"
        
        # Validate video file
        await self._validate_video_file(video_file)
        
        if not self.service:
            # Simulate upload for development
            file_id = f"demo_file_{hash(filename)}"
            demo_url = f"https://drive.google.com/file/d/{file_id}/view"
            return file_id, demo_url, len(await video_file.read())
        
        try:
            # Read file content
            video_content = await video_file.read()
            file_size = len(video_content)
            
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.DRIVE_FOLDER_ID]
            }
            
            # Create media upload
            media = MediaIoBaseUpload(
                io.BytesIO(video_content),
                mimetype=video_file.content_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            
            # Make file publicly accessible
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Generate shareable URL
            shareable_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            return file_id, shareable_url, file_size
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload video to Google Drive: {str(e)}"
            )
    
    async def _validate_video_file(self, video_file: UploadFile):
        """Validate video file type and size"""
        
        # Check file size
        video_content = await video_file.read()
        file_size = len(video_content)
        
        # Reset file pointer
        video_file.file.seek(0)
        
        if file_size > self.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Video file too large. Maximum size is {self.MAX_VIDEO_SIZE // (1024*1024)}MB"
            )
        
        # Check MIME type
        content_type = video_file.content_type
        if content_type not in self.ALLOWED_VIDEO_TYPES:
            # Try to guess MIME type from filename
            if video_file.filename:
                guessed_type, _ = mimetypes.guess_type(video_file.filename)
                if guessed_type and guessed_type in self.ALLOWED_VIDEO_TYPES:
                    content_type = guessed_type
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported video format. Allowed formats: {', '.join(self.ALLOWED_VIDEO_TYPES)}"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to determine video file type"
                )
    
    async def generate_video_thumbnail(
        self, 
        video_file: UploadFile, 
        timestamp: float = 1.0
    ) -> Tuple[bytes, str]:
        """
        Generate thumbnail from video file
        
        Args:
            video_file: The video file
            timestamp: Time in seconds to capture thumbnail
        
        Returns:
            Tuple of (thumbnail_bytes, mime_type)
        """
        if not HAS_VIDEO_PROCESSING:
            raise HTTPException(
                status_code=500,
                detail="Video processing libraries not available. Install opencv-python and Pillow."
            )
        
        try:
            # Save video to temporary file
            video_content = await video_file.read()
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_content)
                temp_file_path = temp_file.name
            
            # Open video with OpenCV
            cap = cv2.VideoCapture(temp_file_path)
            
            if not cap.isOpened():
                os.unlink(temp_file_path)
                raise HTTPException(
                    status_code=400,
                    detail="Unable to process video file"
                )
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Calculate frame number for timestamp
            frame_number = int(min(timestamp * fps, frame_count - 1)) if fps > 0 else 0
            
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            cap.release()
            os.unlink(temp_file_path)
            
            if not ret:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to extract thumbnail from video"
                )
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Resize to reasonable thumbnail size
            pil_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=85)
            thumbnail_bytes = img_byte_arr.getvalue()
            
            return thumbnail_bytes, "image/jpeg"
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate video thumbnail: {str(e)}"
            )
    
    async def delete_video(self, file_id: str) -> bool:
        """
        Delete video from Google Drive
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            print(f"Simulated deletion of video {file_id}")
            return True
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"Failed to delete video {file_id}: {e}")
            return False
    
    def get_video_info(self, file_id: str) -> dict:
        """
        Get video file information from Google Drive
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            Dictionary with file information
        """
        if not self.service:
            return {
                "id": file_id,
                "name": f"demo_video_{file_id}.mp4",
                "size": "unknown",
                "created": "2023-01-01"
            }
        
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,createdTime,mimeType'
            ).execute()
            
            return file_info
            
        except Exception as e:
            print(f"Failed to get video info for {file_id}: {e}")
            return None

# Global instance
google_drive = GoogleDriveUtils()