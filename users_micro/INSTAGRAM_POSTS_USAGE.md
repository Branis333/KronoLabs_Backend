# Instagram-like Posts API Usage Examples

## Overview
Your posts system now works exactly like Instagram - users MUST upload files from their device to create posts.

## API Endpoints

### 1. Create Post with File Upload (Main Endpoint)
```
POST /posts/
Content-Type: multipart/form-data
```

**Required:**
- `files`: One or more media files (images/videos)

**Optional:**
- `caption`: Post caption text
- `location`: Location tag
- `visibility`: "public", "private", or "followers_only" (default: "public")
- `hashtags`: JSON array or comma-separated string of hashtags
- `tagged_users`: JSON array or comma-separated string of user IDs

### 2. Other Endpoints
- `GET /posts/feed` - Get personalized feed
- `GET /posts/{post_id}` - Get specific post
- `GET /posts/user/{user_id}` - Get user's posts
- `POST /posts/{post_id}/like` - Like/unlike post
- `POST /posts/{post_id}/save` - Save/unsave post
- `POST /posts/{post_id}/comments` - Add comment
- `GET /posts/{post_id}/comments` - Get comments
- `DELETE /posts/{post_id}` - Delete post
- `GET /posts/uploads/{user_id}/{filename}` - Serve uploaded files

## Usage Examples

### Example 1: Single Image Post
```python
import requests

files = {'files': open('photo.jpg', 'rb')}
data = {
    'caption': 'Beautiful sunset! 🌅',
    'location': 'Beach Resort',
    'visibility': 'public',
    'hashtags': '["sunset", "beach", "vacation"]'
}

response = requests.post(
    'http://localhost:8000/posts/',
    files=files,
    data=data,
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
```

### Example 2: Multiple Files (Carousel)
```python
import requests

files = [
    ('files', open('photo1.jpg', 'rb')),
    ('files', open('video1.mp4', 'rb')),
    ('files', open('photo2.png', 'rb'))
]
data = {
    'caption': 'My vacation highlights!',
    'location': 'Hawaii',
    'hashtags': 'vacation,hawaii,memories',
    'tagged_users': '123,456'
}

response = requests.post(
    'http://localhost:8000/posts/',
    files=files,
    data=data,
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
```

### Example 3: JavaScript/Frontend
```javascript
const formData = new FormData();
formData.append('files', fileInput.files[0]); // First file
formData.append('files', fileInput.files[1]); // Second file (if any)
formData.append('caption', 'My awesome post!');
formData.append('location', 'New York');
formData.append('visibility', 'public');
formData.append('hashtags', JSON.stringify(['newyork', 'awesome']));

fetch('/posts/', {
    method: 'POST',
    body: formData,
    headers: {
        'Authorization': 'Bearer ' + token
    }
})
.then(response => response.json())
.then(data => console.log('Post created:', data));
```

## File Requirements

### Supported Formats
- **Images**: JPEG, PNG, GIF, WebP, BMP, TIFF
- **Videos**: MP4, MPEG, QuickTime, AVI, WebM, OGG, 3GP

### Size Limits
- **Images**: Maximum 10MB each
- **Videos**: Maximum 100MB each
- **Posts**: Maximum 10 files per post

### Storage
- Files are stored in: `uploads/posts/{user_id}/`
- Automatic unique filename generation
- Files served at: `/posts/uploads/{user_id}/{filename}`

## Response Format
```json
{
    "id": "post-uuid",
    "user_id": 123,
    "user": {
        "id": 123,
        "username": "johndoe",
        "full_name": "John Doe",
        ...
    },
    "caption": "My awesome post!",
    "media_url": "/posts/uploads/123/20250618_143022_abc123_0.jpg",
    "media_type": "carousel",
    "location": "New York",
    "visibility": "public",
    "created_at": "2025-06-18T14:30:22Z",
    "likes_count": 0,
    "comments_count": 0,
    "is_liked": false,
    "is_saved": false,
    "post_media": [
        {
            "id": "media-uuid-1",
            "media_url": "/posts/uploads/123/20250618_143022_abc123_0.jpg",
            "order_index": 0,
            "media_type": "image"
        },
        {
            "id": "media-uuid-2", 
            "media_url": "/posts/uploads/123/20250618_143022_abc123_1.mp4",
            "order_index": 1,
            "media_type": "video"
        }
    ]
}
```

## Key Features

1. **Instagram-like Behavior**: Files MUST be uploaded to create posts
2. **Automatic File Management**: Files are saved, organized, and served automatically
3. **Multiple Media Support**: Single images, videos, or carousel posts
4. **Security**: File type validation, size limits, user isolation
5. **Performance**: Efficient file serving with caching headers
6. **Flexibility**: Support for various input formats (JSON, comma-separated)

Your system is now ready for Instagram-like posting functionality!
