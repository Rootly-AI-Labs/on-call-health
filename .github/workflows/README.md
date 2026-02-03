# GitHub Actions Workflows

## deploy-mcp.yml

Automatically deploys the MCP server to AWS ECS when changes are pushed to main.

### Required GitHub Secrets

Configure these in: Repository Settings → Secrets and variables → Actions

| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region for deployment | `us-east-1` |
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID | `123456789012` |

### IAM Permissions Required

The IAM user/role must have permissions for:
- ECR: Push images (`ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, etc.)
- ECS: Update service and task definitions (`ecs:DescribeTaskDefinition`, `ecs:RegisterTaskDefinition`, `ecs:UpdateService`)

See `infra/ecs/iam-policy.json` for the complete policy.

### Trigger Conditions

The workflow runs when:
- Push to `main` branch
- Changes in:
  - `backend/app/mcp/**`
  - `backend/Dockerfile.mcp`
  - `backend/requirements-mcp.txt`
  - `infra/ecs/**`

### Deployment Process

1. Build Docker image from `Dockerfile.mcp`
2. Tag with commit SHA and `latest`
3. Push both tags to ECR
4. Update ECS task definition with new image
5. Force new deployment of ECS service
6. Wait for deployment to stabilize

### Monitoring

View deployment logs: Actions tab → Deploy MCP to ECS workflow

Check ECS deployment status: AWS Console → ECS → Clusters → on-call-health → Services → on-call-health-mcp-service
