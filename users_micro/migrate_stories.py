"""
Database Migration: Add text column to stories table

This script adds the missing 'text' column to the existing 'stories' table
to support text-only stories and mixed text+media stories.

Run this script once to update your database schema.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from db.database import DATABASE_URL
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_add_text_to_stories():
    """Add text column to stories table if it doesn't exist"""
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Connect to database
        with engine.connect() as connection:
            # Check if text column already exists
            check_column_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'stories' AND column_name = 'text'
            """)
            
            result = connection.execute(check_column_query)
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("✅ Column 'text' already exists in stories table")
                return True
            
            # Add the text column
            alter_query = text("""
                ALTER TABLE stories 
                ADD COLUMN text TEXT
            """)
            
            connection.execute(alter_query)
            connection.commit()
            
            print("✅ Successfully added 'text' column to stories table")
            
            # Verify the column was added
            verify_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'stories' AND column_name = 'text'
            """)
            
            result = connection.execute(verify_query)
            column_info = result.fetchone()
            
            if column_info:
                print(f"✅ Column verified: {column_info.column_name} ({column_info.data_type}, nullable: {column_info.is_nullable})")
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

def migrate_make_media_nullable():
    """Make media_url and media_type nullable to support text-only stories"""
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Check current nullable status
            check_query = text("""
                SELECT column_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'stories' 
                AND column_name IN ('media_url', 'media_type')
                ORDER BY column_name
            """)
            
            result = connection.execute(check_query)
            columns = result.fetchall()
            
            changes_needed = []
            for column in columns:
                if column.is_nullable == 'NO':
                    changes_needed.append(column.column_name)
            
            if not changes_needed:
                print("✅ media_url and media_type are already nullable")
                return True
            
            # Make media_url nullable
            if 'media_url' in changes_needed:
                alter_media_url_query = text("""
                    ALTER TABLE stories 
                    ALTER COLUMN media_url DROP NOT NULL
                """)
                connection.execute(alter_media_url_query)
                print("✅ Made media_url nullable")
            
            # Make media_type nullable  
            if 'media_type' in changes_needed:
                alter_media_type_query = text("""
                    ALTER TABLE stories 
                    ALTER COLUMN media_type DROP NOT NULL
                """)
                connection.execute(alter_media_type_query)
                print("✅ Made media_type nullable")
            
            connection.commit()
            print("✅ Successfully updated column constraints")
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration for stories table...")
    print("=" * 60)
    
    # Step 1: Add text column
    print("Step 1: Adding 'text' column...")
    success1 = migrate_add_text_to_stories()
    
    # Step 2: Make media fields nullable
    print("\nStep 2: Making media fields nullable...")
    success2 = migrate_make_media_nullable()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 Migration completed successfully!")
        print("Your stories table now supports:")
        print("  - Text-only stories")
        print("  - Media-only stories") 
        print("  - Text + media stories")
    else:
        print("❌ Migration failed. Please check the errors above.")
