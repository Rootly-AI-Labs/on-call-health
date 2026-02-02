# Project State: MCP Distribution

**Project:** On-Call Health MCP Server Distribution
**Updated:** 2026-02-02
**Status:** 🚀 Milestone v1.1 In Progress

## Project Reference

**See:** `.planning/PROJECT.md` (updated 2026-02-02)

## Current Position

**Phase:** Not started (defining requirements)
**Plan:** —
**Status:** Defining requirements
**Last activity:** 2026-02-02 — Milestone v1.1 started

## Milestone v1.1 Context

**Goal:** Enable zero-installation MCP server access via SSE-hosted endpoint and PyPI distribution

**Architecture shift:**
- Replace direct database access with REST API calls to oncallhealth.ai
- Support both SSE (hosted) and stdio (PyPI) transports
- Remove legacy direct-DB mode

**Key decisions:**
- SSE + PyPI distribution (both supported)
- REST API backend only (no direct database)
- No monitoring/observability in this milestone (use existing)
- No migration guide (breaking change acceptable)

## Accumulated Context

(This section will track decisions, blockers, and insights as work progresses)

---

*This file tracks living project memory across context resets*
