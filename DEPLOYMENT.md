# 部署指南（Zeabur / 自架 Ubuntu 主機）

> 本文件記錄 2026-09-17 首次成功部署到正式主機的完整流程與踩過的坑。
> **每一條都是實際撞到才寫下來的**，不是預想的注意事項。

## 目前的正式環境

| 項目 | 值 |
|---|---|
| 主機 | Zeabur × Tencent Cloud Singapore，Ubuntu 24.04 LTS |
| 規格 | 2 vCPU / 1.9 GB RAM / 40 GB SSD |
| 對外位址 | 目前 `http://43.156.110.76:3000`（Zeabur，11/14 到期）；搬家後 `https://everevo.com.tw`（AWS Lightsail＋Cloudflare Tunnel，主機不開任何 port） |
| SSH | `ubuntu@43.156.110.76`（仍用 IP） |
| 專案路徑 | `/home/ubuntu/HankERP` |
| 容器 | v2.3.5 起用 `docker-compose.prod.yml`：frontend / backend / celery / db / redis / db-backup / cloudflared，共 7 個 |
| 部署 | `infra/deploy_prod.sh`（見下一節） |

---

## 搬到新主機（v2.3.9）

**為什麼**：Zeabur 2026-10-17 公告停止營運，12/1 停止續約、12/31 前所有專用主機到期關機。
原正式站（Zeabur 代管的騰訊雲新加坡 2C2G，`43.156.110.76`）11/14 到期。新主機選 **AWS Lightsail 4GB（香港或東京）**。

**資料**：系統沒有檔案上傳功能，**資料庫匯出檔就是全部資料**。舊主機匯出方式：

```bash
cd ~/HankERP && docker compose up -d db && sleep 15
docker compose exec -T db pg_dump -U erp_user -d acrylic_erp -Fc > ~/hankerp-final.dump
```

**新主機一鍵安裝**：`infra/setup_new_host.sh`（全新 Ubuntu 24.04；一般帳號或 root 皆可，v2.3.10）

```powershell
# 你的電腦：把資料庫檔傳上新主機（金鑰檔與 IP 換成自己的）
scp -i $HOME\.ssh\<Lightsail 金鑰>.pem .claude-tmp\hankerp-final.dump ubuntu@<新主機 IP>:
ssh -i $HOME\.ssh\<Lightsail 金鑰>.pem ubuntu@<新主機 IP>
```

```bash
# 新主機上
curl -fsSL https://raw.githubusercontent.com/zev-666/HankERP/main/infra/setup_new_host.sh -o setup_new_host.sh
bash setup_new_host.sh ~/hankerp-final.dump
```

腳本會：建 2GB swap → 依 Docker 官方文件安裝 Docker → clone 程式 → 產生 `.env`（SECRET_KEY、DB_PASSWORD 等隨機產生、不顯示；
`COMPOSE_FILE=docker-compose.prod.yml`；網址設為 `https://everevo.com.tw`、API `https://api.everevo.com.tw`；`TUNNEL_TOKEN=PENDING`）→
建置並啟動資料庫 → **只在資料庫是空的時候**還原匯出檔 → 啟動網站（cloudflared 先不啟動）→ migration＋同步角色 → 驗證。
每步失敗就停，可整支重跑（`.env` 已存在就沿用、資料庫已有資料就不還原）。

裝完後網站在主機裡運作、外面連不到（刻意不開 port）。Cloudflare Tunnel 建好後執行 `bash ~/HankERP/infra/deploy_prod.sh`，
腳本看到 `TUNNEL_TOKEN=PENDING` 會請你貼 token，啟動 cloudflared，`https://everevo.com.tw` 上線。

**Lightsail 主機設定**：Ubuntu 24.04 LTS、4GB 方案、開啟每日自動快照、綁定免費的固定 IP；
Networking 防火牆**只留 SSH（22）**，刪掉預設的 HTTP（80）規則（流量走 Tunnel，不需要）。
SSH 用 Lightsail 下載的金鑰（`.pem`）登入，不用密碼。

**已驗證（v2.3.9，雲端沙盒）**：`docker compose config` 實測 `.env` 的 `COMPOSE_FILE` 會生效（7 個服務、無對外 port、
前端建置參數為正式網址；拿掉這行時腳本的檢查會擋下）；匯出檔以 `pg_restore --exit-on-error` 還原到 PostgreSQL 成功（31 張表、版本 head）；
`bash -n`、shellcheck 無警告。**未驗證**：在真的 Lightsail 主機上整支執行（沙盒連不到 Docker Hub）。

### 各家主機的建立重點（v2.3.10）

安裝腳本只需要：**Ubuntu 24.04 LTS、記憶體 4GB、硬碟 25GB 以上、能連外網**。一般帳號（有 sudo）或 root 都可以執行。

| 廠商 | 規格 | 注意 |
|---|---|---|
| AWS Lightsail（東京） | 4GB／US$24 | 新帳號可能被限制方案大小（2026-10 實測），要開客服單放寬；登入帳號 `ubuntu`、用 `.pem` 金鑰 |
| Google Cloud（台灣 asia-east1） | e2-medium（2 vCPU／4GB） | **開機磁碟預設 10GB，要改成 30GB**；防火牆不要勾「允許 HTTP/HTTPS」；可用主控台的「SSH」按鈕登入並「上傳檔案」傳匯出檔 |
| Akamai Linode（東京） | Shared 4GB／US$24 | 預設 root＋密碼登入，建立時改用 SSH 金鑰；Cloud Firewall 只放行 SSH |

所有廠商都一樣：防火牆**只開 SSH（22）**，網站流量走 Cloudflare Tunnel；開啟廠商提供的每日備份／快照。

### 搬家當天的順序

1. 新主機建好、能 SSH 登入。
2. **舊主機重新匯出一次資料庫**（上面的 `pg_dump` 指令）並 scp 回自己電腦——10/20 的匯出檔之後若有人在正式站新增資料，要用新的。
3. 把匯出檔傳上新主機 → 執行 `setup_new_host.sh`（約 10～15 分鐘）。
4. Cloudflare 建 Tunnel（3 條路由）→ 新主機執行 `deploy_prod.sh` 貼 token → `https://everevo.com.tw` 上線、實測。
5. 新站確認沒問題幾天後，才關掉舊主機。

網域（HiNet 購買 → 交給 Cloudflare 管理 DNS）與主機互不相依，可以先做；Tunnel 需要網域已在 Cloudflare 顯示 Active。

## Cloudflare Tunnel 上線（v2.3.5）

```
訪客 ──HTTPS──▶ Cloudflare ══加密通道══▶ 主機上的 cloudflared 容器 ─┬─▶ frontend:3000（everevo.com.tw、www）
                                        （由主機主動往外連）        └─▶ backend:8000（api.everevo.com.tw）
```

前台 `everevo.com.tw`、API `api.everevo.com.tw`，**一個網址對一個服務**（v2.3.7 起；v2.3.5 原本設計同網域依路徑分流，
但 Cloudflare 後台的路由表單不保證有「路徑」欄位，改成子網域最穩）。瀏覽器跨子網域呼叫 API 靠 `CORS_ORIGINS` 放行，
部署腳本最後會檢查。單層子網域在 Cloudflare 免費憑證（Universal SSL）範圍內，不用另外買憑證。
主機不對外開 80／443／3000／8000，IP 被掃到也沒有服務可打。

### 一次性設定（使用者在瀏覽器操作）

1. **買網域** `everevo.com.tw`：.com.tw 要在台灣的註冊商買，用**永陛實業有限公司（統編 12659649）**名義，帳號由公司保管。
2. **把網域交給 Cloudflare 管 DNS**：Cloudflare → Add a domain → `everevo.com.tw` → Free 方案 →
   記下 Cloudflare 給的兩組 nameserver → 回註冊商後台把 DNS 伺服器改成這兩組 → 等 Cloudflare 顯示 Active。
3. **建立 Tunnel**：Cloudflare 後台 → **Networking → Tunnels**（舊版介面在 Zero Trust → Networks → Tunnels）→
   Create a tunnel → 名稱 `everevo-prod` → 安裝指令畫面選 Docker，指令裡 `--token` 後面那一長串就是 token。
   **不要複製到任何地方、不要在主機上執行那行指令**，部署腳本會請你直接貼 token（輸入不顯示），由 `cloudflared` 容器連線。
4. **設定路由**（Tunnel 的 Routes → Add route → Published application；舊版叫 Public hostname）：

   | # | 子網域 | 網域 | 服務網址（Service URL） |
   |---|---|---|---|
   | 1 | （空白） | everevo.com.tw | `http://frontend:3000` |
   | 2 | www | everevo.com.tw | `http://frontend:3000` |
   | 3 | api | everevo.com.tw | `http://backend:8000` |

   `backend`、`frontend` 是 Docker 內網的服務名稱，cloudflared 容器跟它們在同一個網路，所以這樣寫就連得到。
5. **www 轉址到主網域**：Rules → Redirect Rules → 用範本「Redirect from WWW to root」。
   （不轉的話，www 與主網域的登入狀態是分開的。）
6. **SSL/TLS → Edge Certificates → Always Use HTTPS** 打開。

### 部署（PowerShell）

```powershell
scp infra/deploy_prod.sh ubuntu@43.156.110.76:deploy_prod.sh
ssh -t ubuntu@43.156.110.76 bash deploy_prod.sh
```

腳本會：只讀檢查 → 等你輸入 yes → 備份資料庫 → 請你貼上 token（第一次）→ 把 `.env` 改成正式模式
（`COMPOSE_FILE=docker-compose.prod.yml`、網址改成網域、`ENVIRONMENT=production`）→ 重建 → migration → 驗證
（容器內 API 401、`/docs` 已關、主機沒有監聽 3000／8000、公開網址 200）。

**`.env` 設了 `COMPOSE_FILE` 之後，主機上所有 `docker compose` 指令都自動用正式版**（備份、還原、logs 都一樣），
不要再加 `-f docker-compose.yml`，否則會用開發版把 port 又開出去。

### 部署後

- **騰訊雲安全組**刪掉 3000、8000 的入站規則，只留 22（主機已經不監聽，這是第二道保險）。
- 瀏覽器開 `https://everevo.com.tw/login` 實際登入、建一筆資料、從官網送一筆詢價。

### 退回 IP 模式

部署腳本最後會印出對應的 `.env` 備份檔名：

```bash
cp .env.bak-<時間> .env && docker compose -f docker-compose.yml up -d --build --remove-orphans
```

### 為什麼這樣設計

- **限流**：Tunnel 後所有請求都從 cloudflared 容器進來。v2.3.5 前限流用連線來源 IP，
  上 Tunnel 會變成全站共用一個計數（任何人登入錯 5 次，所有人被鎖）。現在正式版設
  `TRUST_CF_CONNECTING_IP=true`，改用 Cloudflare 帶來的真實訪客 IP。
  **這只在「後端不對外開 port」時安全**——能直接連到後端的人可以偽造這個標頭。開發版預設不信任。
- **HSTS** 先用 1 天（`next.config.js`），穩定一個月後再拉長；一開始就設 2 年＋preload，設定出錯無法回頭。
- **官網伺服器端**抓作品案例走 `INTERNAL_API_URL=http://backend:8000`，不繞外網。
- `docker-compose.prod.yml` 是獨立檔案，`backend/tests/test_compose_prod.py` 檢查它與開發版同步、且沒有開 port。

---

## ⚠️ 最重要的一條：`NEXT_PUBLIC_*` 是建置期寫死的

**`NEXT_PUBLIC_API_URL` 在 `npm run build` 那一刻就被編譯進 JS 檔案，不是啟動時才讀取。**

所以之後換網域、換 IP、或加上 SSL 時：

```bash
# ❌ 這樣沒用 —— 改了 .env 重啟，JS 裡面還是舊網址
vim .env && docker compose restart frontend

# ✅ 必須重新建置
vim .env && docker compose up -d --build frontend
```

**忘記這件事的症狀非常有欺騙性**：頁面正常顯示、載入很快、Console 沒有錯誤，
但登入按下去毫無反應，Network 分頁篩選 Fetch/XHR 是完全空的。
因為瀏覽器正在對「使用者自己的電腦」發請求，不是對伺服器。

為了讓建置期能拿到這個值，`frontend/Dockerfile` 的 builder 階段必須有：

```dockerfile
COPY . .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
```

位置很關鍵：**要在 `COPY . .` 之後、`RUN npm run build` 之前**。
放太前面會被 `COPY` 蓋掉，放太後面建置時讀不到。

而 `docker-compose.yml` 要把它當 build 參數傳進去（不能只放在 `environment`）：

```yaml
frontend:
  build:
    context: ./frontend
    args:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
  environment:
    NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
```

`environment` 那份仍然要留 —— 官網首頁是 Server Component，在伺服器端讀的是執行期的值。

---

## 正式主機不可以跑開發模式

`docker-compose.yml` 原本是為本機開發寫的，直接搬上伺服器會留下三個致命設定：

```yaml
frontend:
  volumes:
    - ./frontend:/app      # ← 把 Dockerfile 建好的 production 成品整個蓋掉
    - /app/.next
  command: npm run dev     # ← 強制退回開發模式
```

**後果（實測數據）：**

| | 開發模式 | production |
|---|---|---|
| 登入頁回應時間 | 6.4 秒 | **0.04 秒** |
| 下載資源 | 3.7 MB / 23 個請求 | 大幅減少 |
| HMR WebSocket | 一直嘗試連線並報錯 | 沒有 |

更嚴重的是：在 2 核心機器上，開發模式的 JS 要好幾秒才會接管頁面。
**在那之前按下登入，`<form>` 會退回瀏覽器的原生送出行為** ——
整頁重新整理、網址變成 `/login?`（多一個問號）、完全不會發出 API 請求。

這個症狀很容易被誤判成「程式碼忘了寫 `preventDefault()`」，但程式碼是對的。
**沒有 JavaScript 錯誤卻發生原生表單送出 = JS 根本沒執行**，不是邏輯寫錯。

正式主機的 frontend 區塊應該長這樣（沒有 `volumes`、沒有 `command`）：

```yaml
frontend:
  build:
    context: ./frontend
    args:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
  ports:
    - "3000:3000"
  environment:
    NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
```

---

## 建置需要 swap

Next.js 建置是整個流程最吃記憶體的一步。1.9 GB RAM 的機器**有機率在跑了十分鐘後**
才以 `Killed` 或 `JavaScript heap out of memory` 結束。

建置前先加 swap，30 秒的保險：

```bash
sudo fallocate -l 2G /swapfile2 && sudo chmod 600 /swapfile2 \
  && sudo mkswap /swapfile2 && sudo swapon /swapfile2 && free -h
```

加完應該顯示 Swap 約 3.9 G。實測加了之後 `npm run build` 只花 35 秒就完成。

> 這個 swap 重開機後會消失。平常跑 production 很省記憶體，不需要它；
> 只有**建置前**要記得加。要永久保留的話在 `/etc/fstab` 加一行
> `/swapfile2 none swap sw 0 0`。

---

## 首次部署完整流程

```bash
# 1. 安裝 Docker（Ubuntu 24.04 預設沒有）
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
exit                                    # 必須登出重登，群組權限才生效

# 2. 取得程式碼
git clone https://github.com/zev-666/HankERP.git && cd HankERP

# 3. 建立 .env（不在版控裡，必須手動建）
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # 產生 SECRET_KEY
vim .env
```

`.env` 正式環境必須是這些值（把 IP 換成你的）：

```bash
SECRET_KEY=<上面產生的隨機值，至少32字元>
ENVIRONMENT=production
CORS_ORIGINS=http://43.156.110.76:3000
NEXT_PUBLIC_API_URL=http://43.156.110.76:8000
DB_PASSWORD=<自己換掉，別用預設值>
```

```bash
# 4. 加 swap（見上一節）

# 5. 啟動
docker compose up -d --build

# 6. 建立資料庫
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_data.py

# 7. 驗證（這一步不可省略）
docker compose exec backend python scripts/verify_e2e.py
```

---

## 驗證：三層都要測，缺一不可

這個專案最常犯的錯就是「看到頁面打開就以為成功了」。**必須三層都測**：

### 第一層 — 後端與資料庫

```bash
docker compose exec backend python scripts/verify_e2e.py
```

看到 `✅ 全部 v2.0 新功能端到端驗證通過` 才算過。

**這一層證明不了瀏覽器能用** —— 它是在容器裡用 `127.0.0.1` 自己打自己。

### 第二層 — 對外連通性

在自己的電腦（不是 SSH 視窗）：

```powershell
curl.exe http://43.156.110.76:8000/health
```

回 `{"status":"ok",...}` 代表防火牆有放行 8000。
（PowerShell 的 `curl` 是 `Invoke-WebRequest` 的別名，會跳安全警告，**要加 `.exe`**。）

### 第三層 — 瀏覽器（唯一能證明整條鏈的測試）

1. 開 `http://43.156.110.76:3000/login` 登入
2. 進「線上詢價」頁面
3. **要看到驗證腳本寫進去的那筆「王大明／美妝通路股份有限公司」**

看得到它，才證明 瀏覽器 → 前端 → 後端 → 資料庫 全通。

`NEXT_PUBLIC_API_URL` 錯誤這類 bug **只在第三層才會現形**，前兩層測一百次都測不出來。

---

## 常見狀況對照表

| 症狀 | 真正原因 | 解法 |
|---|---|---|
| 登入沒反應、Network 的 Fetch/XHR 全空、網址變 `/login?` | JS 沒執行（開發模式未 hydrate）或 API 網址錯 | 切 production 模式；確認建置時有傳 `NEXT_PUBLIC_API_URL` |
| 官網首頁正常但沒有任何資料 | 前端連不到後端。首頁刻意設計成「連不到就顯示空狀態」，所以**看起來是正常的** | 同上 |
| backend 啟動後一直 Restarting | `ENVIRONMENT=production` 會擋下不足 32 字元的 `SECRET_KEY` | 重新產生 SECRET_KEY |
| Console 出現 `WebSocket ... /_next/hmr ... failed` | 開發模式的熱重載，**與功能無關** | 切 production 後自然消失 |
| `docker` 指令要求 sudo | `usermod -aG docker` 後沒重登 | `exit` 再重新 ssh |
| 建置跑很久後 `Killed` | 記憶體不足 | 先加 swap |

---

## 目前已知的未完成項目

- [x] ~~沒有網域、沒有 SSL~~ → v2.3.5 `https://everevo.com.tw`（Cloudflare Tunnel）
- [x] ~~backend 仍在跑 `--reload` 與 bind mount~~ → v2.3.5 `docker-compose.prod.yml` 已移除
- [x] ~~8000 port 直接對外曝露~~ → v2.3.5 不開任何 port；騰訊雲安全組的 3000／8000 規則仍需使用者刪除
- [ ] SSH 仍是密碼登入、22 port 對全網開放 —— 應改金鑰登入並限制來源（Should）
- [x] ~~資料庫沒有備份機制~~ → v2.1 新增 `db-backup` 容器（見下方「資料庫備份」）。**異地備份仍未設定**
- [ ] 資料庫裡有 `verify_e2e.py` 產生的測試資料（王大明詢價、客戶 C0001、工單 WO2026-0001）。
      正式交付給工廠前要清掉

## 資料庫備份（v2.1）

`docker-compose.yml` 的 `db-backup` 容器每天做一次 `pg_dump`，寫到主機的 `./backups/`，
保留 14 天（`.env` 可用 `BACKUP_INTERVAL_SECONDS`、`BACKUP_KEEP_DAYS` 調整）。
每份備份做完會立刻用 `pg_restore --list` 讀一次，讀不出來就刪掉並在 log 報錯。

```bash
# 啟用（第一次）
cd /home/ubuntu/HankERP && git pull && docker compose up -d db-backup

# 確認有在跑、看最近一次結果
docker compose logs --tail 20 db-backup
ls -lh backups/

# 立刻手動備份一次（例如改版前）
docker compose run --rm -e BACKUP_ONCE=1 db-backup

# 還原演練：先還原到「新的」資料庫檢查，不要直接覆蓋正式庫
docker compose run --rm db-backup sh /scripts/restore.sh /backups/<檔名>.dump acrylic_restore_check --yes
docker compose exec db psql -U erp_user -d acrylic_restore_check -c "SELECT count(*) FROM customers;"
```

**真的要把正式庫還原成某份備份時**：先 `docker compose stop backend celery`（避免還原中有人寫入），
還原到 `acrylic_erp`，再 `docker compose start backend celery`。

⚠️ **備份和資料庫在同一台主機**：能防「誤刪、程式把資料寫壞」，防不了主機損毀或帳號被停用。
至少每週把 `backups/` 最新一份下載到公司電腦（Windows PowerShell）：

```powershell
$f = ssh ubuntu@43.156.110.76 "ls -t /home/ubuntu/HankERP/backups | head -1"
scp "ubuntu@43.156.110.76:/home/ubuntu/HankERP/backups/$f" .
```

長期應改為自動上傳到物件儲存（Tencent COS／S3），屬 Should Have，待決定部署平台後再做。

---

## 換網域 / 加 SSL 時的檢查清單

（v2.3.5 起由 `infra/deploy_prod.sh` 處理；網域寫在腳本最上方的 `DOMAIN`。）

1. 改 `.env` 的 `CORS_ORIGINS`、`NEXT_PUBLIC_API_URL`、`NEXT_PUBLIC_SITE_URL`
2. **`docker compose up -d --build frontend`** —— 不是 `restart`（見本文件第一節）
3. Cloudflare Tunnel 的 Public hostname 加上新網域（兩條：`/api`、`/health` → backend，其餘 → frontend）
4. 重跑上面三層驗證，尤其第三層
