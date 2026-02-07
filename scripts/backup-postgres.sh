#!/bin/bash
set -e

# PostgreSQL Backup Script for Cloud Run
# Triggers the Cloud Run Job for backing up PostgreSQL

REGION="europe-west1"
PROJECT_ID="your-project-id"
JOB_NAME="postgres-backup"

echo "========================================="
echo "  POSTGRESQL BACKUP"
echo "========================================="
echo ""
echo "This will trigger a PostgreSQL backup job."
echo ""
echo "Backup details:"
echo "  - Source: PostgreSQL in rdl-backend container"
echo "  - Destination: gs://rdl-backups-prod/"
echo "  - Retention: 30 days"
echo "  - Format: SQL dump (gzipped)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

echo ">>> Executing backup job..."
gcloud run jobs execute $JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --wait

echo ""
echo "✓ Backup completed successfully"
echo ""
echo "View logs:"
echo "  gcloud run jobs executions logs read --region=$REGION --job=$JOB_NAME"
echo ""
echo "List backups:"
echo "  gsutil ls gs://rdl-backups-prod/"
echo ""
