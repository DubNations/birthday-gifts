#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/birthday-gifts/backups}"
DATABASE_URL="${DATABASE_URL:-sqlite:///./gift.db}"
mkdir -p "$BACKUP_DIR"

if [[ "$DATABASE_URL" != sqlite:* ]]; then
  echo "backup_sqlite.sh only handles SQLite DATABASE_URL values" >&2
  exit 1
fi

DB_PATH="${DATABASE_URL#sqlite:///}"
if [[ "$DB_PATH" = "$DATABASE_URL" ]]; then
  echo "Unsupported SQLite DATABASE_URL format: $DATABASE_URL" >&2
  exit 1
fi

if [[ "$DB_PATH" != /* ]]; then
  DB_PATH="$(pwd)/$DB_PATH"
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "SQLite database not found: $DB_PATH" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "$DB_PATH" "$BACKUP_DIR/gift_$STAMP.db"
find "$BACKUP_DIR" -name 'gift_*.db' -type f -mtime +30 -delete
