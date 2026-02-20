#!/bin/bash
set -e

echo "Starting AI Assistant service..."
exec gunicorn -b :$PORT config.wsgi_ai:application --workers 2 --threads 2 --timeout 60
