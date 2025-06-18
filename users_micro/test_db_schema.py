"""
Test script to verify the database migration was successful
"""

from db.database import engine
from sqlalchemy import text

def test_database_schema():
    """Test that the stories table has the correct schema"""
    try:
        with engine.connect() as conn:
            # Check stories table structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'stories' 
                ORDER BY ordinal_position
            """))
            
            print("Stories table structure:")
            print("-" * 50)
            for row in result:
                nullable = "YES" if row.is_nullable == "YES" else "NO"
                print(f"  {row.column_name:<15}: {row.data_type:<20} (nullable: {nullable})")
            
            # Specifically check for text column
            text_check = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'stories' AND column_name = 'text'
            """))
            
            if text_check.fetchone():
                print("\n✅ 'text' column exists")
            else:
                print("\n❌ 'text' column missing")
            
            print("\n✅ Database connection successful!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_database_schema()
