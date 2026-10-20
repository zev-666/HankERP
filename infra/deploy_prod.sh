#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# 永陛 & 進化 EVEREVO 正式站部署腳本（v2.3.5 起：Cloudflare Tunnel 模式）
#
# 用法（Windows PowerShell，repo 目錄下）：
#   scp infra/deploy_prod.sh ubuntu@43.156.110.76:deploy_prod.sh
#   ssh -t ubuntu@43.156.110.76 bash deploy_prod.sh
#
# 第一次跑會把正式站從「IP:3000／:8000」切換到「https://everevo.com.tw 走 Tunnel」；
# 之後每次跑就是一般的更新部署（同一支腳本，可重複執行）。
#
# 不會印出任何密碼或 token。TUNNEL_TOKEN 若 .env 還沒有，會請你貼上（輸入不顯示）。
# 部署前會停下來等你輸入 yes；改 .env 前先備份；更新程式前先備份資料庫。
# 取代舊的 repo 根目錄 deploy_prod.sh（那支把 IP 寫死，切到 Tunnel 後不可再用）。
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

DOMAIN="everevo.com.tw"
SITE="https://$DOMAIN"
# API 用獨立子網域（v2.3.7）：Cloudflare 後台的路由表單不保證有「路徑」欄位，
# 一個網址對一個服務最穩。瀏覽器從 everevo.com.tw 呼叫 api.everevo.com.tw，靠 CORS 放行。
API="https://api.$DOMAIN"
CORS="https://$DOMAIN,https://www.$DOMAIN"
APP_DIR="$HOME/HankERP"
PROD_FILE="docker-compose.prod.yml"

ok()   { echo "  ✓ $*"; }
warn() { echo "  ⚠ $*"; }
die()  { echo "  ✗ $*"; echo; echo "已中止。把上面整段輸出貼給 Claude。"; exit 1; }
getkv() { sed -n "s/^$1=//p" .env | tail -1; }
setkv() {
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env
  else printf '%s=%s\n' "$1" "$2" >> .env; fi
}

cd "$APP_DIR" || die "找不到 $APP_DIR"
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else die "需要 Docker Compose v2（docker compose）"; fi
if ! docker info >/dev/null 2>&1; then DC="sudo $DC"; fi
[ -f .env ] || die "找不到 .env"
sed -i 's/\r$//' .env

echo "=================================================================="
echo " 1. 現況（只讀，不改任何東西）"
echo "=================================================================="
OLD_HEAD=$(git rev-parse --short HEAD)
echo "  主機目前版本：$(git log -1 --format='%h %s' | cut -c1-90)"
git fetch -q origin main || die "git fetch 失敗（主機連不到 GitHub？）"
echo "  GitHub 最新：  $(git log -1 --format='%h %s' origin/main | cut -c1-90)"
BEHIND=$(git rev-list --count HEAD..origin/main)
echo "  落後 GitHub $BEHIND 個 commit"
DIRTY=$(git status --porcelain --untracked-files=no)
if [ -n "$DIRTY" ]; then
  echo "$DIRTY" | sed 's/^/    /'
  die "主機上的程式碼被直接改過。為了不蓋掉這些修改，先停在這裡。"
fi
ok "主機程式碼沒有本地修改"
MODE="開發版 compose（IP:port 對外）"
[ "$(getkv COMPOSE_FILE)" = "$PROD_FILE" ] && MODE="正式版 compose（Tunnel）"
echo "  目前模式：$MODE"
echo "  容器："
$DC ps --format '{{.Service}}\t{{.Status}}' 2>/dev/null | sed 's/^/    /'
echo "  .env 內的設定名稱：$(sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' .env | tr '\n' ' ')"
grep -E '^(NEXT_PUBLIC_API_URL|NEXT_PUBLIC_SITE_URL|CORS_ORIGINS|ENVIRONMENT|COMPOSE_FILE)=' .env | sed 's/^/    /'
grep -q '^SECRET_KEY=.\{32,\}' .env || die ".env 的 SECRET_KEY 不存在或少於 32 字元（正式模式會拒絕啟動）"
ok "SECRET_KEY 存在且長度足夠（不顯示）"
grep -q '^SEED_ADMIN_PASSWORD=.\+' .env || die ".env 沒有 SEED_ADMIN_PASSWORD"
ok "SEED_ADMIN_PASSWORD 存在（不顯示）"
grep -q '^DB_PASSWORD=.\+' .env && ok "DB_PASSWORD 有設定（不顯示，不會變動）" \
  || ok "DB_PASSWORD 沒設定，沿用 compose 預設值（不會變動；改了會連不上既有資料庫）"
# PENDING 是 infra/setup_new_host.sh 寫入的佔位值（新主機裝好、Tunnel 還沒建）
if grep -q '^TUNNEL_TOKEN=.\+' .env && [ "$(getkv TUNNEL_TOKEN)" != "PENDING" ]; then ok "TUNNEL_TOKEN 存在（不顯示）"; NEED_TOKEN=0
else warn "TUNNEL_TOKEN 還沒設定，等一下會請你貼上"; NEED_TOKEN=1; fi

CF_UP=$($DC ps --status running --services 2>/dev/null | grep -cx cloudflared || true)
if [ "$BEHIND" = "0" ] && [ "$(getkv COMPOSE_FILE)" = "$PROD_FILE" ] && [ "$NEED_TOKEN" = "0" ] && [ "$CF_UP" = "1" ]; then
  echo; ok "已是最新版且已是 Tunnel 模式，不需要部署。"; exit 0
fi

echo
read -r -p "確認以上無誤，開始部署？輸入 yes 繼續，其他任何輸入都會取消：" ANS
[ "$ANS" = "yes" ] || { echo "已取消，沒有做任何變更。"; exit 0; }

TS=$(date +%Y%m%d-%H%M%S)
echo
echo "=================================================================="
echo " 2. 備份資料庫（用目前正在跑的容器）"
echo "=================================================================="
mkdir -p "$HOME/backups"
BK="$HOME/backups/hankerp-before-deploy-$OLD_HEAD-$TS.sql.gz"
$DC exec -T db pg_dump -U erp_user -d acrylic_erp | gzip > "$BK" || die "pg_dump 失敗，沒有繼續部署"
SZ=$(stat -c %s "$BK"); TABLES=$(gunzip -c "$BK" | grep -c '^CREATE TABLE')
[ "$SZ" -gt 2000 ] && [ "$TABLES" -ge 10 ] || die "備份檔異常（$SZ bytes、$TABLES 張表），沒有繼續部署"
ok "備份完成：$BK（$SZ bytes、$TABLES 張表）"

echo
echo "=================================================================="
echo " 3. 設定 .env 為正式模式（原檔備份為 .env.bak-$TS）"
echo "=================================================================="
cp .env ".env.bak-$TS"
if [ "$NEED_TOKEN" = "1" ]; then
  read -r -s -p "  貼上 Cloudflare Tunnel token（輸入不會顯示，貼完按 Enter）：" TOK; echo
  TOK=$(printf '%s' "$TOK" | tr -d '[:space:]')
  # 後台給的是整行指令時，只取 token 本身
  TOK=${TOK##*--token}
  [ ${#TOK} -ge 100 ] || die "token 長度 ${#TOK} 不對（應是 100 字以上的一長串），.env 未修改"
  setkv TUNNEL_TOKEN "$TOK"; unset TOK
  ok "TUNNEL_TOKEN 已寫入 .env（不顯示）"
fi
# COMPOSE_FILE 寫進 .env 之後，主機上所有 docker compose 指令（含備份、還原、logs）都會自動用正式版，
# 不必每次加 -f，也不會手滑用開發版把 port 又開出去。
setkv COMPOSE_FILE "$PROD_FILE";            ok "COMPOSE_FILE=$PROD_FILE"
setkv ENVIRONMENT production;               ok "ENVIRONMENT=production（關閉 /docs）"
setkv NEXT_PUBLIC_API_URL "$API";           ok "NEXT_PUBLIC_API_URL=$API"
setkv NEXT_PUBLIC_SITE_URL "$SITE";         ok "NEXT_PUBLIC_SITE_URL=$SITE"
setkv CORS_ORIGINS "$CORS";                 ok "CORS_ORIGINS=$CORS"

echo
echo "=================================================================="
echo " 4. 更新程式碼並以正式版重建（前端會重新 build，需要幾分鐘）"
echo "=================================================================="
git checkout -q main && git pull -q --ff-only origin main || die "git pull 失敗"
[ -f "$PROD_FILE" ] || die "找不到 $PROD_FILE（GitHub 上還不是 v2.3.5？）"
# 確認 Compose 真的從 .env 讀到 COMPOSE_FILE（正式版才有 cloudflared 服務）
$DC config --services 2>/dev/null | grep -qx cloudflared \
  || die "docker compose 沒有讀到 $PROD_FILE（.env 的 COMPOSE_FILE 沒生效），未重建任何容器"
ok "docker compose 已改用 $PROD_FILE"
ok "程式碼：$OLD_HEAD → $(git rev-parse --short HEAD)"
$DC up -d --build --remove-orphans || die "docker compose up 失敗"
in_backend() { $DC exec -T backend python -c "import sys,urllib.request as u
try: r=u.urlopen('http://localhost:8000'+sys.argv[1],timeout=3); print(r.status)
except Exception as e: print(getattr(e,'code','ERR'))" "$1" 2>/dev/null; }
echo -n "  等待 backend 就緒"
for _ in $(seq 1 60); do [ "$(in_backend /health)" = "200" ] && break; echo -n "."; sleep 3; done; echo
[ "$(in_backend /health)" = "200" ] || die "backend 3 分鐘內沒有就緒，請看：$DC logs backend --tail 50"
ok "backend 就緒"

echo
echo "=================================================================="
echo " 5. 資料庫 migration ＋ 同步角色權限"
echo "=================================================================="
$DC exec -T backend alembic upgrade head || die "alembic upgrade 失敗"
$DC exec -T backend python scripts/seed_data.py || die "seed_data 失敗"

echo
echo "=================================================================="
echo " 6. 驗證"
echo "=================================================================="
echo "  migration：$($DC exec -T backend alembic current 2>/dev/null | tail -1)"
C=$(in_backend /api/v1/customers)
[ "$C" = "401" ] && ok "未登入呼叫業務 API → 401" || warn "未登入呼叫業務 API 回 $C（預期 401）"
D=$(in_backend /docs)
[ "$D" = "404" ] && ok "/docs 已關閉（正式模式）" || warn "/docs 回 $D（預期 404）"
W=$($DC exec -T frontend wget -q -O /dev/null -S http://localhost:3000/login 2>&1 | awk '/HTTP\//{print $2}' | tail -1)
[ "$W" = "200" ] && ok "前端登入頁（容器內）→ 200" || warn "前端登入頁回 $W"
if $DC exec -T frontend sh -c "grep -rlF '$API' .next 2>/dev/null | head -1" | grep -q .; then
  ok "前端已編入 API 網址 $API"
else warn "前端程式碼裡找不到 $API"; fi
LISTEN=$(ss -ltnH 2>/dev/null | awk '{print $4}' | grep -E ':(3000|8000|5432|6379)$' || true)
[ -z "$LISTEN" ] && ok "主機沒有對外開 3000／8000／5432／6379" || warn "主機仍在監聽：$LISTEN"
echo -n "  cloudflared："
$DC logs --tail 40 cloudflared 2>&1 | grep -c "Registered tunnel connection" | xargs -I{} echo "{} 條通道連線"
for url in "$API/health" "$SITE/login" "$SITE/"; do
  P=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$url")
  [ "$P" = "200" ] && ok "公開網址 $url → 200" || warn "公開網址 $url 回 $P（DNS 或 Tunnel 路由還沒設好？）"
done
CO=$(curl -s -o /dev/null -w '%{http_code}' -m 15 -X OPTIONS "$API/api/v1/auth/login" \
  -H "Origin: $SITE" -H "Access-Control-Request-Method: POST")
[ "$CO" = "200" ] && ok "CORS：$SITE 可以呼叫 $API" || warn "CORS 預檢回 $CO（登入可能會失敗）"
PSQL="$DC exec -T db psql -U erp_user -d acrylic_erp -tA -c"
echo "  角色數：$($PSQL 'select count(*) from roles' 2>/dev/null)"
NOROLE=$($PSQL "select email from users where role_id is null and is_active" 2>/dev/null)
[ -z "$NOROLE" ] && ok "所有啟用中的帳號都有角色" || { warn "下列帳號沒有角色："; echo "$NOROLE" | sed 's/^/      /'; }

echo
echo "=================================================================="
echo " 完成：$OLD_HEAD → $(git rev-parse --short HEAD)"
echo "   資料庫備份：$BK"
echo "   .env 備份： $APP_DIR/.env.bak-$TS"
echo "   請用瀏覽器開 $SITE/login 實際登入一次"
echo
echo "   萬一要退回 IP 模式（舊版開發 compose）："
echo "     cp .env.bak-$TS .env && docker compose -f docker-compose.yml up -d --build --remove-orphans"
echo "   把這整段輸出貼給 Claude"
echo "=================================================================="
