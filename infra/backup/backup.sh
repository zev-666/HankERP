#!/bin/sh
# HankERP PostgreSQL 自動備份（v2.1）
#
# 由 docker-compose 的 db-backup 服務執行（映像與 db 相同，pg_dump 版本一致）。
# 每 BACKUP_INTERVAL_SECONDS 秒做一次 pg_dump（custom 格式，已壓縮），
# 做完立刻用 pg_restore --list 讀一次確認檔案可讀，失敗就刪掉壞檔並以非 0 結束該輪。
# 超過 BACKUP_KEEP_DAYS 天的備份自動刪除。
#
# 環境變數：
#   PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE   連線資訊（libpq 標準變數）
#   BACKUP_DIR               預設 /backups
#   BACKUP_INTERVAL_SECONDS  預設 86400（一天）
#   BACKUP_KEEP_DAYS         預設 14
#   BACKUP_ONCE=1            只備份一次就結束（CI 與手動備份用）
#
# ⚠ 備份檔與資料庫在同一台主機，只能防「誤刪／程式寫壞資料」，防不了主機損毀。
#   正式上線請再把 BACKUP_DIR 定期複製到異地（見 DEPLOYMENT.md「資料庫備份」）。
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
DB="${PGDATABASE:-acrylic_erp}"

mkdir -p "$BACKUP_DIR"

backup_once() {
  ts="$(date +%Y%m%d_%H%M%S)"
  out="$BACKUP_DIR/${DB}_${ts}.dump"
  tmp="$out.partial"
  echo "[backup] $(date '+%Y-%m-%d %H:%M:%S') 開始備份 $DB → $out"
  if ! pg_dump --format=custom --compress=6 --no-owner --dbname="$DB" --file="$tmp"; then
    echo "[backup] ✗ pg_dump 失敗" >&2; rm -f "$tmp"; return 1
  fi
  # 驗證：備份檔要能被 pg_restore 讀出目錄，且至少含有 alembic_version 表
  if ! pg_restore --list "$tmp" | grep -q "TABLE DATA public alembic_version"; then
    echo "[backup] ✗ 備份檔驗證失敗（讀不到 alembic_version）" >&2; rm -f "$tmp"; return 1
  fi
  mv "$tmp" "$out"
  echo "[backup] ✓ 完成 $(du -h "$out" | cut -f1)"
  # 輪替：刪除超過 KEEP_DAYS 天的舊檔
  find "$BACKUP_DIR" -name "${DB}_*.dump" -type f -mtime +"$KEEP_DAYS" -print -delete \
    | sed 's/^/[backup] 刪除過期備份 /'
  return 0
}

if [ "${BACKUP_ONCE:-0}" = "1" ]; then
  backup_once
  exit $?
fi

# 等資料庫就緒
until pg_isready -q; do echo "[backup] 等待資料庫…"; sleep 5; done

while true; do
  backup_once || echo "[backup] 本輪失敗，下一輪再試" >&2
  sleep "$INTERVAL"
done
