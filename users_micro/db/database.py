from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Option 1: Use full DATABASE_URL (recommended for your current setup)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL environment variable is not set!")
    logger.warning("⚠️ Please set DATABASE_URL in your environment variables")
    # Provide a fallback or exit gracefully
    raise ValueError("DATABASE_URL environment variable is required")

logger.info(f"🔗 Connecting to database: {DATABASE_URL[:30]}...")

# Option 2: Build from components (if you prefer Supabase's approach)
# USER = os.getenv("DB_USER", "postgres")
# PASSWORD = os.getenv("DB_PASSWORD")
# HOST = os.getenv("DB_HOST")
# PORT = os.getenv("DB_PORT", "5432")
# DBNAME = os.getenv("DB_NAME", "postgres")
# DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"

try:
    # Create engine with Supabase-optimized settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", 3600)),
        echo=False,  # Set to True for debugging
        # Add SSL settings for Supabase
        connect_args={
            "sslmode": "require",
            "options": "-c timezone=utc"
        }
    )
    logger.info("✅ Database engine created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Test connection function (optional)
def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT NOW();")
            print("Connection successful! Current time:", result.fetchone()[0])
            return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False