#!/bin/bash
# ============================================================================
# Glassdome Worker Fleet Startup
# ============================================================================
# Starts Redis + Celery workers for distributed task processing
#
# Usage:
#   ./scripts/start_workers.sh          # Start all workers
#   ./scripts/start_workers.sh status   # Check worker status
#   ./scripts/start_workers.sh stop     # Stop all workers
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV="$PROJECT_DIR/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# ============================================================================
# Functions
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Glassdome Worker Fleet                           ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_redis() {
    if docker ps | grep -q glassdome-redis; then
        echo -e "${GREEN}✓${NC} Redis is running"
        return 0
    else
        echo -e "${YELLOW}○${NC} Redis not running, starting..."
        cd "$PROJECT_DIR"
        docker compose -f docker-compose.minimal.yml up -d redis 2>/dev/null || \
        docker run -d --name glassdome-redis -p 6379:6379 redis:7-alpine
        sleep 2
        echo -e "${GREEN}✓${NC} Redis started"
        return 0
    fi
}

start_worker() {
    local name=$1
    local module=$2
    local queues=$3
    local concurrency=${4:-4}
    
    # Check if already running
    if pgrep -f "celery.*-n ${name}@" > /dev/null; then
        echo -e "${YELLOW}○${NC} $name already running"
        return 0
    fi
    
    echo -e "${BLUE}→${NC} Starting $name (concurrency=$concurrency, queues=$queues)"
    
    cd "$PROJECT_DIR"
    source "$VENV/bin/activate"
    
    celery -A "glassdome.workers.$module" worker \
        --loglevel=info \
        --concurrency="$concurrency" \
        -Q "$queues" \
        -n "${name}@%h" \
        --logfile="$LOG_DIR/${name}.log" \
        --pidfile="$LOG_DIR/${name}.pid" \
        --detach
    
    sleep 1
    
    if pgrep -f "celery.*-n ${name}@" > /dev/null; then
        echo -e "${GREEN}✓${NC} $name started"
    else
        echo -e "${RED}✗${NC} $name failed to start - check $LOG_DIR/${name}.log"
    fi
}

stop_workers() {
    echo -e "${YELLOW}Stopping all Celery workers...${NC}"
    
    # Kill by PID files
    for pidfile in "$LOG_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo -e "${GREEN}✓${NC} Stopped $(basename "$pidfile" .pid)"
            fi
            rm -f "$pidfile"
        fi
    done
    
    # Kill any remaining celery processes
    pkill -f "celery.*glassdome" 2>/dev/null || true
    
    echo -e "${GREEN}All workers stopped${NC}"
}

show_status() {
    echo ""
    echo -e "${BLUE}=== Redis ===${NC}"
    if docker ps | grep -q glassdome-redis; then
        echo -e "${GREEN}✓${NC} Redis container running"
        docker exec glassdome-redis redis-cli ping 2>/dev/null || echo "  (not responding)"
    else
        echo -e "${RED}✗${NC} Redis not running"
    fi
    
    echo ""
    echo -e "${BLUE}=== Celery Workers ===${NC}"
    
    cd "$PROJECT_DIR"
    source "$VENV/bin/activate"
    
    # Try to ping workers
    celery -A glassdome.workers.celery_app inspect ping 2>/dev/null || echo "No workers responding"
    
    echo ""
    echo -e "${BLUE}=== Worker Processes ===${NC}"
    ps aux | grep "[c]elery.*glassdome" | awk '{print "  " $11, $12, $13, $14}' || echo "  No processes found"
    
    echo ""
    echo -e "${BLUE}=== Log Files ===${NC}"
    ls -la "$LOG_DIR"/*.log 2>/dev/null | awk '{print "  " $9, $5}' || echo "  No logs yet"
}

# ============================================================================
# Main
# ============================================================================

print_header

case "${1:-start}" in
    start)
        echo -e "${BLUE}Starting Glassdome Worker Fleet...${NC}"
        echo ""
        
        # 1. Start Redis
        check_redis
        echo ""
        
        # 2. Start Orchestrator (handles lab deployments)
        start_worker "orchestrator" "orchestrator" "deploy,configure,network" 8
        
        # 3. Start Reaper workers (vulnerability injection)
        start_worker "reaper-1" "reaper" "inject,exploit" 4
        start_worker "reaper-2" "reaper" "inject,exploit" 4
        
        # 4. Start WhiteKnight (validation)
        start_worker "whiteknight-1" "whiteknight" "validate,test" 4
        
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Worker Fleet Started!${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "  Orchestrator:  8 concurrent tasks (deploy, configure, network)"
        echo "  Reaper x2:     8 concurrent tasks (inject, exploit)"
        echo "  WhiteKnight:   4 concurrent tasks (validate, test)"
        echo ""
        echo "  Total capacity: 20 parallel tasks"
        echo ""
        echo "  Logs: $LOG_DIR/"
        echo "  Status: ./scripts/start_workers.sh status"
        echo "  Stop:   ./scripts/start_workers.sh stop"
        echo ""
        ;;
        
    stop)
        stop_workers
        ;;
        
    status)
        show_status
        ;;
        
    restart)
        stop_workers
        sleep 2
        exec "$0" start
        ;;
        
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac

