"""
Simple Database Nuke Script - Guaranteed to Work

This uses your existing database connection and just drops everything.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import your database
from db.database import engine
from sqlalchemy import text

print("💥 NUKING DATABASE...")

try:
    with engine.connect() as conn:
        print("🔗 Connected to database")
        
        # Get all table names
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        
        tables = [row[0] for row in result.fetchall()]
        print(f"📋 Found {len(tables)} tables")
        
        if tables:
            # Drop everything with CASCADE
            for table in tables:
                print(f"💥 Dropping {table}")
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            
            conn.commit()
            print(f"✅ Dropped {len(tables)} tables")
        
        print("🎉 DATABASE NUKED SUCCESSFULLY!")
        print("🔄 Run your app to recreate tables")
        
except Exception as e:
    print(f"❌ Error: {e}")
