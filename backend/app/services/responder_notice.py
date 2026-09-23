"""Shared responder-facing notice for Slack check-ins."""

RESPONDER_NOTICE_URL = (
    "https://github.com/Rootly-AI-Labs/On-Call-Health/blob/main/"
    "RESPONDER_WORKLOAD_NOTICE.md"
)

RESPONDER_NOTICE = (
    "On-Call Health helps your team spot overload early and share the load. "
    "People with access to your team's analyses can see individual workload "
    "scores and check-in responses linked to your name or email.\n\n"
    "Where the Rootly MCP health-risk integration is enabled, authorized callers "
    "can retrieve existing individual scores and compare them with on-call "
    "schedules through tools such as Claude or Codex.\n\n"
    f"<{RESPONDER_NOTICE_URL}|How your workload information is used>"
)
