#!/bin/bash
set -e

echo "==========================================="
echo "  Glassdome Container Starting"
echo "==========================================="
echo "  Mode:      ${GLASSDOME_MODE}"
echo "  Worker ID: ${WORKER_ID:-default}"
echo "  Redis:     ${REDIS_URL}"
echo "  Log Level: ${LOG_LEVEL:-INFO}"
echo "==========================================="

# Create log directory
mkdir -p /app/logs

# Wait for Redis to be available
echo "[init] Waiting for Redis..."
REDIS_RETRIES=0
until python -c "import redis; r=redis.from_url('${REDIS_URL}'); r.ping()" 2>/dev/null; do
    REDIS_RETRIES=$((REDIS_RETRIES + 1))
    if [ $REDIS_RETRIES -gt 30 ]; then
        echo "[ERROR] Redis not available after 30 seconds. Exiting."
        exit 1
    fi
    sleep 1
done
echo "[init] Redis is ready!"

# Initialize logging
python -c "from glassdome.workers.logging_config import setup_worker_logging; setup_worker_logging()"

case "${GLASSDOME_MODE}" in
    "backend")
        echo "[start] Glassdome API Server on port 8000"
        exec uvicorn glassdome.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --log-level ${LOG_LEVEL:-info}
        ;;
    
    "orchestrator")
        echo "[start] Orchestrator Worker (concurrency: ${WORKER_CONCURRENCY:-4})"
        exec celery -A glassdome.workers.orchestrator worker \
            --loglevel=${LOG_LEVEL:-info} \
            --concurrency=${WORKER_CONCURRENCY:-4} \
            -Q deploy,configure,network \
            -n orchestrator@%h \
            --logfile=/app/logs/orchestrator.log
        ;;
    
    "reaper")
        echo "[start] Reaper Worker: ${WORKER_ID}"
        exec celery -A glassdome.workers.reaper worker \
            --loglevel=${LOG_LEVEL:-info} \
            --concurrency=2 \
            -Q inject,exploit \
            -n ${WORKER_ID}@%h \
            --logfile=/app/logs/reaper-${WORKER_ID}.log
        ;;
    
    "whiteknight")
        echo "[start] WhiteKnight Worker: ${WORKER_ID}"
        exec celery -A glassdome.workers.whiteknight worker \
            --loglevel=${LOG_LEVEL:-info} \
            --concurrency=2 \
            -Q validate,test \
            -n ${WORKER_ID}@%h \
            --logfile=/app/logs/whiteknight-${WORKER_ID}.log
        ;;
    
    "whitepawn")
        echo "[start] WhitePawn Monitor: ${WORKER_ID}"
        exec python -m glassdome.workers.whitepawn_monitor
        ;;
    
    *)
        echo "[ERROR] Unknown mode: ${GLASSDOME_MODE}"
        echo "Valid modes: backend, orchestrator, reaper, whiteknight, whitepawn"
        exit 1
        ;;
esac

