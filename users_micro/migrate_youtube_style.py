#!/usr/bin/env python3
"""
YouTube-Style Video System Migration Script

This script creates the necessary tables for YouTube-style video optimization:
- Video table with binary storage capabilities  
- VideoQuality table for multi-resolution storage
- VideoSegment table for streaming segments
- Proper indexes for performance

Run this after implementing the YouTube-style video system.
"""

from sqlalchemy import text
from db.connection import get_db

def create_youtube_style_tables():
    """
    Creates YouTube-style video tables with binary storage optimization
    """
    
    # Get database connection
    db = next(get_db())
    
    print("🎬 Creating YouTube-Style Video Tables...")
    
    try:
        # Create Video table with YouTube-style features
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS videos (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                tags JSONB DEFAULT '[]'::jsonb,
                
                -- YouTube-style processing status
                processing_status VARCHAR(50) DEFAULT 'processing',
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Video metadata
                duration INTEGER, -- in seconds
                original_resolution VARCHAR(20), -- e.g., "1920x1080"
                original_size BIGINT, -- in bytes
                
                -- Thumbnails (multiple sizes)
                thumbnail_small_data BYTEA, -- 320x180
                thumbnail_medium_data BYTEA, -- 480x270  
                thumbnail_large_data BYTEA, -- 640x360
                thumbnail_mime_type VARCHAR(50) DEFAULT 'image/jpeg',
                
                -- Video metadata
                original_filename VARCHAR(255),
                fps INTEGER,
                
                -- Engagement metrics
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0,
                
                -- Privacy and moderation
                is_public BOOLEAN DEFAULT true,
                is_monetized BOOLEAN DEFAULT false,
                is_age_restricted BOOLEAN DEFAULT false,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("✅ Created videos table")
        
        # Create VideoQuality table for multi-resolution storage
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS video_qualities (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                video_id VARCHAR(36) NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                
                -- Quality specifications  
                quality VARCHAR(10) NOT NULL, -- "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"
                resolution VARCHAR(20) NOT NULL, -- "1920x1080", "1280x720", etc.
                bitrate INTEGER NOT NULL, -- in kbps
                codec VARCHAR(20) DEFAULT 'h264', -- "h264", "vp9", "av1"
                
                -- File information
                total_size BIGINT, -- total size of all segments in bytes
                segment_duration INTEGER DEFAULT 4, -- seconds per segment
                total_segments INTEGER,
                
                -- Processing status
                processing_status VARCHAR(50) DEFAULT 'processing',
                processing_progress INTEGER DEFAULT 0, -- percentage
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(video_id, quality)
            );
        """))
        print("✅ Created video_qualities table")
        
        # Create VideoSegment table for streaming chunks
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS video_segments (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                video_quality_id VARCHAR(36) NOT NULL REFERENCES video_qualities(id) ON DELETE CASCADE,
                
                -- Segment information
                segment_index INTEGER NOT NULL, -- 0, 1, 2, 3, ...
                segment_data BYTEA NOT NULL, -- actual video segment binary data
                segment_size INTEGER NOT NULL, -- size in bytes
                start_time DECIMAL(10,3) NOT NULL, -- start time in seconds
                end_time DECIMAL(10,3) NOT NULL, -- end time in seconds
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(video_quality_id, segment_index)
            );
        """))
        print("✅ Created video_segments table")
        
        # Create performance indexes
        print("🚀 Creating performance indexes...")
        
        # Video table indexes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_public ON videos(is_public);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_views ON videos(views DESC);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_videos_processing ON videos(processing_status);"))
        
        # VideoQuality indexes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_video_qualities_video_id ON video_qualities(video_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_video_qualities_quality ON video_qualities(quality);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_video_qualities_processing ON video_qualities(processing_status);"))
        
        # VideoSegment indexes
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_video_segments_quality_id ON video_segments(video_quality_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_video_segments_index ON video_segments(video_quality_id, segment_index);"))
        
        print("✅ Created all performance indexes")
        
        # Update existing video-related tables to work with new system
        print("🔄 Updating existing video-related tables...")
        
        # Update video_likes table if exists
        db.execute(text("""
            ALTER TABLE video_likes 
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))
        
        # Update video_comments table if exists  
        db.execute(text("""
            ALTER TABLE video_comments 
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))
        
        # Update saved_videos table if exists
        db.execute(text("""
            ALTER TABLE saved_videos 
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))
        
        print("✅ Updated existing video-related tables")
        
        # Commit all changes
        db.commit()
        
        print("🎉 YouTube-Style Video System Migration Complete!")
        print("\n📊 Created Tables:")
        print("   • videos - Main video metadata with thumbnails")
        print("   • video_qualities - Multi-resolution video storage")  
        print("   • video_segments - Streaming segments for each quality")
        print("\n🚀 Features Enabled:")
        print("   • Multi-resolution transcoding (144p to 4K)")
        print("   • Adaptive bitrate streaming")
        print("   • Binary storage (no external dependencies)")
        print("   • Multiple thumbnail sizes")
        print("   • Processing status tracking")
        print("   • Performance-optimized indexes")
        print("\n🎬 Ready for YouTube-style video processing!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise e
    finally:
        db.close()

def check_migration_status():
    """Check if migration was successful"""
    db = next(get_db())
    
    try:
        # Check if tables exist
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('videos', 'video_qualities', 'video_segments')
            ORDER BY table_name;
        """))
        
        tables = [row[0] for row in result.fetchall()]
        
        print("📋 Migration Status:")
        print(f"   • videos table: {'✅ EXISTS' if 'videos' in tables else '❌ MISSING'}")
        print(f"   • video_qualities table: {'✅ EXISTS' if 'video_qualities' in tables else '❌ MISSING'}")
        print(f"   • video_segments table: {'✅ EXISTS' if 'video_segments' in tables else '❌ MISSING'}")
        
        if len(tables) == 3:
            print("🎉 All YouTube-style tables are ready!")
            return True
        else:
            print("⚠️ Some tables are missing. Run migration again.")
            return False
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🎬 YouTube-Style Video System Migration")
    print("=====================================")
    
    # Check current status
    if check_migration_status():
        print("✅ Migration already complete!")
    else:
        print("🚀 Starting migration...")
        create_youtube_style_tables()
        
    print("\n🎯 Next Steps:")
    print("1. Install FFmpeg: https://ffmpeg.org/download.html")
    print("2. Update main.py to include streaming router")
    print("3. Test video upload with: POST /videos/")
    print("4. Test streaming with: GET /videos/{id}/stream")