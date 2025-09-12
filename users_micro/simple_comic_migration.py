"""
Simple Comics Migration

This script adds comic tables to your existing database.
Run this after you've already applied the binary storage migration.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from db.database import DATABASE_URL

def create_comic_tables():
    """Create all comic-related tables"""
    
    print("🎨 Creating Comics Tables...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # Comics table
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
                        status VARCHAR(50) NOT NULL DEFAULT 'ongoing' CHECK (status IN ('ongoing', 'completed', 'hiatus')),
                        is_public BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Comic pages table
                print("📄 Creating comic_pages table...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comic_pages (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        comic_id UUID NOT NULL REFERENCES comics(id) ON DELETE CASCADE,
                        page_number INTEGER NOT NULL CHECK (page_number > 0),
                        page_data BYTEA NOT NULL,
                        page_mime_type VARCHAR(100) NOT NULL,
                        page_title VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(comic_id, page_number)
                    )
                """))
                
                # Comic likes table
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
                
                # Comic comments table
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
                
                # Saved comics table
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
                
                # Update reports table
                print("🚨 Updating reports table...")
                conn.execute(text("""
                    ALTER TABLE reports 
                    ADD COLUMN IF NOT EXISTS comic_id UUID REFERENCES comics(id) ON DELETE CASCADE
                """))
                
                # Add basic indexes
                print("📊 Creating indexes...")
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_user_id ON comics(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_status ON comics(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comics_created_at ON comics(created_at DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_pages_comic_id ON comic_pages(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_likes_comic_id ON comic_likes(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comic_comments_comic_id ON comic_comments(comic_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_saved_comics_user_id ON saved_comics(user_id)"))
                
                trans.commit()
                
                print("✅ All comic tables created successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Error creating tables: {e}")
                trans.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Run the migration"""
    print("🎨 Comics Migration Script")
    print("=" * 30)
    
    success = create_comic_tables()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("✅ Comics system is ready to use")
        print("🚀 You can now create comics with your API!")
    else:
        print("\n💥 FAILED!")
        print("❌ Please check the errors above")

if __name__ == "__main__":
    main()