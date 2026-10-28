#!/bin/bash
# Build and push the frontend base Docker image with pre-installed dependencies
# Run this script when frontend dependencies change (package.json)
#
# Usage:
#   ./build-base-images.sh          # Build only (local platform)
#   ./build-base-images.sh --push   # Build multi-platform and push to Docker Hub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REPO="rootlyio/on-call-health"
FRONTEND_IMAGE="$REPO:frontend-base"
PLATFORMS="linux/amd64,linux/arm64"

PUSH=false
if [[ "$1" == "--push" ]]; then
    PUSH=true
fi

# Check Docker Hub login status and login if needed
check_docker_login() {
    if ! docker info 2>/dev/null | grep -q "Username:"; then
        echo "Not logged into Docker Hub. Logging in..."
        docker login
        if [[ $? -ne 0 ]]; then
            echo "Error: Docker login failed. Cannot push images."
            exit 1
        fi
    else
        echo "Already logged into Docker Hub."
    fi
}

# Ensure buildx builder exists for multi-platform builds
setup_buildx() {
    if ! docker buildx inspect multiplatform-builder &>/dev/null; then
        echo "Creating multi-platform builder..."
        docker buildx create --name multiplatform-builder --use
    else
        docker buildx use multiplatform-builder
    fi
}

echo "Building frontend base Docker image..."

if [[ "$PUSH" == true ]]; then
    check_docker_login
    setup_buildx

    # Build and push frontend base image (multi-platform)
    echo "Building and pushing frontend base image for $PLATFORMS..."
    docker buildx build \
        --platform "$PLATFORMS" \
        -f "$PROJECT_ROOT/frontend/Dockerfile.base" \
        -t "$FRONTEND_IMAGE" \
        --push \
        "$PROJECT_ROOT/frontend"

    echo ""
    echo "Multi-platform image pushed successfully!"
    echo "  - $FRONTEND_IMAGE ($PLATFORMS)"
else
    # Build for local platform only
    echo "Building frontend base image (local platform)..."
    docker build \
        -f "$PROJECT_ROOT/frontend/Dockerfile.base" \
        -t "$FRONTEND_IMAGE" \
        "$PROJECT_ROOT/frontend"

    echo ""
    echo "Base image built successfully (local platform only)!"
    echo "  - $FRONTEND_IMAGE"
    echo ""
    echo "To build multi-platform and push to Docker Hub, run:"
    echo "  $0 --push"
fi
