"""
API endpoint for fetching changelog data from git commits.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from subprocess import run, PIPE, CalledProcessError
import json

from ...auth.dependencies import get_current_active_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/changelog", summary="Get changelog from git commits")
async def get_changelog(
    days: int = 30,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Fetch changelog entries from git commits.
    Groups commits by date and extracts relevant information.
    """
    try:
        # Calculate the date range
        since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Git log command to get commits with detailed information
        # Using a simpler format that's easier to parse
        git_command = [
            'git', 'log',
            f'--since={since_date}',
            f'--max-count={limit}',
            '--pretty=format:COMMIT_START%n%H%n%an%n%ae%n%ai%n%s%n%b%nCOMMIT_END',
            '--no-merges'
        ]
        
        try:
            result = run(git_command, capture_output=True, text=True, check=True)
            raw_output = result.stdout.strip()
        except CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch git history")
        
        if not raw_output:
            return {"entries": []}
        
        # Parse git log output with the new format
        commits = []
        commit_blocks = raw_output.split('COMMIT_START\n')[1:]  # Skip empty first element
        
        for block in commit_blocks:
            if 'COMMIT_END' in block:
                lines = block.replace('COMMIT_END', '').strip().split('\n')
                if len(lines) >= 5:
                    sha = lines[0].strip()
                    author_name = lines[1].strip()
                    author_email = lines[2].strip()
                    date = lines[3].strip()
                    message = lines[4].strip()
                    
                    # Get body if present (remaining lines)
                    body_lines = [l.strip() for l in lines[5:] if l.strip()]
                    full_message = message
                    if body_lines:
                        full_message += '\n' + '\n'.join(body_lines)
                    
                    # Get commit stats
                    stats = {"additions": 0, "deletions": 0}
                    try:
                        stat_result = run(
                            ['git', 'show', '--stat', '--format=', sha],
                            capture_output=True,
                            text=True
                        )
                        if stat_result.stdout:
                            for line in stat_result.stdout.split('\n'):
                                if 'insertion' in line:
                                    match = line.split(' ')[1]
                                    if match.isdigit():
                                        stats["additions"] = int(match)
                                if 'deletion' in line:
                                    match = line.split(' ')[1]
                                    if match.isdigit():
                                        stats["deletions"] = int(match)
                    except:
                        pass  # Stats are optional
                    
                    commit = {
                        "sha": sha,
                        "message": full_message,
                        "author": {
                            "name": author_name,
                            "email": author_email,
                            "date": date
                        },
                        "url": f"https://github.com/Rootly-AI-Labs/rootly-burnout-detector-web/commit/{sha}",
                        "stats": stats
                    }
                    commits.append(commit)
        
        # Group commits by date
        entries = []
        commits_by_date = {}
        
        for commit in commits:
            # Parse the author date
            author_date = commit["author"]["date"]
            # Extract just the date part (YYYY-MM-DD)
            date_only = author_date.split(' ')[0]
            
            if date_only not in commits_by_date:
                commits_by_date[date_only] = []
            commits_by_date[date_only].append(commit)
        
        # Convert to list of entries
        for date, date_commits in sorted(commits_by_date.items(), reverse=True):
            entries.append({
                "date": date,
                "commits": date_commits
            })
        
        # Try to add version tags if available
        try:
            # Get tags
            tag_result = run(['git', 'tag', '--sort=-creatordate'], capture_output=True, text=True)
            tags = tag_result.stdout.strip().split('\n') if tag_result.stdout.strip() else []
            
            # Get tag dates
            for tag in tags[:10]:  # Only check recent tags
                if tag:
                    tag_date_result = run(['git', 'log', '-1', '--format=%ai', tag], capture_output=True, text=True)
                    if tag_date_result.stdout:
                        tag_date = tag_date_result.stdout.strip().split(' ')[0]
                        # Find the entry for this date and add version
                        for entry in entries:
                            if entry["date"] == tag_date:
                                entry["version"] = tag
                                break
        except Exception as e:
            logger.warning(f"Could not fetch git tags: {e}")
        
        return {
            "entries": entries,
            "total_commits": len(commits),
            "date_range": {
                "from": since_date,
                "to": datetime.now().strftime('%Y-%m-%d')
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching changelog: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate changelog")