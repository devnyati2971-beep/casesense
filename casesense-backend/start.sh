#!/bin/bash

# Start the background worker (Arq) in the background
echo "Starting background worker..."
arq worker.worker_settings.WorkerSettings &

# Start the FastAPI web server in the foreground
echo "Starting web server..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
