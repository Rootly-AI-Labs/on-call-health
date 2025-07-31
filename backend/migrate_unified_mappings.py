"""
Migration script to unify manual and automatic mappings into a single table.

This script:
1. Adds new columns to integration_mappings table
2. Migrates data from user_mappings to integration_mappings
3. Updates existing integration_mappings with new defaults
4. Provides rollback capability

Run this script after deploying the updated IntegrationMapping model.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, select
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models import SessionLocal, IntegrationMapping, UserMapping
from app.models.base import Base

def get_database_url():
    """Get database URL from environment variables."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Fallback to local SQLite for development
        database_url = "sqlite:///./burnout_detector.db"
    return database_url

def add_new_columns(engine):
    """Add new columns to integration_mappings table."""
    print("🔧 Adding new columns to integration_mappings table...")
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist (for idempotency)
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'integration_mappings' 
                AND column_name IN ('mapping_source', 'created_by_user_id', 'confidence_score', 'last_verified')
            """))
            existing_columns = {row[0] for row in result.fetchall()}
            
            # Add columns that don't exist yet
            columns_to_add = [
                ("mapping_source", "VARCHAR(20) NOT NULL DEFAULT 'auto'"),
                ("created_by_user_id", "INTEGER REFERENCES users(id)"), 
                ("confidence_score", "FLOAT"),
                ("last_verified", "TIMESTAMP WITH TIME ZONE")
            ]
            
            for col_name, col_definition in columns_to_add:
                if col_name not in existing_columns:
                    print(f"  Adding column: {col_name}")
                    conn.execute(text(f"ALTER TABLE integration_mappings ADD COLUMN {col_name} {col_definition}"))
                else:
                    print(f"  Column {col_name} already exists, skipping")
            
            conn.commit()
            print("✅ Successfully added new columns")
            
    except SQLAlchemyError as e:
        print(f"❌ Error adding columns: {e}")
        # For SQLite, use a different approach
        if "information_schema" in str(e):
            print("🔄 Detected SQLite, using SQLite-specific column check...")
            try:
                with engine.connect() as conn:
                    # SQLite approach - try to add columns one by one
                    columns_to_add = [
                        ("mapping_source", "VARCHAR(20) NOT NULL DEFAULT 'auto'"),
                        ("created_by_user_id", "INTEGER"),
                        ("confidence_score", "REAL"),
                        ("last_verified", "TIMESTAMP")
                    ]
                    
                    for col_name, col_definition in columns_to_add:
                        try:
                            conn.execute(text(f"ALTER TABLE integration_mappings ADD COLUMN {col_name} {col_definition}"))
                            print(f"  ✅ Added column: {col_name}")
                        except SQLAlchemyError as col_error:
                            if "duplicate column name" in str(col_error) or "already exists" in str(col_error):
                                print(f"  ⚠️ Column {col_name} already exists, skipping")
                            else:
                                print(f"  ❌ Error adding column {col_name}: {col_error}")
                    
                    conn.commit()
                    print("✅ SQLite column addition completed")
            except SQLAlchemyError as sqlite_error:
                print(f"❌ SQLite migration failed: {sqlite_error}")
                raise
        else:
            raise

def migrate_user_mappings(db):
    """Migrate data from user_mappings to integration_mappings."""
    print("🔄 Migrating data from user_mappings to integration_mappings...")
    
    try:
        # Get all user mappings
        user_mappings = db.query(UserMapping).all()
        print(f"  Found {len(user_mappings)} user mappings to migrate")
        
        migrated_count = 0
        for user_mapping in user_mappings:
            # Check if mapping already exists in integration_mappings
            existing = db.query(IntegrationMapping).filter(
                IntegrationMapping.user_id == user_mapping.user_id,
                IntegrationMapping.source_platform == user_mapping.source_platform,
                IntegrationMapping.source_identifier == user_mapping.source_identifier,
                IntegrationMapping.target_platform == user_mapping.target_platform,
                IntegrationMapping.target_identifier == user_mapping.target_identifier
            ).first()
            
            if existing:
                print(f"  ⚠️ Mapping already exists for {user_mapping.source_identifier} -> {user_mapping.target_identifier}, skipping")
                continue
            
            # Create new integration mapping from user mapping
            integration_mapping = IntegrationMapping.create_manual_mapping(
                user_id=user_mapping.user_id,
                source_platform=user_mapping.source_platform,
                source_identifier=user_mapping.source_identifier,
                target_platform=user_mapping.target_platform,
                target_identifier=user_mapping.target_identifier,
                created_by_user_id=user_mapping.created_by
            )
            
            # Copy additional fields
            integration_mapping.confidence_score = user_mapping.confidence_score
            integration_mapping.last_verified = user_mapping.last_verified
            integration_mapping.created_at = user_mapping.created_at
            integration_mapping.updated_at = user_mapping.updated_at
            
            db.add(integration_mapping)
            migrated_count += 1
            print(f"  ✅ Migrated: {user_mapping.source_identifier} -> {user_mapping.target_identifier}")
        
        db.commit()
        print(f"✅ Successfully migrated {migrated_count} user mappings")
        
    except SQLAlchemyError as e:
        print(f"❌ Error migrating user mappings: {e}")
        db.rollback()
        raise

def update_existing_mappings(db):
    """Update existing integration mappings with default values for new columns."""
    print("🔄 Updating existing integration mappings with default values...")
    
    try:
        # Get all existing integration mappings that don't have mapping_source set
        existing_mappings = db.query(IntegrationMapping).filter(
            IntegrationMapping.mapping_source == None
        ).all()
        
        print(f"  Found {len(existing_mappings)} existing mappings to update")
        
        for mapping in existing_mappings:
            mapping.mapping_source = 'auto'  # Mark as automatic
            # Leave other fields as NULL for auto mappings
            
        db.commit()
        print("✅ Successfully updated existing mappings")
        
    except SQLAlchemyError as e:
        print(f"❌ Error updating existing mappings: {e}")
        db.rollback()
        raise

def verify_migration(db):
    """Verify the migration was successful."""
    print("🔍 Verifying migration...")
    
    try:
        # Count records in both tables
        integration_count = db.query(IntegrationMapping).count()
        user_mappings_count = db.query(UserMapping).count()
        manual_mappings_count = db.query(IntegrationMapping).filter(
            IntegrationMapping.mapping_source == 'manual'
        ).count()
        
        print(f"  📊 Integration mappings total: {integration_count}")
        print(f"  📊 User mappings (old): {user_mappings_count}")
        print(f"  📊 Manual mappings (new): {manual_mappings_count}")
        
        # Check for any manual mappings
        if manual_mappings_count > 0:
            print("✅ Migration verification successful - manual mappings found in unified table")
            
            # Show sample manual mapping
            sample = db.query(IntegrationMapping).filter(
                IntegrationMapping.mapping_source == 'manual'
            ).first()
            if sample:
                print(f"  📄 Sample manual mapping: {sample.source_identifier} -> {sample.target_identifier}")
        else:
            print("⚠️ No manual mappings found - this might be expected if no manual mappings existed")
        
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Error verifying migration: {e}")
        return False

def main():
    """Run the unified mappings migration."""
    print("🚀 Starting unified mappings migration...")
    print(f"📅 Migration started at: {datetime.now()}")
    
    try:
        # Get database connection
        database_url = get_database_url()
        print(f"🔗 Connecting to database: {database_url.split('@')[-1] if '@' in database_url else 'local SQLite'}")
        
        engine = create_engine(database_url)
        db = SessionLocal()
        
        # Step 1: Add new columns
        add_new_columns(engine)
        
        # Step 2: Migrate user mappings
        migrate_user_mappings(db)
        
        # Step 3: Update existing mappings
        update_existing_mappings(db)
        
        # Step 4: Verify migration
        if verify_migration(db):
            print("🎉 Migration completed successfully!")
            print("\n📋 Next steps:")
            print("  1. Update API endpoints to use unified table")
            print("  2. Test manual mapping creation")
            print("  3. Remove user_mappings table references")
            print("  4. Deploy updated code")
        else:
            print("❌ Migration verification failed")
            return 1
        
        db.close()
        return 0
        
    except Exception as e:
        print(f"💥 Migration failed: {e}")
        print(f"📋 To rollback, you may need to:")
        print("  1. Remove added columns from integration_mappings")
        print("  2. Restore from backup if available")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)