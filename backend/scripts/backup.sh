#!/usr/bin/env bash
# Бэкап продовой БД (pg_dump из контейнера db, сжатый) + ротация.
#
# Cron (ежедневно в 3:00):
#   0 3 * * * /path/to/backend/scripts/backup.sh >> /var/log/sfedu-backup.log 2>&1
#
# Восстановление:
#   gunzip -c FILE.sql.gz | docker compose -f docker-compose.prod.yml exec -T db \
#     psql -U sfedu -d sfedu_econ
set -euo pipefail

COMPOSE="$(cd "$(dirname "$0")/.." && pwd)/docker-compose.prod.yml"
DIR="${BACKUP_DIR:-/var/backups/sfedu-econ}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

mkdir -p "$DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$DIR/sfedu_econ-$STAMP.sql.gz"

docker compose -f "$COMPOSE" exec -T db pg_dump -U sfedu sfedu_econ | gzip >"$FILE"
echo "backup: $FILE ($(du -h "$FILE" | cut -f1))"

# Ротация: старше KEEP_DAYS удаляем
find "$DIR" -name 'sfedu_econ-*.sql.gz' -mtime "+$KEEP_DAYS" -delete
