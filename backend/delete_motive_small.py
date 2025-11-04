#!/usr/bin/env python3
"""Delete Motive analyses one at a time to avoid timeout"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))

from app.models import get_db
from sqlalchemy import text

def delete_motive_analyses_careful():
    """Delete Motive analyses one at a time"""
    db = next(get_db())
    try:
        # Get just the IDs, without loading the massive results field
        print("Fetching Motive analysis IDs (without loading data)...")
        result = db.execute(text("""
            SELECT id FROM analyses
            WHERE integration_name = 'Motive'
        """))

        ids = [row[0] for row in result.fetchall()]
        print(f"Found {len(ids)} Motive analyses to delete: {ids}")

        if len(ids) == 0:
            print("No Motive analyses found")
            return

        # Delete one at a time to avoid loading massive payloads
        deleted_count = 0
        for analysis_id in ids:
            try:
                db.execute(text("""
                    DELETE FROM analyses WHERE id = :id
                """), {"id": analysis_id})
                db.commit()
                deleted_count += 1
                print(f"  ✅ Deleted analysis {analysis_id}")
            except Exception as e:
                print(f"  ❌ Failed to delete analysis {analysis_id}: {e}")
                db.rollback()
                continue

        print(f"\n✅ Successfully deleted {deleted_count}/{len(ids)} Motive analyses")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    delete_motive_analyses_careful()
