#!/bin/bash
# =============================================================================
# MCP Server Deployment Script for AWS ECS Fargate
# =============================================================================
#
# This script builds and deploys the MCP server Docker image to AWS ECS Fargate.
# It handles ECR authentication, image building, pushing, and ECS service updates.
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - Docker installed and running
#   - ECR repository created: aws ecr create-repository --repository-name on-call-health-mcp
#   - Secrets Manager secret created: aws secretsmanager create-secret --name mcp/api-key --secret-string "your-api-key"
#   - ECS cluster created: aws ecs create-cluster --cluster-name on-call-health
#   - ecsTaskExecutionRole with IAM policy from iam-policy.json attached
#   - CloudWatch log group: /ecs/on-call-health-mcp (auto-created if enabled)
#
# Usage:
#   export AWS_ACCOUNT_ID="123456789012"
#   export AWS_REGION="us-east-1"
#   ./deploy.sh
#
# Optional environment variables:
#   IMAGE_TAG - Docker image tag (default: latest)
#   ECS_CLUSTER - ECS cluster name (default: on-call-health)
#   ECS_SERVICE - ECS service name (default: mcp-server)
#
# =============================================================================

set -e  # Exit immediately on any error

# =============================================================================
# Environment Variable Validation
# =============================================================================

echo "==> Validating required environment variables..."

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "ERROR: AWS_ACCOUNT_ID is not set"
    echo "Usage: export AWS_ACCOUNT_ID=\"123456789012\""
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "ERROR: AWS_REGION is not set"
    echo "Usage: export AWS_REGION=\"us-east-1\""
    exit 1
fi

# =============================================================================
# Derived Variables
# =============================================================================

ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/on-call-health-mcp"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ECS_CLUSTER="${ECS_CLUSTER:-on-call-health}"
ECS_SERVICE="${ECS_SERVICE:-mcp-server}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")/backend"

echo "==> Configuration:"
echo "    AWS Account: $AWS_ACCOUNT_ID"
echo "    AWS Region:  $AWS_REGION"
echo "    ECR Repo:    $ECR_REPO"
echo "    Image Tag:   $IMAGE_TAG"
echo "    ECS Cluster: $ECS_CLUSTER"
echo "    ECS Service: $ECS_SERVICE"
echo "    Backend Dir: $BACKEND_DIR"

# =============================================================================
# Step 1: Authenticate Docker to ECR
# =============================================================================

echo ""
echo "==> Step 1: Authenticating Docker to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "    Docker authenticated successfully"

# =============================================================================
# Step 2: Build Docker Image
# =============================================================================

echo ""
echo "==> Step 2: Building Docker image..."
DOCKER_BUILDKIT=1 docker build \
    --platform linux/amd64 \
    -f "${BACKEND_DIR}/Dockerfile.mcp" \
    -t "on-call-health-mcp:${IMAGE_TAG}" \
    "${BACKEND_DIR}"

echo "    Docker image built successfully"

# =============================================================================
# Step 3: Tag Image for ECR
# =============================================================================

echo ""
echo "==> Step 3: Tagging image for ECR..."
docker tag "on-call-health-mcp:${IMAGE_TAG}" "${ECR_REPO}:${IMAGE_TAG}"

echo "    Image tagged: ${ECR_REPO}:${IMAGE_TAG}"

# =============================================================================
# Step 4: Push Image to ECR
# =============================================================================

echo ""
echo "==> Step 4: Pushing image to ECR..."
docker push "${ECR_REPO}:${IMAGE_TAG}"

echo "    Image pushed successfully"

# =============================================================================
# Step 5: Prepare Task Definition
# =============================================================================

echo ""
echo "==> Step 5: Preparing task definition..."

# Create a temporary file with substituted values
TASK_DEF_TEMPLATE="${SCRIPT_DIR}/task-definition.json"
TASK_DEF_RESOLVED=$(mktemp)

# Substitute placeholders with actual values
sed -e "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" \
    -e "s/REGION/${AWS_REGION}/g" \
    "${TASK_DEF_TEMPLATE}" > "${TASK_DEF_RESOLVED}"

echo "    Task definition prepared with account: ${AWS_ACCOUNT_ID}, region: ${AWS_REGION}"

# =============================================================================
# Step 6: Register Task Definition
# =============================================================================

echo ""
echo "==> Step 6: Registering task definition..."

TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json "file://${TASK_DEF_RESOLVED}" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "    Task definition registered: ${TASK_DEF_ARN}"

# Clean up temporary file
rm -f "${TASK_DEF_RESOLVED}"

# =============================================================================
# Step 7: Update ECS Service (if exists)
# =============================================================================

echo ""
echo "==> Step 7: Checking ECS service..."

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --query 'services[0].status' \
    --output text 2>/dev/null || echo "MISSING")

if [ "$SERVICE_EXISTS" != "MISSING" ] && [ "$SERVICE_EXISTS" != "None" ] && [ "$SERVICE_EXISTS" != "INACTIVE" ]; then
    echo "    Service exists, updating to new task definition..."

    aws ecs update-service \
        --cluster "$ECS_CLUSTER" \
        --service "$ECS_SERVICE" \
        --task-definition "$TASK_DEF_ARN" \
        --force-new-deployment \
        --query 'service.serviceName' \
        --output text

    echo "    Service updated successfully"
else
    echo "    Service does not exist. To create the service, run:"
    echo ""
    echo "    aws ecs create-service \\"
    echo "        --cluster $ECS_CLUSTER \\"
    echo "        --service-name $ECS_SERVICE \\"
    echo "        --task-definition $TASK_DEF_ARN \\"
    echo "        --desired-count 1 \\"
    echo "        --launch-type FARGATE \\"
    echo "        --network-configuration 'awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}'"
    echo ""
    echo "    Replace subnet-xxx and sg-xxx with your VPC subnet and security group IDs."
fi

# =============================================================================
# Deployment Complete
# =============================================================================

echo ""
echo "==> Deployment complete!"
echo ""
echo "Summary:"
echo "  - Image: ${ECR_REPO}:${IMAGE_TAG}"
echo "  - Task Definition: ${TASK_DEF_ARN}"
echo ""
echo "To check deployment status:"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE"
echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/on-call-health-mcp --follow"
