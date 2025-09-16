"""
Instagram-Style Media Optimization Utilities

Advanced image processing for maximum storage efficiency:
- Progressive JPEG compression with quality optimization
- Modern format conversion (WebP, AVIF when supported)
- Multi-size generation for responsive delivery
- Blur-up placeholder generation
- Advanced compression with quality preservation
- Instagram-style optimization techniques
"""

import base64
import mimetypes
from typing import Optional, Tuple, Dict, List
from fastapi import UploadFile, HTTPException
import io

# Try to import image processing libraries
try:
    from PIL import Image, ImageFilter, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

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
    
    # Instagram-style optimization settings
    IMAGE_QUALITY_HIGH = 90      # High quality for important images
    IMAGE_QUALITY_MEDIUM = 75    # Medium quality for feed images
    IMAGE_QUALITY_LOW = 60       # Lower quality for thumbnails
    IMAGE_QUALITY_BLUR = 10      # Ultra low quality for blur-up placeholder
    
    # Multi-size generation presets (width x height)
    IMAGE_SIZES = {
        'thumbnail': (150, 150),     # Square thumbnails
        'small': (320, 320),         # Small feed images
        'medium': (640, 640),        # Medium feed images  
        'large': (1080, 1080),       # Large feed images
        'xl': (1920, 1920),          # Extra large for detail view
    }
    
    # Progressive JPEG settings
    PROGRESSIVE_THRESHOLD = 10 * 1024  # Files larger than 10KB get progressive
    
    # Format priority (modern first)
    MODERN_FORMATS = ['WEBP', 'AVIF']
    FALLBACK_FORMAT = 'JPEG'
    
    @staticmethod
    def optimize_image_instagram_style(
        image_data: bytes,
        target_size: tuple = None,
        quality: int = IMAGE_QUALITY_MEDIUM,
        format_preference: str = None
    ) -> Tuple[bytes, str]:
        """
        Instagram-style image optimization with progressive compression,
        format conversion, and intelligent sizing.
        
        Args:
            image_data: Original image binary data
            target_size: Tuple (width, height) for resizing
            quality: JPEG quality (1-100)
            format_preference: Preferred output format ('WEBP', 'AVIF', 'JPEG')
        
        Returns:
            Tuple of (optimized_binary_data, mime_type)
        """
        if not HAS_PIL:
            # Fallback: return original data
            return image_data, "image/jpeg"
        
        try:
            # Open image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG/WebP compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if target size specified
            if target_size:
                # Instagram-style smart cropping: maintain aspect ratio, center crop
                img_aspect = img.width / img.height
                target_aspect = target_size[0] / target_size[1]
                
                if img_aspect > target_aspect:
                    # Image is wider, crop width
                    new_height = img.height
                    new_width = int(new_height * target_aspect)
                    left = (img.width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, new_height))
                else:
                    # Image is taller, crop height
                    new_width = img.width
                    new_height = int(new_width / target_aspect)
                    top = (img.height - new_height) // 2
                    img = img.crop((0, top, new_width, top + new_height))
                
                # Resize to exact target dimensions
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Enhance image quality (subtle)
            if quality > MediaUtils.IMAGE_QUALITY_LOW:
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)  # Slight sharpening
            
            # Determine output format
            output_format = format_preference or MediaUtils.FALLBACK_FORMAT
            
            # Generate optimized image
            output_buffer = io.BytesIO()
            
            if output_format == 'WEBP':
                img.save(
                    output_buffer,
                    format='WEBP',
                    quality=quality,
                    optimize=True,
                    method=6  # Best compression
                )
                mime_type = 'image/webp'
            elif output_format == 'AVIF':
                # AVIF support might not be available, fallback to WebP
                try:
                    img.save(
                        output_buffer,
                        format='AVIF',
                        quality=quality,
                        optimize=True
                    )
                    mime_type = 'image/avif'
                except Exception:
                    # Fallback to WebP
                    output_buffer = io.BytesIO()
                    img.save(
                        output_buffer,
                        format='WEBP',
                        quality=quality,
                        optimize=True,
                        method=6
                    )
                    mime_type = 'image/webp'
            else:
                # JPEG with progressive encoding for larger files
                original_size = len(image_data)
                use_progressive = original_size > MediaUtils.PROGRESSIVE_THRESHOLD
                
                img.save(
                    output_buffer,
                    format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=use_progressive
                )
                mime_type = 'image/jpeg'
            
            optimized_data = output_buffer.getvalue()
            output_buffer.close()
            
            return optimized_data, mime_type
            
        except Exception as e:
            # If optimization fails, return original
            print(f"Image optimization failed: {e}")
            return image_data, "image/jpeg"
    
    @staticmethod
    def generate_image_variants(image_data: bytes) -> dict:
        """
        Generate Instagram-style multiple image variants for responsive loading.
        
        Args:
            image_data: Original image binary data
            
        Returns:
            Dictionary with different sized variants and blur placeholder
        """
        if not HAS_PIL:
            # Fallback: return original only
            return {
                'original': {
                    'data': image_data,
                    'mime_type': 'image/jpeg',
                    'size': len(image_data)
                }
            }
        
        variants = {}
        
        try:
            # Generate each size variant
            for size_name, dimensions in MediaUtils.IMAGE_SIZES.items():
                quality = MediaUtils.IMAGE_QUALITY_HIGH if size_name in ['large', 'xl'] else MediaUtils.IMAGE_QUALITY_MEDIUM
                
                # Use WebP for modern browsers (better compression)
                optimized_data, mime_type = MediaUtils.optimize_image_instagram_style(
                    image_data,
                    target_size=dimensions,
                    quality=quality,
                    format_preference='WEBP'
                )
                
                variants[size_name] = {
                    'data': optimized_data,
                    'mime_type': mime_type,
                    'size': len(optimized_data),
                    'dimensions': dimensions
                }
            
            # Generate ultra-low quality blur placeholder
            blur_data, blur_mime = MediaUtils.optimize_image_instagram_style(
                image_data,
                target_size=(50, 50),  # Tiny blur placeholder
                quality=MediaUtils.IMAGE_QUALITY_BLUR,
                format_preference='JPEG'
            )
            
            variants['blur_placeholder'] = {
                'data': blur_data,
                'mime_type': blur_mime,
                'size': len(blur_data),
                'dimensions': (50, 50)
            }
            
            # Keep original as fallback
            variants['original'] = {
                'data': image_data,
                'mime_type': 'image/jpeg',
                'size': len(image_data)
            }
            
        except Exception as e:
            print(f"Variant generation failed: {e}")
            variants['original'] = {
                'data': image_data,
                'mime_type': 'image/jpeg',
                'size': len(image_data)
            }
        
        return variants
    
    @staticmethod
    def apply_instagram_blur_effect(image_data: bytes) -> bytes:
        """
        Apply Instagram-style gaussian blur for placeholder effect.
        
        Args:
            image_data: Image binary data
            
        Returns:
            Blurred image binary data
        """
        if not HAS_PIL:
            return image_data
        
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Apply strong gaussian blur
            blurred = img.filter(ImageFilter.GaussianBlur(radius=5))
            
            # Convert to small, highly compressed JPEG
            output_buffer = io.BytesIO()
            blurred.save(
                output_buffer,
                format='JPEG',
                quality=10,  # Very low quality for tiny placeholder
                optimize=True
            )
            
            result = output_buffer.getvalue()
            output_buffer.close()
            return result
            
        except Exception:
            return image_data

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
            if HAS_MAGIC:
                mime_type = magic.from_buffer(content, mime=True)
            else:
                # Fallback to guessing from filename
                mime_type, _ = mimetypes.guess_type(file.filename)
                if not mime_type:
                    mime_type = file.content_type or 'application/octet-stream'
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
        """Process profile image upload with Instagram-style optimization"""
        # Get original file
        original_data, mime_type = await MediaUtils.process_uploaded_file(
            file,
            max_size=MediaUtils.MAX_PROFILE_IMAGE_SIZE,
            allowed_types=MediaUtils.ALLOWED_IMAGE_TYPES
        )
        
        # Apply Instagram-style optimization for profile pictures
        # Use circular crop friendly size and high quality
        optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
            original_data,
            target_size=MediaUtils.IMAGE_SIZES['medium'],  # 640x640 for profiles
            quality=MediaUtils.IMAGE_QUALITY_HIGH,
            format_preference='WEBP'
        )
        
        return optimized_data, optimized_mime
    
    @staticmethod
    async def process_post_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process post media upload with Instagram-style optimization"""
        content, mime_type = await MediaUtils.process_uploaded_file(file)
        
        # Apply different processing for images vs videos
        file_size = len(content)
        if mime_type in MediaUtils.ALLOWED_IMAGE_TYPES:
            if file_size > MediaUtils.MAX_IMAGE_SIZE:
                raise HTTPException(status_code=400, detail="Image exceeds 10MB limit")
            
            # Apply Instagram-style optimization for post images
            optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
                content,
                target_size=MediaUtils.IMAGE_SIZES['large'],  # 1080x1080 for posts
                quality=MediaUtils.IMAGE_QUALITY_MEDIUM,
                format_preference='WEBP'
            )
            return optimized_data, optimized_mime
            
        elif mime_type in MediaUtils.ALLOWED_VIDEO_TYPES:
            if file_size > MediaUtils.MAX_VIDEO_SIZE:
                raise HTTPException(status_code=400, detail="Video exceeds 50MB limit")
            # Videos already handled by video processor
            return content, mime_type
        
        return content, mime_type
    
    @staticmethod
    async def process_story_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process story media upload with Instagram-style optimization"""
        content, mime_type = await MediaUtils.process_uploaded_file(file)
        
        # Stories need optimized vertical format (9:16 aspect ratio)
        if mime_type in MediaUtils.ALLOWED_IMAGE_TYPES:
            # Apply Instagram-style optimization for stories (vertical format)
            optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
                content,
                target_size=(608, 1080),  # 9:16 aspect ratio
                quality=MediaUtils.IMAGE_QUALITY_MEDIUM,
                format_preference='WEBP'
            )
            return optimized_data, optimized_mime
        
        # For videos, use existing processing
        return content, mime_type
    
    @staticmethod
    async def process_message_media(file: UploadFile) -> Tuple[bytes, str]:
        """Process message media upload with Instagram-style optimization"""
        content, mime_type = await MediaUtils.process_uploaded_file(file)
        
        # Messages need smaller, faster loading images
        if mime_type in MediaUtils.ALLOWED_IMAGE_TYPES:
            # Apply Instagram-style optimization for messages (smaller size)
            optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
                content,
                target_size=MediaUtils.IMAGE_SIZES['medium'],  # 640x640 for messages
                quality=MediaUtils.IMAGE_QUALITY_MEDIUM,
                format_preference='WEBP'
            )
            return optimized_data, optimized_mime
        
        # For videos, use existing processing
        return content, mime_type
    
    @staticmethod
    async def process_comic_thumbnail(file: UploadFile) -> dict:
        """Process comic thumbnail upload with Instagram-style optimization"""
        content, mime_type = await MediaUtils.process_uploaded_file(
            file,
            max_size=MediaUtils.MAX_IMAGE_SIZE,
            allowed_types=MediaUtils.ALLOWED_IMAGE_TYPES
        )
        
        # Apply Instagram-style optimization for comic thumbnails
        optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
            content,
            target_size=MediaUtils.IMAGE_SIZES['small'],  # 320x320 for thumbnails
            quality=MediaUtils.IMAGE_QUALITY_MEDIUM,
            format_preference='WEBP'
        )
        
        return {
            "media_data": optimized_data,
            "media_mime_type": optimized_mime
        }
    
    @staticmethod
    async def process_comic_page(file: UploadFile) -> dict:
        """Process comic page upload with Instagram-style optimization"""
        content, mime_type = await MediaUtils.process_uploaded_file(
            file,
            max_size=MediaUtils.MAX_IMAGE_SIZE,  # 10MB limit for comic pages
            allowed_types=MediaUtils.ALLOWED_IMAGE_TYPES
        )
        
        # Apply Instagram-style optimization for comic pages (high quality)
        optimized_data, optimized_mime = MediaUtils.optimize_image_instagram_style(
            content,
            target_size=MediaUtils.IMAGE_SIZES['xl'],  # 1920x1920 for high-res pages
            quality=MediaUtils.IMAGE_QUALITY_HIGH,
            format_preference='WEBP'
        )
        
        return {
            "media_data": optimized_data,
            "media_mime_type": optimized_mime
        }
    
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
    
    @staticmethod
    async def process_image_with_variants(file: UploadFile, context: str = "post") -> dict:
        """
        Process image with Instagram-style multiple variants for responsive loading.
        This maximizes storage efficiency by providing optimal images for each use case.
        
        Args:
            file: Uploaded image file
            context: Context type ("post", "profile", "story", "message", "comic_page", "comic_thumbnail")
            
        Returns:
            Dictionary with optimized variants and metadata
        """
        # Get original image
        original_data, mime_type = await MediaUtils.process_uploaded_file(
            file,
            max_size=MediaUtils.MAX_IMAGE_SIZE,
            allowed_types=MediaUtils.ALLOWED_IMAGE_TYPES
        )
        
        # Generate all variants
        variants = MediaUtils.generate_image_variants(original_data)
        
        # Determine primary variant based on context
        context_mapping = {
            'profile': 'medium',      # 640x640 for profile images
            'post': 'large',          # 1080x1080 for post images  
            'story': 'large',         # 1080x1080 for stories (will be cropped to 9:16)
            'message': 'medium',      # 640x640 for messages
            'comic_page': 'xl',       # 1920x1920 for comic pages
            'comic_thumbnail': 'small' # 320x320 for thumbnails
        }
        
        primary_size = context_mapping.get(context, 'large')
        primary_variant = variants.get(primary_size, variants['original'])
        
        # Calculate compression savings
        original_size = len(original_data)
        optimized_size = primary_variant['size']
        compression_ratio = (original_size - optimized_size) / original_size * 100
        
        return {
            # Primary optimized image (for backward compatibility)
            "media_data": primary_variant['data'],
            "media_mime_type": primary_variant['mime_type'],
            
            # All variants for responsive loading
            "variants": variants,
            
            # Metadata
            "context": context,
            "primary_size": primary_size,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "compression_ratio": round(compression_ratio, 2),
            "total_variants": len(variants)
        }
    
    @staticmethod
    def get_responsive_image_data(variants: dict, requested_size: str = None) -> dict:
        """
        Get appropriate image variant for responsive delivery.
        
        Args:
            variants: Dictionary of image variants
            requested_size: Requested size ('thumbnail', 'small', 'medium', 'large', 'xl', 'blur_placeholder')
            
        Returns:
            Dictionary with image data and metadata
        """
        if not requested_size or requested_size not in variants:
            # Default to medium size or original if not available
            requested_size = 'medium' if 'medium' in variants else 'original'
        
        variant = variants.get(requested_size, variants.get('original'))
        
        if not variant:
            raise HTTPException(status_code=404, detail="Image variant not found")
        
        return {
            "data": variant['data'],
            "mime_type": variant['mime_type'],
            "size": variant['size'],
            "variant": requested_size,
            "dimensions": variant.get('dimensions')
        }

    @staticmethod
    async def process_video_thumbnail(thumbnail_file: UploadFile) -> dict:
        """
        Process video thumbnail upload with Instagram-style optimization
        
        Args:
            thumbnail_file: Uploaded thumbnail file
            
        Returns:
            Dictionary with processed media data
        """
        if not thumbnail_file or not thumbnail_file.filename:
            raise HTTPException(
                status_code=400,
                detail="Thumbnail file is required for videos"
            )
        
        # Process as image with Instagram-style optimization
        result = await MediaUtils.process_image_with_variants(thumbnail_file, context="post")
        
        # Encode to base64 for storage/transmission
        base64_data = MediaUtils.encode_to_base64(result["media_data"])
        
        return {
            "media_data": result["media_data"],
            "media_mime_type": result["media_mime_type"],
            "media_base64": base64_data,
            "file_size": result["optimized_size"],
            "variants": result["variants"],
            "compression_ratio": result["compression_ratio"]
        }
    
    @staticmethod
    async def validate_video_file(video_file: UploadFile) -> dict:
        """
        Validate video file without processing (since it goes to Google Drive)
        
        Args:
            video_file: Uploaded video file
            
        Returns:
            Dictionary with video file info
        """
        if not video_file or not video_file.filename:
            raise HTTPException(
                status_code=400,
                detail="Video file is required"
            )
        
        # Read file content to check size
        content = await video_file.read()
        file_size = len(content)
        
        # Reset file pointer for later use
        video_file.file.seek(0)
        
        # Check file size (500MB limit for videos)
        max_video_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_video_size:
            raise HTTPException(
                status_code=413,
                detail=f"Video file too large. Maximum size is {max_video_size // (1024*1024)}MB"
            )
        
        # Validate MIME type
        content_type = video_file.content_type
        video_types = {
            'video/mp4', 'video/mpeg', 'video/quicktime', 
            'video/x-msvideo', 'video/webm', 'video/ogg', 'video/3gpp'
        }
        
        if content_type not in video_types:
            # Try to guess from filename
            if video_file.filename:
                guessed_type, _ = mimetypes.guess_type(video_file.filename)
                if guessed_type and guessed_type in video_types:
                    content_type = guessed_type
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported video format: {content_type}. Allowed: MP4, AVI, MOV, WebM, etc."
                    )
        
        return {
            "filename": video_file.filename,
            "content_type": content_type,
            "file_size": file_size
        }

    @staticmethod
    def create_progressive_data_url(binary_data: bytes, mime_type: str, is_placeholder: bool = False) -> str:
        """
        Create Instagram-style progressive data URL with blur-up effect.
        
        Args:
            binary_data: Image binary data
            mime_type: MIME type of the image
            is_placeholder: Whether this is a blur placeholder
            
        Returns:
            Data URL string with appropriate loading hints
        """
        if not binary_data or not mime_type:
            return None
        
        base64_data = MediaUtils.encode_to_base64(binary_data)
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        # Add loading hints for frontend
        if is_placeholder:
            # Ultra-low quality placeholder for blur-up effect
            return f"{data_url}#blur-placeholder"
        else:
            return data_url
    
    @staticmethod
    def get_optimal_image_format(user_agent: str = None) -> str:
        """
        Determine optimal image format based on browser support.
        
        Args:
            user_agent: User agent string from request headers
            
        Returns:
            Optimal format ('AVIF', 'WEBP', or 'JPEG')
        """
        if not user_agent:
            return 'WEBP'  # Default to WebP
        
        user_agent = user_agent.lower()
        
        # Check for AVIF support (newest Chrome, Firefox)
        if 'chrome/90' in user_agent or 'firefox/93' in user_agent:
            return 'AVIF'
        
        # Check for WebP support (most modern browsers)
        if any(browser in user_agent for browser in ['chrome', 'firefox', 'safari', 'edge']):
            return 'WEBP'
        
        # Fallback to JPEG for older browsers
        return 'JPEG'
    
    @staticmethod
    def calculate_storage_savings(original_size: int, optimized_variants: dict) -> dict:
        """
        Calculate Instagram-style storage savings from optimization.
        
        Args:
            original_size: Original file size in bytes
            optimized_variants: Dictionary of optimized variants
            
        Returns:
            Dictionary with savings statistics
        """
        total_optimized_size = sum(variant.get('size', 0) for variant in optimized_variants.values())
        
        # Calculate theoretical size if we stored all variants unoptimized
        theoretical_unoptimized_size = original_size * len(optimized_variants)
        
        # Actual savings
        actual_savings = theoretical_unoptimized_size - total_optimized_size
        savings_percentage = (actual_savings / theoretical_unoptimized_size) * 100 if theoretical_unoptimized_size > 0 else 0
        
        return {
            'original_size_mb': round(original_size / (1024 * 1024), 2),
            'total_optimized_size_mb': round(total_optimized_size / (1024 * 1024), 2),
            'theoretical_unoptimized_mb': round(theoretical_unoptimized_size / (1024 * 1024), 2),
            'savings_mb': round(actual_savings / (1024 * 1024), 2),
            'savings_percentage': round(savings_percentage, 2),
            'compression_efficiency': round((1 - total_optimized_size / original_size) * 100, 2) if original_size > 0 else 0,
            'variants_count': len(optimized_variants)
        }

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

# New Instagram-style helper functions
async def process_image_instagram_style(file: UploadFile, context: str = "post") -> dict:
    """Helper function for Instagram-style image processing"""
    return await MediaUtils.process_image_with_variants(file, context)

def optimize_for_storage(image_data: bytes, target_size: tuple = None) -> Tuple[bytes, str]:
    """Helper function for maximum storage optimization"""
    return MediaUtils.optimize_image_instagram_style(
        image_data,
        target_size=target_size,
        quality=MediaUtils.IMAGE_QUALITY_MEDIUM,
        format_preference='WEBP'
    )
