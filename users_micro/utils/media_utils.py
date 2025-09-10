"""
Media Utilities for Binary Storage

Helper functions for handling binary media data stored in database:
- Convert uploaded files to binary data
- Encode binary data to base64 for API responses
- Decode base64 data to binary for database storage
- Validate media types and sizes
"""

import base64
import mimetypes
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import magic

class MediaUtils:
    
    # Allowed MIME types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
        'image/webp', 'image/bmp', 'image/tiff'
    }
    
    ALLOWED_VIDEO_TYPES = {
        'video/mp4', 'video/mpeg', 'video/quicktime', 
        'video/x-msvideo', 'video/webm', 'video/ogg', 'video/3gpp'
    }
    
    # Size limits (in bytes)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    async def process_uploaded_file(
        file: UploadFile, 
        max_size: int = MAX_IMAGE_SIZE,
        allowed_types: set = None
    ) -> Tuple[bytes, str]:
        """
        Process an uploaded file and return binary data and MIME type
        
        Args:
            file: FastAPI UploadFile object
            max_size: Maximum file size in bytes
            allowed_types: Set of allowed MIME types
        
        Returns:
            Tuple of (binary_data, mime_type)
        
        Raises:
            HTTPException: If file validation fails
        """
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        if file_size > max_size:
            size_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=400, 
                detail=f"File size exceeds {size_mb}MB limit"
            )
        
        # Detect MIME type
        try:
            mime_type = magic.from_buffer(content, mime=True)
        except:
            # Fallback to guessing from filename
            mime_type, _ = mimetypes.guess_type(file.filename)
            if not mime_type:
                mime_type = file.content_type or 'application/octet-stream'
        
        # Validate MIME type
        if allowed_types is None:
            allowed_types = MediaUtils.ALLOWED_IMAGE_TYPES | MediaUtils.ALLOWED_VIDEO_TYPES
        
        if mime_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {mime_type}"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        return content, mime_type
    
    @staticmethod
    async def process_profile_image(file: UploadFile) -> Tuple[bytes, str]:
        """Process profile image upload"""
        return await MediaUtils.process_uploaded_file(
            file,
            max_size=MediaUtils.MAX_PROFILE_IMAGE_SIZE,
            allowed_types=MediaUtils.ALLOWED_IMAGE_TYPES
        )
    
    @staticmethod
    async def process_post_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process post media upload (image or video)"""
        content, mime_type = await MediaUtils.process_uploaded_file(file)
        
        # Apply different size limits for images vs videos
        file_size = len(content)
        if mime_type in MediaUtils.ALLOWED_IMAGE_TYPES:
            if file_size > MediaUtils.MAX_IMAGE_SIZE:
                raise HTTPException(status_code=400, detail="Image exceeds 10MB limit")
        elif mime_type in MediaUtils.ALLOWED_VIDEO_TYPES:
            if file_size > MediaUtils.MAX_VIDEO_SIZE:
                raise HTTPException(status_code=400, detail="Video exceeds 50MB limit")
        
        return content, mime_type
    
    @staticmethod
    async def process_story_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process story media upload"""
        return await MediaUtils.process_post_media(file)  # Same rules as posts
    
    @staticmethod
    async def process_message_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process message media upload"""
        return await MediaUtils.process_post_media(file)  # Same rules as posts
    
    @staticmethod
    def encode_to_base64(binary_data: bytes) -> str:
        """Convert binary data to base64 string for API responses"""
        if not binary_data:
            return None
        return base64.b64encode(binary_data).decode('utf-8')
    
    @staticmethod
    def decode_from_base64(base64_string: str) -> bytes:
        """Convert base64 string to binary data for database storage"""
        if not base64_string:
            return None
        try:
            return base64.b64decode(base64_string)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 data: {str(e)}")
    
    @staticmethod
    def get_media_type_from_mime(mime_type: str) -> str:
        """Get media type (image/video) from MIME type"""
        if mime_type in MediaUtils.ALLOWED_IMAGE_TYPES:
            return "image"
        elif mime_type in MediaUtils.ALLOWED_VIDEO_TYPES:
            return "video"
        else:
            return "unknown"
    
    @staticmethod
    def create_data_url(binary_data: bytes, mime_type: str) -> str:
        """Create a data URL for frontend consumption"""
        if not binary_data or not mime_type:
            return None
        
        base64_data = MediaUtils.encode_to_base64(binary_data)
        return f"data:{mime_type};base64,{base64_data}"

# Helper functions for backward compatibility
async def process_uploaded_file(file: UploadFile) -> Tuple[bytes, str]:
    """Backward compatibility function"""
    return await MediaUtils.process_uploaded_file(file)

def encode_media_to_base64(binary_data: bytes) -> str:
    """Backward compatibility function"""
    return MediaUtils.encode_to_base64(binary_data)

def decode_media_from_base64(base64_string: str) -> bytes:
    """Backward compatibility function"""
    return MediaUtils.decode_from_base64(base64_string)
