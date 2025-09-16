#!/usr/bin/env python3
"""
Quick fix for Video table column mismatch
Adds missing columns to existing videos table
"""

from sqlalchemy import text
from db.connection import get_db

def fix_video_columns():
    """Add missing columns to videos table"""
    db = next(get_db())
    
    print("🔧 Fixing Video table columns...")
    
    try:
        # Add missing columns if they don't exist
        columns_to_add = [
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_small_data BYTEA;",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_medium_data BYTEA;",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_large_data BYTEA;",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_mime_type VARCHAR(50) DEFAULT 'image/jpeg';",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS fps INTEGER;",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0;",
            "ALTER TABLE videos ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50) DEFAULT 'processing';"
        ]
        
        for sql in columns_to_add:
            print(f"Adding column: {sql}")
            db.execute(text(sql))
        
        # Drop old columns if they exist (from migration script)
        old_columns = [
            "ALTER TABLE videos DROP COLUMN IF EXISTS thumbnail_small;",
            "ALTER TABLE videos DROP COLUMN IF EXISTS thumbnail_medium;", 
            "ALTER TABLE videos DROP COLUMN IF EXISTS thumbnail_large;",
            "ALTER TABLE videos DROP COLUMN IF EXISTS views;",
            "ALTER TABLE videos DROP COLUMN IF EXISTS likes;",
            "ALTER TABLE videos DROP COLUMN IF EXISTS dislikes;"
        ]
        
        for sql in old_columns:
            print(f"Removing old column: {sql}")
            try:
                db.execute(text(sql))
            except:
                pass  # Column might not exist
        
        db.commit()
        print("✅ Video table columns fixed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to fix columns: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    fix_video_columns()