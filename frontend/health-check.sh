#!/bin/bash

# Health Check Script for Rootly Burnout Detector
# Usage: ./health-check.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
FRONTEND_URL="http://localhost:3000"
BACKEND_URL="http://localhost:8000"
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"

# Functions
log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check service health
check_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-5}
    
    if curl -f -m $timeout "$url" >/dev/null 2>&1; then
        log_info "$service_name is healthy"
        return 0
    else
        log_error "$service_name is not responding"
        return 1
    fi
}

# Check Docker containers
check_containers() {
    echo "🐳 Checking Docker containers..."
    
    containers=("burnout-detector-frontend" "burnout-detector-backend" "burnout-detector-db")
    all_healthy=true
    
    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" --format "table {{.Names}}" | grep -q "$container"; then
            log_info "$container is running"
        else
            log_error "$container is not running"
            all_healthy=false
        fi
    done
    
    return $all_healthy
}

# Check services
check_services() {
    echo ""
    echo "🌐 Checking service endpoints..."
    
    all_healthy=true
    
    # Check backend health endpoint
    if check_service "Backend API" "$BACKEND_URL/health"; then
        # Check API docs
        check_service "API Documentation" "$BACKEND_URL/docs" 3
    else
        all_healthy=false
    fi
    
    # Check frontend
    if ! check_service "Frontend" "$FRONTEND_URL"; then
        all_healthy=false
    fi
    
    return $all_healthy
}

# Check database connectivity
check_database() {
    echo ""
    echo "🗄️ Checking database connectivity..."
    
    if docker-compose exec -T postgres pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
        log_info "Database is accepting connections"
        return 0
    else
        log_error "Database is not accepting connections"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    echo ""
    echo "💾 Checking disk space..."
    
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt 80 ]; then
        log_info "Disk usage: ${usage}% (OK)"
    elif [ "$usage" -lt 90 ]; then
        log_warn "Disk usage: ${usage}% (Warning)"
    else
        log_error "Disk usage: ${usage}% (Critical)"
    fi
}

# Check memory usage
check_memory() {
    echo ""
    echo "🧠 Checking memory usage..."
    
    if command -v free >/dev/null 2>&1; then
        memory_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
        log_info "Memory usage: ${memory_usage}%"
    else
        log_warn "Cannot check memory usage (free command not available)"
    fi
}

# Show container stats
show_stats() {
    echo ""
    echo "📊 Container Statistics:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        burnout-detector-frontend burnout-detector-backend burnout-detector-db 2>/dev/null || \
        log_warn "Could not retrieve container statistics"
}

# Main health check
main() {
    echo "🏥 Rootly Burnout Detector Health Check"
    echo "======================================="
    
    overall_health=true
    
    # Run all checks
    if ! check_containers; then
        overall_health=false
    fi
    
    if ! check_services; then
        overall_health=false
    fi
    
    if ! check_database; then
        overall_health=false
    fi
    
    check_disk_space
    check_memory
    show_stats
    
    echo ""
    echo "======================================="
    
    if $overall_health; then
        log_info "🎉 All systems are healthy!"
        exit 0
    else
        log_error "❌ Some systems are unhealthy!"
        echo ""
        echo "🔧 Troubleshooting commands:"
        echo "   docker-compose logs -f"
        echo "   docker-compose ps"
        echo "   docker-compose restart <service>"
        exit 1
    fi
}

# Run main function
main