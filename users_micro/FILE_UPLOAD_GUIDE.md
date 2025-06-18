# 📸 File Upload System - Instagram-like Media Upload

Your KronoLabs backend now supports direct file uploads from users' devices, just like Instagram!

## 🚀 Features Implemented

### 1. **Multiple File Upload Endpoints**

#### `POST /posts/upload-media`
Upload multiple files (up to 10) and get URLs back for later use.

**Request:**
```bash
curl -X POST "http://localhost:8000/posts/upload-media" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@image1.jpg" \
  -F "files=@video1.mp4" \
  -F "files=@image2.png"
```

**Response:**
```json
{
  "message": "Media files uploaded successfully",
  "uploaded_files": [
    {
      "media_url": "/uploads/posts/123/20250618_143022_a1b2c3d4_0.jpg",
      "media_type": "image",
      "order_index": 0,
      "original_filename": "image1.jpg",
      "file_size": 2048576,
      "file_size_mb": 2.0,
      "saved_filename": "20250618_143022_a1b2c3d4_0.jpg",
      "content_type": "image/jpeg"
    }
  ],
  "total_files": 1,
  "upload_info": {
    "user_id": 123,
    "timestamp": "2025-06-18T14:30:22.123456",
    "total_size_mb": 2.0
  }
}
```

#### `POST /posts/create-with-files`
Upload files and create a post in one request (like Instagram's flow).

**Request:**
```bash
curl -X POST "http://localhost:8000/posts/create-with-files" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@image1.jpg" \
  -F "files=@video1.mp4" \
  -F "caption=Beautiful sunset! 🌅" \
  -F "location=Beach Resort" \
  -F "visibility=public" \
  -F "hashtags=[\"sunset\", \"beach\", \"vacation\"]" \
  -F "tagged_users=[456, 789]"
```

**Response:** Full PostResponse with uploaded media included.

### 2. **File Serving**

#### `GET /uploads/posts/{user_id}/{filename}`
Serve uploaded files with proper caching headers.

Example: `http://localhost:8000/uploads/posts/123/20250618_143022_a1b2c3d4_0.jpg`

### 3. **Supported File Types**

#### **Images (max 10MB each):**
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)
- TIFF (.tiff)

#### **Videos (max 100MB each):**
- MP4 (.mp4)
- MPEG (.mpeg)
- QuickTime (.mov)
- AVI (.avi)
- WebM (.webm)
- OGG (.ogg)
- 3GP (.3gp)

### 4. **Upload Limits**
- **Maximum files per post:** 10 (like Instagram)
- **Image size limit:** 10MB per file
- **Video size limit:** 100MB per file
- **File validation:** Content type + extension validation
- **Security:** Files stored in user-specific directories

## 📁 File Storage Structure

```
uploads/
└── posts/
    └── {user_id}/
        ├── 20250618_143022_a1b2c3d4_0.jpg
        ├── 20250618_143025_b2c3d4e5_1.mp4
        └── 20250618_143030_c3d4e5f6_0.png
```

## 🔐 Security Features

1. **File Type Validation:** Double validation (MIME type + extension)
2. **Size Limits:** Enforced for both images and videos
3. **User Isolation:** Files stored in user-specific directories
4. **Unique Filenames:** Timestamp + UUID to prevent conflicts
5. **Content Validation:** Empty files rejected

## 💻 Frontend Integration Examples

### HTML Form Upload
```html
<form id="postForm" enctype="multipart/form-data">
  <input type="file" name="files" multiple accept="image/*,video/*" />
  <input type="text" name="caption" placeholder="Write a caption..." />
  <input type="text" name="location" placeholder="Add location..." />
  <button type="submit">Post</button>
</form>

<script>
document.getElementById('postForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  
  const response = await fetch('/posts/create-with-files', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + localStorage.getItem('token')
    },
    body: formData
  });
  
  const result = await response.json();
  console.log('Post created:', result);
});
</script>
```

### JavaScript File Upload
```javascript
async function uploadFiles(files, caption, location) {
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  
  formData.append('caption', caption);
  formData.append('location', location);
  formData.append('visibility', 'public');
  formData.append('hashtags', JSON.stringify(['tag1', 'tag2']));
  
  try {
    const response = await fetch('/posts/create-with-files', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    if (response.ok) {
      const post = await response.json();
      console.log('Post created successfully:', post);
      return post;
    } else {
      throw new Error('Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
}
```

### React Component Example
```jsx
import React, { useState } from 'react';

function PostUpload() {
  const [files, setFiles] = useState([]);
  const [caption, setCaption] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setUploading(true);

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('caption', caption);
    formData.append('visibility', 'public');

    try {
      const response = await fetch('/posts/create-with-files', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (response.ok) {
        const post = await response.json();
        console.log('Post created:', post);
        // Reset form
        setFiles([]);
        setCaption('');
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="file"
        multiple
        accept="image/*,video/*"
        onChange={handleFileChange}
        disabled={uploading}
      />
      <textarea
        value={caption}
        onChange={(e) => setCaption(e.target.value)}
        placeholder="Write a caption..."
        disabled={uploading}
      />
      <button type="submit" disabled={uploading || files.length === 0}>
        {uploading ? 'Uploading...' : 'Post'}
      </button>
    </form>
  );
}
```

## 🎯 Usage Scenarios

### Scenario 1: Instagram-like Single Upload
1. User selects image/video from device
2. Adds caption and location
3. Submits form to `/posts/create-with-files`
4. Post created with uploaded media

### Scenario 2: Carousel Post (Multiple Files)
1. User selects up to 10 images/videos
2. System creates carousel post
3. Files served in order with proper media types

### Scenario 3: Two-Step Upload
1. Upload files first with `/posts/upload-media`
2. Get media URLs back
3. Create post using traditional `/posts/` endpoint with URLs

## 🛠 Testing

### Test Upload System
```bash
curl -X GET "http://localhost:8000/posts/test-upload" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Upload Single File
```bash
curl -X POST "http://localhost:8000/posts/upload-media" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test-image.jpg"
```

### Create Post with Files
```bash
curl -X POST "http://localhost:8000/posts/create-with-files" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@test-image.jpg" \
  -F "caption=Test post with uploaded image"
```

## 🔧 Configuration

The system automatically:
- Creates `uploads/posts/` directory structure
- Mounts static file serving at `/uploads`
- Validates file types and sizes
- Generates unique filenames with timestamps

Your Instagram-like file upload system is now ready! 🎉
