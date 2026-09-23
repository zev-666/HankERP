#!/bin/sh
# HankERP PostgreSQL 還原（v2.1）
#
# 用法（在 db-backup 容器內執行，見 DEPLOYMENT.md「資料庫備份」）：
#   sh /scripts/restore.sh /backups/acrylic_erp_20260923_030000.dump <目標資料庫> --yes
#
# 會「清掉目標資料庫中既有的物件再還原」（pg_restore --clean --if-exists）。
# 為避免誤操作，必須明確帶 --yes。還原到正式庫之前，建議先還原到一個新的資料庫
# （例如 acrylic_restore_check）確認內容正確，再決定是否覆蓋正式庫。
set -eu

FILE="${1:-}"
TARGET="${2:-}"
CONFIRM="${3:-}"

if [ -z "$FILE" ] || [ -z "$TARGET" ]; then
  echo "用法：sh restore.sh <備份檔.dump> <目標資料庫> --yes" >&2; exit 2
fi
if [ ! -f "$FILE" ]; then
  echo "找不到備份檔：$FILE" >&2; exit 2
fi
if [ "$CONFIRM" != "--yes" ]; then
  echo "這會覆蓋資料庫「$TARGET」的內容。確認無誤請在最後加上 --yes" >&2; exit 3
fi

# 目標資料庫不存在就建立
if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$TARGET'" | grep -q 1; then
  echo "[restore] 建立資料庫 $TARGET"
  createdb "$TARGET"
fi

echo "[restore] $FILE → $TARGET"
pg_restore --clean --if-exists --no-owner --exit-on-error --dbname="$TARGET" "$FILE"
echo "[restore] ✓ 完成。alembic 版本：$(psql -d "$TARGET" -tAc 'SELECT version_num FROM alembic_version')"
