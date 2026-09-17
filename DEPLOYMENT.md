# 部署指南（Zeabur / 自架 Ubuntu 主機）

> 本文件記錄 2026-09-17 首次成功部署到正式主機的完整流程與踩過的坑。
> **每一條都是實際撞到才寫下來的**，不是預想的注意事項。

## 目前的正式環境

| 項目 | 值 |
|---|---|
| 主機 | Zeabur × Tencent Cloud Singapore，Ubuntu 24.04 LTS |
| 規格 | 2 vCPU / 1.9 GB RAM / 40 GB SSD |
| 對外位址 | `http://43.156.110.76:3000`（前端）、`:8000`（API） |
| 專案路徑 | `/home/ubuntu/HankERP` |
| 容器 | frontend / backend / celery / db / redis，共 5 個 |

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

- [ ] **沒有網域、沒有 SSL** —— 現在是 `http://IP:port`，瀏覽器顯示「不安全」
- [ ] **backend 仍在跑 `--reload`**（開發模式旗標），且掛著 `./backend:/app` bind mount。
      功能正常，但不是正式環境該有的設定，之後應比照前端處理
- [ ] **8000 port 直接對外曝露** —— 之後應該用反向代理（Caddy / nginx）只開 443
- [ ] **資料庫沒有備份機制**
- [ ] 資料庫裡有 `verify_e2e.py` 產生的測試資料（王大明詢價、客戶 C0001、工單 WO2026-0001）。
      正式交付給工廠前要清掉

## 換網域 / 加 SSL 時的檢查清單

1. 改 `.env` 的 `CORS_ORIGINS` 與 `NEXT_PUBLIC_API_URL`
2. **`docker compose up -d --build frontend`** —— 不是 `restart`（見本文件第一節）
3. 重跑上面三層驗證，尤其第三層
