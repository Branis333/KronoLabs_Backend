# Enhanced Direct Messages API - Usage Guide

## Overview
Your messaging system now supports Instagram-like functionality with rich content sharing:

- **Text messages** - Traditional text messaging
- **Image/video uploads** - Send photos and videos directly from device
- **Post sharing** - Share posts from the platform in messages
- **Story sharing** - Share stories from the platform in messages  
- **Mixed messages** - Combine text, media, and shared content

## Database Changes Applied ✅

### DirectMessage Model Updates:
- ✅ Added `shared_post_id` column (UUID, nullable, references posts table)
- ✅ Added `shared_story_id` column (UUID, nullable, references stories table)
- ✅ Enhanced message schemas to support new content types

## API Endpoints

### 1. Send Enhanced Message
```
POST /messages/
Content-Type: multipart/form-data
```

**Parameters:**
- `receiver_id` (required): ID of the message recipient
- `message_text` (optional): Text content of the message
- `shared_post_id` (optional): UUID of post to share
- `shared_story_id` (optional): UUID of story to share  
- `file` (optional): Image/video file to upload

**Validation:** At least one of `message_text`, `file`, `shared_post_id`, or `shared_story_id` must be provided.

### 2. Serve Message Media
```
GET /messages/uploads/{user_id}/{filename}
```
Serves uploaded message media files with access control.

## Usage Examples

### 1. Text-Only Message
```python
import requests

# Send simple text message
data = {
    'receiver_id': 2,
    'message_text': 'Hey! How are you doing? 👋'
}

response = requests.post('/messages/', 
    data=data,
    headers={'Authorization': f'Bearer {token}'}
)
```

### 2. Image/Video Upload Message
```python
# Send message with uploaded image
data = {
    'receiver_id': 2,
    'message_text': 'Check out this amazing sunset!'
}

files = {
    'file': ('sunset.jpg', open('sunset.jpg', 'rb'), 'image/jpeg')
}

response = requests.post('/messages/', 
    data=data, 
    files=files,
    headers={'Authorization': f'Bearer {token}'}
)
```

### 3. Share Post in Message
```python
# Share a post from the platform
data = {
    'receiver_id': 2,
    'message_text': 'You have to see this post!',
    'shared_post_id': '123e4567-e89b-12d3-a456-426614174000'
}

response = requests.post('/messages/', 
    data=data,
    headers={'Authorization': f'Bearer {token}'}
)
```

### 4. Share Story in Message
```python
# Share a story from the platform
data = {
    'receiver_id': 2,
    'message_text': 'Look at this story!',
    'shared_story_id': '987fcdeb-51a2-43d1-9876-ba987654321f'
}

response = requests.post('/messages/', 
    data=data,
    headers={'Authorization': f'Bearer {token}'}
)
```

### 5. Mixed Message (Text + Image + Shared Post)
```python
# Send message with text, uploaded image, and shared post
data = {
    'receiver_id': 2,
    'message_text': 'This reminds me of that post you shared!',
    'shared_post_id': '123e4567-e89b-12d3-a456-426614174000'
}

files = {
    'file': ('similar_pic.jpg', open('similar_pic.jpg', 'rb'), 'image/jpeg')
}

response = requests.post('/messages/', 
    data=data, 
    files=files,
    headers={'Authorization': f'Bearer {token}'}
)
```

## Response Format

### Enhanced MessageResponse
```json
{
  "id": "uuid",
  "sender_id": 1,
  "receiver_id": 2,
  "sender": {
    "id": 1,
    "username": "john_doe",
    "full_name": "John Doe",
    "profile_image_url": "/uploads/profiles/1_profile.jpg",
    ...
  },
  "receiver": {
    "id": 2,
    "username": "jane_doe", 
    "full_name": "Jane Doe",
    "profile_image_url": "/uploads/profiles/2_profile.jpg",
    ...
  },
  "message_text": "Check out this post!",
  "media_url": "/messages/uploads/1/20250618_161000_abc123_0.jpg",
  "shared_post_id": "123e4567-e89b-12d3-a456-426614174000",
  "shared_story_id": null,
  "shared_post": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "user": {...},
    "caption": "Beautiful sunset at the beach",
    "media_url": "/posts/uploads/3/sunset.jpg",
    "media_type": "image",
    "created_at": "2025-06-18T10:30:00Z",
    ...
  },
  "shared_story": null,
  "created_at": "2025-06-18T16:10:00Z",
  "is_read": false
}
```

## Frontend Integration Examples

### React/JavaScript
```javascript
// Send text + image message
const sendEnhancedMessage = async (receiverId, text, file, sharedPostId, sharedStoryId) => {
  const formData = new FormData();
  formData.append('receiver_id', receiverId);
  
  if (text) formData.append('message_text', text);
  if (file) formData.append('file', file);
  if (sharedPostId) formData.append('shared_post_id', sharedPostId);
  if (sharedStoryId) formData.append('shared_story_id', sharedStoryId);
  
  const response = await fetch('/messages/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return await response.json();
};

// Share post in message
const sharePost = async (receiverId, postId, message = '') => {
  return await sendEnhancedMessage(
    receiverId, 
    message, 
    null, 
    postId, 
    null
  );
};

// Share story in message  
const shareStory = async (receiverId, storyId, message = '') => {
  return await sendEnhancedMessage(
    receiverId, 
    message, 
    null, 
    null, 
    storyId
  );
};

// Upload and send image
const sendImageMessage = async (receiverId, imageFile, text = '') => {
  return await sendEnhancedMessage(
    receiverId, 
    text, 
    imageFile, 
    null, 
    null
  );
};
```

## File Upload Requirements

### Message Media
- **Images**: JPEG, PNG, GIF, WebP, BMP (max 10MB)
- **Videos**: MP4, MPEG, QuickTime, AVI, WebM (max 50MB)
- **Storage**: `uploads/messages/{user_id}/`
- **Access Control**: Only sender and receiver can access files

### Validation Rules
- At least one content type required (text, file, or shared content)
- Shared stories must not be expired
- Shared posts and stories must exist
- File type and size validation
- Receiver must exist and not be the sender

## Security Features

### File Access Control
- Users can only access media from conversations they're part of
- URL-based access protection
- File paths are validated server-side

### Content Validation
- Shared posts and stories are validated for existence
- Story expiration is checked before sharing
- User permissions are verified

## Error Handling

### Common Errors
```json
// Missing content
{
  "detail": "Message must contain at least text, media, or shared content"
}

// Invalid file type
{
  "detail": "Unsupported file type: application/pdf or extension: .pdf"
}

// File too large
{
  "detail": "Video exceeds 50MB limit"
}

// Shared content not found
{
  "detail": "Shared post not found"
}

// Expired story
{
  "detail": "Cannot share expired story"
}

// Access denied to media
{
  "detail": "Access denied to this media file"
}
```

## Storage Structure
```
uploads/
├── messages/
│   └── {sender_user_id}/
│       ├── 20250618_161000_abc123_0.jpg
│       ├── 20250618_161500_def456_0.mp4
│       └── ...
├── posts/
│   └── {user_id}/
│       └── ...
└── stories/
    └── {user_id}/
        └── ...
```

Your enhanced messaging system now supports rich Instagram-like communication with media uploads and content sharing! 🎉
