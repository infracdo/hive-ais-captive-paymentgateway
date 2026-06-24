#!/bin/bash
# Start Apollo Captive Payment Gateway

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the application
python -m uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8080} --reload
