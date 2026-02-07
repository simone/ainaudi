#!/bin/bash
set -e

echo "=== AInaudi Cloud Run Entrypoint ==="

# Environment variables
export PGDATA=/var/lib/postgresql/data
export POSTGRES_DB=${DB_NAME:-rdl_referendum}
export POSTGRES_USER=${DB_USER:-postgres}
export POSTGRES_PASSWORD=${DB_PASSWORD}
export POSTGRES_MAX_CONNECTIONS=${POSTGRES_MAX_CONNECTIONS:-100}

# =============================================================================
# Step 1: Initialize PostgreSQL if not initialized
# =============================================================================
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo ">>> Initializing PostgreSQL database..."
    gosu postgres initdb -D "$PGDATA" --encoding=UTF8 --locale=en_US.UTF-8

    # Configure PostgreSQL
    echo ">>> Configuring PostgreSQL..."
    cat >> "$PGDATA/postgresql.conf" <<EOF
# Connection settings
max_connections = ${POSTGRES_MAX_CONNECTIONS}
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 2621kB

# WAL settings
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9

# Query planner
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200

# Logging (minimal for Cloud Run)
logging_collector = off
log_destination = 'stderr'
log_line_prefix = '%m [%p] '
log_timezone = 'UTC'

# Network
listen_addresses = 'localhost'
port = 5432
EOF

    # Configure authentication (trust localhost for simplicity)
    cat >> "$PGDATA/pg_hba.conf" <<EOF
# Trust local connections (PostgreSQL and Django in same container)
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF

    # Start PostgreSQL temporarily to create user and database
    echo ">>> Creating database and user..."
    gosu postgres pg_ctl -D "$PGDATA" start -w -o "-c listen_addresses='localhost'"

    gosu postgres psql -v ON_ERROR_STOP=1 <<-EOSQL
        CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}' SUPERUSER;
        CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};
EOSQL

    gosu postgres pg_ctl -D "$PGDATA" stop -w
    echo ">>> PostgreSQL initialization complete"
else
    echo ">>> PostgreSQL already initialized"
fi

# =============================================================================
# Step 2: Start PostgreSQL in background
# =============================================================================
echo ">>> Starting PostgreSQL..."
gosu postgres pg_ctl -D "$PGDATA" -l /tmp/postgres.log start -w

# Wait for PostgreSQL to be ready
echo ">>> Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if gosu postgres pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo ">>> PostgreSQL is ready"
        break
    fi
    echo "    Attempt $i/30..."
    sleep 1
done

if ! gosu postgres pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL failed to start within 30 seconds"
    cat /tmp/postgres.log
    exit 1
fi

# =============================================================================
# Step 3: Run Django migrations
# =============================================================================
echo ">>> Running Django migrations..."
python manage.py migrate --noinput

# =============================================================================
# Step 4: Collect static files
# =============================================================================
echo ">>> Collecting static files..."
python manage.py collectstatic --noinput --clear || true

# =============================================================================
# Step 5: Start Gunicorn
# =============================================================================
echo ">>> Starting Gunicorn..."
echo "    Workers: ${GUNICORN_WORKERS:-2}"
echo "    Threads: ${GUNICORN_THREADS:-4}"
echo "    Timeout: 60s"

exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application
