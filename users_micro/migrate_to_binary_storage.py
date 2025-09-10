"""
Complete Database Migration: Convert all URL-based media storage to binary (BLOB) storage

This migration will:
1. Add binary data columns for all media
2. Add MIME type columns for all media
3. Remove URL-based columns
4. Update all tables: users, posts, post_media, stories, direct_messages

WARNING: This migration will remove all existing media data stored as URLs.
Make sure to backup your database before running this migration.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from db.database import DATABASE_URL
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_users_table():
    """Update users table to use binary storage for profile images"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("🔄 Migrating users table...")
            
            # Check if new columns exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('profile_image', 'profile_image_mime_type')
            """)
            result = connection.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            # Add new binary columns
            if 'profile_image' not in existing_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN profile_image BYTEA"))
                print("  ✅ Added profile_image (BYTEA) column")
            
            if 'profile_image_mime_type' not in existing_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN profile_image_mime_type VARCHAR(100)"))
                print("  ✅ Added profile_image_mime_type column")
            
            # Update avatar column to BYTEA if it's not already
            connection.execute(text("ALTER TABLE users ALTER COLUMN avatar TYPE BYTEA USING NULL"))
            print("  ✅ Updated avatar column to BYTEA")
            
            # Drop old URL column if it exists
            try:
                connection.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS profile_image_url"))
                print("  ✅ Removed profile_image_url column")
            except:
                pass
            
            connection.commit()
            print("✅ Users table migration completed")
            return True
            
    except Exception as e:
        print(f"❌ Error migrating users table: {str(e)}")
        return False

def migrate_posts_table():
    """Update posts table to use binary storage for media"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("🔄 Migrating posts table...")
            
            # Check if new columns exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'posts' 
                AND column_name IN ('media_data', 'media_mime_type')
            """)
            result = connection.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            # Add new binary columns
            if 'media_data' not in existing_columns:
                connection.execute(text("ALTER TABLE posts ADD COLUMN media_data BYTEA"))
                print("  ✅ Added media_data (BYTEA) column")
            
            if 'media_mime_type' not in existing_columns:
                connection.execute(text("ALTER TABLE posts ADD COLUMN media_mime_type VARCHAR(100)"))
                print("  ✅ Added media_mime_type column")
            
            # Drop old URL column
            try:
                connection.execute(text("ALTER TABLE posts DROP COLUMN IF EXISTS media_url"))
                print("  ✅ Removed media_url column")
            except:
                pass
            
            connection.commit()
            print("✅ Posts table migration completed")
            return True
            
    except Exception as e:
        print(f"❌ Error migrating posts table: {str(e)}")
        return False

def migrate_post_media_table():
    """Update post_media table to use binary storage"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("🔄 Migrating post_media table...")
            
            # Check if new columns exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'post_media' 
                AND column_name IN ('media_data', 'media_mime_type')
            """)
            result = connection.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            # Add new binary columns
            if 'media_data' not in existing_columns:
                connection.execute(text("ALTER TABLE post_media ADD COLUMN media_data BYTEA NOT NULL DEFAULT ''"))
                print("  ✅ Added media_data (BYTEA) column")
            
            if 'media_mime_type' not in existing_columns:
                connection.execute(text("ALTER TABLE post_media ADD COLUMN media_mime_type VARCHAR(100) NOT NULL DEFAULT 'image/jpeg'"))
                print("  ✅ Added media_mime_type column")
            
            # Drop old URL column
            try:
                connection.execute(text("ALTER TABLE post_media DROP COLUMN IF EXISTS media_url"))
                print("  ✅ Removed media_url column")
            except:
                pass
            
            connection.commit()
            print("✅ Post_media table migration completed")
            return True
            
    except Exception as e:
        print(f"❌ Error migrating post_media table: {str(e)}")
        return False

def migrate_stories_table():
    """Update stories table to use binary storage"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("🔄 Migrating stories table...")
            
            # Check if new columns exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'stories' 
                AND column_name IN ('media_data', 'media_mime_type')
            """)
            result = connection.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            # Add new binary columns
            if 'media_data' not in existing_columns:
                connection.execute(text("ALTER TABLE stories ADD COLUMN media_data BYTEA"))
                print("  ✅ Added media_data (BYTEA) column")
            
            if 'media_mime_type' not in existing_columns:
                connection.execute(text("ALTER TABLE stories ADD COLUMN media_mime_type VARCHAR(100)"))
                print("  ✅ Added media_mime_type column")
            
            # Drop old URL column
            try:
                connection.execute(text("ALTER TABLE stories DROP COLUMN IF EXISTS media_url"))
                print("  ✅ Removed media_url column")
            except:
                pass
            
            connection.commit()
            print("✅ Stories table migration completed")
            return True
            
    except Exception as e:
        print(f"❌ Error migrating stories table: {str(e)}")
        return False

def migrate_direct_messages_table():
    """Update direct_messages table to use binary storage"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            print("🔄 Migrating direct_messages table...")
            
            # Check if new columns exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'direct_messages' 
                AND column_name IN ('media_data', 'media_mime_type')
            """)
            result = connection.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            # Add new binary columns
            if 'media_data' not in existing_columns:
                connection.execute(text("ALTER TABLE direct_messages ADD COLUMN media_data BYTEA"))
                print("  ✅ Added media_data (BYTEA) column")
            
            if 'media_mime_type' not in existing_columns:
                connection.execute(text("ALTER TABLE direct_messages ADD COLUMN media_mime_type VARCHAR(100)"))
                print("  ✅ Added media_mime_type column")
            
            # Drop old URL column
            try:
                connection.execute(text("ALTER TABLE direct_messages DROP COLUMN IF EXISTS media_url"))
                print("  ✅ Removed media_url column")
            except:
                pass
            
            connection.commit()
            print("✅ Direct_messages table migration completed")
            return True
            
    except Exception as e:
        print(f"❌ Error migrating direct_messages table: {str(e)}")
        return False

def main():
    print("🚀 Starting complete migration to binary media storage...")
    print("=" * 80)
    
    success_count = 0
    total_migrations = 5
    
    # Run all migrations
    migrations = [
        ("Users", migrate_users_table),
        ("Posts", migrate_posts_table),
        ("Post Media", migrate_post_media_table),
        ("Stories", migrate_stories_table),
        ("Direct Messages", migrate_direct_messages_table),
    ]
    
    for name, migration_func in migrations:
        if migration_func():
            success_count += 1
        print()
    
    print("=" * 80)
    if success_count == total_migrations:
        print("🎉 ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
        print()
        print("✅ Your backend now stores all media as binary data in the database:")
        print("   • Profile images: users.profile_image (BYTEA)")
        print("   • Post media: posts.media_data (BYTEA)")
        print("   • Post media files: post_media.media_data (BYTEA)")
        print("   • Story media: stories.media_data (BYTEA)")
        print("   • Message media: direct_messages.media_data (BYTEA)")
        print()
        print("📝 All MIME types are stored in corresponding *_mime_type columns")
        print("🗑️  All old URL-based columns have been removed")
        print()
        print("⚠️  NOTE: You'll need to update your endpoints to handle base64 encoding/decoding")
    else:
        print(f"❌ Migration partially failed: {success_count}/{total_migrations} completed")
        print("Please check the errors above and try again.")

if __name__ == "__main__":
    main()
