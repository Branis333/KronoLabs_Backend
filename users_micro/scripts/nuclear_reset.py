"""
Nuclear Database Reset - One Command Solution

This script will:
1. Connect to your database
2. Drop EVERYTHING 
3. Recreate all tables fresh

No questions asked - just run it!
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def nuclear_reset():
    """Nuclear option - wipe everything and start fresh"""
    try:
        print("💥 NUCLEAR DATABASE RESET INITIATED...")
        
        # Import database connection
        from db.connection import get_db_url
        from sqlalchemy import create_engine, text
        
        # Get database URL and create engine
        database_url = get_db_url()
        engine = create_engine(database_url)
        
        print("🔗 Connected to database")
        
        # Drop everything in the public schema
        with engine.connect() as conn:
            print("🗑️  Nuking all tables...")
            
            # This will drop ALL tables, views, sequences, etc.
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            
            conn.commit()
            print("💥 Schema nuked and recreated")
        
        # Recreate all tables from models  
        print("🏗️  Rebuilding database structure...")
        
        # Import all model bases
        from models.users_models import Base as UsersBase
        from models.social_models import Base as SocialBase
        from models.other_models import Base as OtherBase
        
        # Create all tables
        UsersBase.metadata.create_all(engine)
        SocialBase.metadata.create_all(engine) 
        OtherBase.metadata.create_all(engine)
        
        print("✅ Database structure rebuilt")
        print("🎉 NUCLEAR RESET COMPLETE!")
        print("💾 Database is now completely empty and ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Nuclear reset failed: {e}")
        print("🛠️  Check your database connection and try again")
        return False

if __name__ == "__main__":
    print("🚨 NUCLEAR DATABASE RESET 🚨")
    print("This will PERMANENTLY DELETE EVERYTHING!")
    print()
    nuclear_reset()
