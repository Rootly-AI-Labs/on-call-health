import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/burnout_detector")

# Connect to the database
engine = create_engine(DATABASE_URL)

RESET_SQL = """
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"""

def wipe_database():
    print(f"Connecting to: {DATABASE_URL}")
    with engine.connect() as conn:
        print("Dropping schema...")
        conn.execute(text(RESET_SQL))
        conn.commit()
        print("Database wiped successfully.")

if __name__ == "__main__":
    wipe_database()
