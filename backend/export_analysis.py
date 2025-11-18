"""
One-time script to export analysis data from local PostgreSQL database to JSON.
This exports analysis ID 12 and all related data for use as demo/mock data.
"""
import json
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Local database connection
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/burnout_detector"

# Set DATABASE_URL in environment BEFORE importing models
# This prevents the config from throwing an error
os.environ["DATABASE_URL"] = DATABASE_URL

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.models.analysis import Analysis
from app.models.integration_mapping import IntegrationMapping

def datetime_serializer(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_analysis(analysis_id: int, output_file: str = "mock_analysis_data.json"):
    """
    Export analysis and related data to JSON file.

    Args:
        analysis_id: The ID of the analysis to export
        output_file: Name of the output JSON file
    """
    print(f"[*] Connecting to database: {DATABASE_URL}")

    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Fetch the analysis
        print(f"[*] Fetching analysis with ID: {analysis_id}")
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            print(f"[ERROR] Analysis with ID {analysis_id} not found")
            return False

        print(f"[OK] Found analysis: {analysis.uuid}")
        print(f"   Status: {analysis.status}")
        print(f"   User ID: {analysis.user_id}")
        print(f"   Created: {analysis.created_at}")

        # Fetch related integration mappings
        print(f"[*] Fetching related integration mappings...")
        mappings = db.query(IntegrationMapping).filter(
            IntegrationMapping.analysis_id == analysis_id
        ).all()

        print(f"   Found {len(mappings)} integration mappings")

        # Build the export data structure
        export_data = {
            "analysis": {
                "id": analysis.id,
                "uuid": analysis.uuid,
                "user_id": analysis.user_id,
                "rootly_integration_id": analysis.rootly_integration_id,
                "organization_id": analysis.organization_id,
                "integration_name": analysis.integration_name,
                "platform": analysis.platform,
                "time_range": analysis.time_range,
                "status": analysis.status,
                "config": analysis.config,
                "results": analysis.results,
                "error_message": analysis.error_message,
                "created_at": analysis.created_at,
                "completed_at": analysis.completed_at,
            },
            "integration_mappings": [
                {
                    "id": mapping.id,
                    "user_id": mapping.user_id,
                    "analysis_id": mapping.analysis_id,
                    "source_platform": mapping.source_platform,
                    "source_identifier": mapping.source_identifier,
                    "target_platform": mapping.target_platform,
                    "target_identifier": mapping.target_identifier,
                    "mapping_successful": mapping.mapping_successful,
                    "mapping_method": mapping.mapping_method,
                    "error_message": mapping.error_message,
                    "data_collected": mapping.data_collected,
                    "data_points_count": mapping.data_points_count,
                    "created_at": mapping.created_at,
                    "updated_at": mapping.updated_at,
                }
                for mapping in mappings
            ],
            "metadata": {
                "exported_at": datetime.now(),
                "source_database": DATABASE_URL.replace("1234", "****"),  # Hide password
                "original_analysis_id": analysis_id,
            }
        }

        # Write to JSON file
        output_path = Path(__file__).parent / output_file
        print(f"[*] Writing data to: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=datetime_serializer)

        print(f"[OK] Successfully exported analysis to {output_file}")
        print(f"[*] Export contains:")
        print(f"   - 1 analysis record")
        print(f"   - {len(mappings)} integration mapping records")

        # Print summary of analysis results
        if analysis.results:
            print(f"\n[*] Analysis Results Summary:")
            if isinstance(analysis.results, dict):
                if "team_scores" in analysis.results:
                    team_scores = analysis.results["team_scores"]
                    print(f"   Team Scores: {json.dumps(team_scores, indent=4)}")
                if "members" in analysis.results:
                    print(f"   Number of members: {len(analysis.results['members'])}")

        return True

    except Exception as e:
        print(f"[ERROR] Error during export: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()
        print("[*] Database connection closed")

if __name__ == "__main__":
    # Export analysis ID 12 - could be different depending on local data data base - used table plus to view analysis and ids
    success = export_analysis(
        analysis_id=12,
        output_file="mock_analysis_data.json"
    )

    if success:
        print("\n[OK] Export completed successfully!")
        print("You can now use this JSON file to create demo analyses for new users.")
    else:
        print("\n[ERROR] Export failed!")
        sys.exit(1)
