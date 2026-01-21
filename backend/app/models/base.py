"""
Database configuration and base models.
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "For local development, use PostgreSQL (e.g., postgresql://user:password@localhost/dbname)"
    )

# Query timeout settings (in milliseconds)
STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "60000"))  # 60 seconds default
LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "30000"))  # 30 seconds default

# Create PostgreSQL engine with increased pool limits and query timeouts
engine = create_engine(
    DATABASE_URL,
    pool_size=30,           # Increased from 20 to 30 base connections
    max_overflow=20,        # Allow 20 overflow connections (total 50 max)
    pool_pre_ping=True,     # Test connections before use
    pool_recycle=300,       # Recycle connections every 5 minutes
    pool_timeout=60,        # Wait up to 60 seconds for connection
    echo_pool=False,        # Set to True for debugging pool issues
    connect_args={
        "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c lock_timeout={LOCK_TIMEOUT_MS}"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

# Dependency to get DB session with better error handling
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit successful transactions
    except Exception as e:
        db.rollback()  # Rollback on errors
        raise e
    finally:
        db.close()  # Always close the session

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)