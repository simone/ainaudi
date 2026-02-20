#!/bin/bash
set -e

echo "Starting API service..."
exec gunicorn -b :$PORT config.wsgi_api:application --workers 2 --threads 4
