"""
Video Backend Setup Guide

This guide will help you set up the complete video system with Google Drive integration.

📋 OVERVIEW
- Videos are uploaded to Google Drive for storage
- Thumbnails are stored as binary data in the database
- Full YouTube-like functionality: upload, view, like, comment, save
- Support for categories, tags, and search

🔧 INSTALLATION REQUIREMENTS

1. Install Python dependencies:
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib opencv-python Pillow

2. Alternative installation (if you get import errors):
pip install --upgrade google-api-python-client
pip install --upgrade google-auth-httplib2  
pip install --upgrade google-auth-oauthlib
pip install opencv-python-headless  # Use headless version for servers
pip install Pillow

🔑 GOOGLE DRIVE SETUP

Step 1: Create Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable the Google Drive API:
   - Go to APIs & Services > Library
   - Search for "Google Drive API"
   - Click Enable

Step 2: Create Service Account
1. Go to APIs & Services > Credentials
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details
4. Click "Create and Continue"
5. Grant "Editor" role (or custom role with Drive permissions)
6. Click "Done"

Step 3: Generate Key File
1. In Credentials, click on your service account email
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Download the JSON file
6. Rename it to "google_drive_credentials.json"
7. Place it in your project root OR create a "credentials" folder

Step 4: Share Google Drive Folder
1. Open the Google Drive folder: https://drive.google.com/drive/folders/1FH-72iCDmnggCcJht_eJ6HCxRj70snIt
2. Right-click > Share
3. Add the service account email (found in your JSON file)
4. Give "Editor" permissions
5. Click "Send"

📁 FILE STRUCTURE
Your project should have:
```
your_project/
├── credentials/
│   └── google_drive_credentials.json  # Service account key
├── utils/
│   ├── google_drive_utils.py         # Google Drive operations
│   └── media_utils.py                # Enhanced with video support
├── models/
│   ├── social_models.py              # Video models added
│   └── users_models.py               # Video relationships added
├── schemas/
│   └── social_schemas.py             # Video schemas added
├── Endpoints/
│   └── videos.py                     # Complete video API
└── main.py                           # Videos router included
```

⚙️ CONFIGURATION

The system will automatically look for credentials in these locations:
1. credentials/google_drive_credentials.json
2. google_drive_credentials.json (in root)
3. Path specified in GOOGLE_DRIVE_CREDENTIALS_PATH environment variable

Example environment variable setup:
```
export GOOGLE_DRIVE_CREDENTIALS_PATH="/path/to/your/credentials.json"
```

🎯 API ENDPOINTS

Video Management:
- POST /videos/                          # Upload video with thumbnail
- GET /videos/                           # Browse all videos (with filters)
- GET /videos/{video_id}                 # Get specific video + increment views
- PATCH /videos/{video_id}               # Update video info (creator only)
- DELETE /videos/{video_id}              # Delete video (creator only)

Interactions:
- POST /videos/{video_id}/like           # Like/unlike video
- POST /videos/{video_id}/save           # Save/unsave to watchlist
- POST /videos/{video_id}/comments       # Add comment
- GET /videos/{video_id}/comments        # Get comments

Media Serving:
- GET /videos/media/thumbnail/{video_id} # Serve thumbnail from database

📤 UPLOAD FLOW

1. User uploads video file + thumbnail
2. Thumbnail is processed and stored in database as binary
3. Video is uploaded to Google Drive
4. Google Drive returns shareable URL
5. Video record created with thumbnail (binary) + video URL
6. Users can stream video directly from Google Drive URL

🔍 FEATURES INCLUDED

✅ Video upload with validation (MP4, AVI, MOV, WebM, etc.)
✅ Thumbnail upload and processing
✅ Google Drive storage with public access
✅ YouTube-like video browsing and discovery
✅ Like/unlike functionality
✅ Save to watchlist (favorites)
✅ Commenting system with threading
✅ View count tracking
✅ Category and tag support
✅ Search and filtering
✅ Privacy controls (public/private)
✅ Creator-only edit and delete
✅ Automatic thumbnail generation (if OpenCV available)

🚀 TESTING

1. Start your FastAPI server:
   uvicorn main:app --reload

2. Test video upload:
   ```bash
   curl -X POST "http://localhost:8000/videos/" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -F "title=My First Video" \
     -F "description=Test video description" \
     -F "category=Entertainment" \
     -F "video_file=@/path/to/video.mp4" \
     -F "thumbnail=@/path/to/thumbnail.jpg"
   ```

3. Browse videos:
   GET http://localhost:8000/videos/

4. Get specific video:
   GET http://localhost:8000/videos/{video_id}

📊 DATABASE TABLES

New tables created:
- videos: Main video information with thumbnail binary data
- video_likes: User likes on videos  
- video_comments: Comments with threading support
- saved_videos: User watchlist/favorites

Updated tables:
- users: Added video relationships

🔒 SECURITY NOTES

1. Service account has limited permissions to your specific Drive folder
2. Videos are made publicly readable but not writable
3. Only authenticated users can upload videos
4. Only video creators can edit/delete their videos
5. Database stores binary thumbnails securely
6. Google Drive URLs are publicly accessible for streaming

⚠️ TROUBLESHOOTING

Issue: "Google API client libraries not installed"
Solution: Run pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Issue: "Video processing libraries not available"  
Solution: Run pip install opencv-python Pillow

Issue: "Failed to upload video to Google Drive"
Solutions:
- Check service account has access to the Drive folder
- Verify credentials file path and format
- Ensure Google Drive API is enabled in your project

Issue: "Permission denied" from Google Drive
Solution: Make sure you shared the Drive folder with your service account email

Issue: Videos upload but can't be played
Solution: Check that files are made publicly readable (the code handles this automatically)

🎉 SUCCESS!

If everything is set up correctly:
1. Videos will be uploaded to your Google Drive folder
2. Thumbnails will be stored in your database
3. Users can browse, watch, like, and comment on videos
4. The system works like a YouTube clone with your own storage

Need help? Check the Google Drive folder to see if files are being uploaded, and check your FastAPI logs for any error messages.
"""