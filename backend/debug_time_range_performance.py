#!/usr/bin/env python3
"""
Debug script to analyze performance differences between 7-day and 30-day analyses.

This script helps identify:
1. Data volume differences
2. API call patterns and pagination
3. Rate limiting issues
4. Timeout risks
5. Performance bottlenecks
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.rootly_client import RootlyAPIClient
from app.services.burnout_analyzer import BurnoutAnalyzerService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_data_volume_differences():
    """Test the differences in data volume between 7-day and 30-day analyses."""
    
    # You'll need to set your Rootly API token here
    # In production, this would come from environment variables
    api_token = os.getenv("ROOTLY_API_TOKEN")
    if not api_token:
        logger.error("Please set ROOTLY_API_TOKEN environment variable")
        return
    
    client = RootlyAPIClient(api_token)
    
    # Test both time ranges
    time_ranges = [7, 30]
    results = {}
    
    for days in time_ranges:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 TESTING {days}-DAY ANALYSIS")
        logger.info(f"{'='*60}")
        
        try:
            start_time = datetime.now()
            
            # Test user collection (should be same for both)
            logger.info(f"📊 Testing user collection for {days}-day analysis...")
            users_start = datetime.now()
            users = await client.get_users(limit=1000)
            users_duration = (datetime.now() - users_start).total_seconds()
            
            # Test incident collection (will vary by time range)
            logger.info(f"📊 Testing incident collection for {days}-day analysis...")
            incidents_start = datetime.now()
            incidents = await client.get_incidents(days_back=days, limit=10000)
            incidents_duration = (datetime.now() - incidents_start).total_seconds()
            
            # Full data collection test
            collection_start = datetime.now()
            data = await client.collect_analysis_data(days_back=days)
            collection_duration = (datetime.now() - collection_start).total_seconds()
            
            total_duration = (datetime.now() - start_time).total_seconds()
            
            # Store results
            results[days] = {
                "users_count": len(users),
                "users_duration": users_duration,
                "incidents_count": len(incidents),
                "incidents_duration": incidents_duration,
                "collection_duration": collection_duration,
                "total_duration": total_duration,
                "incidents_per_second": len(incidents) / incidents_duration if incidents_duration > 0 else 0,
                "incidents_per_day": len(incidents) / days if days > 0 else 0,
                "performance_metrics": data.get("collection_metadata", {}).get("performance_metrics", {})
            }
            
            logger.info(f"✅ {days}-day analysis completed successfully")
            logger.info(f"   Users: {len(users)}")
            logger.info(f"   Incidents: {len(incidents)}")
            logger.info(f"   Total time: {total_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ {days}-day analysis failed: {e}")
            results[days] = {"error": str(e)}
    
    # Compare results
    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 PERFORMANCE COMPARISON")
    logger.info(f"{'='*60}")
    
    if 7 in results and 30 in results and "error" not in results[7] and "error" not in results[30]:
        day7 = results[7]
        day30 = results[30]
        
        logger.info(f"📊 DATA VOLUME COMPARISON:")
        logger.info(f"   7-day:  {day7['incidents_count']} incidents")
        logger.info(f"   30-day: {day30['incidents_count']} incidents")
        logger.info(f"   Ratio:  {day30['incidents_count'] / day7['incidents_count']:.1f}x more incidents for 30-day")
        
        logger.info(f"📊 PERFORMANCE COMPARISON:")
        logger.info(f"   7-day total time:  {day7['total_duration']:.2f}s")
        logger.info(f"   30-day total time: {day30['total_duration']:.2f}s")
        logger.info(f"   Time ratio: {day30['total_duration'] / day7['total_duration']:.1f}x slower for 30-day")
        
        logger.info(f"📊 INCIDENT FETCH PERFORMANCE:")
        logger.info(f"   7-day incidents/sec:  {day7['incidents_per_second']:.1f}")
        logger.info(f"   30-day incidents/sec: {day30['incidents_per_second']:.1f}")
        
        logger.info(f"📊 INCIDENT DENSITY:")
        logger.info(f"   7-day incidents/day:  {day7['incidents_per_day']:.1f}")
        logger.info(f"   30-day incidents/day: {day30['incidents_per_day']:.1f}")
        
        # Check for potential timeout risk
        timeout_threshold = 900  # 15 minutes
        if day30['total_duration'] > timeout_threshold * 0.8:  # 80% of timeout
            logger.warning(f"⚠️  30-day analysis took {day30['total_duration']:.2f}s - approaching timeout risk!")
        
        if day30['total_duration'] > timeout_threshold:
            logger.error(f"🚨 30-day analysis took {day30['total_duration']:.2f}s - exceeds 15-minute timeout!")
        
        # Identify bottlenecks
        logger.info(f"\n📊 BOTTLENECK ANALYSIS:")
        day30_incident_pct = (day30['incidents_duration'] / day30['total_duration']) * 100
        logger.info(f"   30-day incident fetch is {day30_incident_pct:.1f}% of total time")
        
        if day30_incident_pct > 80:
            logger.warning(f"⚠️  Incident fetching is the primary bottleneck for 30-day analyses")
        
        # Performance recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        if day30['incidents_count'] / day7['incidents_count'] > 5:
            logger.info(f"   - 30-day analyses fetch {day30['incidents_count'] / day7['incidents_count']:.1f}x more data")
            logger.info(f"   - Consider implementing data volume limits or caching")
        
        if day30['incidents_per_second'] < day7['incidents_per_second'] * 0.5:
            logger.info(f"   - 30-day fetch rate is significantly slower - possible API rate limiting")
        
        if day30['total_duration'] > 300:  # 5 minutes
            logger.info(f"   - 30-day analyses are slow - consider background processing")
            
    else:
        logger.error("❌ Could not complete comparison - one or both tests failed")

async def test_analyzer_service_performance():
    """Test the full analyzer service performance for different time ranges."""
    
    api_token = os.getenv("ROOTLY_API_TOKEN")
    if not api_token:
        logger.error("Please set ROOTLY_API_TOKEN environment variable")
        return
    
    analyzer = BurnoutAnalyzerService(api_token, platform="rootly")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔍 TESTING FULL ANALYZER SERVICE")
    logger.info(f"{'='*60}")
    
    time_ranges = [7, 30]
    
    for days in time_ranges:
        logger.info(f"\n🔄 Testing {days}-day burnout analysis...")
        
        try:
            start_time = datetime.now()
            result = await analyzer.analyze_burnout(time_range_days=days)
            duration = (datetime.now() - start_time).total_seconds()
            
            team_members = len(result.get("team_analysis", {}).get("members", []))
            incidents_used = result.get("metadata", {}).get("total_incidents", 0)
            
            logger.info(f"✅ {days}-day analyzer completed in {duration:.2f}s")
            logger.info(f"   Team members analyzed: {team_members}")
            logger.info(f"   Incidents processed: {incidents_used}")
            
            # Check for performance issues
            if duration > 600:  # 10 minutes
                logger.error(f"🚨 {days}-day analysis took {duration:.2f}s - timeout risk!")
            elif duration > 300:  # 5 minutes
                logger.warning(f"⚠️  {days}-day analysis took {duration:.2f}s - performance concern")
            
        except Exception as e:
            logger.error(f"❌ {days}-day analyzer failed: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting time range performance analysis...")
    
    # Test data collection performance
    asyncio.run(test_data_volume_differences())
    
    # Test full analyzer performance
    asyncio.run(test_analyzer_service_performance())
    
    logger.info("✅ Performance analysis complete!")
    logger.info("\n💡 Next steps:")
    logger.info("1. Run this script and observe the performance differences")
    logger.info("2. Look for timeout warnings in 30-day analyses")
    logger.info("3. Check if incident fetching is the bottleneck")
    logger.info("4. Consider implementing performance optimizations based on findings")