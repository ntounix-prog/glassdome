#!/bin/bash

echo "========================================================================"
echo "🧠 GLASSDOME OVERSEER - STARTING SERVICE"
echo "========================================================================"
echo "Starting autonomous entity with FastAPI wrapper..."
echo ""

# Run Overseer service with uvicorn
exec uvicorn glassdome.overseer.service:app --host 0.0.0.0 --port 8001

