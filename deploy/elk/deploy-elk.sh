#!/bin/bash
# ============================================================================
# ELK Stack Deployment Script for Glassdome
# ============================================================================
# 
# Run this script on 192.168.3.26 to deploy the ELK stack.
#
# Usage:
#   ./deploy-elk.sh          # Full deployment
#   ./deploy-elk.sh update   # Update/restart services
#   ./deploy-elk.sh status   # Check status
#   ./deploy-elk.sh logs     # View logs
#   ./deploy-elk.sh cleanup  # Remove everything
#
# Author: Brett Turner (ntounix)
# Created: December 2025
# ============================================================================

set -e

# Configuration
ELK_DIR="/opt/elk"
COMPOSE_FILE="docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prereqs() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "  curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed."
        exit 1
    fi
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]] && ! groups | grep -q docker; then
        log_warn "Not running as root and not in docker group."
        log_warn "You may need to run with sudo."
    fi
    
    log_success "Prerequisites check passed"
}

# Set up vm.max_map_count for Elasticsearch
setup_sysctl() {
    log_info "Configuring system settings for Elasticsearch..."
    
    # Check current value
    CURRENT_MAP_COUNT=$(sysctl -n vm.max_map_count 2>/dev/null || echo "0")
    REQUIRED_MAP_COUNT=262144
    
    if [[ "$CURRENT_MAP_COUNT" -lt "$REQUIRED_MAP_COUNT" ]]; then
        log_info "Setting vm.max_map_count to $REQUIRED_MAP_COUNT..."
        sudo sysctl -w vm.max_map_count=$REQUIRED_MAP_COUNT
        
        # Make persistent
        if ! grep -q "vm.max_map_count" /etc/sysctl.conf 2>/dev/null; then
            echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
        fi
        log_success "System settings configured"
    else
        log_success "System settings already configured (vm.max_map_count=$CURRENT_MAP_COUNT)"
    fi
}

# Deploy the ELK stack
deploy() {
    log_info "Deploying ELK Stack..."
    
    # Create directory
    sudo mkdir -p "$ELK_DIR"
    cd "$ELK_DIR"
    
    # Check if files exist (copy from script directory if not)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [[ ! -f "$ELK_DIR/docker-compose.yml" ]]; then
        log_info "Copying configuration files..."
        sudo cp -r "$SCRIPT_DIR"/* "$ELK_DIR/" 2>/dev/null || {
            log_warn "Could not copy files from $SCRIPT_DIR"
            log_info "Please copy the elk directory contents to $ELK_DIR"
        }
    fi
    
    # Set permissions
    sudo chown -R 1000:1000 "$ELK_DIR" 2>/dev/null || true
    
    # Pull latest images
    log_info "Pulling Docker images..."
    docker-compose pull
    
    # Start the stack
    log_info "Starting ELK Stack..."
    docker-compose up -d
    
    # Wait for services
    log_info "Waiting for services to start..."
    sleep 30
    
    # Check health
    check_health
    
    echo ""
    log_success "ELK Stack deployment complete!"
    echo ""
    echo "  Elasticsearch: http://$(hostname -I | awk '{print $1}'):9200"
    echo "  Kibana:        http://$(hostname -I | awk '{print $1}'):5601"
    echo "  Logstash:      TCP $(hostname -I | awk '{print $1}'):5044 (Beats)"
    echo "                 TCP $(hostname -I | awk '{print $1}'):5045 (JSON)"
    echo ""
}

# Check service health
check_health() {
    log_info "Checking service health..."
    
    # Elasticsearch
    for i in {1..30}; do
        if curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; then
            ES_STATUS=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            log_success "Elasticsearch is healthy (status: $ES_STATUS)"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_warn "Elasticsearch is not responding yet"
        fi
        sleep 2
    done
    
    # Kibana
    for i in {1..30}; do
        if curl -sf http://localhost:5601/api/status > /dev/null 2>&1; then
            log_success "Kibana is healthy"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_warn "Kibana is not responding yet (may still be starting)"
        fi
        sleep 2
    done
    
    # Logstash
    if curl -sf http://localhost:9600 > /dev/null 2>&1; then
        log_success "Logstash is healthy"
    else
        log_warn "Logstash API is not responding"
    fi
}

# Show status
status() {
    log_info "ELK Stack Status"
    echo ""
    
    cd "$ELK_DIR" 2>/dev/null || {
        log_error "ELK directory not found: $ELK_DIR"
        exit 1
    }
    
    docker-compose ps
    echo ""
    
    check_health
    
    echo ""
    log_info "Index statistics:"
    curl -s "http://localhost:9200/_cat/indices?v" 2>/dev/null || echo "  (Elasticsearch not available)"
}

# View logs
logs() {
    cd "$ELK_DIR" 2>/dev/null || {
        log_error "ELK directory not found: $ELK_DIR"
        exit 1
    }
    
    SERVICE=${2:-""}
    if [[ -n "$SERVICE" ]]; then
        docker-compose logs -f "$SERVICE"
    else
        docker-compose logs -f
    fi
}

# Update/restart services
update() {
    log_info "Updating ELK Stack..."
    
    cd "$ELK_DIR" 2>/dev/null || {
        log_error "ELK directory not found: $ELK_DIR"
        exit 1
    }
    
    docker-compose pull
    docker-compose up -d
    
    sleep 10
    check_health
    
    log_success "Update complete"
}

# Cleanup everything
cleanup() {
    log_warn "This will remove all ELK data!"
    read -p "Are you sure? (y/N): " confirm
    
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
    
    cd "$ELK_DIR" 2>/dev/null || {
        log_warn "ELK directory not found, nothing to clean"
        exit 0
    }
    
    log_info "Stopping and removing containers..."
    docker-compose down -v
    
    log_info "Removing ELK directory..."
    sudo rm -rf "$ELK_DIR"
    
    log_success "Cleanup complete"
}

# Main
case "${1:-deploy}" in
    deploy)
        check_prereqs
        setup_sysctl
        deploy
        ;;
    update)
        update
        ;;
    status)
        status
        ;;
    logs)
        logs "$@"
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {deploy|update|status|logs|cleanup}"
        exit 1
        ;;
esac

