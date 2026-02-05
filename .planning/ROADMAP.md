# Roadmap: MCP Distribution

## Milestones

- v1.0 MVP - Phases 1-4 (shipped 2026-02-03)
- **v1.1 MCP Distribution** - Phases 5-12 (shipped 2026-02-04) — See [archive](.planning/milestones/v1.1-ROADMAP.md)

## Overview

Transform the MCP server from a direct-database-access implementation to a distributed architecture where MCP clients connect via SSE-hosted endpoint or PyPI package, both calling oncallhealth.ai REST APIs instead of querying the database directly. This enables zero-installation access via hosted SSE and self-hosted deployment via uvx. Production deployment uses AWS ECS/Fargate with load balancing and auto-scaling.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED 2026-02-03</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for archived v1.0 phases.

</details>


---
*Roadmap created: 2026-02-02*
*Last updated: 2026-02-04*
