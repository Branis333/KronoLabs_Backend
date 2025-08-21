from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from Endpoints import auth, posts, social, stories, messages, search
from db.connection import engine
from db.database import test_connection
import models.users_models as user_models
import models.social_models as social_models
from sqlalchemy import text

app = FastAPI(
    title="KronoLabs Social Media API",
    description="Backend API for KronoLabs - Social Media App for Artists",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test database connection on startup
@app.on_event("startup")
async def startup_event():
    print("Testing Supabase connection...")
    try:
        # Test connection directly here
        with engine.connect() as connection:
            result = connection.execute(text("SELECT NOW() as current_time, version() as db_version;"))
            row = result.fetchone()
            print(f"✅ Supabase connection successful!")
            print(f"Database time: {row[0]}")
            print(f"Database version: {row[1]}")
            
            # Try to create tables if they don't exist
            from models.users_models import Base as UserBase
            from models.social_models import Base as SocialBase
            UserBase.metadata.create_all(bind=engine)
            SocialBase.metadata.create_all(bind=engine)
            print("✅ Database tables verified/created")
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print("⚠️ App will start but database functionality will be limited")

# Remove the immediate table creation from here since we moved it to startup event
# user_models.Base.metadata.create_all(bind=engine)
# social_models.Base.metadata.create_all(bind=engine)

# Create uploads directory if it doesn't exist
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

# Mount static files for serving uploaded media
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(social.router)
app.include_router(stories.router)
app.include_router(messages.router)
app.include_router(search.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to KronoLabs Social Media API for Artists",
        "version": "1.0.0",
        "features": [
            "User Authentication",
            "Posts with Media",
            "Stories (24h)",
            "Direct Messages",
            "Follow/Unfollow",
            "Likes & Comments",
            "Search & Discovery",
            "Notifications",
            "Hashtags",
            "User Tagging"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint with database status"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            db_status = "connected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "message": "KronoLabs API is running successfully"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": str(e),
            "message": "API is running but database is unavailable"
        }