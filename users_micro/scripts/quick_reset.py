"""
Quick Database Reset Script

This script provides a simple way to completely reset your database.
Run this when you want to start fresh with an empty database.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from db.connection import get_db_url

def reset_database():
    """Reset database by dropping and recreating all tables"""
    
    print("🔄 Resetting database...")
    
    try:
        # Get database connection
        database_url = get_db_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # For PostgreSQL - drop all tables in public schema
            print("🗑️  Dropping all tables...")
            
            # Get all table names
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            
            tables = [row[0] for row in result]
            
            if tables:
                # Drop all tables with CASCADE
                for table in tables:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                
                conn.commit()
                print(f"✅ Dropped {len(tables)} tables")
            else:
                print("ℹ️  No tables found to drop")
            
        # Now recreate tables
        print("🏗️  Recreating tables...")
        
        # Import all models to register them
        from models.users_models import Base as UsersBase
        from models.social_models import Base as SocialBase  
        from models.other_models import Base as OtherBase
        
        # Create all tables
        UsersBase.metadata.create_all(engine)
        SocialBase.metadata.create_all(engine)
        OtherBase.metadata.create_all(engine)
        
        print("✅ Database reset complete!")
        print("💾 All tables recreated and ready for fresh data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL data in your database!")
    confirm = input("Continue? (yes/no): ").lower().strip()
    
    if confirm == 'yes':
        reset_database()
    else:
        print("❌ Cancelled")
