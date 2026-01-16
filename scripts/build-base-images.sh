#!/bin/bash
# Build and push base Docker images with pre-installed dependencies
# Run this script when dependencies change (requirements.txt or package.json)
#
# Usage:
#   ./build-base-images.sh          # Build only (local platform)
#   ./build-base-images.sh --push   # Build multi-platform and push to Docker Hub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REPO="rootlyio/on-call-health"
BACKEND_IMAGE="$REPO:backend-base"
FRONTEND_IMAGE="$REPO:frontend-base"
PLATFORMS="linux/amd64,linux/arm64"

PUSH=false
if [[ "$1" == "--push" ]]; then
    PUSH=true
fi

# Ensure buildx builder exists for multi-platform builds
setup_buildx() {
    if ! docker buildx inspect multiplatform-builder &>/dev/null; then
        echo "Creating multi-platform builder..."
        docker buildx create --name multiplatform-builder --use
    else
        docker buildx use multiplatform-builder
    fi
}

echo "Building base Docker images..."

if [[ "$PUSH" == true ]]; then
    setup_buildx

    # Build and push backend base image (multi-platform)
    echo "Building and pushing backend base image for $PLATFORMS..."
    docker buildx build \
        --platform "$PLATFORMS" \
        -f "$PROJECT_ROOT/backend/Dockerfile.base" \
        -t "$BACKEND_IMAGE" \
        --push \
        "$PROJECT_ROOT/backend"

    # Build and push frontend base image (multi-platform)
    echo "Building and pushing frontend base image for $PLATFORMS..."
    docker buildx build \
        --platform "$PLATFORMS" \
        -f "$PROJECT_ROOT/frontend/Dockerfile.base" \
        -t "$FRONTEND_IMAGE" \
        --push \
        "$PROJECT_ROOT/frontend"

    echo ""
    echo "Multi-platform images pushed successfully!"
    echo "  - $BACKEND_IMAGE ($PLATFORMS)"
    echo "  - $FRONTEND_IMAGE ($PLATFORMS)"
else
    # Build for local platform only
    echo "Building backend base image (local platform)..."
    docker build \
        -f "$PROJECT_ROOT/backend/Dockerfile.base" \
        -t "$BACKEND_IMAGE" \
        "$PROJECT_ROOT/backend"

    echo "Building frontend base image (local platform)..."
    docker build \
        -f "$PROJECT_ROOT/frontend/Dockerfile.base" \
        -t "$FRONTEND_IMAGE" \
        "$PROJECT_ROOT/frontend"

    echo ""
    echo "Base images built successfully (local platform only)!"
    echo "  - $BACKEND_IMAGE"
    echo "  - $FRONTEND_IMAGE"
    echo ""
    echo "To build multi-platform and push to Docker Hub, run:"
    echo "  $0 --push"
fi
