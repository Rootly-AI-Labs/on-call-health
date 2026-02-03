# Requirements: v1.1 MCP Distribution

**Defined:** 2026-02-02
**Core Value:** MCP clients and automation tools can authenticate reliably without JWT token expiration or session coupling.

## v1.1 Requirements

Requirements for MCP server distribution milestone. Each maps to roadmap phases.

### Transport Layer

- [ ] **TRANS-01**: Streamable HTTP endpoint at `/mcp` supporting MCP protocol
- [ ] **TRANS-02**: SSE endpoint at `/sse` for backward compatibility with older MCP clients
- [ ] **TRANS-03**: Connection heartbeat sent every 30 seconds to prevent proxy timeouts
- [ ] **TRANS-04**: Health check endpoint at `/health` returning 200 OK when service is ready
- [ ] **TRANS-05**: API key authentication via X-API-Key header for both transports
- [ ] **TRANS-06**: Proper CORS headers for web-based MCP clients (Claude web interface)

### REST API Client

- [ ] **CLIENT-01**: httpx-based async REST client with connection pooling
- [ ] **CLIENT-02**: Exponential backoff retry (3-5 retries with jitter) for transient failures
- [ ] **CLIENT-03**: Circuit breaker pattern to prevent retry storm amplification
- [ ] **CLIENT-04**: 5 second default timeout with configurable override
- [ ] **CLIENT-05**: Error mapping from HTTP status codes to MCP exceptions
- [ ] **CLIENT-06**: Connection pool health monitoring and automatic recreation
- [ ] **CLIENT-07**: API key injection into all outgoing requests (X-API-Key header)
- [ ] **CLIENT-08**: Base URL configuration for oncallhealth.ai API endpoint

### PyPI Distribution

- [ ] **PYPI-01**: Package named `oncallhealth-mcp` (or similar) published to PyPI
- [ ] **PYPI-02**: pyproject.toml with hatchling build backend
- [ ] **PYPI-03**: Console script entry point for `uvx oncallhealth-mcp` execution
- [ ] **PYPI-04**: Environment variable configuration (API_KEY, BASE_URL)
- [ ] **PYPI-05**: Flexible dependency version bounds (avoid pinning)
- [ ] **PYPI-06**: README with installation and setup instructions
- [ ] **PYPI-07**: Support for both SSE and stdio transports via CLI flag

### MCP Tools Refactor

- [ ] **TOOLS-01**: Migrate `analysis_start` from direct DB to REST API client
- [ ] **TOOLS-02**: Migrate `analysis_status` from direct DB to REST API client
- [ ] **TOOLS-03**: Migrate `analysis_results` from direct DB to REST API client
- [ ] **TOOLS-04**: Migrate `analysis_current` from direct DB to REST API client
- [ ] **TOOLS-05**: Migrate `integrations_list` from direct DB to REST API client
- [ ] **TOOLS-06**: Maintain existing tool signatures and behavior
- [ ] **TOOLS-07**: Error handling for network failures (timeout, connection refused, etc.)
- [ ] **TOOLS-08**: Remove all direct database query code from MCP server

### Infrastructure

- [ ] **INFRA-01**: Connection limit per user (max 5-10 concurrent SSE connections)
- [ ] **INFRA-02**: Connection limit per API key (prevent resource exhaustion)
- [ ] **INFRA-03**: Rate limiting for SSE endpoint (per-connection and per-user)
- [ ] **INFRA-04**: Graceful connection cleanup on client disconnect
- [ ] **INFRA-05**: Logging for connection events (connect, disconnect, errors)

### AWS Deployment

- [ ] **AWS-01**: Dockerfile for containerizing MCP server SSE endpoint
- [ ] **AWS-02**: Multi-stage Docker build for optimized image size
- [ ] **AWS-03**: Docker image pushed to AWS ECR (Elastic Container Registry)
- [ ] **AWS-04**: ECS task definition with environment variables (API_KEY, BASE_URL)
- [ ] **AWS-05**: ECS service deployment (Fargate or EC2)
- [ ] **AWS-06**: Application Load Balancer with health check routing
- [ ] **AWS-07**: Auto-scaling configuration based on CPU/connection count
- [ ] **AWS-08**: Domain name configuration (mcp.oncallhealth.com or similar)
- [ ] **AWS-09**: SSL/TLS certificate (ACM) for HTTPS
- [ ] **AWS-10**: Infrastructure-as-Code (Terraform or CloudFormation)

### Documentation

- [x] **DOCS-01**: SSE endpoint usage guide (Claude Desktop config)
- [x] **DOCS-02**: PyPI/uvx installation guide
- [x] **DOCS-03**: Environment variable reference
- [x] **DOCS-04**: Migration notice for users on stdio+direct-DB mode (breaking change)
- [x] **DOCS-05**: Deployment guide for hosting SSE endpoint on AWS
- [x] **DOCS-06**: Docker build and deployment instructions

## Future Requirements

Deferred to later milestones.

### Advanced Features

- **FUTURE-01**: Streamable HTTP v2 protocol support (when spec stabilizes)
- **FUTURE-02**: Connection pool metrics and monitoring dashboard
- **FUTURE-03**: Automatic retry budget adjustment based on backend health
- **FUTURE-04**: Multi-region SSE endpoints for reduced latency

### Observability

- **FUTURE-05**: Detailed connection lifecycle metrics
- **FUTURE-06**: Request tracing across MCP -> REST API -> backend
- **FUTURE-07**: Alerting for connection pool exhaustion

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| WebSocket transport | Not in MCP specification, Streamable HTTP is the standard |
| Direct database mode for SSE | Security risk - hosted endpoint should only call APIs |
| OAuth flow in PyPI package | Too complex, existing web login + API key generation works |
| Embedded web UI in MCP server | Scope creep, not part of MCP protocol |
| Monitoring/observability | Use existing infrastructure, not part of this milestone |
| Migration guide | Breaking change acceptable, new installation is simple |
| Request count tracking per connection | Defer until usage patterns understood |
| IP allowlisting | High complexity, wait for demand |
| Multi-tenancy isolation | Single-tenant deployment sufficient for v1.1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLIENT-01 | Phase 5 | Complete |
| CLIENT-02 | Phase 5 | Complete |
| CLIENT-03 | Phase 5 | Complete |
| CLIENT-04 | Phase 5 | Complete |
| CLIENT-05 | Phase 5 | Complete |
| CLIENT-06 | Phase 5 | Complete |
| CLIENT-07 | Phase 5 | Complete |
| CLIENT-08 | Phase 5 | Complete |
| TOOLS-01 | Phase 6 | Complete |
| TOOLS-02 | Phase 6 | Complete |
| TOOLS-03 | Phase 6 | Complete |
| TOOLS-04 | Phase 6 | Complete |
| TOOLS-05 | Phase 6 | Complete |
| TOOLS-06 | Phase 6 | Complete |
| TOOLS-07 | Phase 6 | Complete |
| TOOLS-08 | Phase 6 | Complete |
| TRANS-01 | Phase 7 | Complete |
| TRANS-02 | Phase 7 | Complete |
| TRANS-03 | Phase 7 | Complete |
| TRANS-04 | Phase 7 | Complete |
| TRANS-05 | Phase 7 | Complete |
| TRANS-06 | Phase 7 | Complete |
| PYPI-01 | Phase 8 | Complete |
| PYPI-02 | Phase 8 | Complete |
| PYPI-03 | Phase 8 | Complete |
| PYPI-04 | Phase 8 | Complete |
| PYPI-05 | Phase 8 | Complete |
| PYPI-06 | Phase 8 | Complete |
| PYPI-07 | Phase 8 | Complete |
| INFRA-01 | Phase 9 | Complete |
| INFRA-02 | Phase 9 | Complete |
| INFRA-03 | Phase 9 | Complete |
| INFRA-04 | Phase 9 | Complete |
| INFRA-05 | Phase 9 | Complete |
| DOCS-01 | Phase 10 | Complete |
| DOCS-02 | Phase 10 | Complete |
| DOCS-03 | Phase 10 | Complete |
| DOCS-04 | Phase 10 | Complete |
| DOCS-05 | Phase 10 | Complete |
| DOCS-06 | Phase 10 | Complete |
| AWS-01 | Phase 11 | Pending |
| AWS-02 | Phase 11 | Pending |
| AWS-03 | Phase 11 | Pending |
| AWS-04 | Phase 11 | Pending |
| AWS-05 | Phase 11 | Pending |
| AWS-06 | Phase 11 | Pending |
| AWS-07 | Phase 11 | Pending |
| AWS-08 | Phase 11 | Pending |
| AWS-09 | Phase 11 | Pending |
| AWS-10 | Phase 11 | Pending |

**Coverage:**
- v1.1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-02-02*
*Last updated: 2026-02-02 after roadmap revision (added AWS deployment)*
