#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# 永陛 & 進化 EVEREVO — 新主機一鍵安裝（v2.3.9）
#
# 在一台全新的 Ubuntu 24.04（AWS Lightsail、Google Cloud、Linode 等皆可，4GB 記憶體、硬碟 25GB 以上）
# 上，從零裝好整套系統，
# 並把舊主機匯出的資料庫還原進來。直接用正式版設定（docker-compose.prod.yml）：
# 不對外開任何 port、主機重開機後所有服務自動啟動。
#
# 用法（登入新主機後；一般帳號或 root 都可以）：
#   curl -fsSL https://raw.githubusercontent.com/zev-666/HankERP/main/infra/setup_new_host.sh -o setup_new_host.sh
#   bash setup_new_host.sh ~/hankerp-final.dump
#
# 做的事（每一步失敗就停下，修好後可以整支重跑，已完成的步驟會跳過）：
#   1. 檢查環境   2. 建 2GB 虛擬記憶體   3. 安裝 Docker   4. 下載程式
#   5. 產生 .env（密鑰隨機產生、不顯示）  6. 建置並啟動資料庫
#   7. 還原資料庫（只在資料庫是空的時候）  8. 啟動網站、同步角色權限
#   9. 驗證
#
# 這時網站已經在主機裡跑起來，但外面還連不到——要等 Cloudflare Tunnel 建好後，
# 再執行 bash ~/HankERP/infra/deploy_prod.sh 貼上 token，才會從 https://everevo.com.tw 上線。
#
# 不會印出任何密碼或密鑰。
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

DOMAIN="everevo.com.tw"
SITE="https://$DOMAIN"
API="https://api.$DOMAIN"
REPO="https://github.com/zev-666/HankERP.git"
APP_DIR="$HOME/HankERP"
DUMP="${1:-}"

ok()   { echo "  ✓ $*"; }
warn() { echo "  ⚠ $*"; }
die()  { echo "  ✗ $*"; echo; echo "已停止。把上面整段輸出貼給 Claude；修好後可以整支重跑。"; exit 1; }
step() { echo; echo "=================================================================="; echo " $*"; echo "=================================================================="; }

step "1. 檢查環境"
ME=$(id -un)
if [ "$(id -u)" = "0" ]; then
  # Linode／Vultr 等預設用 root 登入；用 root 執行也可以，程式會裝在 /root/HankERP
  command -v sudo >/dev/null || { apt-get update -qq && apt-get install -y -qq sudo >/dev/null; } || die "安裝 sudo 失敗"
  warn "目前用 root 執行，程式會放在 $HOME/HankERP"
else
  sudo -n true 2>/dev/null || sudo -v || die "這個帳號（$ME）沒有 sudo 權限"
fi
ok "執行帳號：$ME"
. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || die "這支腳本只支援 Ubuntu（目前是 ${PRETTY_NAME:-未知}）"
ok "作業系統：$PRETTY_NAME"
MEM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
[ "$MEM_MB" -ge 3500 ] && ok "記憶體 ${MEM_MB}MB" || warn "記憶體只有 ${MEM_MB}MB，建議 4GB 以上（前端建置會很吃記憶體）"
FREE_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
[ "$FREE_GB" -ge 15 ] || die "硬碟剩 ${FREE_GB}GB，至少要 15GB"
ok "硬碟可用 ${FREE_GB}GB"
[ -n "$DUMP" ] || die "要指定舊主機匯出的資料庫檔，例如：bash setup_new_host.sh ~/hankerp-final.dump"
[ -f "$DUMP" ] || die "找不到資料庫檔 $DUMP（先用 scp 從你的電腦傳上來）"
[ "$(head -c 5 "$DUMP")" = "PGDMP" ] || die "$DUMP 不是 pg_dump 的匯出檔（開頭不是 PGDMP）"
DUMP=$(readlink -f "$DUMP")
ok "資料庫檔：$DUMP（$(stat -c %s "$DUMP") bytes）"

step "2. 虛擬記憶體（swap）"
if swapon --show --noheadings | grep -q .; then
  ok "已經有 swap：$(swapon --show --noheadings --bytes | awk '{s+=$3} END{print int(s/1048576)}')MB"
else
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null \
    && sudo swapon /swapfile || die "建立 swap 失敗"
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  ok "已建立 2GB swap（重開機後自動掛上）"
fi

step "3. 安裝 Docker"
if command -v docker >/dev/null 2>&1 && sudo docker compose version >/dev/null 2>&1; then
  ok "已安裝：$(sudo docker --version)"
else
  # Docker 官方文件的 apt 安裝方式：https://docs.docker.com/engine/install/ubuntu/
  sudo apt-get update -qq || die "apt-get update 失敗"
  sudo apt-get install -y -qq ca-certificates curl git >/dev/null || die "安裝 curl/git 失敗"
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc || die "下載 Docker 金鑰失敗"
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq || die "apt-get update（Docker 套件庫）失敗"
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null \
    || die "安裝 Docker 失敗"
  sudo systemctl enable --now docker >/dev/null 2>&1
  [ "$ME" = "root" ] || sudo usermod -aG docker "$ME"
  ok "已安裝：$(sudo docker --version)（下次登入起不用 sudo 也能用 docker）"
fi
DC="sudo docker compose"

step "4. 下載程式"
command -v git >/dev/null || sudo apt-get install -y -qq git >/dev/null || die "安裝 git 失敗"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull -q --ff-only origin main || die "git pull 失敗（$APP_DIR 有本地修改？）"
  ok "已更新到 $(git -C "$APP_DIR" log -1 --format='%h %s' | cut -c1-70)"
else
  git clone -q "$REPO" "$APP_DIR" || die "git clone 失敗"
  ok "已下載 $(git -C "$APP_DIR" log -1 --format='%h %s' | cut -c1-70)"
fi
cd "$APP_DIR" || die "找不到 $APP_DIR"
[ -f docker-compose.prod.yml ] || die "程式版本太舊，沒有 docker-compose.prod.yml"

step "5. 設定檔 .env（密鑰隨機產生，不顯示）"
rand() { openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | cut -c1-"$1"; }
if [ -f .env ]; then
  ok ".env 已存在，沿用（不重新產生密鑰，否則會連不上已建立的資料庫）"
else
  umask 077
  cat > .env <<EOF
# 由 infra/setup_new_host.sh 於 $(date '+%Y-%m-%d %H:%M') 產生。密鑰為隨機值，請勿外流。
COMPOSE_FILE=docker-compose.prod.yml
ENVIRONMENT=production
SECRET_KEY=$(rand 48)
DB_PASSWORD=$(rand 32)
SEED_ADMIN_PASSWORD=$(rand 24)
CORS_ORIGINS=$SITE,https://www.$DOMAIN
NEXT_PUBLIC_API_URL=$API
NEXT_PUBLIC_SITE_URL=$SITE
# Cloudflare Tunnel 建好後，由 infra/deploy_prod.sh 詢問並寫入
TUNNEL_TOKEN=PENDING
EOF
  umask 022
  ok "已產生 .env（權限 600，只有 $ME 讀得到）"
fi
grep -q '^COMPOSE_FILE=docker-compose.prod.yml' .env || die ".env 沒有 COMPOSE_FILE=docker-compose.prod.yml"
$DC config --services 2>/dev/null | grep -qx cloudflared || die "docker compose 沒有讀到正式版設定（COMPOSE_FILE 沒生效）"
ok "docker compose 使用 docker-compose.prod.yml"

step "6. 建置映像檔並啟動資料庫（前端建置約 3～6 分鐘）"
$DC build || die "建置失敗"
$DC up -d db redis || die "啟動資料庫失敗"
echo -n "  等待資料庫就緒"
for _ in $(seq 1 40); do $DC exec -T db pg_isready -U erp_user -d acrylic_erp >/dev/null 2>&1 && break; echo -n "."; sleep 3; done; echo
$DC exec -T db pg_isready -U erp_user -d acrylic_erp >/dev/null 2>&1 || die "資料庫 2 分鐘內沒有就緒：$DC logs db --tail 30"
ok "資料庫就緒"

step "7. 還原資料庫"
PSQL="$DC exec -T db psql -U erp_user -d acrylic_erp -tAc"
TABLES=$($PSQL "select count(*) from information_schema.tables where table_schema='public'" | tr -dc '0-9')
if [ "${TABLES:-0}" -gt 0 ]; then
  ok "資料庫已經有 $TABLES 張表，跳過還原（避免覆蓋新主機上的資料）"
else
  $DC cp "$DUMP" db:/tmp/restore.dump || die "把資料庫檔複製進容器失敗"
  $DC exec -T db pg_restore -U erp_user -d acrylic_erp --no-owner --exit-on-error /tmp/restore.dump \
    || die "還原失敗（資料庫可能只還原了一半：把輸出貼給 Claude，不要直接重跑）"
  $DC exec -T db rm -f /tmp/restore.dump
  ok "還原完成"
fi
echo "  資料表：$($PSQL "select count(*) from information_schema.tables where table_schema='public'")"
echo "  資料庫版本：$($PSQL 'select version_num from alembic_version')"
echo "  帳號：$($PSQL 'select count(*) from users') 個；客戶：$($PSQL 'select count(*) from customers') 筆；工單：$($PSQL 'select count(*) from work_orders') 筆"

step "8. 啟動網站、更新資料庫結構、同步角色權限"
# cloudflared 這時不啟動：要等 Cloudflare Tunnel 建好、拿到 token
$DC up -d backend celery frontend db-backup || die "啟動失敗"
in_backend() { $DC exec -T backend python -c "import sys,urllib.request as u
try: r=u.urlopen('http://localhost:8000'+sys.argv[1],timeout=3); print(r.status)
except Exception as e: print(getattr(e,'code','ERR'))" "$1" 2>/dev/null; }
echo -n "  等待後端就緒"
for _ in $(seq 1 60); do [ "$(in_backend /health)" = "200" ] && break; echo -n "."; sleep 3; done; echo
[ "$(in_backend /health)" = "200" ] || die "後端 3 分鐘內沒有就緒：$DC logs backend --tail 50"
$DC exec -T backend alembic upgrade head || die "alembic upgrade 失敗"
$DC exec -T backend python scripts/seed_data.py || die "seed_data 失敗"

step "9. 驗證"
[ "$(in_backend /api/v1/customers)" = "401" ] && ok "未登入呼叫業務 API → 401" || warn "業務 API 沒有回 401"
[ "$(in_backend /docs)" = "404" ] && ok "/docs 已關閉（正式模式）" || warn "/docs 沒有關閉"
W=$($DC exec -T frontend wget -q -O /dev/null -S http://localhost:3000/login 2>&1 | awk '/HTTP\//{print $2}' | tail -1)
[ "$W" = "200" ] && ok "前端登入頁（主機內）→ 200" || warn "前端登入頁回 $W"
$DC exec -T frontend sh -c "grep -rlF '$API' .next 2>/dev/null | head -1" | grep -q . \
  && ok "前端已編入 API 網址 $API" || warn "前端程式碼裡找不到 $API"
LISTEN=$(ss -ltnH 2>/dev/null | awk '{print $4}' | grep -E ':(3000|8000|5432|6379)$' || true)
[ -z "$LISTEN" ] && ok "主機沒有對外開 3000／8000／5432／6379" || warn "主機仍在監聽：$LISTEN"
echo "  容器："
$DC ps --format '{{.Service}}\t{{.Status}}' | sed 's/^/    /'

echo
echo "=================================================================="
echo " 新主機安裝完成：$(git log -1 --format='%h')"
echo "   網站已經在主機裡運作，但外面還連不到（刻意的：不開任何 port）。"
echo "   下一步：Cloudflare Tunnel 建好之後執行"
echo "     bash ~/HankERP/infra/deploy_prod.sh"
echo "   貼上 token，https://$DOMAIN 就會上線。"
echo "   把這整段輸出貼給 Claude"
echo "=================================================================="
