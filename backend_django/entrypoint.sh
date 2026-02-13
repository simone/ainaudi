#!/bin/bash
set -e

echo "Starting Gunicorn..."
exec gunicorn -b :$PORT config.wsgi:application --workers 2 --threads 4
