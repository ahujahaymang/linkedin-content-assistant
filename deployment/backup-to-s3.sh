#!/bin/bash
set -e

# Configuration
APP_DIR="/opt/content-assistant"
BACKUP_DIR="/tmp/content-assistant-backups"
S3_BUCKET="s3://content-assistant-backups-601084425795"
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="content-assistant-backup-$DATE.tar.gz"

echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup: $BACKUP_NAME"
tar -czf "$BACKUP_DIR/$BACKUP_NAME" \
    -C "$APP_DIR" \
    data \
    profiles \
    config \
    logs

# Upload to S3
echo "Uploading to S3: $S3_BUCKET/$BACKUP_NAME"
aws s3 cp "$BACKUP_DIR/$BACKUP_NAME" "$S3_BUCKET/$BACKUP_NAME"

# Remove local backup
rm -f "$BACKUP_DIR/$BACKUP_NAME"

# Keep only last 30 days of backups in S3
echo "Cleaning old backups (keeping last 30 days)..."
aws s3 ls "$S3_BUCKET/" | \
    awk '{print $4}' | \
    grep "content-assistant-backup-" | \
    sort -r | \
    tail -n +31 | \
    while read file; do
        echo "Deleting old backup: $file"
        aws s3 rm "$S3_BUCKET/$file"
    done

echo "Backup completed at $(date)"
