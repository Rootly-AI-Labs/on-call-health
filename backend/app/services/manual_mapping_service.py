"""
Manual mapping service for managing user platform correlations.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

from ..models import UserMapping, get_db

logger = logging.getLogger(__name__)

class ManualMappingService:
    """Service for managing manual user mappings across platforms."""
    
    def __init__(self, db: Session = None):
        self.db = db or next(get_db())
    
    def create_mapping(
        self,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str,
        target_identifier: str,
        created_by: int,
        mapping_type: str = "manual"
    ) -> UserMapping:
        """Create a new manual mapping."""
        
        # Check if mapping already exists
        existing = self.get_mapping(
            user_id, source_platform, source_identifier, target_platform
        )
        
        if existing:
            # Update existing mapping
            existing.target_identifier = target_identifier
            existing.mapping_type = mapping_type
            existing.updated_at = datetime.now()
            existing.last_verified = datetime.now() if mapping_type == "manual" else None
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated existing mapping: {existing}")
            return existing
        
        # Create new mapping
        mapping = UserMapping.create_manual_mapping(
            user_id=user_id,
            source_platform=source_platform,
            source_identifier=source_identifier,
            target_platform=target_platform,
            target_identifier=target_identifier,
            created_by=created_by
        )
        
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        
        logger.info(f"Created new mapping: {mapping}")
        return mapping
    
    def get_mapping(
        self,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str
    ) -> Optional[UserMapping]:
        """Get a specific mapping."""
        return self.db.query(UserMapping).filter(
            and_(
                UserMapping.user_id == user_id,
                UserMapping.source_platform == source_platform,
                UserMapping.source_identifier == source_identifier,
                UserMapping.target_platform == target_platform
            )
        ).first()
    
    def get_user_mappings(self, user_id: int) -> List[UserMapping]:
        """Get all mappings for a user."""
        return self.db.query(UserMapping).filter(
            UserMapping.user_id == user_id
        ).order_by(
            UserMapping.source_platform,
            UserMapping.target_platform,
            UserMapping.source_identifier
        ).all()
    
    def get_platform_mappings(
        self, 
        user_id: int, 
        target_platform: str
    ) -> List[UserMapping]:
        """Get all mappings for a specific target platform."""
        return self.db.query(UserMapping).filter(
            and_(
                UserMapping.user_id == user_id,
                UserMapping.target_platform == target_platform
            )
        ).order_by(UserMapping.source_identifier).all()
    
    def delete_mapping(self, mapping_id: int, user_id: int) -> bool:
        """Delete a mapping (with ownership check)."""
        mapping = self.db.query(UserMapping).filter(
            and_(
                UserMapping.id == mapping_id,
                UserMapping.user_id == user_id
            )
        ).first()
        
        if mapping:
            self.db.delete(mapping)
            self.db.commit()
            logger.info(f"Deleted mapping: {mapping}")
            return True
        
        return False
    
    def lookup_target_identifier(
        self,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str
    ) -> Optional[str]:
        """Look up target identifier for a mapping."""
        mapping = self.get_mapping(user_id, source_platform, source_identifier, target_platform)
        return mapping.target_identifier if mapping else None
    
    def get_mapping_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get mapping statistics for a user."""
        mappings = self.get_user_mappings(user_id)
        
        total = len(mappings)
        manual_count = len([m for m in mappings if m.mapping_type == "manual"])
        auto_count = len([m for m in mappings if m.mapping_type == "auto_detected"])
        verified_count = len([m for m in mappings if m.is_verified])
        
        # Platform breakdown
        platform_stats = {}
        for mapping in mappings:
            key = f"{mapping.source_platform}_to_{mapping.target_platform}"
            if key not in platform_stats:
                platform_stats[key] = {"total": 0, "verified": 0, "manual": 0}
            
            platform_stats[key]["total"] += 1
            if mapping.is_verified:
                platform_stats[key]["verified"] += 1
            if mapping.mapping_type == "manual":
                platform_stats[key]["manual"] += 1
        
        return {
            "total_mappings": total,
            "manual_mappings": manual_count,
            "auto_detected_mappings": auto_count,
            "verified_mappings": verified_count,
            "verification_rate": verified_count / total if total > 0 else 0,
            "platform_breakdown": platform_stats,
            "last_updated": max([m.updated_at for m in mappings]) if mappings else None
        }
    
    def verify_mapping(self, mapping_id: int, user_id: int) -> bool:
        """Mark a mapping as verified."""
        mapping = self.db.query(UserMapping).filter(
            and_(
                UserMapping.id == mapping_id,
                UserMapping.user_id == user_id
            )
        ).first()
        
        if mapping:
            mapping.last_verified = datetime.now()
            mapping.updated_at = datetime.now()
            self.db.commit()
            logger.info(f"Verified mapping: {mapping}")
            return True
        
        return False
    
    def bulk_create_mappings(
        self,
        user_id: int,
        mappings_data: List[Dict[str, str]],
        created_by: int
    ) -> Tuple[List[UserMapping], List[str]]:
        """Bulk create mappings with error handling."""
        created_mappings = []
        errors = []
        
        for data in mappings_data:
            try:
                mapping = self.create_mapping(
                    user_id=user_id,
                    source_platform=data["source_platform"],
                    source_identifier=data["source_identifier"],
                    target_platform=data["target_platform"],
                    target_identifier=data["target_identifier"],
                    created_by=created_by,
                    mapping_type=data.get("mapping_type", "manual")
                )
                created_mappings.append(mapping)
            except Exception as e:
                error_msg = f"Failed to create mapping {data}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return created_mappings, errors
    
    def get_unmapped_identifiers(
        self,
        user_id: int,
        source_platform: str,
        source_identifiers: List[str],
        target_platform: str
    ) -> List[str]:
        """Get source identifiers that don't have mappings to target platform."""
        existing_mappings = self.db.query(UserMapping.source_identifier).filter(
            and_(
                UserMapping.user_id == user_id,
                UserMapping.source_platform == source_platform,
                UserMapping.target_platform == target_platform,
                UserMapping.source_identifier.in_(source_identifiers)
            )
        ).all()
        
        mapped_identifiers = {m[0] for m in existing_mappings}
        return [identifier for identifier in source_identifiers if identifier not in mapped_identifiers]
    
    def suggest_mappings(
        self,
        user_id: int,
        source_platform: str,
        source_identifier: str,
        target_platform: str
    ) -> List[Dict[str, Any]]:
        """Suggest potential mappings based on patterns."""
        suggestions = []
        
        # Look for similar patterns in existing mappings
        existing_mappings = self.db.query(UserMapping).filter(
            and_(
                UserMapping.user_id == user_id,
                UserMapping.source_platform == source_platform,
                UserMapping.target_platform == target_platform
            )
        ).all()
        
        if not existing_mappings:
            return suggestions
        
        # Extract patterns from existing mappings
        for mapping in existing_mappings:
            source = mapping.source_identifier
            target = mapping.target_identifier
            
            # Pattern 1: Email username extraction
            if "@" in source and "@" in source_identifier:
                source_username = source.split("@")[0]
                target_username = target
                new_source_username = source_identifier.split("@")[0]
                
                # Simple username matching
                if source_username.lower() in target_username.lower():
                    suggested_target = target_username.replace(source_username, new_source_username)
                    suggestions.append({
                        "target_identifier": suggested_target,
                        "confidence": 0.7,
                        "evidence": [f"Username pattern from {source} -> {target}"],
                        "method": "username_pattern"
                    })
            
            # Pattern 2: Domain/organization pattern
            if "." in target and target_platform == "github":
                # GitHub username might follow company patterns
                if source_identifier.split("@")[0] == source.split("@")[0]:
                    suggestions.append({
                        "target_identifier": target,
                        "confidence": 0.4,
                        "evidence": [f"Same username as {source}"],
                        "method": "username_reuse"
                    })
        
        # Remove duplicates and sort by confidence
        unique_suggestions = {}
        for suggestion in suggestions:
            key = suggestion["target_identifier"]
            if key not in unique_suggestions or suggestion["confidence"] > unique_suggestions[key]["confidence"]:
                unique_suggestions[key] = suggestion
        
        return sorted(unique_suggestions.values(), key=lambda x: x["confidence"], reverse=True)[:5]