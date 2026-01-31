# Dockerfile for Django backend - Production with Distroless
# Multi-stage build for minimal attack surface

# =============================================================================
# Stage 1: Builder - Install all dependencies
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Collector - Prepare application
# =============================================================================
FROM python:3.11-slim-bookworm AS collector

WORKDIR /app

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings 2>/dev/null || true

# Remove unnecessary files
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN find /app -type f -name "*.pyc" -delete 2>/dev/null || true
RUN rm -rf /app/.git /app/tests /app/*.md 2>/dev/null || true


# =============================================================================
# Stage 3: Runtime - Distroless Python
# =============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application from collector
COPY --from=collector /app /app

# Copy required shared libraries for psycopg2
# These are needed because distroless doesn't include them
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpq.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libgssapi_krb5.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libldap*.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/liblber*.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libkrb5.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libk5crypto.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libkrb5support.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libsasl2.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libkeyutils.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libcom_err.so* /usr/lib/x86_64-linux-gnu/

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Health check endpoint (via curl not available in distroless)
# Use Docker's HEALTHCHECK with python instead
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"

# Run with gunicorn
# Note: Using python -m to ensure we use the venv's gunicorn
ENTRYPOINT ["python", "-m", "gunicorn"]
CMD ["--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
