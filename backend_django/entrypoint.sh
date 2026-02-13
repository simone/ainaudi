#!/bin/bash
set -e

echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn -b :$PORT config.wsgi:application --workers 2 --threads 4
