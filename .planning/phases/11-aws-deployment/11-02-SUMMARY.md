---
phase: 11-aws-deployment
plan: 02
subsystem: infra
tags: [aws, ecs, fargate, docker, ecr, deployment, cloudwatch, iam]

# Dependency graph
requires:
  - phase: 11-aws-deployment
    plan: 01
    provides: Multi-stage Dockerfile.mcp for containerization
provides:
  - ECS task definition with Fargate compatibility (512 CPU, 1024 memory)
  - IAM policy for ECS task execution role with Secrets Manager and CloudWatch access
  - Deployment script for ECR authentication, image push, and ECS service update
  - Live ECS service running at http://13.218.46.36:8080
affects: [production-deployment, aws-infrastructure, monitoring]

# Tech tracking
tech-stack:
  added: [AWS ECS Fargate, AWS ECR, AWS CloudWatch Logs]
  patterns:
    - "ECS task definition with awsvpc network mode"
    - "Shell-based deployment with placeholder substitution"
    - "Client-side API key authentication via X-API-Key header"

key-files:
  created:
    - infra/ecs/task-definition.json
    - infra/ecs/iam-policy.json
    - infra/ecs/deploy.sh
  modified: []

key-decisions:
  - "Use client-side X-API-Key header injection (not server-side Secrets Manager injection)"
  - "Deploy without ALB (static IP needed for MCP SSE, defer to post-v1.1)"
  - "HTTP-only deployment (SSL deferred with domain setup)"
  - "Single task deployment (no auto-scaling needed for current usage)"

patterns-established:
  - "MCP server extracts API key from client-provided headers"
  - "Each client (Claude Desktop) provides their own API key via env vars"
  - "Health check endpoint at /health for container health monitoring"

# Metrics
duration: user-executed
completed: 2026-02-03
---

# Phase 11 Plan 02: ECS Deployment Infrastructure Summary

**ECS Fargate infrastructure files created and service deployed to http://13.218.46.36:8080 with client-side API key authentication**

## Performance

- **Duration:** User-executed (not Claude-executed)
- **Started:** 2026-02-03T00:15:00Z
- **Completed:** 2026-02-03T02:00:00Z
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 3

## Accomplishments

- ECS task definition created with Fargate compatibility (512 CPU, 1024 memory, awsvpc network)
- IAM policy with Secrets Manager read access and CloudWatch Logs write access
- Deployment script handling ECR authentication, Docker build/push, and ECS service updates
- Service successfully deployed and running at http://13.218.46.36:8080
- Health endpoint verified responding with {"status":"healthy","service":"on-call-health-mcp"}

## Task Commits

This phase was user-executed following the human-verify checkpoint. Files were created through the checkpoint workflow:

1. **Task 1: Create ECS task definition and IAM policy** - Files created during checkpoint
2. **Task 2: Create deployment script** - deploy.sh created during checkpoint
3. **Task 3: Human verification** - User deployed to AWS and verified service running

## Files Created/Modified

- `infra/ecs/task-definition.json` - ECS Fargate task definition with health checks and logging
- `infra/ecs/iam-policy.json` - IAM policy for ecsTaskExecutionRole (Secrets Manager, CloudWatch, ECR)
- `infra/ecs/deploy.sh` - Deployment script with ECR auth, Docker build, push, and ECS update

## API Key Authentication Model

**This deployment uses client-side X-API-Key header injection**, not server-side Secrets Manager injection:

- MCP server extracts API key from X-API-Key header in incoming HTTP requests
- Clients (like Claude Desktop) provide their API key when connecting to the MCP server
- Each user configures `ONCALLHEALTH_API_KEY` in their local Claude Desktop config
- The MCP server relays this API key to the On-Call Health backend API
- No server-side API key injection from Secrets Manager into the container

**Why this pattern:**
- Publicly accessible MCP endpoint where each user provides their own credentials
- Secrets Manager secret mentioned in deploy.sh documentation is for potential future use (e.g., ALB backend authentication)
- Task definition does NOT have a "secrets" section because no server-side injection is needed

**Client configuration example:**
```json
{
  "mcpServers": {
    "oncallhealth": {
      "url": "http://13.218.46.36:8080/sse",
      "transport": {
        "type": "sse"
      },
      "env": {
        "ONCALLHEALTH_API_KEY": "och_live_..."
      }
    }
  }
}
```

The `ONCALLHEALTH_API_KEY` env var is read by the client and injected into the X-API-Key header when connecting.

## Current AWS Deployment State

**Live Service:**
- URL: http://13.218.46.36:8080 (ECS public IP)
- Protocol: HTTP only (no SSL)
- Health check: http://13.218.46.36:8080/health
- ECS cluster: on-call-health
- ECS service: mcp-server
- Task definition: on-call-health-mcp (Fargate)

**Configuration:**
- CPU: 512 (0.5 vCPU)
- Memory: 1024 MB
- Network mode: awsvpc
- Desired count: 1 task
- Launch type: Fargate

**Logging:**
- CloudWatch log group: /ecs/on-call-health-mcp
- Log retention: Default (never expire - to be configured later if needed)

**No ALB deployed:**
- Service uses task public IP directly (13.218.46.36)
- Static IP required for MCP SSE connections (ALB would rotate IPs)
- ALB deployment deferred to post-v1.1 milestone

## Deferred to Post-v1.1

The following requirements are intentionally incomplete and deferred to future work:

- **AWS-06: Application Load Balancer** - Static IP needed for MCP SSE, requires separate architecture work
- **AWS-07: Auto-scaling configuration** - Single task sufficient for current usage, premature optimization
- **AWS-08: Domain name configuration** - User handling separately (mcp.oncallhealth.com)
- **AWS-09: SSL/TLS certificate** - Deferred with domain setup (requires ACM certificate)
- **AWS-10: Infrastructure-as-Code** - Manual AWS Console setup preferred by user

**Rationale:**
- v1.1 milestone goal: Get MCP server deployed and accessible
- ALB adds complexity without clear benefit for current usage (SSE needs stable endpoint)
- Auto-scaling premature until usage patterns established
- Domain and SSL are operational concerns handled outside development workflow
- IaC (Terraform/CDK) adds maintenance burden for single-deployment scenario

## Files Created Detail

### infra/ecs/task-definition.json
ECS Fargate task definition with:
- Family: on-call-health-mcp
- Network mode: awsvpc (required for Fargate)
- Requires compatibilities: FARGATE
- CPU: 512 (0.5 vCPU)
- Memory: 1024 MB
- Container: mcp-server on port 8080
- Environment variables: ONCALLHEALTH_API_URL, LOG_LEVEL
- Health check: Python urllib checking /health endpoint (30s interval)
- Logging: awslogs driver to /ecs/on-call-health-mcp

### infra/ecs/iam-policy.json
IAM policy document for ecsTaskExecutionRole with:
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- ECR: GetAuthorizationToken (account-wide)
- ECR Repository: BatchCheckLayerAvailability, GetDownloadUrlForLayer, BatchGetImage

### infra/ecs/deploy.sh
Deployment script automating:
1. Environment variable validation (AWS_ACCOUNT_ID, AWS_REGION)
2. ECR authentication (aws ecr get-login-password)
3. Docker image build (DOCKER_BUILDKIT=1, platform linux/amd64)
4. Image tagging for ECR repository
5. Image push to ECR
6. Task definition placeholder substitution (ACCOUNT_ID, REGION)
7. Task definition registration
8. ECS service update with force-new-deployment

## Decisions Made

1. **Client-side API key authentication**: MCP server extracts API key from X-API-Key header provided by clients, not injected server-side from Secrets Manager. This is the correct pattern for a publicly accessible MCP endpoint where each user provides their own credentials.

2. **No ALB deployment**: Static IP needed for MCP SSE connections. ALB would introduce IP rotation which breaks persistent connections. Deferred to post-v1.1 after architecture review.

3. **HTTP-only deployment**: SSL/TLS certificate requires domain name setup. Both deferred as operational concerns handled by user outside development workflow.

4. **Single task, no auto-scaling**: Current usage fits within single Fargate task (0.5 vCPU, 1GB RAM). Auto-scaling premature optimization until usage patterns established.

5. **Manual AWS infrastructure**: User prefers AWS Console setup over Infrastructure-as-Code. No Terraform/CDK for this deployment.

## Deviations from Plan

None - plan executed exactly as written. Infrastructure files created as specified, user deployed successfully following checkpoint instructions.

## Verification Results

**Docker build:**
```bash
DOCKER_BUILDKIT=1 docker build \
  --platform linux/amd64 \
  -f backend/Dockerfile.mcp \
  -t on-call-health-mcp:latest \
  backend/
# Success: Image built ~353MB
```

**ECR push:**
```bash
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin \
  ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com
docker push ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/on-call-health-mcp:latest
# Success: Image pushed to ECR
```

**ECS deployment:**
```bash
aws ecs describe-services \
  --cluster on-call-health \
  --services mcp-server \
  --query 'services[0].status'
# Output: "ACTIVE"

aws ecs describe-tasks \
  --cluster on-call-health \
  --tasks <task-arn> \
  --query 'tasks[0].lastStatus'
# Output: "RUNNING"
```

**Health check:**
```bash
curl http://13.218.46.36:8080/health
# {"status":"healthy","service":"on-call-health-mcp"}
```

**CloudWatch logs:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

## Issues Encountered

None - deployment proceeded smoothly following documented prerequisites.

## Next Phase Readiness

- ECS deployment complete, MCP server accessible at http://13.218.46.36:8080
- Health endpoint operational for monitoring
- CloudWatch logging configured for troubleshooting
- AWS-01 through AWS-05 requirements satisfied
- AWS-06 through AWS-10 intentionally deferred to post-v1.1
- v1.1 milestone AWS deployment goals achieved

## Requirements Completed

This phase completes the following requirements:

- **AWS-01**: Dockerfile for containerizing MCP server ✓ (11-01)
- **AWS-02**: Multi-stage Docker build ✓ (11-01)
- **AWS-03**: Docker image pushed to AWS ECR ✓
- **AWS-04**: ECS task definition with environment variables ✓
- **AWS-05**: ECS service deployment (Fargate) ✓

Deferred requirements (documented as out of scope for v1.1):

- **AWS-06**: Application Load Balancer (static IP needed)
- **AWS-07**: Auto-scaling configuration (premature)
- **AWS-08**: Domain name configuration (user-handled)
- **AWS-09**: SSL/TLS certificate (with domain)
- **AWS-10**: Infrastructure-as-Code (not needed)

---
*Phase: 11-aws-deployment*
*Completed: 2026-02-03*
