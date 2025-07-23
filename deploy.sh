#!/bin/bash

# Rootly Burnout Detector - Quick Deployment Script
# Usage: ./deploy.sh [environment]
# Environments: dev, staging, production

set -e

ENVIRONMENT=${1:-dev}
PROJECT_NAME="burnout-detector"

echo "🚀 Starting deployment for $ENVIRONMENT environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || { 
        log_error "Docker is required but not installed. Install Docker and try again."
        exit 1
    }
    
    command -v docker-compose >/dev/null 2>&1 || { 
        log_error "Docker Compose is required but not installed. Install Docker Compose and try again."
        exit 1
    }
    
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Please edit .env file with your configuration before proceeding."
            read -p "Press Enter to continue after editing .env..."
        else
            log_error ".env.example not found. Please create .env file with required variables."
            exit 1
        fi
    fi
    
    log_info "Prerequisites check completed ✓"
}

# Environment-specific configuration
configure_environment() {
    log_info "Configuring for $ENVIRONMENT environment..."
    
    case $ENVIRONMENT in
        "dev")
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-dev"
            export DEBUG=true
            export NODE_ENV=development
            ;;
        "staging")
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-staging"
            export DEBUG=false
            export NODE_ENV=production
            ;;
        "production")
            export COMPOSE_PROJECT_NAME="${PROJECT_NAME}-prod"
            export DEBUG=false
            export NODE_ENV=production
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            log_error "Available environments: dev, staging, production"
            exit 1
            ;;
    esac
    
    log_info "Environment configured for: $ENVIRONMENT"
}

# Build and deploy services
deploy_services() {
    log_info "Building and deploying services..."
    
    # Stop existing containers
    docker-compose down
    
    # Remove old images to ensure fresh build
    log_info "Cleaning up old images..."
    docker-compose build --no-cache
    
    # Start services
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    check_service_health
}

# Check if services are running properly
check_service_health() {
    log_info "Checking service health..."
    
    # Check backend health
    for i in {1..30}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_info "Backend service is healthy ✓"
            break
        else
            if [ $i -eq 30 ]; then
                log_error "Backend service failed to start"
                docker-compose logs backend
                exit 1
            fi
            log_warn "Waiting for backend to be ready... ($i/30)"
            sleep 2
        fi
    done
    
    # Check frontend
    for i in {1..30}; do
        if curl -f http://localhost:3000 >/dev/null 2>&1; then
            log_info "Frontend service is healthy ✓"
            break
        else
            if [ $i -eq 30 ]; then
                log_error "Frontend service failed to start"
                docker-compose logs frontend
                exit 1
            fi
            log_warn "Waiting for frontend to be ready... ($i/30)"
            sleep 2
        fi
    done
    
    # Check database
    if docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        log_info "Database service is healthy ✓"
    else
        log_error "Database service is not healthy"
        docker-compose logs postgres
        exit 1
    fi
}

# Display deployment info
show_deployment_info() {
    log_info "🎉 Deployment completed successfully!"
    echo ""
    echo "📱 Application URLs:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo ""
    echo "🔧 Useful commands:"
    echo "   View logs:     docker-compose logs -f"
    echo "   Stop services: docker-compose down"
    echo "   Restart:       docker-compose restart"
    echo "   Shell access:  docker-compose exec backend bash"
    echo ""
    
    if [ "$ENVIRONMENT" = "production" ]; then
        log_warn "PRODUCTION DEPLOYMENT CHECKLIST:"
        echo "   □ Configure reverse proxy (Nginx)"
        echo "   □ Set up SSL certificates"
        echo "   □ Configure monitoring"
        echo "   □ Set up backups"
        echo "   □ Review security settings"
        echo ""
    fi
}

# Main deployment flow
main() {
    echo "🔥 Rootly Burnout Detector Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "======================================="
    echo ""
    
    check_prerequisites
    configure_environment
    deploy_services
    show_deployment_info
}

# Handle script interruption
cleanup() {
    log_warn "Deployment interrupted. Cleaning up..."
    docker-compose down 2>/dev/null || true
    exit 1
}

trap cleanup INT TERM

# Run main function
main