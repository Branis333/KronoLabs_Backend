"""
Database Migration: Add shared content support to direct_messages table

This script adds the missing columns to support:
- Sharing posts in messages (shared_post_id)
- Sharing stories in messages (shared_story_id)

Run this script once to update your database schema.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from db.database import DATABASE_URL
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_add_shared_content_to_messages():
    """Add shared_post_id and shared_story_id columns to direct_messages table"""
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Connect to database
        with engine.connect() as connection:
            # Check if columns already exist
            check_columns_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'direct_messages' 
                AND column_name IN ('shared_post_id', 'shared_story_id')
            """)
            
            result = connection.execute(check_columns_query)
            existing_columns = [row.column_name for row in result.fetchall()]
            
            changes_made = []
            
            # Add shared_post_id column if it doesn't exist
            if 'shared_post_id' not in existing_columns:
                alter_post_query = text("""
                    ALTER TABLE direct_messages 
                    ADD COLUMN shared_post_id UUID REFERENCES posts(id)
                """)
                connection.execute(alter_post_query)
                changes_made.append("shared_post_id")
                print("✅ Added 'shared_post_id' column to direct_messages table")
            else:
                print("✅ Column 'shared_post_id' already exists")
            
            # Add shared_story_id column if it doesn't exist
            if 'shared_story_id' not in existing_columns:
                alter_story_query = text("""
                    ALTER TABLE direct_messages 
                    ADD COLUMN shared_story_id UUID REFERENCES stories(id)
                """)
                connection.execute(alter_story_query)
                changes_made.append("shared_story_id")
                print("✅ Added 'shared_story_id' column to direct_messages table")
            else:
                print("✅ Column 'shared_story_id' already exists")
            
            if changes_made:
                connection.commit()
                print(f"✅ Successfully added columns: {', '.join(changes_made)}")
            else:
                print("✅ All columns already exist, no changes needed")
            
            # Verify the columns were added
            verify_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'direct_messages' 
                AND column_name IN ('shared_post_id', 'shared_story_id')
                ORDER BY column_name
            """)
            
            result = connection.execute(verify_query)
            columns = result.fetchall()
            
            if len(columns) == 2:
                print("\n✅ Verification successful:")
                for column in columns:
                    print(f"  {column.column_name}: {column.data_type} (nullable: {column.is_nullable})")
                return True
            else:
                print("❌ Column verification failed")
                return False
                
    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration for direct_messages table...")
    print("=" * 70)
    
    success = migrate_add_shared_content_to_messages()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 Migration completed successfully!")
        print("Your direct messages now support:")
        print("  - Text messages")
        print("  - Image/video uploads")
        print("  - Sharing posts from the platform")
        print("  - Sharing stories from the platform")
        print("  - Mixed messages (combinations of the above)")
    else:
        print("❌ Migration failed. Please check the errors above.")
