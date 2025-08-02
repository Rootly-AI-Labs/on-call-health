"""
Burnout Analysis Workflows

Advanced workflows for orchestrating complex burnout analyses using smolagents.
"""
from .comprehensive_analysis import (
    ComprehensiveBurnoutWorkflow,
    run_team_analysis_workflow
)

__all__ = [
    "ComprehensiveBurnoutWorkflow", 
    "run_team_analysis_workflow"
]