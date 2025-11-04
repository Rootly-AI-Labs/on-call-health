#!/usr/bin/env python3
"""Delete Motive analyses that are causing database timeouts"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))

from app.models import get_db, Analysis
from sqlalchemy import text

def delete_motive_analyses():
    """Delete all analyses for Motive organization"""
    db = next(get_db())
    try:
        # First, count them
        count_result = db.execute(text("""
            SELECT COUNT(*) FROM analyses
            WHERE integration_name = 'Motive'
        """)).fetchone()

        count = count_result[0] if count_result else 0
        print(f"Found {count} Motive analyses to delete")

        if count == 0:
            print("No Motive analyses found")
            return

        # Delete them
        result = db.execute(text("""
            DELETE FROM analyses
            WHERE integration_name = 'Motive'
            RETURNING id
        """))

        deleted_ids = [row[0] for row in result.fetchall()]
        db.commit()

        print(f"✅ Successfully deleted {len(deleted_ids)} Motive analyses")
        print(f"   Deleted IDs: {deleted_ids}")

    except Exception as e:
        print(f"❌ Error deleting Motive analyses: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    delete_motive_analyses()
