#!/bin/bash
# Build and push base Docker images with pre-installed dependencies
# Run this script when dependencies change (requirements.txt or package.json)
#
# Usage:
#   ./build-base-images.sh          # Build only
#   ./build-base-images.sh --push   # Build and push to Docker Hub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REPO="rootlyio/on-call-health"
BACKEND_IMAGE="$REPO:backend-base"
FRONTEND_IMAGE="$REPO:frontend-base"

PUSH=false
if [[ "$1" == "--push" ]]; then
    PUSH=true
fi

echo "Building base Docker images..."

# Build backend base image
echo "Building backend base image..."
docker build \
    -f "$PROJECT_ROOT/backend/Dockerfile.base" \
    -t "$BACKEND_IMAGE" \
    "$PROJECT_ROOT/backend"

# Build frontend base image
echo "Building frontend base image..."
docker build \
    -f "$PROJECT_ROOT/frontend/Dockerfile.base" \
    -t "$FRONTEND_IMAGE" \
    "$PROJECT_ROOT/frontend"

echo ""
echo "Base images built successfully!"
echo "  - $BACKEND_IMAGE"
echo "  - $FRONTEND_IMAGE"

if [[ "$PUSH" == true ]]; then
    echo ""
    echo "Pushing images to Docker Hub..."
    docker push "$BACKEND_IMAGE"
    docker push "$FRONTEND_IMAGE"
    echo ""
    echo "Images pushed successfully!"
else
    echo ""
    echo "To push to Docker Hub, run:"
    echo "  $0 --push"
    echo ""
    echo "Or manually:"
    echo "  docker push $BACKEND_IMAGE"
    echo "  docker push $FRONTEND_IMAGE"
fi
