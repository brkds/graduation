#!/usr/bin/env bash
set -u

DB="${1:-/home/zwy/project2721707-302151/8_8.db}"
TARGET="${2:-/home/zwy/project2721707-302151/testdata/linux_full/linux-6.6/<scratch space>}"
BATCH_SIZE="${BATCH_SIZE:-5000}"
TIMEOUT_MS="${TIMEOUT_MS:-120000}"
RETRY_DELAY="${RETRY_DELAY:-1}"
# 0 表示无限次重试；>0 表示达到该上限后退出
MAX_LOCK_RETRIES="${MAX_LOCK_RETRIES:-0}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 not found"
  exit 1
fi
if [ ! -f "$DB" ]; then
  echo "DB not found: $DB"
  exit 1
fi

echo "DB=$DB"
echo "TARGET=$TARGET"
echo "BATCH_SIZE=$BATCH_SIZE TIMEOUT_MS=$TIMEOUT_MS MAX_LOCK_RETRIES=$MAX_LOCK_RETRIES"

# 统计信息
LOCK_FAILURES=0
ATTEMPTS=0
START_TS=$(date +%s)

remaining=$(sqlite3 -batch -noheader "$DB" ".timeout $TIMEOUT_MS" \
  "SELECT COUNT(*) FROM CallRelations WHERE call_site_file_path = '$TARGET';" 2>/dev/null || true)
echo "initial_remaining=${remaining:-unknown}"

while :; do
  ATTEMPTS=$((ATTEMPTS+1))
  OUT=$(sqlite3 -batch -noheader "$DB" \
    ".timeout $TIMEOUT_MS" \
    "PRAGMA foreign_keys=ON;" \
    "BEGIN IMMEDIATE;" \
    "DELETE FROM CallRelations WHERE id IN (SELECT id FROM CallRelations WHERE call_site_file_path = '$TARGET' LIMIT $BATCH_SIZE);" \
    "SELECT changes();" \
    "COMMIT;" 2>&1)
  RC=$?
  if [ $RC -ne 0 ]; then
    if echo "$OUT" | grep -qi "database is locked"; then
      LOCK_FAILURES=$((LOCK_FAILURES+1))
      echo "locked (failure #$LOCK_FAILURES), retrying in ${RETRY_DELAY}s..."
      if [ "$MAX_LOCK_RETRIES" -gt 0 ] && [ "$LOCK_FAILURES" -ge "$MAX_LOCK_RETRIES" ]; then
        echo "reached MAX_LOCK_RETRIES=$MAX_LOCK_RETRIES, aborting."
        END_TS=$(date +%s)
        echo "attempts=$ATTEMPTS lock_failures=$LOCK_FAILURES elapsed=$((END_TS-START_TS))s"
        exit 2
      fi
      sleep "$RETRY_DELAY"
      continue
    else
      echo "sqlite3 error: $OUT"
      exit 1
    fi
  fi

  deleted="${OUT:-0}"
  remaining=$(sqlite3 -batch -noheader "$DB" ".timeout $TIMEOUT_MS" \
    "SELECT COUNT(*) FROM CallRelations WHERE call_site_file_path = '$TARGET';" 2>/dev/null || true)
  echo "deleted=$deleted remaining=${remaining:-unknown}"

  [ "$deleted" = "0" ] && break
done

END_TS=$(date +%s)
echo "done. attempts=$ATTEMPTS lock_failures=$LOCK_FAILURES elapsed=$((END_TS-START_TS))s"