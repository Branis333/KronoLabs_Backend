"""
Database Migration: Add Comics Support

This migration adds comic functionality to the existing database:
- Creates comic tables (comics, comic_pages, comic_likes, comic_comments, saved_comics)
- Updates reports table to support comic reports
- Adds comic relationships to users table

Run this after the previous binary storage migration.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid
from db.connection import get_db
from db.database import DATABASE_URL

def run_comics_migration():
    """Add comics support to existing database"""
    
    print("🎨 Starting Comics Migration...")
    
    try:
        # Get database connection
        database_url = DATABASE_URL
        engine = create_engine(database_url)
        
        print("🔗 Connected to database")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("📋 Creating comics table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comics (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        thumbnail_data BYTEA NOT NULL,
                        thumbnail_mime_type VARCHAR(100) NOT NULL,
                        genre VARCHAR(100),
                        status VARCHAR(50) NOT NULL DEFAULT 'ongoing',
                        is_public BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✅ Comics table created")
                
                print("📄 Creating comic_pages table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comic_pages (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        comic_id UUID NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
                        page_number INTEGER NOT NULL,
                        page_data BYTEA NOT NULL,
                        page_mime_type VARCHAR(100) NOT NULL,
                        page_title VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(comic_id, page_number)
                    )
                """))
                print("✅ Comic pages table created")
                
                print("👍 Creating comic_likes table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comic_likes (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        comic_id UUID NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, comic_id)
                    )
                """))
                print("✅ Comic likes table created")
                
                print("💬 Creating comic_comments table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comic_comments (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        comic_id UUID NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        text TEXT NOT NULL,
                        parent_comment_id UUID REFERENCES comic_comments(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✅ Comic comments table created")
                
                print("💾 Creating saved_comics table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS saved_comics (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        comic_id UUID NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, comic_id)
                    )
                """))
                print("✅ Saved comics table created")
                
                print("🚨 Updating reports table to support comics...")
                # Check if comic_id column exists in reports table
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'reports' AND column_name = 'comic_id'
                """))
                
                if not result.fetchone():
                    conn.execute(text("""
                        ALTER TABLE reports 
                        ADD COLUMN comic_id UUID REFERENCES comics(id) ON DELETE CASCADE
                    """))
                    print("✅ Added comic_id to reports table")
                else:
                    print("ℹ️  Reports table already has comic_id column")
                
                print("📊 Creating indexes for better performance...")
                
                # Comics indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_user_id ON comics(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_status ON comics(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_genre ON comics(genre)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_is_public ON comics(is_public)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_created_at ON comics(created_at DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_updated_at ON comics(updated_at DESC)"))
                
                # Comic pages indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_pages_comic_id ON comic_pages(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_pages_page_number ON comic_pages(comic_id, page_number)"))
                
                # Comic likes indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_likes_comic_id ON comic_likes(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_likes_user_id ON comic_likes(user_id)"))
                
                # Comic comments indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_comments_comic_id ON comic_comments(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_comments_user_id ON comic_comments(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_comments_parent ON comic_comments(parent_comment_id)"))
                
                # Saved comics indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_saved_comics_user_id ON saved_comics(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_saved_comics_comic_id ON saved_comics(comic_id)"))
                
                print("✅ All indexes created")
                
                print("🔧 Creating useful views...")
                
                # View for comic statistics
                conn.execute(text("""
                    CREATE OR REPLACE VIEW comic_stats AS
                    SELECT 
                        c.id,
                        c.title,
                        c.user_id,
                        u.username,
                        c.status,
                        c.genre,
                        COUNT(DISTINCT cp.id) as pages_count,
                        COUNT(DISTINCT cl.id) as likes_count,
                        COUNT(DISTINCT cc.id) as comments_count,
                        COUNT(DISTINCT sc.id) as saves_count,
                        c.created_at,
                        c.updated_at
                    FROM comics c
                    JOIN users u ON c.user_id = u.id
                    LEFT JOIN comic_pages cp ON c.id = cp.comic_id
                    LEFT JOIN comic_likes cl ON c.id = cl.comic_id
                    LEFT JOIN comic_comments cc ON c.id = cc.comic_id
                    LEFT JOIN saved_comics sc ON c.id = sc.comic_id
                    GROUP BY c.id, u.username
                """))
                print("✅ Comic stats view created")
                
                print("🔍 Adding search capabilities...")
                
                # Add full-text search indexes for comics
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_comics_title_search 
                    ON comics USING gin(to_tsvector('english', title))
                """))
                
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_comics_description_search 
                    ON comics USING gin(to_tsvector('english', COALESCE(description, '')))
                """))
                
                print("✅ Search indexes created")
                
                print("⚡ Creating triggers for automatic updated_at...")
                
                # Function to update updated_at timestamp
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql'
                """))
                
                # Trigger for comics table
                conn.execute(text("""
                    DROP TRIGGER IF EXISTS update_comics_updated_at ON comics
                """))
                
                conn.execute(text("""
                    CREATE TRIGGER update_comics_updated_at
                    BEFORE UPDATE ON comics
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
                """))
                
                print("✅ Triggers created")
                
                print("🎯 Adding constraints and validation...")
                
                # Add check constraints for valid status values
                conn.execute(text("""
                    ALTER TABLE comics 
                    DROP CONSTRAINT IF EXISTS comics_status_check
                """))
                
                conn.execute(text("""
                    ALTER TABLE comics 
                    ADD CONSTRAINT comics_status_check 
                    CHECK (status IN ('ongoing', 'completed', 'hiatus'))
                """))
                
                # Add check constraint for page numbers
                conn.execute(text("""
                    ALTER TABLE comic_pages 
                    DROP CONSTRAINT IF EXISTS comic_pages_page_number_check
                """))
                
                conn.execute(text("""
                    ALTER TABLE comic_pages 
                    ADD CONSTRAINT comic_pages_page_number_check 
                    CHECK (page_number > 0)
                """))
                
                print("✅ Constraints added")
                
                # Commit transaction
                trans.commit()
                
                print("\n🎉 Comics Migration Completed Successfully!")
                print("📊 Summary of changes:")
                print("  ✅ Created 5 new tables for comics functionality")
                print("  ✅ Updated reports table to support comic reports")  
                print("  ✅ Added 15+ indexes for optimal performance")
                print("  ✅ Created comic stats view for analytics")
                print("  ✅ Added full-text search capabilities")
                print("  ✅ Set up automatic timestamp triggers")
                print("  ✅ Added data validation constraints")
                print("\n💡 Your database now supports:")
                print("  🎨 Comic creation with thumbnails and pages")
                print("  📄 Unlimited pages per comic")
                print("  👍 Likes, comments, and saves for comics")
                print("  🔍 Full-text search for comics")
                print("  📊 Built-in analytics and statistics")
                print("  🚨 Reporting system for comics")
                
                return True
                
            except Exception as e:
                print(f"❌ Error during migration: {e}")
                trans.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    
    print("\n🔍 Verifying migration...")
    
    try:
        database_url = DATABASE_URL
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if all tables exist
            tables_to_check = [
                'comics', 'comic_pages', 'comic_likes', 
                'comic_comments', 'saved_comics'
            ]
            
            for table in tables_to_check:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                
                exists = result.fetchone()[0]
                if exists:
                    print(f"  ✅ Table '{table}' exists")
                else:
                    print(f"  ❌ Table '{table}' missing")
                    return False
            
            # Check if comic_id column was added to reports
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'reports' AND column_name = 'comic_id'
                )
            """))
            
            if result.fetchone()[0]:
                print("  ✅ Reports table updated with comic_id")
            else:
                print("  ❌ Reports table missing comic_id column")
                return False
            
            # Check some indexes
            result = conn.execute(text("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE tablename LIKE 'comic%' OR indexname LIKE '%comic%'
            """))
            
            index_count = result.fetchone()[0]
            print(f"  ✅ Found {index_count} comic-related indexes")
            
            # Check view
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = 'comic_stats'
                )
            """))
            
            if result.fetchone()[0]:
                print("  ✅ Comic stats view created")
            else:
                print("  ❌ Comic stats view missing")
            
            print("✅ Migration verification completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration function"""
    
    print("🎨 Comics Database Migration")
    print("=" * 50)
    
    # Run migration
    success = run_comics_migration()
    
    if success:
        # Verify migration
        verify_migration()
        print("\n🎉 Comics system is now ready!")
        print("🚀 You can now:")
        print("  - Create comics with POST /comics/")
        print("  - Browse comics with GET /comics/")
        print("  - Add pages with POST /comics/{id}/pages")
        print("  - Like, save, and comment on comics")
    else:
        print("\n💥 Migration failed!")
        print("🛠️  Please check the error messages above and try again")

if __name__ == "__main__":
    main()