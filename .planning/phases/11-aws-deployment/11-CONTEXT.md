# Phase 11: AWS Deployment - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Create Dockerfile for MCP SSE server and deploy to AWS ECS Fargate. Simple deployment without load balancer, auto-scaling, or complex Infrastructure-as-Code. Focus on getting the working server (Phases 5-10) into a production-ready container on AWS.

</domain>

<decisions>
## Implementation Decisions

### Docker Configuration
- Base image: `python:3.11-slim` (official Python slim image)
- Multi-stage build: Yes (separate build stage for dependencies, slim runtime stage)
- Container should run the MCP SSE server (from Phase 7)

### AWS Deployment
- Platform: ECS Fargate (simple task, no load balancer or auto-scaling)
- Single task definition with container definition
- Port exposure for MCP SSE endpoint

### Secrets Management
- Use AWS Secrets Manager for sensitive environment variables
- Store: ONCALLHEALTH_API_KEY, DATABASE_URL (if needed), etc.
- ECS task pulls secrets at runtime from Secrets Manager

### Claude's Discretion
- Exact Dockerfile optimization techniques
- ECS task resource allocation (CPU/memory limits)
- Docker image tagging strategy
- Health check configuration in ECS

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for Docker containerization and ECS deployment.

</specifics>

<deferred>
## Deferred Ideas

The following were in the original Phase 11 scope but are deferred to future phases:

- Application Load Balancer (ALB) — add when scaling is needed
- Auto-scaling based on CPU/connection metrics — add when traffic demands it
- Infrastructure-as-Code (Terraform/CloudFormation) — add when infrastructure becomes complex
- HTTPS/SSL certificate management (ACM) — add with ALB
- Domain configuration (mcp.oncallhealth.ai) — add with ALB
- Blue-green or rolling deployment strategy — add when zero-downtime deploys are needed

</deferred>

---

*Phase: 11-aws-deployment*
*Context gathered: 2026-02-03*
