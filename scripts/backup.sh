#!/usr/bin/env bash
# SQLite バックアップスクリプト
# Usage: ./scripts/backup.sh [db_path] [backup_dir]

set -euo pipefail

DB_PATH="${1:-./data/traders.db}"
BACKUP_DIR="${2:-./data/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/traders_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'"

echo "Backup created: ${BACKUP_FILE}"

# 30日以上古いバックアップを削除
find "$BACKUP_DIR" -name "traders_*.db" -mtime +30 -delete

echo "Old backups cleaned up (30+ days)."
