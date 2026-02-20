#!/bin/bash
set -e

echo "Starting RDL service (scrutinio + risorse)..."
exec gunicorn -b :$PORT config.wsgi_rdl:application --workers 4 --threads 4
