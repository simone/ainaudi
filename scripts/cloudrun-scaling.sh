#!/bin/bash
set -e

# Cloud Run Scaling Script for AInaudi RDL System
# Usage:
#   ./scripts/cloudrun-scaling.sh evento     # Scale up for election event
#   ./scripts/cloudrun-scaling.sh normale    # Scale down to normal mode

REGION="europe-west1"  # Set your region
PROJECT_ID="your-project-id"  # Set your project ID
SERVICE_NAME="rdl-backend"

function scale_evento() {
    echo "========================================="
    echo "  SCALING TO EVENTO MODE"
    echo "========================================="
    echo ""
    echo "This will scale the backend to handle election day load:"
    echo "  - Min instances: 1 → 2"
    echo "  - Max instances: 5 → 10"
    echo "  - CPU: 1000m → 2000m (1 → 2 vCPU)"
    echo "  - Memory: 1Gi → 2Gi"
    echo "  - PostgreSQL max_connections: 100 → 200"
    echo ""
    echo "Expected capacity: ~200 concurrent RDL users"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 1
    fi

    echo ">>> Updating Cloud Run service..."
    gcloud run services update $SERVICE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --min-instances=2 \
        --max-instances=10 \
        --cpu=2 \
        --memory=2Gi \
        --update-env-vars="POSTGRES_MAX_CONNECTIONS=200,GUNICORN_WORKERS=4,GUNICORN_THREADS=4" \
        --no-cpu-throttling

    echo ""
    echo "✓ Scaled to EVENTO mode successfully"
    echo ""
    echo "Configuration:"
    echo "  - Min instances: 2 (always warm)"
    echo "  - Max instances: 10"
    echo "  - CPU per instance: 2 vCPU"
    echo "  - Memory per instance: 2Gi"
    echo "  - PostgreSQL max_connections: 200"
    echo "  - Gunicorn workers: 4 (8 threads each = 32 per instance)"
    echo ""
    echo "Total capacity:"
    echo "  - Max concurrent requests: 10 instances × 80 = 800"
    echo "  - Max database connections: 10 instances × 20 = 200 (within limit)"
    echo ""
    echo "Monitor at:"
    echo "  https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
}

function scale_normale() {
    echo "========================================="
    echo "  SCALING TO NORMALE MODE"
    echo "========================================="
    echo ""
    echo "This will scale the backend down to normal operations:"
    echo "  - Min instances: 2 → 1"
    echo "  - Max instances: 10 → 5"
    echo "  - CPU: 2000m → 1000m (2 → 1 vCPU)"
    echo "  - Memory: 2Gi → 1Gi"
    echo "  - PostgreSQL max_connections: 200 → 100"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted"
        exit 1
    fi

    echo ">>> Updating Cloud Run service..."
    gcloud run services update $SERVICE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --min-instances=1 \
        --max-instances=5 \
        --cpu=1 \
        --memory=1Gi \
        --update-env-vars="POSTGRES_MAX_CONNECTIONS=100,GUNICORN_WORKERS=2,GUNICORN_THREADS=4" \
        --no-cpu-throttling

    echo ""
    echo "✓ Scaled to NORMALE mode successfully"
    echo ""
    echo "Configuration:"
    echo "  - Min instances: 1"
    echo "  - Max instances: 5"
    echo "  - CPU per instance: 1 vCPU"
    echo "  - Memory per instance: 1Gi"
    echo "  - PostgreSQL max_connections: 100"
    echo "  - Gunicorn workers: 2 (8 threads each = 16 per instance)"
    echo ""
}

function show_current() {
    echo "========================================="
    echo "  CURRENT CONFIGURATION"
    echo "========================================="
    echo ""
    gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/minScale'],
                        spec.template.metadata.annotations['autoscaling.knative.dev/maxScale'],
                        spec.template.spec.containers[0].resources.limits.cpu,
                        spec.template.spec.containers[0].resources.limits.memory)" | \
    awk '{print "  Min instances: " $1 "\n  Max instances: " $2 "\n  CPU: " $3 "\n  Memory: " $4}'
    echo ""
}

# Main
case "${1:-}" in
    evento)
        scale_evento
        ;;
    normale)
        scale_normale
        ;;
    status)
        show_current
        ;;
    *)
        echo "Usage: $0 {evento|normale|status}"
        echo ""
        echo "Commands:"
        echo "  evento   - Scale up for election event (2-10 instances, 2 vCPU, 2Gi)"
        echo "  normale  - Scale down to normal operations (1-5 instances, 1 vCPU, 1Gi)"
        echo "  status   - Show current configuration"
        echo ""
        echo "Timeline:"
        echo "  - Run 'evento' 1 month before election day (~27 Feb for 27 Mar election)"
        echo "  - Run 'normale' 1 week after election day (~3 Apr)"
        exit 1
        ;;
esac
