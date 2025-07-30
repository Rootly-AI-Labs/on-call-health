#!/usr/bin/env python3
"""
Script to run consistency checks on all analyses and generate a comprehensive report.
This implements the data verification plan from CLAUDE.md.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.analysis import Analysis

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default."""
    return os.getenv(
        'DATABASE_URL', 
        'postgresql://user:password@localhost:5432/burnout_detector'
    )

def check_analysis_consistency(analysis):
    """Check data consistency for a single analysis (same logic as API endpoint)."""
    try:
        analysis_data = analysis.results if isinstance(analysis.results, dict) else json.loads(analysis.results)
        
        # Initialize report
        report = {
            "analysis_id": analysis.id,
            "overall_consistent": True,
            "checks": {},
            "issues": [],
            "summary": {}
        }
        
        # Extract data components
        metadata = analysis_data.get("metadata", {})
        team_analysis = analysis_data.get("team_analysis", {})
        daily_trends = analysis_data.get("daily_trends", [])
        team_health = analysis_data.get("team_health", {})
        
        # Get team members
        members = team_analysis.get("members", []) if isinstance(team_analysis, dict) else team_analysis
        if not isinstance(members, list):
            members = []
        
        # Check 1: Incident Totals
        metadata_total = metadata.get("total_incidents", 0)
        team_analysis_sum = sum(m.get("incident_count", 0) for m in members)
        daily_trends_sum = sum(d.get("incident_count", 0) for d in daily_trends)
        
        incident_check = {
            "metadata_total": metadata_total,
            "team_sum": team_analysis_sum,
            "daily_sum": daily_trends_sum,
            "consistent": metadata_total == team_analysis_sum == daily_trends_sum
        }
        
        if not incident_check["consistent"]:
            report["overall_consistent"] = False
            report["issues"].append(f"Incident totals don't match: metadata={metadata_total}, team={team_analysis_sum}, daily={daily_trends_sum}")
        
        report["checks"]["incidents"] = incident_check
        
        # Check 2: Date Range
        metadata_days = metadata.get("days_analyzed", analysis.time_range or 30)
        daily_trends_days = len(daily_trends)
        
        date_check = {
            "expected_days": metadata_days,
            "actual_days": daily_trends_days,
            "consistent": metadata_days == daily_trends_days
        }
        
        if not date_check["consistent"]:
            report["overall_consistent"] = False
            report["issues"].append(f"Date range mismatch: expected {metadata_days} days, got {daily_trends_days}")
        
        report["checks"]["date_range"] = date_check
        
        # Check 3: Member Count
        metadata_users = metadata.get("total_users", 0)
        actual_members = len(members)
        
        member_check = {
            "expected_members": metadata_users,
            "actual_members": actual_members,
            "consistent": metadata_users == actual_members
        }
        
        if not member_check["consistent"]:
            report["overall_consistent"] = False
            report["issues"].append(f"Member count mismatch: expected {metadata_users}, got {actual_members}")
        
        report["checks"]["members"] = member_check
        
        # Generate summary
        total_checks = len(report["checks"])
        passed_checks = sum(1 for check in report["checks"].values() if check.get("consistent", True))
        
        report["summary"] = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "consistency_percentage": round((passed_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
            "issues_count": len(report["issues"])
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Error checking consistency for analysis {analysis.id}: {str(e)}")
        return {
            "analysis_id": analysis.id,
            "overall_consistent": False,
            "error": str(e),
            "checks": {},
            "issues": [f"Consistency check failed: {str(e)}"],
            "summary": {"total_checks": 0, "passed_checks": 0, "consistency_percentage": 0, "issues_count": 1}
        }

def main():
    """Main function to audit all analyses."""
    logger.info("Starting comprehensive data consistency audit")
    
    # Create database connection
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Get all completed analyses
        analyses = session.query(Analysis).filter(Analysis.status == 'completed').all()
        logger.info(f"Found {len(analyses)} completed analyses to audit")
        
        if not analyses:
            logger.info("No completed analyses found")
            return
        
        # Run consistency checks
        audit_results = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "total_analyses": len(analyses),
            "analyses_checked": 0,
            "consistent_analyses": 0,
            "analyses_with_issues": 0,
            "overall_consistency_rate": 0,
            "common_issues": {},
            "detailed_results": []
        }
        
        for i, analysis in enumerate(analyses, 1):
            logger.info(f"Checking analysis {i}/{len(analyses)}: ID {analysis.id}")
            
            report = check_analysis_consistency(analysis)
            audit_results["detailed_results"].append(report)
            audit_results["analyses_checked"] += 1
            
            if report["overall_consistent"]:
                audit_results["consistent_analyses"] += 1
                logger.info(f"✅ Analysis {analysis.id}: Consistent ({report['summary']['consistency_percentage']}%)")
            else:
                audit_results["analyses_with_issues"] += 1
                logger.warning(f"❌ Analysis {analysis.id}: Issues found ({report['summary']['consistency_percentage']}%)")
                
                # Track common issues
                for issue in report["issues"]:
                    issue_type = issue.split(":")[0]  # Get issue category
                    audit_results["common_issues"][issue_type] = audit_results["common_issues"].get(issue_type, 0) + 1
        
        # Calculate overall statistics
        audit_results["overall_consistency_rate"] = round(
            (audit_results["consistent_analyses"] / audit_results["total_analyses"]) * 100, 1
        ) if audit_results["total_analyses"] > 0 else 0
        
        # Generate final report
        logger.info(f"\n{'='*60}")
        logger.info(f"COMPREHENSIVE DATA CONSISTENCY AUDIT REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Audit Timestamp: {audit_results['audit_timestamp']}")
        logger.info(f"Total Analyses: {audit_results['total_analyses']}")
        logger.info(f"Consistent Analyses: {audit_results['consistent_analyses']}")
        logger.info(f"Analyses with Issues: {audit_results['analyses_with_issues']}")
        logger.info(f"Overall Consistency Rate: {audit_results['overall_consistency_rate']}%")
        
        if audit_results["common_issues"]:
            logger.info(f"\nMost Common Issues:")
            for issue_type, count in sorted(audit_results["common_issues"].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {issue_type}: {count} analyses affected")
        
        # Save detailed report to file
        report_filename = f"consistency_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(audit_results, f, indent=2, default=str)
        
        logger.info(f"\nDetailed report saved to: {report_filename}")
        
        # Recommendations
        logger.info(f"\n{'='*60}")
        logger.info(f"RECOMMENDATIONS")
        logger.info(f"{'='*60}")
        
        if audit_results["overall_consistency_rate"] >= 95:
            logger.info("🎉 Excellent! Your data consistency is very high.")
        elif audit_results["overall_consistency_rate"] >= 80:
            logger.info("👍 Good data consistency, but some issues need attention.")
        elif audit_results["overall_consistency_rate"] >= 60:
            logger.info("⚠️  Moderate consistency issues detected. Review needed.")
        else:
            logger.info("🚨 Significant consistency issues detected. Immediate action required.")
        
        if "Incident totals don't match" in str(audit_results["common_issues"]):
            logger.info("- Consider regenerating trends data for analyses with incident mismatches")
            logger.info("- Run: python regenerate_all_trends.py")
        
        if "Date range mismatch" in str(audit_results["common_issues"]):
            logger.info("- Some analyses may be missing daily trend data")
            logger.info("- Check the daily trends generation logic")
        
        if "Member count mismatch" in str(audit_results["common_issues"]):
            logger.info("- Verify user data collection is working correctly")
            logger.info("- Check for API permission issues")
        
    except Exception as e:
        logger.error(f"Audit failed: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    main()