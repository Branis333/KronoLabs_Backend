"""
Working Database Reset Script

This script will completely empty your database using your existing database setup.
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def reset_database():
    """Reset database using existing database configuration"""
    try:
        print("💥 Starting database reset...")
        
        # Import your existing database setup
        from db.database import engine, DATABASE_URL
        from sqlalchemy import text, MetaData
        
        print(f"🔗 Connected to: {DATABASE_URL[:30]}...")
        
        # Method 1: Drop all tables using cascade
        print("🗑️  Dropping all tables...")
        
        with engine.connect() as conn:
            # For PostgreSQL - get all tables in public schema
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Found {len(tables)} tables to drop")
            
            if tables:
                # Drop all tables with CASCADE to handle foreign keys
                for table in tables:
                    print(f"  🗑️  Dropping {table}")
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                
                conn.commit()
                print(f"✅ Successfully dropped {len(tables)} tables")
            else:
                print("ℹ️  No tables found to drop")
        
        # Method 2: Recreate all tables from your models
        print("🏗️  Recreating database structure...")
        
        # Import all your model bases to register the tables
        from models.users_models import Base as UsersBase
        from models.social_models import Base as SocialBase
        from models.other_models import Base as OtherBase
        
        # Create all tables
        print("  📋 Creating users tables...")
        UsersBase.metadata.create_all(engine)
        
        print("  📋 Creating social media tables...")  
        SocialBase.metadata.create_all(engine)
        
        print("  📋 Creating other tables...")
        OtherBase.metadata.create_all(engine)
        
        # Verify what was created
        metadata = MetaData()
        metadata.reflect(bind=engine)
        new_tables = list(metadata.tables.keys())
        
        print(f"✅ Database reset complete!")
        print(f"📊 Created {len(new_tables)} tables:")
        for table in sorted(new_tables):
            print(f"  📋 {table}")
        
        print("🎉 Database is now completely empty and ready for use!")
        return True
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚨 DATABASE RESET TOOL 🚨")
    print("This will DELETE ALL DATA in your database!")
    print()
    
    # Simple confirmation
    response = input("Type 'RESET' to continue or anything else to cancel: ").strip()
    
    if response == 'RESET':
        print("\n🚀 Starting reset process...")
        success = reset_database()
        
        if success:
            print("\n✨ SUCCESS! Your database is now completely empty.")
        else:
            print("\n💥 FAILED! Something went wrong.")
    else:
        print("❌ Cancelled. Database unchanged.")

if __name__ == "__main__":
    main()
