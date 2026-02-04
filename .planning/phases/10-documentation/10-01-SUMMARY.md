---
phase: "10-documentation"
plan: "01"
subsystem: "documentation"
tags: ["docs", "sse", "environment-variables", "pypi", "v1.1"]
dependency-graph:
  requires: ["Phase 5-9 (v1.1 implementation)"]
  provides: ["SSE deployment guide", "env var reference", "v1.1 context in PyPI README"]
  affects: ["Phase 10-02 (migration guide)", "Phase 11 (AWS deployment)"]
tech-stack:
  added: []
  patterns: ["modular documentation structure", "consolidated env var reference"]
key-files:
  created:
    - docs/DEPLOYMENT_SSE.md
    - docs/ENV_REFERENCE.md
  modified:
    - packages/oncallhealth-mcp/README.md
decisions:
  - key: "docs-gitignore"
    choice: "docs/ files untracked"
    rationale: "Project .gitignore excludes *.md except specific patterns; docs/ files exist locally but are not committed"
metrics:
  duration: "5min"
  completed: "2026-02-03"
---

# Phase 10 Plan 01: Documentation - SSE Guide, Env Reference, PyPI v1.1 Context

SSE deployment guide with Custom Connectors, consolidated env var reference from config.py, PyPI README augmented with REST API architecture context.

## Summary

Created three documentation deliverables:

1. **Hosted SSE Endpoint Guide** (`docs/DEPLOYMENT_SSE.md`) - Setup instructions for connecting Claude Desktop to the hosted MCP server via Custom Connectors (recommended) and JSON config alternative using mcp-remote bridge.

2. **Environment Variable Reference** (`docs/ENV_REFERENCE.md`) - Consolidated single source of truth for all env vars across deployment modes: core variables, AWS deployment variables (for Phase 11), and advanced client configuration sourced from `config.py`.

3. **PyPI README v1.1 Context** (`packages/oncallhealth-mcp/README.md`) - Added architecture blockquote, link to ENV_REFERENCE.md, "What's New in v1.1" section explaining the REST API approach, and link to Migration Guide.

## Tasks Completed

| Task | Description | Commit | Key Files |
|------|-------------|--------|-----------|
| 1 | Create Hosted SSE Endpoint Guide | (untracked) | docs/DEPLOYMENT_SSE.md |
| 2 | Create Environment Variable Reference | (untracked) | docs/ENV_REFERENCE.md |
| 3 | Augment PyPI README with v1.1 Context | c0cd84b9 | packages/oncallhealth-mcp/README.md |

## Deviations from Plan

### Documentation File Tracking

**1. [Observation] docs/*.md files not committed to git**

- **Found during:** Task 1 and 2 commit attempts
- **Issue:** Project `.gitignore` excludes `*.md` files except for specific patterns (`README.md`, `.planning/**/*.md`)
- **Impact:** `docs/DEPLOYMENT_SSE.md` and `docs/ENV_REFERENCE.md` exist locally but are not tracked in git
- **Resolution:** Files created as specified; this is existing project configuration (comment in .gitignore: "internal documentation not for public release")
- **Recommendation:** If these docs should be versioned, add `!docs/*.md` to .gitignore exceptions

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Custom Connectors as primary | Recommended over JSON config | Simpler user experience for Pro/Max/Team/Enterprise users |
| mcp-remote as JSON fallback | npx mcp-remote bridge pattern | Standard approach for stdio clients connecting to remote SSE |
| Env vars from config.py | 14 advanced variables documented | Single source of truth, accurate defaults |
| Relative links in README | `../../docs/ENV_REFERENCE.md` | Works within repo structure |

## Artifacts Created

### docs/DEPLOYMENT_SSE.md
- Prerequisites section
- Custom Connectors setup (5 steps)
- JSON alternative with mcp-remote
- Health check verification
- Minimal troubleshooting table

### docs/ENV_REFERENCE.md
- Core variables table (API_KEY, API_URL, LOG_LEVEL)
- AWS deployment variables (for Phase 11)
- Advanced configuration (14 variables from config.py)
- Notes on API key format

### packages/oncallhealth-mcp/README.md (modified)
- v1.1 Architecture blockquote
- Link to ENV_REFERENCE.md
- "What's New in v1.1" section
- Link to Migration Guide

## Verification Results

- [x] All three files exist
- [x] DEPLOYMENT_SSE.md contains Custom Connectors and JSON config options
- [x] ENV_REFERENCE.md contains tables for all deployment modes
- [x] README.md contains v1.1 architecture note
- [x] README.md links to ENV_REFERENCE.md

## Next Phase Readiness

**Ready for 10-02 (Migration Guide and AWS Documentation):**
- ENV_REFERENCE.md provides foundation for migration guide
- Links from README already point to Migration Guide (to be created)
- AWS variables documented for Phase 11

**Blockers:** None
