# Roadmap: MCP Distribution

## Milestones

- v1.0 MVP - Phases 1-4 (shipped 2026-02-03)
- **v1.1 MCP Distribution** - Phases 5-11 (in progress)

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

### v1.1 MCP Distribution (In Progress)

**Milestone Goal:** Enable zero-installation MCP server access via SSE-hosted endpoint and PyPI distribution, replacing direct database access with REST API calls. Deploy to AWS for production hosting.

- [x] **Phase 5: REST API Client** - Foundation layer for all MCP-to-API communication
- [x] **Phase 6: MCP Tools Refactor** - Migrate all tools from direct DB to REST API client
- [x] **Phase 7: Transport Implementation** - SSE and Streamable HTTP endpoints
- [x] **Phase 8: PyPI Distribution** - Publishable package for self-hosted users
- [x] **Phase 9: Infrastructure** - Connection limits, rate limiting, graceful cleanup
- [x] **Phase 10: Documentation** - User guides for SSE and PyPI deployment
- [ ] **Phase 11: AWS Deployment** - Docker containerization and ECS/Fargate production deployment

## Phase Details

### Phase 5: REST API Client
**Goal**: MCP server can make authenticated API calls to oncallhealth.ai with resilient error handling
**Depends on**: Phase 4 (v1.0 complete - API key authentication exists)
**Requirements**: CLIENT-01, CLIENT-02, CLIENT-03, CLIENT-04, CLIENT-05, CLIENT-06, CLIENT-07, CLIENT-08
**Success Criteria** (what must be TRUE):
  1. MCP server can make async HTTP requests to oncallhealth.ai API with connection pooling
  2. Transient failures (timeouts, 5xx errors) are retried with exponential backoff and jitter
  3. Persistent failures trigger circuit breaker, preventing retry storms
  4. HTTP status codes are translated to appropriate MCP exceptions
  5. API key is automatically injected into all outgoing requests
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md - Core REST client with config, exceptions, API key injection
- [ ] 05-02-PLAN.md - Resilience patterns (retry, circuit breaker, health monitor)

### Phase 6: MCP Tools Refactor
**Goal**: All MCP tools use REST API client instead of direct database queries
**Depends on**: Phase 5
**Requirements**: TOOLS-01, TOOLS-02, TOOLS-03, TOOLS-04, TOOLS-05, TOOLS-06, TOOLS-07, TOOLS-08
**Success Criteria** (what must be TRUE):
  1. User can start an analysis via MCP using REST API (no database dependency)
  2. User can check analysis status via MCP using REST API
  3. User can retrieve analysis results via MCP using REST API
  4. User can list integrations via MCP using REST API
  5. All direct database query code is removed from MCP server
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md - Migrate analysis tools (status, results, current, start) to REST client
- [ ] 06-02-PLAN.md - Migrate integrations_list and remove all database dependencies

### Phase 7: Transport Implementation
**Goal**: MCP server accessible via SSE and Streamable HTTP transports with proper authentication
**Depends on**: Phase 6
**Requirements**: TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05, TRANS-06
**Success Criteria** (what must be TRUE):
  1. Claude Desktop can connect to `/mcp` endpoint using Streamable HTTP transport
  2. Older MCP clients can connect to `/sse` endpoint for backward compatibility
  3. Connections stay alive across proxy timeouts (heartbeat every 30 seconds)
  4. Health check at `/health` returns 200 OK when service is ready
  5. Web-based MCP clients work with proper CORS headers
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md - Transport layer with Streamable HTTP, SSE, and health check endpoints
- [ ] 07-02-PLAN.md - CORS configuration, heartbeat, and main.py integration

### Phase 8: PyPI Distribution
**Goal**: Users can install and run MCP server via `uvx oncallhealth-mcp` with minimal configuration
**Depends on**: Phase 6 (tools use REST client), Phase 7 (transport options available)
**Requirements**: PYPI-01, PYPI-02, PYPI-03, PYPI-04, PYPI-05, PYPI-06, PYPI-07
**Success Criteria** (what must be TRUE):
  1. User can install package via `pip install oncallhealth-mcp`
  2. User can run server via `uvx oncallhealth-mcp` with API_KEY environment variable
  3. User can choose between SSE and stdio transports via CLI flag
  4. README provides clear installation and setup instructions
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md - Package structure, pyproject.toml, and MCP source code
- [ ] 08-02-PLAN.md - CLI entry point, README, and build verification

### Phase 9: Infrastructure
**Goal**: Hosted SSE endpoint is protected against resource exhaustion and abuse
**Depends on**: Phase 7
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. Single user cannot exhaust server resources (max 5-10 concurrent connections)
  2. Single API key cannot exhaust connections (per-key limits)
  3. SSE endpoint has rate limiting independent of API endpoint rate limits
  4. Disconnected clients are cleaned up gracefully (no resource leaks)
  5. Connection events are logged for debugging and monitoring
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md - Connection tracking and rate limiting infrastructure
- [ ] 09-02-PLAN.md - Graceful cleanup and structured logging

### Phase 10: Documentation
**Goal**: Users can successfully deploy MCP server using either hosted SSE or PyPI package
**Depends on**: Phase 7, Phase 8, Phase 9
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**Success Criteria** (what must be TRUE):
  1. User can configure Claude Desktop to use hosted SSE endpoint following docs
  2. User can install and configure PyPI package following docs
  3. User understands all environment variables and their purpose
  4. User understands this is a breaking change from stdio+direct-DB mode
  5. User can build Docker image and deploy to AWS following documentation
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md - SSE deployment guide and environment variable reference
- [ ] 10-02-PLAN.md - Migration guide and AWS deployment documentation
- [ ] 10-03-PLAN.md - Deprecate legacy documentation with redirect notices

### Phase 11: AWS Deployment
**Goal**: MCP SSE endpoint is running on AWS ECS/Fargate with load balancing, auto-scaling, and HTTPS
**Depends on**: Phase 7 (transport implementation complete)
**Requirements**: AWS-01, AWS-02, AWS-03, AWS-04, AWS-05, AWS-06, AWS-07, AWS-08, AWS-09, AWS-10
**Success Criteria** (what must be TRUE):
  1. User can connect to MCP SSE endpoint at https://mcp.oncallhealth.ai (or similar domain)
  2. Docker image is automatically built and pushed to ECR on deployment
  3. ECS service starts containers with correct environment variables (API_KEY, BASE_URL)
  4. Application Load Balancer routes traffic to healthy containers
  5. Service auto-scales based on CPU/connection metrics (handles load spikes)
  6. All infrastructure is defined as code (Terraform or CloudFormation)
**Plans**: TBD

Plans:
- [ ] 11-01: Docker containerization and ECR setup
- [ ] 11-02: ECS/Fargate deployment with ALB
- [ ] 11-03: Domain, SSL, and auto-scaling configuration

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-4 | v1.0 | 8/8 | Complete | 2026-02-03 |
| 5. REST API Client | v1.1 | 2/2 | Complete | 2026-02-03 |
| 6. MCP Tools Refactor | v1.1 | 2/2 | Complete | 2026-02-03 |
| 7. Transport Implementation | v1.1 | 2/2 | Complete | 2026-02-03 |
| 8. PyPI Distribution | v1.1 | 2/2 | Complete | 2026-02-03 |
| 9. Infrastructure | v1.1 | 2/2 | Complete | 2026-02-03 |
| 10. Documentation | v1.1 | 3/3 | Complete | 2026-02-03 |
| 11. AWS Deployment | v1.1 | 0/3 | Not started | - |

---
*Roadmap created: 2026-02-02*
*Last updated: 2026-02-03*
