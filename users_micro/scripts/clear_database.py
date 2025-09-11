"""
Database Clear Script - DANGER ZONE!

This script will completely empty your database by:
1. Dropping all tables
2. Recreating all tables from scratch
3. Ensuring a completely clean database state

WARNING: This will permanently delete ALL data in your database!
Use with extreme caution!
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text, create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from db.connection import get_db_url
from models.users_models import Base as UsersBase
from models.social_models import Base as SocialBase
from models.other_models import Base as OtherBase

def confirm_deletion():
    """Ask for user confirmation before proceeding"""
    print("🚨 WARNING: This will PERMANENTLY DELETE ALL DATA in your database! 🚨")
    print("This action cannot be undone!")
    print()
    
    confirmation = input("Type 'DELETE EVERYTHING' to confirm (case sensitive): ")
    
    if confirmation != "DELETE EVERYTHING":
        print("❌ Operation cancelled. Database remains unchanged.")
        return False
    
    print("⚠️  Last chance! Are you absolutely sure?")
    final_confirm = input("Type 'YES I AM SURE' to proceed: ")
    
    if final_confirm != "YES I AM SURE":
        print("❌ Operation cancelled. Database remains unchanged.")
        return False
    
    return True

def clear_database():
    """Completely clear the database"""
    try:
        # Get database URL
        database_url = get_db_url()
        print(f"🔗 Connecting to database...")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        print("\n🗑️  Starting database cleanup...")
        
        # Method 1: Drop all tables using metadata reflection
        print("📋 Reflecting existing database schema...")
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        print(f"📊 Found {len(metadata.tables)} tables to drop")
        
        if metadata.tables:
            print("🔥 Dropping all existing tables...")
            metadata.drop_all(bind=engine)
            print("✅ All tables dropped successfully")
        else:
            print("ℹ️  No existing tables found")
        
        # Method 2: Recreate all tables from models
        print("\n🏗️  Recreating database schema from models...")
        
        # Create all tables from all bases
        UsersBase.metadata.create_all(bind=engine)
        SocialBase.metadata.create_all(bind=engine)
        OtherBase.metadata.create_all(bind=engine)
        
        print("✅ Database schema recreated successfully")
        
        # Verify the new schema
        print("\n🔍 Verifying new database schema...")
        new_metadata = MetaData()
        new_metadata.reflect(bind=engine)
        
        print(f"📊 Database now has {len(new_metadata.tables)} tables:")
        for table_name in sorted(new_metadata.tables.keys()):
            print(f"  📋 {table_name}")
        
        print("\n🎉 Database successfully cleared and recreated!")
        print("💾 All tables are now empty and ready for fresh data")
        
    except Exception as e:
        print(f"❌ Error during database cleanup: {str(e)}")
        print("💡 Make sure your database is running and accessible")
        return False
    
    return True

def alternative_clear_method():
    """Alternative method using individual table truncation"""
    try:
        database_url = get_db_url()
        engine = create_engine(database_url)
        
        print("\n🔄 Using alternative cleanup method...")
        print("📋 This will TRUNCATE all tables (delete all data but keep structure)")
        
        # Get all table names
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        with engine.connect() as conn:
            # Disable foreign key constraints temporarily
            if 'postgresql' in database_url:
                print("🔓 Temporarily disabling foreign key constraints...")
                for table_name in metadata.tables.keys():
                    conn.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
                conn.commit()
                print("✅ All tables truncated successfully")
            else:
                # For other databases
                for table_name in metadata.tables.keys():
                    conn.execute(text(f'DELETE FROM "{table_name}"'))
                conn.commit()
                print("✅ All table data deleted successfully")
        
        print("🎉 Alternative cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Alternative cleanup failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("🧹 Database Cleanup Script")
    print("=" * 50)
    
    if not confirm_deletion():
        return
    
    print("\n🚀 Starting database cleanup process...")
    
    # Try primary method first
    success = clear_database()
    
    if not success:
        print("\n🔄 Primary method failed. Trying alternative method...")
        success = alternative_clear_method()
    
    if success:
        print("\n✨ SUCCESS: Database is now completely empty!")
        print("🔄 You can now run your migrations or start fresh")
    else:
        print("\n💥 FAILED: Could not clear the database")
        print("🛠️  Please check your database connection and try again")

if __name__ == "__main__":
    main()
