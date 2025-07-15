#!/usr/bin/env python3
"""
Create a mock analysis with rich AI insights for demonstration
"""
import sqlite3
import json
from datetime import datetime

def create_mock_ai_analysis():
    """Create a mock analysis with rich AI insights data."""
    
    # Rich mock analysis data with realistic AI insights
    mock_analysis_data = {
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "days_analyzed": 30,
            "total_users": 8,
            "total_incidents": 156,
            "date_range": {
                "start": "2024-06-15T07:11:00.000000+00:00",
                "end": "2024-07-15T07:11:00.000000+00:00"
            },
            "include_weekends": True,
            "include_github": True,
            "include_slack": True
        },
        "data_sources": {
            "incident_data": True,
            "github_data": True,
            "slack_data": True
        },
        "team_health": {
            "overall_score": 6.2,
            "risk_distribution": {
                "low": 3,
                "medium": 3,
                "high": 2
            },
            "average_burnout_score": 5.4,
            "health_status": "concerning",
            "members_at_risk": 5
        },
        "team_analysis": {
            "members": [
                {
                    "user_id": "spencer_001",
                    "user_name": "Spencer Cheng",
                    "user_email": "spencer.cheng@rootly.com",
                    "burnout_score": 7.8,
                    "risk_level": "high",
                    "incident_count": 43,
                    "factors": {
                        "workload": 0.9,
                        "after_hours": 0.8,
                        "weekend_work": 0.4,
                        "incident_load": 0.85,
                        "response_time": 0.2
                    },
                    "ai_insights": {
                        "workload": {
                            "workload_status": "overloaded",
                            "intensity_score": 8.5,
                            "sustainability_indicators": [
                                "Handling 43% above team average incidents",
                                "Consistent after-hours activity detected",
                                "Weekend work patterns emerging"
                            ],
                            "recommendations": [
                                "Redistribute 30% of incident load to other team members",
                                "Implement stricter after-hours boundaries",
                                "Consider delegating weekend on-call duties"
                            ]
                        },
                        "patterns": {
                            "incident_clustering": "High incident density on Tuesdays and Thursdays",
                            "response_timing": "Consistently quick responses indicating high stress",
                            "communication_style": "Increasingly brief in incident communications"
                        },
                        "sentiment": {
                            "overall_trend": "declining",
                            "stress_indicators": ["Short responses", "Late night activity", "Weekend commits"]
                        }
                    },
                    "ai_risk_assessment": {
                        "overall_risk_level": "high",
                        "risk_score": 8.2,
                        "risk_factors": [
                            "Sustained high incident volume",
                            "After-hours work pattern",
                            "Declining communication sentiment"
                        ],
                        "protective_factors": [
                            "Strong technical skills",
                            "Team collaboration"
                        ]
                    },
                    "ai_recommendations": [
                        {
                            "priority": "urgent",
                            "category": "workload_management",
                            "title": "Immediate Workload Reduction",
                            "description": "Redistribute 30-40% of current incident load to reduce burnout risk",
                            "actions": [
                                "Transfer non-critical incidents to other team members",
                                "Implement incident triage system",
                                "Set up rotation schedule"
                            ]
                        }
                    ]
                },
                {
                    "user_id": "alex_002",
                    "user_name": "Alex Johnson",
                    "user_email": "alex@company.com",
                    "burnout_score": 6.1,
                    "risk_level": "medium",
                    "incident_count": 28,
                    "factors": {
                        "workload": 0.6,
                        "after_hours": 0.5,
                        "weekend_work": 0.1,
                        "incident_load": 0.7,
                        "response_time": 0.4
                    },
                    "ai_insights": {
                        "workload": {
                            "workload_status": "manageable",
                            "intensity_score": 6.1,
                            "sustainability_indicators": [
                                "Moderate incident load within healthy range",
                                "Good work-life balance maintained"
                            ],
                            "recommendations": [
                                "Continue current workload distribution",
                                "Monitor for any increases in incident volume"
                            ]
                        }
                    },
                    "ai_risk_assessment": {
                        "overall_risk_level": "medium",
                        "risk_score": 6.1,
                        "risk_factors": ["Moderate incident load"],
                        "protective_factors": ["Good work-life balance", "Consistent performance"]
                    }
                },
                {
                    "user_id": "sarah_003",
                    "user_name": "Sarah Chen",
                    "user_email": "sarah@company.com",
                    "burnout_score": 8.4,
                    "risk_level": "high",
                    "incident_count": 51,
                    "factors": {
                        "workload": 0.95,
                        "after_hours": 0.9,
                        "weekend_work": 0.6,
                        "incident_load": 0.9,
                        "response_time": 0.1
                    },
                    "ai_insights": {
                        "workload": {
                            "workload_status": "critical",
                            "intensity_score": 9.2,
                            "sustainability_indicators": [
                                "Highest incident volume on team",
                                "Extensive weekend and after-hours work",
                                "Signs of escalating stress in communications"
                            ],
                            "recommendations": [
                                "URGENT: Immediate workload reduction required",
                                "Consider temporary reassignment of responsibilities",
                                "Implement mandatory time off"
                            ]
                        }
                    },
                    "ai_risk_assessment": {
                        "overall_risk_level": "critical",
                        "risk_score": 9.2,
                        "risk_factors": [
                            "Extreme workload",
                            "Consistent overtime",
                            "Weekend work pattern"
                        ]
                    }
                }
            ]
        },
        "ai_enhanced": True,
        "ai_team_insights": {
            "available": True,
            "insights": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "team_size": 8,
                "data_sources": ["incident_data", "github_data", "slack_data"],
                "risk_distribution": {
                    "distribution": {
                        "low": 3,
                        "medium": 3,
                        "high": 2,
                        "critical": 0
                    },
                    "high_risk_percentage": 25.0,
                    "ai_escalations": 2,
                    "total_members": 8
                },
                "common_patterns": [
                    {
                        "pattern": "Tuesday/Thursday Incident Clustering",
                        "description": "62% of critical incidents occur on Tuesdays and Thursdays",
                        "affected_members": 6,
                        "severity": "medium",
                        "recommendation": "Review incident distribution and implement proactive monitoring on high-risk days"
                    },
                    {
                        "pattern": "After-Hours Escalation",
                        "description": "40% increase in after-hours incident handling over past month",
                        "affected_members": 5,
                        "severity": "high",
                        "recommendation": "Implement better on-call rotation and incident triage system"
                    },
                    {
                        "pattern": "Communication Sentiment Decline",
                        "description": "Team communication sentiment has decreased by 23% indicating stress",
                        "affected_members": 7,
                        "severity": "medium",
                        "recommendation": "Schedule team wellness check-ins and stress management resources"
                    }
                ],
                "team_recommendations": [
                    {
                        "priority": "urgent",
                        "category": "workload_redistribution",
                        "title": "Immediate Workload Rebalancing",
                        "description": "Critical team members are handling 65% of incident volume. Redistribute workload immediately.",
                        "actions": [
                            "Identify incidents that can be reassigned",
                            "Implement incident triage system",
                            "Cross-train team members on critical systems"
                        ],
                        "expected_impact": "Reduce burnout risk for 2 critical team members",
                        "timeline": "Within 1 week"
                    },
                    {
                        "priority": "high",
                        "category": "process_improvement",
                        "title": "Enhanced On-Call Rotation",
                        "description": "Current on-call system is causing burnout. Implement fairer rotation.",
                        "actions": [
                            "Create formal on-call schedule",
                            "Set maximum consecutive on-call days",
                            "Implement escalation procedures"
                        ],
                        "expected_impact": "Reduce after-hours stress by 40%",
                        "timeline": "Within 2 weeks"
                    },
                    {
                        "priority": "medium",
                        "category": "team_wellness",
                        "title": "Stress Management Program",
                        "description": "Implement proactive wellness initiatives to support team mental health.",
                        "actions": [
                            "Weekly team wellness check-ins",
                            "Mental health resources access",
                            "Workload monitoring dashboard"
                        ],
                        "expected_impact": "Improve team sentiment by 25%",
                        "timeline": "Within 1 month"
                    }
                ],
                "workload_distribution": {
                    "available": True,
                    "average_intensity": 6.8,
                    "intensity_range": {
                        "min": 3.2,
                        "max": 9.2
                    },
                    "imbalances": [
                        {
                            "member": "Sarah Chen",
                            "overload_percentage": 42,
                            "recommendation": "Reduce by 30-40%"
                        },
                        {
                            "member": "Spencer Cheng", 
                            "overload_percentage": 35,
                            "recommendation": "Reduce by 25-30%"
                        }
                    ],
                    "distribution_health": "poor"
                }
            }
        }
    }
    
    # Insert into database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Create new analysis record
    cursor.execute("""
        INSERT INTO analyses (user_id, status, results, created_at, completed_at, time_range)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        2,  # user_id
        "completed",
        json.dumps(mock_analysis_data),
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat(),
        30
    ))
    
    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ Created mock analysis with ID: {analysis_id}")
    print(f"📊 Mock data includes:")
    print(f"   - 8 team members with varying burnout levels")
    print(f"   - 3 common patterns identified by AI")
    print(f"   - 3 prioritized team recommendations")
    print(f"   - Detailed workload distribution analysis")
    print(f"   - Individual AI insights for each member")
    
    return analysis_id

if __name__ == "__main__":
    create_mock_ai_analysis()