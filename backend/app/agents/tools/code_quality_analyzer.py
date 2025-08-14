"""
Code Quality Analysis Tool for Burnout Detection Agent

Analyzes GitHub activity patterns to detect code quality issues that may indicate burnout:
- PR size patterns (large PRs indicate rushed work)
- Commit frequency and timing
- Code churn (additions/deletions ratio)
- Review patterns
"""
from typing import Dict, List, Any, Optional
import statistics
from datetime import datetime, timedelta
import logging

try:
    from smolagents import BaseTool
except ImportError:
    # Fallback for development/testing when smolagents not available
    class BaseTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

logger = logging.getLogger(__name__)


class CodeQualityAnalyzerTool(BaseTool):
    """Tool for analyzing code quality patterns that may indicate burnout."""
    
    def __init__(self):
        try:
            # Try the smolagents BaseTool signature
            super().__init__()
            self.name = "code_quality_analyzer"
            self.description = "Analyzes GitHub activity to detect code quality issues and rushed development patterns"
        except TypeError:
            # Fallback to our custom BaseTool signature  
            super().__init__(
                name="code_quality_analyzer",
                description="Analyzes GitHub activity to detect code quality issues and rushed development patterns"
            )
        
    def __call__(self, github_data: Dict[str, Any], time_window_days: int = 30) -> Dict[str, Any]:
        """
        Analyze code quality patterns from GitHub data.
        
        Args:
            github_data: Dictionary containing commits, PRs, and review data
            time_window_days: Analysis window in days
            
        Returns:
            Dictionary with code quality analysis results
        """
        if not github_data:
            return {
                "quality_score": 0.0,
                "risk_indicators": ["No GitHub data available"],
                "patterns": {},
                "recommendations": []
            }
        
        analysis = {
            "quality_score": 100.0,  # Start with perfect score
            "risk_indicators": [],
            "patterns": {},
            "recommendations": []
        }
        
        # Analyze PR patterns
        pr_analysis = self._analyze_pr_patterns(github_data.get("pull_requests", []))
        analysis["patterns"]["pull_requests"] = pr_analysis
        
        # Analyze commit patterns
        commit_analysis = self._analyze_commit_patterns(github_data.get("commits", []))
        analysis["patterns"]["commits"] = commit_analysis
        
        # Analyze code churn
        churn_analysis = self._analyze_code_churn(github_data.get("commits", []))
        analysis["patterns"]["code_churn"] = churn_analysis
        
        # Analyze review patterns
        review_analysis = self._analyze_review_patterns(
            github_data.get("reviews_given", []),
            github_data.get("reviews_received", [])
        )
        analysis["patterns"]["reviews"] = review_analysis
        
        # Calculate overall quality score and risk indicators
        analysis = self._calculate_quality_score(analysis)
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        logger.info(f"Code Quality Analysis - Score: {analysis['quality_score']:.1f}, Risk indicators: {len(analysis['risk_indicators'])}")
        
        return analysis
    
    def _analyze_pr_patterns(self, pull_requests: List[Dict]) -> Dict[str, Any]:
        """Analyze pull request patterns for quality issues."""
        if not pull_requests:
            return {"status": "no_data"}
        
        pr_sizes = []
        large_prs = 0
        rushed_prs = 0
        weekend_prs = 0
        
        for pr in pull_requests:
            # Calculate PR size
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            total_changes = additions + deletions
            pr_sizes.append(total_changes)
            
            # Check for large PRs (>500 lines)
            if total_changes > 500:
                large_prs += 1
            
            # Check for rushed PRs (created and merged same day)
            created = pr.get("created_at")
            merged = pr.get("merged_at")
            if created and merged:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                merged_dt = datetime.fromisoformat(merged.replace('Z', '+00:00'))
                if (merged_dt - created_dt).days == 0:
                    rushed_prs += 1
                    
            # Check for weekend PRs
            if created:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                if created_dt.weekday() >= 5:  # Saturday or Sunday
                    weekend_prs += 1
        
        avg_pr_size = statistics.mean(pr_sizes) if pr_sizes else 0
        large_pr_ratio = large_prs / len(pull_requests) if pull_requests else 0
        rushed_pr_ratio = rushed_prs / len(pull_requests) if pull_requests else 0
        weekend_pr_ratio = weekend_prs / len(pull_requests) if pull_requests else 0
        
        return {
            "total_prs": len(pull_requests),
            "avg_pr_size": round(avg_pr_size),
            "large_pr_ratio": round(large_pr_ratio, 2),
            "rushed_pr_ratio": round(rushed_pr_ratio, 2),
            "weekend_pr_ratio": round(weekend_pr_ratio, 2),
            "quality_issues": {
                "large_prs": large_prs,
                "rushed_prs": rushed_prs,
                "weekend_prs": weekend_prs
            }
        }
    
    def _analyze_commit_patterns(self, commits: List[Dict]) -> Dict[str, Any]:
        """Analyze commit patterns for quality issues."""
        if not commits:
            return {"status": "no_data"}
        
        commit_messages = []
        late_night_commits = 0
        weekend_commits = 0
        commit_hours = []
        
        for commit in commits:
            # Analyze commit message quality
            message = commit.get("message", "")
            commit_messages.append(len(message))
            
            # Check commit timing
            timestamp = commit.get("timestamp") or commit.get("created_at")
            if timestamp:
                commit_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = commit_dt.hour
                commit_hours.append(hour)
                
                # Late night (10 PM - 4 AM)
                if hour >= 22 or hour < 4:
                    late_night_commits += 1
                    
                # Weekend
                if commit_dt.weekday() >= 5:
                    weekend_commits += 1
        
        avg_message_length = statistics.mean(commit_messages) if commit_messages else 0
        short_messages = len([m for m in commit_messages if m < 10])
        
        return {
            "total_commits": len(commits),
            "avg_message_length": round(avg_message_length),
            "short_message_ratio": round(short_messages / len(commits), 2) if commits else 0,
            "late_night_ratio": round(late_night_commits / len(commits), 2) if commits else 0,
            "weekend_ratio": round(weekend_commits / len(commits), 2) if commits else 0,
            "peak_hours": self._find_peak_hours(commit_hours) if commit_hours else []
        }
    
    def _analyze_code_churn(self, commits: List[Dict]) -> Dict[str, Any]:
        """Analyze code churn patterns."""
        if not commits:
            return {"status": "no_data"}
        
        total_additions = 0
        total_deletions = 0
        churn_events = 0
        
        for commit in commits:
            additions = commit.get("additions", 0) or commit.get("stats", {}).get("additions", 0)
            deletions = commit.get("deletions", 0) or commit.get("stats", {}).get("deletions", 0)
            
            total_additions += additions
            total_deletions += deletions
            
            # High churn: more deletions than additions (rewriting code)
            if deletions > additions * 0.5 and deletions > 50:
                churn_events += 1
        
        churn_ratio = total_deletions / max(total_additions, 1)
        
        return {
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "churn_ratio": round(churn_ratio, 2),
            "high_churn_commits": churn_events,
            "avg_commit_size": round((total_additions + total_deletions) / len(commits)) if commits else 0
        }
    
    def _analyze_review_patterns(self, reviews_given: List[Dict], reviews_received: List[Dict]) -> Dict[str, Any]:
        """Analyze code review patterns."""
        review_engagement = "normal"
        
        if not reviews_given and not reviews_received:
            review_engagement = "no_reviews"
        elif len(reviews_given) < len(reviews_received) * 0.3:
            review_engagement = "low_engagement"
        elif len(reviews_given) > len(reviews_received) * 2:
            review_engagement = "high_burden"
            
        return {
            "reviews_given": len(reviews_given) if reviews_given else 0,
            "reviews_received": len(reviews_received) if reviews_received else 0,
            "review_engagement": review_engagement
        }
    
    def _find_peak_hours(self, hours: List[int]) -> List[int]:
        """Find peak activity hours."""
        if not hours:
            return []
            
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
        # Sort by count and return top 3 hours
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality score and identify risk indicators."""
        score = analysis["quality_score"]
        risk_indicators = []
        
        # PR pattern penalties
        pr_patterns = analysis["patterns"].get("pull_requests", {})
        if pr_patterns.get("large_pr_ratio", 0) > 0.3:
            score -= 15
            risk_indicators.append("High ratio of large PRs indicates rushed development")
        if pr_patterns.get("rushed_pr_ratio", 0) > 0.2:
            score -= 10
            risk_indicators.append("Many PRs created and merged same day")
        if pr_patterns.get("weekend_pr_ratio", 0) > 0.15:
            score -= 5
            risk_indicators.append("Significant weekend PR activity")
            
        # Commit pattern penalties
        commit_patterns = analysis["patterns"].get("commits", {})
        if commit_patterns.get("short_message_ratio", 0) > 0.3:
            score -= 10
            risk_indicators.append("Poor commit message quality")
        if commit_patterns.get("late_night_ratio", 0) > 0.2:
            score -= 15
            risk_indicators.append("High late-night commit activity")
        if commit_patterns.get("weekend_ratio", 0) > 0.15:
            score -= 5
            risk_indicators.append("Frequent weekend commits")
            
        # Code churn penalties
        churn = analysis["patterns"].get("code_churn", {})
        if churn.get("churn_ratio", 0) > 0.7:
            score -= 20
            risk_indicators.append("High code churn indicates instability")
        if churn.get("high_churn_commits", 0) > 5:
            score -= 10
            risk_indicators.append("Multiple high-churn commits suggest rework")
            
        # Review pattern penalties
        reviews = analysis["patterns"].get("reviews", {})
        if reviews.get("review_engagement") == "low_engagement":
            score -= 10
            risk_indicators.append("Low code review engagement")
        elif reviews.get("review_engagement") == "no_reviews":
            score -= 20
            risk_indicators.append("No code review activity detected")
            
        analysis["quality_score"] = max(0, score)
        analysis["risk_indicators"] = risk_indicators
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # PR recommendations
        pr_patterns = analysis["patterns"].get("pull_requests", {})
        if pr_patterns.get("large_pr_ratio", 0) > 0.3:
            recommendations.append("Break down large PRs into smaller, reviewable chunks")
        if pr_patterns.get("rushed_pr_ratio", 0) > 0.2:
            recommendations.append("Allow more time for PR review and testing")
            
        # Commit recommendations
        commit_patterns = analysis["patterns"].get("commits", {})
        if commit_patterns.get("late_night_ratio", 0) > 0.2:
            recommendations.append("Establish healthier work hours to avoid late-night coding")
        if commit_patterns.get("short_message_ratio", 0) > 0.3:
            recommendations.append("Improve commit message quality for better history tracking")
            
        # Churn recommendations
        churn = analysis["patterns"].get("code_churn", {})
        if churn.get("churn_ratio", 0) > 0.7:
            recommendations.append("Review development process to reduce code rework")
            
        # Review recommendations
        reviews = analysis["patterns"].get("reviews", {})
        if reviews.get("review_engagement") in ["low_engagement", "no_reviews"]:
            recommendations.append("Increase participation in code reviews for knowledge sharing")
            
        return recommendations


def create_code_quality_analyzer_tool():
    """Factory function to create code quality analyzer tool for smolagents."""
    return CodeQualityAnalyzerTool()