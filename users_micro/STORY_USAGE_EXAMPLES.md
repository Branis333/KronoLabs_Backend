# Instagram-Style Stories API - Usage Examples

## Overview
Your stories API now supports Instagram-like functionality with flexible content creation:

- **Text-only stories** (like Instagram text stories)
- **Media-only stories** (images/videos)
- **Mixed stories** (text + media)
- **Profile pictures** during registration and profile updates

## Story Creation Examples

### 1. Text-Only Story
```python
# POST /stories/
# Form data:
# text: "Check out this amazing sunset! 🌅"
# files: (none)

# Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": 1,
  "user": {...},
  "text": "Check out this amazing sunset! 🌅",
  "media_url": null,
  "media_type": null,
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "view_count": 0,
  "is_viewed": false
}
```

### 2. Media-Only Story
```python
# POST /stories/
# Form data:
# files: [image.jpg]
# text: (none)

# Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174001",
  "user_id": 1,
  "user": {...},
  "text": null,
  "media_url": "/stories/uploads/1/20241215_103000_abc12345_0.jpg",
  "media_type": "image",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "view_count": 0,
  "is_viewed": false
}
```

### 3. Text + Media Story
```python
# POST /stories/
# Form data:
# text: "Beautiful morning! ☀️"
# files: [morning.mp4]

# Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174002",
  "user_id": 1,
  "user": {...},
  "text": "Beautiful morning! ☀️",
  "media_url": "/stories/uploads/1/20241215_103000_xyz98765_0.mp4",
  "media_type": "video",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z",
  "view_count": 0,
  "is_viewed": false
}
```

## Profile Picture Examples

### 1. Registration with Profile Picture
```python
# POST /register
# Form data:
# username: "john_doe"
# email: "john@example.com"
# password: "securepassword123"
# full_name: "John Doe"
# profile_picture: [profile.jpg]

# Response:
{
  "message": "User created successfully",
  "user_id": 1,
  "username": "john_doe",
  "profile_image_url": "/uploads/profiles/1_20241215_103000_profile.jpg"
}
```

### 2. Registration without Profile Picture
```python
# POST /register
# Form data:
# username: "jane_doe"
# email: "jane@example.com"
# password: "securepassword123"
# full_name: "Jane Doe"
# profile_picture: (none)

# Response:
{
  "message": "User created successfully",
  "user_id": 2,
  "username": "jane_doe",
  "profile_image_url": null
}
```

### 3. Update Profile with New Picture
```python
# PUT /update-profile
# Headers: Authorization: Bearer <token>
# Form data:
# full_name: "John Smith"
# bio: "Photography enthusiast"
# profile_picture: [new_profile.jpg]

# Response:
{
  "message": "Profile updated successfully",
  "user": {
    "id": 1,
    "username": "john_doe",
    "full_name": "John Smith",
    "bio": "Photography enthusiast",
    "profile_image_url": "/uploads/profiles/1_20241215_104500_new_profile.jpg",
    ...
  }
}
```

## Frontend Integration Examples

### React/JavaScript Example for Stories
```javascript
// Text-only story
const createTextStory = async (text) => {
  const formData = new FormData();
  formData.append('text', text);
  
  const response = await fetch('/stories/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return await response.json();
};

// Media story with text
const createMediaStory = async (file, text = null) => {
  const formData = new FormData();
  formData.append('files', file);
  if (text) formData.append('text', text);
  
  const response = await fetch('/stories/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return await response.json();
};

// Registration with profile picture
const registerWithPhoto = async (userData, profilePicture) => {
  const formData = new FormData();
  Object.keys(userData).forEach(key => {
    formData.append(key, userData[key]);
  });
  if (profilePicture) {
    formData.append('profile_picture', profilePicture);
  }
  
  const response = await fetch('/register', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
};
```

## File Upload Requirements

### Stories
- **Images**: JPEG, PNG, GIF, WebP, BMP, TIFF (max 10MB)
- **Videos**: MP4, MPEG, QuickTime, AVI, WebM, OGG, 3GP (max 50MB)
- **Text**: Optional string (any length)
- **Validation**: Must have either text OR media (or both)

### Profile Pictures
- **Images**: JPEG, PNG, GIF, WebP, BMP, TIFF (max 5MB)
- **Optional**: Can register/update without profile picture

## Error Handling

### Story Creation Errors
```json
// Missing both text and media
{
  "detail": "You must provide either text or at least one media file for a story."
}

// Invalid file type
{
  "detail": "Unsupported file type: application/pdf or extension: .pdf"
}

// File too large
{
  "detail": "Video file video.mp4 exceeds 50MB limit"
}
```

### Profile Picture Errors
```json
// Invalid file type
{
  "detail": "Unsupported profile picture format. Use JPEG, PNG, GIF, WebP, BMP, or TIFF"
}

// File too large
{
  "detail": "Profile picture size exceeds 5MB limit"
}
```

## Storage Structure
```
uploads/
├── stories/
│   └── {user_id}/
│       ├── 20241215_103000_abc12345_0.jpg
│       ├── 20241215_103000_xyz98765_0.mp4
│       └── ...
└── profiles/
    ├── 1_20241215_103000_profile.jpg
    ├── 2_20241215_104500_new_profile.jpg
    └── ...
```

Your Instagram-like backend is now fully functional with flexible story creation and profile picture management!
