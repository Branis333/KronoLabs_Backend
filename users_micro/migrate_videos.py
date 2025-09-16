"""
Database Migration Script - Video System
Run this script to add video tables to your existing database
"""

import asyncio
from sqlalchemy import text
from db.connection import engine

# SQL for creating video tables
VIDEO_MIGRATION_SQL = """
-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_data BYTEA NOT NULL,  -- Binary thumbnail data
    thumbnail_mime_type VARCHAR(100) NOT NULL,
    video_url TEXT NOT NULL,  -- Google Drive URL
    video_filename VARCHAR(255),
    duration INTEGER,  -- Duration in seconds
    category VARCHAR(100),
    tags TEXT,  -- JSON string of tags
    is_public BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create video_likes table
CREATE TABLE IF NOT EXISTS video_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, video_id)  -- Prevent duplicate likes
);

-- Create video_comments table
CREATE TABLE IF NOT EXISTS video_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    parent_comment_id UUID REFERENCES video_comments(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create saved_videos table (user watchlist)
CREATE TABLE IF NOT EXISTS saved_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, video_id)  -- Prevent duplicate saves
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);
CREATE INDEX IF NOT EXISTS idx_videos_is_public ON videos(is_public);
CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);
CREATE INDEX IF NOT EXISTS idx_videos_title ON videos USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_videos_description ON videos USING GIN(to_tsvector('english', description));

CREATE INDEX IF NOT EXISTS idx_video_likes_user_id ON video_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_video_likes_video_id ON video_likes(video_id);
CREATE INDEX IF NOT EXISTS idx_video_likes_created_at ON video_likes(created_at);

CREATE INDEX IF NOT EXISTS idx_video_comments_video_id ON video_comments(video_id);
CREATE INDEX IF NOT EXISTS idx_video_comments_user_id ON video_comments(user_id);
CREATE INDEX IF NOT EXISTS idx_video_comments_parent_id ON video_comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_video_comments_created_at ON video_comments(created_at);

CREATE INDEX IF NOT EXISTS idx_saved_videos_user_id ON saved_videos(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_videos_video_id ON saved_videos(video_id);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_video_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_video_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW
    EXECUTE FUNCTION update_video_updated_at();

-- Insert some sample categories (optional)
-- You can remove this if you don't want sample data
/*
INSERT INTO videos (
    user_id, title, description, thumbnail_data, thumbnail_mime_type, 
    video_url, category, is_public, view_count
) VALUES 
-- Sample data would go here, but we'll leave this empty for now
-- since we don't have actual user IDs or binary data to insert
*/

COMMIT;
"""

async def run_migration():
    """Run the video migration"""
    try:
        print("🚀 Starting video system migration...")
        
        # Execute migration SQL in separate transactions for better error handling
        with engine.connect() as connection:
            
            # First, let's use SQLAlchemy to create the tables from models
            print("📋 Creating tables using SQLAlchemy models...")
            try:
                from models.users_models import Base as UserBase
                from models.social_models import Base as SocialBase
                
                # Create all tables
                UserBase.metadata.create_all(bind=engine)
                SocialBase.metadata.create_all(bind=engine)
                print("✅ Tables created successfully using SQLAlchemy")
                
            except Exception as e:
                print(f"⚠️  SQLAlchemy table creation: {e}")
                print("   Continuing with manual SQL...")
            
            # Now create indexes and other enhancements manually
            index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_videos_is_public ON videos(is_public)",
                "CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category)",
                "CREATE INDEX IF NOT EXISTS idx_video_likes_user_id ON video_likes(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_video_likes_video_id ON video_likes(video_id)",
                "CREATE INDEX IF NOT EXISTS idx_video_comments_video_id ON video_comments(video_id)",
                "CREATE INDEX IF NOT EXISTS idx_video_comments_user_id ON video_comments(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_saved_videos_user_id ON saved_videos(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_saved_videos_video_id ON saved_videos(video_id)"
            ]
            
            # Create indexes
            print("📊 Creating performance indexes...")
            for statement in index_statements:
                try:
                    connection.execute(text(statement))
                    print(f"✅ Created index: {statement.split('ON')[1].strip()}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"⚠️  Index already exists: {statement.split('ON')[1].strip()}")
                    else:
                        print(f"❌ Index error: {e}")
                
                connection.commit()  # Commit each index separately
            
            # Create trigger function
            print("⚙️  Creating update trigger...")
            try:
                trigger_function = """
                CREATE OR REPLACE FUNCTION update_video_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
                connection.execute(text(trigger_function))
                connection.commit()
                print("✅ Created trigger function")
                
                # Create the trigger
                trigger_sql = """
                CREATE TRIGGER trigger_update_video_updated_at
                    BEFORE UPDATE ON videos
                    FOR EACH ROW
                    EXECUTE FUNCTION update_video_updated_at();
                """
                connection.execute(text(trigger_sql))
                connection.commit()
                print("✅ Created update trigger")
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️  Trigger already exists")
                else:
                    print(f"⚠️  Trigger creation failed: {e}")
        
        print("\n🎉 Video system migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Install video dependencies: pip install -r requirements_video.txt")
        print("2. Set up Google Drive credentials (see VIDEO_SETUP_GUIDE.md)")
        print("3. Test video upload endpoint: POST /videos/")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    # Run migration
    success = asyncio.run(run_migration())
    
    if success:
        print("\n✨ Video system is ready to use!")
        print("📚 Check VIDEO_SETUP_GUIDE.md for complete setup instructions")
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        print("🔍 Make sure your database is running and accessible.")