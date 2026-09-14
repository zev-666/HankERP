# HankERP — 壓克力展示架智慧工廠 ERP

桃園龜山複合式壓克力製造商（壓克力＋木工＋鐵件＋LED＋噴漆）的數位轉型 ERP 系統。
涵蓋官網、CRM、報價、BOM、庫存、採購、生產工單、MES 現場報工、裁切最佳化與成本分析。

| | |
|---|---|
| **目前版本** | v2.0（2026-09-14） |
| **後端** | FastAPI 0.135 + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL 15/16 + Celery + Redis |
| **前端** | Next.js 16.3.5 + Tailwind CSS + TanStack Query + Zustand + Recharts |
| **實測規模** | 13 個業務模組 · 68 個業務 API 端點（＋`/health` 共 69）· 30 張業務資料表 · 23 條前端路由（21 靜態 ＋ 2 動態）|

> 上列數字全部是量出來的，不是抄的：端點數讀真實啟動後的 `/openapi.json`，
> 頁面數讀真實 `npm run build` 的 Route 表，資料表數查真實 PostgreSQL 的
> `information_schema.tables`。量法寫在 `CONTRIBUTING.md`。

---

## 快速啟動

### A. Docker（推薦）

```bash
# 1. 複製環境變數（共3個.env檔案，缺任何一個都會啟動失敗）
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# 1.1 ⚠️ 必做：把根目錄 .env 裡的 SECRET_KEY 換成真正的隨機值
#     （docker-compose.yml 強制要求，沒換會拒絕啟動，這是刻意的資安防呆機制）
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# 把印出的值貼進 .env 的 SECRET_KEY= 後面

# 2. 啟動全部服務（PostgreSQL + Redis + Backend + Celery + Frontend）
docker compose up -d --build

# 3. 執行資料庫遷移（migration檔案已內建，無需執行 autogenerate）
docker compose exec backend alembic upgrade head

# 4. 建立種子資料（預設租戶、9種角色、管理員帳號）※ 可重複執行，不會重複建立
docker compose exec backend python scripts/seed_data.py
```

### B. 本機（不用 Docker）

```bash
# 後端
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                # 改掉 DATABASE_URL 與 SECRET_KEY
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload --port 8000

# 前端（另開終端）
cd frontend
npm ci && cp .env.local.example .env.local
npm run dev
```

### 開啟系統

| 入口 | 網址 |
|---|---|
| 官網首頁 | http://localhost:3000 |
| 作品案例 | http://localhost:3000/portfolio |
| 線上詢價 | http://localhost:3000/quote |
| ERP 登入 | http://localhost:3000/login |
| MES 現場報工 | http://localhost:3000/mes |
| API 文件 | http://localhost:8000/docs（僅開發環境可見，正式環境自動關閉） |

預設管理員帳號：`admin@guishan-acrylic.com` / `ChangeMe123!`（請於正式環境立即更改）

### 驗證安裝是否正確

```bash
cd backend && pytest -q                                        # 17 項單元測試
API_BASE=http://127.0.0.1:8000 python scripts/verify_e2e.py    # 端到端：詢價→客戶、工單→發料→完工入庫
cd ../frontend && npm run build && npx eslint . --max-warnings=0 && npm audit
```

> **注意**：README 舊版提到的「MinIO」服務為規劃階段殘留敘述，`docker-compose.yml`
> 與程式碼中實際上並未實作 MinIO 物件儲存（`MEDIA_ROOT` 設定值目前也沒有對應的檔案上傳邏輯）。
> 若未來需要圖片／檔案儲存功能，屬於待開發項目。

---

## 系統模組對照

| 模組 | 後端路徑 | 前端頁面 | 端到端驗證狀態 |
|------|---------|---------|---------|
| 官方網站 | `/api/v1/public/*` | `/` `/portfolio` `/portfolio/[slug]` `/about` `/quote` | ✅ 已測試（v2.0 起前端真實串接後端） |
| 線上詢價 | `/api/v1/inquiries` `/api/v1/public/inquiries` | `/quote` `/erp/inquiries` | ✅ 已測試（送出→落庫→後台→轉客戶全程） |
| 作品展示系統 | `/api/v1/portfolio` `/api/v1/public/portfolio` | `/erp/portfolio` `/portfolio` | ✅ 已測試（後台發佈→官網即時顯示） |
| 客戶管理 CRM | `/api/v1/customers` | `/erp/customers` | ✅ 已測試 |
| 報價／AI估價／PDF | `/api/v1/quotations` | `/erp/quotations` | ✅ 已測試（含資料持久化驗證） |
| 產品／BOM 管理 | `/api/v1/products` `/api/v1/bom` | `/erp/products` | ✅ 已測試（含成本展開計算） |
| 庫存管理 | `/api/v1/inventory` | `/erp/inventory` | ✅ 已測試（含成品 FG 倉） |
| 採購管理 | `/api/v1/purchase-orders` | `/erp/purchasing` | ✅ 已測試 |
| 生產工單 | `/api/v1/work-orders` | `/erp/production` | ✅ 已測試（含發料扣庫存、完工入庫） |
| MES 現場報工 | `/api/v1/work-orders/{id}/operations` | `/mes` | ✅ 已測試 |
| 裁切最佳化 | `/api/v1/nesting` | `/erp/nesting` | ✅ 已測試（含9板型比較） |
| 設備管理 | `/api/v1/equipment` | `/erp/equipment` | ✅ 已測試 |
| 成本分析 | `/api/v1/analytics` | `/erp/analytics` | ✅ 已測試 |

## 核心業務流程（v2.0 起全線打通）

```
官網詢價 → 後台詢價管理 → 轉正式客戶 → 報價（AI試算/手動）→ PDF
                                              ↓
產品 + BOM → 生產工單 → 發料（扣 RAW 倉）→ MES 報工 → 完工入庫（進 FG 倉）
                 ↓
            裁切排版最佳化 → 剩料登記
```

v2.0 之前，「發料」與「完工入庫」兩個箭頭是斷的：生產模組與庫存模組各自能跑，
但工單領了料庫存不會動，工單做完了成品也不會進倉。

---

## 文件導覽

| 檔案 | 用途 |
|---|---|
| `README.md` | 現況、啟動方式、版本紀錄（**唯一事實來源**） |
| `MASTER_SPEC.md` | 完整技術規格、資料庫 schema、RBAC 權限矩陣、三年藍圖 |
| `MVP_CHECKLIST.md` | 每一項功能的 ✅／⚠️／❌ 狀態 |
| `CLAUDE.md` | AI 協作開發指引（工程規則 ＋ ERP 顧問決策框架） |
| `CONTRIBUTING.md` | 開發環境、送交前檢查清單、文件同步規則 |

## 新增的功能端點

- `POST /api/v1/public/inquiries` — 官網詢價送出（公開、5次/小時速率限制）**v2.0**
- `GET /api/v1/inquiries`、`PATCH /api/v1/inquiries/{id}/status` — 詢價後台管理 **v2.0**
- `POST /api/v1/inquiries/{id}/convert-to-customer` — 詢價轉正式客戶（冪等）**v2.0**
- `POST /api/v1/work-orders/{id}/issue-materials` — 工單發料，自動扣減原料庫存 **v2.0**
- `POST /api/v1/work-orders/{id}/complete` — 完工入庫，成品進 FG 倉 **v2.0**
- `POST /api/v1/auth/register`、`/change-password`、`/forgot-password`、`/reset-password`
- `GET /api/v1/customers/{id}/360` — 客戶360視圖
- `GET /api/v1/quotations/{id}/pdf` — 報價單PDF下載
- `GET /api/v1/work-orders/{id}` — 工單詳情（含工序清單，供MES使用）
- `POST /api/v1/nesting/compare-presets` — 9種板型自動比較，找出最省片數方案

## 後續可優化方向

1. 密碼重設 token 目前存於記憶體字典，正式環境建議改用 Redis 並加上速率限制
2. PDF 中文字型使用 reportlab 內建 STSong-Light（Adobe 標準 CID 字型），若需思源黑體需額外安裝字型檔
3. 裁切視覺化目前為 CSS absolute positioning，可升級為 Konva.js 取得更精準的拖曳與列印輸出
4. MES 頁面目前用輪詢（10-15秒）更新狀態，正式量產環境建議改用 WebSocket 即時推送
5. `equipment/{id}/status` 的 `status` 為 query 參數而非 JSON body，與其餘端點慣例不一致
6. `ezdxf`、`pymupdf`、`pillow` 已列於 requirements.txt 但尚無程式碼使用（CAD/PDF 解析為規劃中功能）
7. `nesting/router.py` 的 `/calculate` 目前是同步執行（BFD 演算法 5000 件 <100ms，已由 pytest 驗證），
   `calculate_nesting_async` 是死程式碼、`batch_optimize_multiple_orders`（跨工單混排）是 stub。
   零件量大幅上升時才需要真的接上 Celery 非同步與輪詢端點。
   （v1.9 已修正 Celery worker 根本不認得這兩個 task 的 `autodiscover_tasks` 問題，見下方版本紀錄）
8. 作品 slug 目前保留中文字元（`彩妝展示架-1789349945`），可用但 URL 會被百分比編碼、
   不利分享與 SEO；若在意可改為 ASCII slug ＋ 短碼。詳見 v2.0 紀錄裡的相關 bug。
9. 詢價目前無 email 通知，業務需自行進後台查看；接上 SMTP 或 LINE Notify 是下一個高性價比項目
10. 安全庫存預警、庫存盤點報表、供應商比價、報價轉銷售訂單仍未實作（見 `MVP_CHECKLIST.md`）

## ⚠️ 儲存庫可見性

本專案包含**真實的壓克力單價表與加工成本費率**（`backend/app/ai/quote_engine.py`）。
若 GitHub 儲存庫設為 Public，任何人都能看到你的成本結構。
建議改為 Private：Settings → General → Danger Zone → Change repository visibility。

---

## 版本紀錄

> 每次做過「真實執行驗證」（真實 PostgreSQL ＋ 真實 HTTP request，非靜態推論）後的修正，
> 一律記錄於此，作為唯一事實來源（single source of truth）。
> **修正完務必同步回填 `MASTER_SPEC.md` 與 `MVP_CHECKLIST.md`**，避免版本分岔。
>
> v1.0–v1.9 的交付物為 `acrylic-erp-verified.zip`；**v2.0 起改以 git 儲存庫
> `zev-666/HankERP` 為單一事實來源**，不再用 zip 傳遞版本——分散在多個 zip、
> 各檔案版本又不同步，正是 v2.0 要解決的問題本身。

### v2.0（2026-09-14）— 三份檔案合併整合 ＋ 補上斷掉的業務流程

**背景**：先前的交付分散在三個 zip，且各檔案版本不同步（README 最新在一包、
MASTER_SPEC／MVP_CHECKLIST 最新在另一包、兩份程式碼 zip 內容不同）。
本版把各檔案的最新版本合併為單一 repo（`zev-666/HankERP`），
並針對 MVP_CHECKLIST 自己標為 ❌ 的功能缺口實際動手補完，不再只是誠實記載它壞掉。

#### A. 本輪重新量測後發現的「文件數字再度過期」

| 文件宣稱 | 實測 | 原因 |
|---|---|---|
| 62 個業務端點（＋/health 共 63） | **61 個（＋/health 共 62）** | v1.7 資安稽核移除了 `POST /auth/setup-admin`，端點數從此少一個，但三份文件都沒回頭重數 |
| 108 個檔案（63 Python ＋ 25 TS/TSX） | **110 個（64 Python ＋ 25 TS/TSX）** | v1.7–v1.9 陸續新增 `rate_limit.py`、`requirements-dev.txt` 等檔案後未更新 |
| RBAC 8 種角色 | 規格書規劃 **9 種**，`seed_data.py` 只建 8 種 | 品管（qc）角色從 v1.0 起就沒進過資料庫 |
| npm audit 0 vulnerabilities（v1.4 時屬實） | **3 項（2 high ＋ 1 critical）** | 時間過去一個月，Next.js 16.3.1 被揭露 RCE 漏洞（GHSA-p293-qw3h-jr36 / GHSA-2xp9-vwfh-vxw4），sharp 與 js-yaml 亦有新漏洞 |

**這正是本專案反覆出現的同一種錯誤**：把上一版文件寫的數字當成已驗證事實。
「npm audit 0 漏洞」這一項尤其值得記住——它在寫下的當天是真的，
但**安全性稽核結果有保鮮期**，任何一次交付前都必須重跑，不能引用一個月前的結論。

**修正**：Next.js 16.3.1 → **16.3.5**，sharp、js-yaml 同步更新，`npm audit` 回到 0 vulnerabilities。
所有數字重新量測後更新至三份文件（量法見 `CONTRIBUTING.md`）。

#### B. 補完先前誠實標記為 ❌ 的功能缺口

**B-1　線上詢價表單真的會送出了**

先前 `/quote` 頁面的送出按鈕只有 `setSubmitted(true)` 切換前端畫面，
**沒有任何 API 呼叫**——客戶填完按送出，畫面顯示「詢價已送出」，
但資料直接消失，業務端永遠看不到。對一家把官網當業務入口的工廠，這是最貴的一個缺口。

- 新增 `inquiries` 資料表與 `app/modules/inquiries/`（model → schema → router）
- `POST /api/v1/public/inquiries`：公開端點，套 `@limiter.limit("5/hour")`，
  `tenant_id` 由後端決定不接受前端傳入（防跨租戶寫入），所有欄位有長度上限
- `GET /api/v1/inquiries`：後台列表，附各狀態筆數；`PATCH /{id}/status` 更新處理狀態
- `POST /api/v1/inquiries/{id}/convert-to-customer`：一鍵帶入 customers 主檔，**冪等**
  （已轉換過的詢價再呼叫只回傳既有客戶，不會重複建立）
- 前端新增 `/erp/inquiries` 詢價管理頁（狀態篩選、詳情彈窗、轉客戶）

**B-2　官網作品展示不再是寫死的假資料**

先前 `(public)/page.tsx` 的案例區塊是程式碼裡的 `const CASES = [...]` 四筆固定內容，
後台無論發佈什麼，官網永遠顯示同樣四筆；而 `(public)/portfolio/` 是個**空資料夾**，
官網根本沒有作品展示頁可以點進去。

- 首頁改為 Server Component 讀取 `/api/v1/public/portfolio`，無資料時顯示空狀態而非假資料
- 新增 `/portfolio` 列表頁與 `/portfolio/[slug]` 詳情頁（含 `generateMetadata` 動態 SEO）
- 新增 `/erp/portfolio` 後台作品管理頁（建立草稿 → 發佈到官網 → 官網即時可見）
- 新增 `src/lib/publicApi.ts`：後端不可用時降級為空清單，**確保後端沒開前端仍能 build**

**B-3　工單發料與完工入庫（MVP_CHECKLIST 自列的「最高優先」斷點）**

生產模組與庫存模組先前各自運作正常，但兩者從未串接：工單領了料庫存不會動，
工單完工成品不會進倉，等於 ERP 最核心的「料帳合一」是斷的。

- `POST /work-orders/{id}/issue-materials`：依備料清單扣減 RAW 倉庫存，寫入 ISSUE 異動紀錄。
  設計上**先全部檢查再全部扣帳**，任一項不足就整批拒絕（HTTP 409）並回傳缺料清單
  ——不做部分發料，因為部分發料會讓現場拿到不完整的料，且資料庫留下難以回溯的半成狀態。
  只發尚未發足的差額，因此重複呼叫是安全的。
- `POST /work-orders/{id}/complete`：全部工序完成後，成品入 FG 倉、工單轉 completed。
  入庫數預設取**最後一道工序**的良品數，而非各工序良品數加總（加總會嚴重灌水）。
- **資料庫結構變更**：`inventory_balances` 與 `inventory_transactions` 新增 `product_id`
  並將 `material_id` 改為可空，以 CHECK 約束保證兩者恰有一個有值。
  原因：成品屬 `products` 主檔而非 `materials` 主檔，原 schema 只認得物料，
  「完工入庫」在資料模型上根本做不出來——這不是實作偷懶，是規格層面的缺口。
  `work_orders` 新增 `completed_qty` 記錄實際入庫數。
- 前端 `/erp/production` 加上「發料」「完工入庫」按鈕，庫存不足時把缺料明細攤開給倉管看

**B-4　其他補齊**

- 新增 `/about` 關於我們＋設備介紹頁（先前標記 ❌）
- 新增 `app/sitemap.ts`（動態納入每一則已發佈作品）與 `app/robots.ts`
  （`/erp/`、`/mes/`、`/login` 不予索引）——先前 SEO 項目標記 ❌
- `seed_data.py` 補上品管（qc）角色，與 MASTER_SPEC 第九章的 9 種角色規劃一致

#### C. 本輪新發現並修復的 bug

**bug#14（阻斷性，前端）：Next.js 16 的動態路由參數是「未解碼」的**

`/portfolio/[slug]` 詳情頁一律回 404。追查後確認：Next.js 16 傳給 page 的
`params.slug` 是**原始未解碼的路徑片段**（`%E5%BD%A9%E5%A6%9D-123` 而非 `彩妝-123`），
而作品 slug 會保留中文字元（`_slugify` 保留 `一-鿿`），
於是再做一次 `encodeURIComponent` 就變成雙重編碼，後端查不到。

**怎麼確認的**：沒有靠猜。建立一個臨時的 probe 頁面直接把 `params.slug` 原樣印出來，
用真實 HTTP request 取得結果 `RAW:%E5%9C%8B%E9%9A%9B-123|LEN:22`，確認長度 22
（已解碼的中文只會是 6 個字元），才確定是編碼問題而非路由或後端問題。
順帶記錄一個 Next.js 慣例：以 `_` 開頭的資料夾是 private folder，不會產生路由——
第一次 probe 取名 `__probe` 完全沒出現在 build 的 Route 表，改名後才生效。

**修正**：`getPublicCase()` 先 `decodeURIComponent` 再重新編碼（對已解碼的 ASCII slug 也安全）。
**驗證**：真實 `next start` 後 curl 詳情頁，HTTP 200 且頁面內確實出現該筆案例的
「成果」「作法」「尺寸」文字。

**bug#15（阻斷性，本機開發）：`seed_data.py` 在容器外一律失敗**

v1.4 的 bug#13 只在 `backend/Dockerfile` 加了 `ENV PYTHONPATH=/app`，
容器內可行，但任何人在本機照文件執行 `python scripts/seed_data.py` 仍然
`ModuleNotFoundError: No module named 'app'`。修正方式改為在腳本內自我修補 `sys.path`，
容器與本機兩條路徑都不再依賴外部環境變數。
**驗證**：完全不設 PYTHONPATH，直接 `./venv/bin/python scripts/seed_data.py` 成功建立 9 種角色。

**bug#16（資料完整性，開發體驗）：`seed_data.py` 重跑會炸**

先前每執行一次就多一個租戶、多一組角色，第二次因 email unique 約束直接
`IntegrityError`，而錯誤訊息完全看不出「其實你已經建過了」。
改為先檢查租戶是否存在，已存在則印出現況並跳過。
**驗證**：連續執行兩次，第二次正確印出「種子資料已存在，未重複建立（角色 9 種）」。

**bug#17（前端錯誤處理）：結構化錯誤明細被吃掉**

`lib/api.ts` 的 `throw new Error(err.detail)` 在 `detail` 是物件時會變成
`[object Object]`，呼叫端拿不到任何明細。發料庫存不足時後端回傳的缺料清單
就是這種結構化 detail，倉管只會看到一句「失敗」而不知道缺什麼、缺多少。
改為物件時序列化成 JSON 字串，由呼叫端 parse 後顯示明細。

#### D. 程式碼品質與工程基礎建設

- **ESLint 4 個 warning 全部清掉**（v1.4 起就記載但一直沒處理）：
  `erp/layout.tsx`、`mes/layout.tsx` 補上 `useEffect` 依賴陣列；
  `lib/api.ts`、`store/auth.ts` 的 `window.location.href` 加上具名 disable 註解並
  寫清楚理由（登出／401 時**刻意**整頁重載，以清空 TanStack Query 快取，
  避免下一位使用者在同一台現場平板上看到前一位的資料）。現在 `eslint . --max-warnings=0` 通過。
- **新增 `.github/workflows/ci.yml`**：CI 不只跑單元測試，而是真的起 PostgreSQL 16 ＋ Redis、
  跑 migration、seed、啟動 uvicorn，再用真實 HTTP request 走完詢價與工單全流程，
  並印出當下實際的端點數——讓「文件數字過期」這類問題在 CI 就被抓到。
  前端 job 另跑 `eslint --max-warnings=0`、`npm run build`、`npm audit --audit-level=high`。
- **新增 `backend/scripts/verify_e2e.py`**：把本輪的端到端驗證固化為可重複執行的腳本，
  任一項失敗以 exit code 1 結束，本機與 CI 共用同一份。
- **新增 `CLAUDE.md`**：整合工程開發規則與 ERP 顧問決策框架
  （先確認值不值得做，再決定寫不寫程式；Must/Should/Could/Won't 分級；數字必須標明來源）。
- **新增 `CONTRIBUTING.md`**（環境、檢查清單、各項數字的量法）、
  **`LICENSE`**（專有授權＋儲存庫可見性風險提醒）、`.gitignore` 補強。

#### E. 本輪的驗證方式

全程使用全新 PostgreSQL 16 資料庫 ＋ 全新 Python venv ＋ 全新 `npm ci`，非沿用殘留環境：

| 驗證項目 | 方法 | 結果 |
|---|---|---|
| 資料表 | 真實 migration 後查 `information_schema.tables` | 30 張業務表 ＋ `alembic_version` |
| 單元測試 | `pytest -q` | 17 passed |
| API 端點 | 真實啟動 uvicorn 讀 `/openapi.json` | 68 業務端點 ＋ `/health` = 69，13 個模組 |
| 前端建置 | 真實 `npm run build` 讀 Route 表 | 23 條路由（21 靜態 ＋ 2 動態），0 錯誤 |
| 前端 lint | `eslint . --max-warnings=0` | 0 error 0 warning |
| 相依套件安全性 | `npm audit` | 0 vulnerabilities |
| 端到端業務流程 | `scripts/verify_e2e.py`，真實 HTTP ＋ 直接查資料庫 | 13 個情境全通過 |
| 官網前後端串接 | 真實 `next start` ＋ curl HTML，確認 API 內容出現在頁面裡 | 首頁／列表／詳情／sitemap 全部確認 |
| 種子資料 | 不設 PYTHONPATH 直接執行，並連續執行兩次 | 9 種角色建立成功，第二次正確跳過 |

端到端腳本涵蓋的 13 個情境包含這些**故意要失敗**的案例，確認擋得住：
庫存不足時發料被整批拒絕且庫存數字完全沒動、工序未完成時不准完工入庫、
已完工的工單不准重複入庫、詢價重複轉客戶不會重建客戶。

### v1.9（2026-08-31）

**修正項目：Celery worker基礎設施稽核，發現task從未被真正註冊過的根本性bug**

- **問題1（本輪最重要）**：`backend/app/tasks/celery_app.py`的
  `celery_app.autodiscover_tasks(["app.tasks"])`命名慣例與實際檔案`nesting_tasks.py`
  不符（Celery預期在`app.tasks.tasks`這個子模組找task，但檔名是`nesting_tasks.py`），
  導致**真正啟動`celery -A app.tasks.celery_app worker`後，worker完全不知道
  `calculate_nesting_async`、`batch_optimize_multiple_orders`這兩個task存在**。
  若之後真的接上`.delay()`呼叫，worker會回報`NotRegistered`錯誤，任務永遠執行不了。
  **修復**：改用明確`from app.tasks import nesting_tasks`確保task被註冊，不依賴
  autodiscover的命名慣例。
- **問題2**：`nesting_tasks.py`的`calculate_nesting_async`用`Part(**p)`直接建構，
  若呼叫端傳入的`parts_data`缺少`label`欄位會直接`TypeError`崩潰。
  **修復**：補上`label`預設值，未提供時自動沿用`id`。
- **問題3**：`v1.7`資安稽核新增的`docker-compose.yml`的`SECRET_KEY`必填機制，
  README「快速啟動」步驟1未同步補上建立根目錄`.env`的步驟，照文件操作會在步驟2卡住。
  已補上步驟1.1。同時移除README長期存在但程式碼從未實作的「MinIO」相關敘述。
- **問題4**：`main.py`與`auth/router.py`各自建立獨立的`Limiter`實例，架構不一致
  （雖然基本計數行為仍正常運作，但`slowapi`例外處理讀取`Retry-After`等標頭時
  使用的是`app.state.limiter`，跟實際觸發限制的實例不同，屬於脆弱設計）。
  已改用共用單一實例（新增`app/rate_limit.py`）。
- **問題5**：Celery worker設定缺少明確的`broker_connection_retry_on_startup`，
  導致啟動時出現`CPendingDeprecationWarning`（Celery 6.0起此設定的預設行為會改變）。
  已明確設定為`True`消除警告並future-proof。

**額外驗證（回應「測試用solo pool，正式部署用prefork/concurrency=4是否行為一致」的疑慮）**：
先前驗證僅用`--pool=solo`啟動worker測試，與`docker-compose.yml`實際使用的
`celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4`（預設prefork多進程池）
存在差異，兩者的task分派/執行機制不同，不能假設solo測過等於prefork沒問題。
已改用與部署完全一致的指令重新測試：確認`concurrency: 4 (prefork)`正確啟動、
單一任務與4個任務同時並行送出皆正確完成（`received`與`succeeded`各5次，數字吻合）；
另確認`docker-compose.yml`的`celery`服務與`backend`服務共用同一份`Dockerfile`
（已修正為非root使用者執行），沙盒測試中出現的root警告僅為測試環境限制，
不影響實際容器化部署行為。

**如何抓到的**：使用者持續要求「繼續除錯」，這次刻意去驗證先前從未真正測試過的角落——
不是只呼叫task的底層函式邏輯（那樣會繞過Celery的task registry機制），而是**真正啟動
`celery -A app.tasks.celery_app worker`背景程序**，才發現`[tasks]`清單是空的。

**驗證方式**：真實安裝Redis + PostgreSQL，真正啟動`celery worker`程序（非模擬），
確認`[tasks]`啟動日誌列出兩個task；用`.delay()`送出兩種情境（缺label／有label）的
真實任務，確認worker端`received`→`succeeded`且回傳結果正確；同時完整回歸12業務模組
真實HTTP測試、17項pytest、前端16頁面build，確認本輪修正未影響既有功能。

### v1.8（2026-08-26）

**修正項目：v1.7資安稽核後，重新從頭驗證時發現的3個遺漏問題**

- **問題1**：`pip`（Python套件安裝工具本身）24.0版有新公告的CVE（PYSEC-2026-3721）。
  雖非執行期依賴（僅建置階段使用），仍於`backend/Dockerfile`加入`RUN pip install --upgrade pip`
  升級至26.2.1，`pip-audit`確認零已知漏洞（先前需忽略的6項也不再需要忽略）。
- **問題2（本輪最重要）**：v1.7新增的`docker-compose.yml`資安機制要求根目錄`.env`必須設定
  `SECRET_KEY`，但README.md「快速啟動」步驟1**從未提及要建立這個根目錄`.env`檔案**，
  只照著README步驟操作會在步驟2卡住並看到`SECRET_KEY is missing a value`錯誤。
  已補上步驟1.1，包含產生隨機密鑰的指令與說明。
- **問題3**：README.md長期提及「MinIO」服務（啟動訊息、控制台網址），但`docker-compose.yml`
  與程式碼中從未真正實作MinIO物件儲存，`MEDIA_ROOT`設定值也沒有對應的檔案上傳邏輯，
  純屬規劃階段的文件殘留，已移除並加註說明避免誤導。

**如何抓到的**：使用者要求「從頭到尾再跑一遍」，這次刻意完全照README步驟本身操作
（而非用已知有效的捷徑指令繞過），才重現「照文件操作會卡住」這個問題——先前多輪驗證
都是我自己手動組出正確指令執行，沒有逐字照README走過一次，因此沒發現文件本身的步驟缺漏。

**驗證方式**：完全依照修正後的README步驟1→1.1→2逐字操作（複製3個`.env`檔案、
產生密鑰、`docker compose config`成功解析），並重新跑一次migration（30張表）+
pytest（17項）確認功能無破壞。

### v1.7（2026-08-21）— 資安漏洞稽核

**執行完整資安檢查：自動化依賴掃描 + Python靜態分析 + 手動審查常見Web漏洞，
發現並修正9項真實資安問題，全數用真實工具驗證修正生效且未破壞既有功能。**

| # | 類別 | 問題 | 嚴重度 | 修正 |
|---|---|---|---|---|
| 1 | 依賴漏洞 | `python-jose 3.3.0`有演算法混淆攻擊CVE歷史，且transitive依賴`ecdsa`套件有維護者明確表示不修復的timing attack漏洞（PYSEC-2026-1325） | 🔴 高 | 換成`PyJWT 2.13.0`，消除`ecdsa`依賴（專案只用HS256，從未需要橢圓曲線演算法） |
| 2 | 依賴漏洞 | `starlette`（fastapi 0.109.2的transitive依賴）多項CVE | 🔴 高 | 升級`fastapi`至0.135.0，取得無版本上限的starlette修復版本 |
| 3 | 依賴漏洞 | `python-multipart 0.0.9`多項CVE | 🟡 中 | 升級至0.0.31 |
| 4 | 依賴漏洞 | `pillow 10.2.0`多項CVE，且**完全未被程式碼使用**（確認過的規劃中功能） | 🟡 中 | 直接移除套件，消除攻擊面而非升級 |
| 5 | 身份驗證 | `POST /api/v1/auth/setup-admin`端點**完全沒有身份驗證保護**，任何人可對外呼叫，用寫死的密碼`Admin@2025!`搶先建立管理員帳號，與官方`scripts/seed_data.py`機制重複且更不安全 | 🔴 極高 | 直接移除此端點 |
| 6 | 敏感資訊洩漏 | `POST /forgot-password`任何環境下都會在回應中直接回傳`dev_only_token`，等於不需要真的收到email就能取得密碼重設token（帳號接管風險） | 🔴 高 | 改為只在`ENVIRONMENT != production`時才回傳，正式環境自動移除 |
| 7 | 設定管理 | `SECRET_KEY`預設值為`"dev-secret-key"`且寫死於`docker-compose.yml`，若忘記更換，JWT可被任意偽造 | 🔴 極高 | `config.py`加上啟動期防呆：`ENVIRONMENT=production`時若偵測到預設弱密鑰或長度<32字元，直接拋出`RuntimeError`拒絕啟動；`docker-compose.yml`改為`${SECRET_KEY:?...}`必要變數，未設定直接無法啟動容器（雙層防護） |
| 8 | 網路曝露 | `docker-compose.yml`中PostgreSQL（5432）與Redis（6379）直接對外曝露port，Redis預設無身份驗證機制，是已知的高風險錯誤設定類型 | 🔴 高 | 移除對外`ports`設定，僅供Docker內部網路存取；保留註解說明本機除錯時如何安全地暫時開放（綁定`127.0.0.1`） |
| 9 | 缺乏防護 | 完全沒有Rate Limiting，`/login`可被無限次嘗試密碼進行暴力破解 | 🟡 中 | 加入`slowapi`，`/login`限制5次/分鐘、`/register`限制10次/小時、`/forgot-password`限制3次/小時 |

**其餘檢查項目（確認無問題，未修改）**：
- SQL注入：全專案查詢皆透過SQLAlchemy ORM參數化查詢，無raw SQL字串拼接，零風險
- XSS：前端未使用`dangerouslySetInnerHTML`，零風險
- 密碼強度政策：已有最低8碼+需含數字的驗證規則
- `.gitignore`：已正確排除`.env`等機敏檔案
- Bandit靜態分析：修正前2項Low signal，修正後**零問題**

**額外強化項目（非漏洞修復，屬防禦縱深）**：
- 正式環境自動關閉`/docs`、`/redoc`、`/openapi.json`，避免完整API結構被公開偵查
- CORS白名單改為環境變數控制，不再寫死於程式碼
- `backend/Dockerfile`、`frontend/Dockerfile`皆加上非root使用者執行容器，降低容器逃逸風險影響範圍
- `frontend/next.config.js`加上標準安全標頭（X-Frame-Options、X-Content-Type-Options、Referrer-Policy、Permissions-Policy、Strict-Transport-Security）
- 移除`next.config.js`中未使用、範圍過寬（萬用字元`https://**`）的`images.remotePatterns`設定

**驗證方式**：
- `pip-audit`修正前後對照：44個已知漏洞（5個套件）→ 0個（應用程式依賴部分，pip自身漏洞不計入因非執行期依賴）
- `bandit`靜態分析：2個Low → 0個
- `npm audit`：0 vulnerabilities（前端本就乾淨，維持不變）
- 真實PostgreSQL + 真實uvicorn + 真實登入流程（非繞過驗證）：JWT簽發/驗證、錯誤密碼拒絕、偽造簽章拒絕、無token拒絕，全數正確
- 實測模擬暴力破解：連續6次錯誤登入，第6次正確被`429 Too Many Requests`擋下
- 實測正式環境防呆：用預設弱密鑰+`ENVIRONMENT=production`啟動，正確被`RuntimeError`拒絕；用真正安全密鑰啟動則正常運作且`/docs`回傳404
- 實測`docker-compose.yml`：真實Docker daemon的`docker compose config`驗證語法正確、變數替換正確、缺少`.env`時正確拒絕並給出清楚錯誤訊息
- 17項pytest測試、16頁面前端build、核心業務端到端流程（裁切、報價含資料持久化）：全數重新回歸測試通過，確認資安修正未破壞既有功能

**檔案數變動**：新增專案根目錄 `.env.example`（供 `docker-compose.yml` 的 `SECRET_KEY`/`CORS_ORIGINS`/`DB_PASSWORD` 變數替換使用，與 `backend/.env.example`、`frontend/.env.local.example` 是不同檔案），
檔案總數 108 → **109**。

### v1.6（2026-08-19）

**修正項目：使用者指出前幾輪反覆小修小補的方式在浪費時間，要求完整重跑一次從零驗證，
一次修完不要再分批交付。這輪抓到本專案史上最大的一個文件錯誤：「52個API端點」從
v1.0基準版本開始就是錯的，真實數字是62個，六輪對話（v1.0~v1.5）都沒人抓到**

- **問題（本輪最重大發現）：「52個API端點」錯誤數字，橫跨全部版本歷史從未被抓到**。
  用三種完全獨立的方式交叉驗證，結果一致：①grep所有`@router`/`@public_router`裝飾器
  （含容易被漏掉的`portfolio`模組獨立`public_router`實例）：62個 ②Python精確解析每個
  router的`prefix`+路徑組合：62個業務端點+1個`/health`共63個 ③**最權威**：真實啟動
  uvicorn，直接讀取FastAPI自動產生的`/openapi.json`schema逐一列出：63個。三種方法完全
  一致，證實「52」這個數字從未被真正驗證過，只是從v1.0基準的原始claim一路複製到v1.5，
  期間即使我在v1.3/v1.4/v1.5多次重新驗證其他數字（檔案數、頁面數）時，都沒有回頭驗證
  這個端點數字本身，是本專案「驗證盲區複製」問題最嚴重的一次案例。
  **修正**：README.md/MASTER_SPEC.md/MVP_CHECKLIST.md全部改為「62個業務API端點
  （不含/health，共63個HTTP端點）」。

- **次要澄清（非錯誤，是容易混淆的地方）**：「12業務模組」不等於`app/modules/`資料夾數
  （實際只有10個資料夾+獨立的`app/auth/`=11個程式碼模組）。「12」是MASTER_SPEC最初規劃的
  **概念性**業務模組清單（含「官方網站」「CNC與雷射加工管理」「剩料回收管理」等沒有獨立
  backend資料夾、而是分散實作在其他模組裡的項目），不是資料夾計數，容易讓人誤解，
  已在MASTER_SPEC加註說明避免混淆。

**驗證方式**：這次採用「先完整审计、收集全部問題、一次性修正、最後只打包驗證一次」的
流程，不再邊發現邊改邊生成檔案。第一階段用三種獨立方法交叉驗證端點數（grep正規表達式、
Python精確解析、FastAPI真實OpenAPI schema），確認62/63這個數字後才進入文件修正階段，
修正完所有已知問題後，才重新打包並在全新獨立環境驗證一次，只生成一次最終檔案。

### v1.5（2026-08-18）

**修正項目：使用者指出前幾輪文件可能仍有不實宣稱，重新逐項稽核後，確認抓到3個真實的
「文件宣稱與程式碼實際內容不符」問題——這些不是新bug，是文件本身寫錯或誇大**

- **問題1（本輪最重要的發現）：「17個頁面」的數字從v1.0基準版本就是錯的，
  一路延續到v1.4都沒被抓出來**。實際用`npm run build`真實輸出核對，
  Next.js的路由生成結果明確顯示`(16/16)`，逐一清點`src/app/`底下的`page.tsx`
  檔案也確認只有15個+Next自動產生的`/_not-found`＝16個路由，不是17個。
  本輪之前的v1.3、v1.4我都只是延續README原本「17個頁面」的舊宣稱去驗證
  「build有沒有過」，卻沒有回頭核對「17」這個數字本身對不對——這是我的疏失，
  不是新產生的bug，是舊的文件錯誤沒被抓到，現已在README/MASTER_SPEC全部改為16。

- **問題2：README模組對照表宣稱「作品展示系統…官網首頁讀取」，但實際上
  `src/app/(public)/page.tsx`的案例展示區塊是**寫死在程式碼裡的4筆假資料**
  （`const CASES = [...]`），完全沒有呼叫`/api/v1/public/portfolio`。
  後端API本身沒問題（已用真實HTTP request測過），但前後端**沒有串接**，
  首頁看到的案例永遠是同樣4筆固定內容，不會反映後台CMS實際發布的作品。
  另外`src/app/(public)/portfolio/`資料夾裡沒有`page.tsx`，是空資料夾，
  代表官網根本沒有獨立的「作品展示頁」可以點進去看，只有首頁那4筆假資料。
  已修正README模組對照表描述，並在MVP_CHECKLIST.md補充說明。

- **問題3（提醒性質，非新發現）：`/quote`線上詢價表單的送出按鈕只有
  `setSubmitted(true)`切換前端UI狀態，沒有任何API呼叫**，代表使用者填完表單
  按送出後，資料不會被儲存、不會有email通知、業務端完全看不到。
  這件事MVP_CHECKLIST.md先前已用⚠️標記「送出邏輯未逐一驗證」，這次是把
  「未逐一驗證」講得更明確：不是「還沒驗證所以不確定」，是驗證後**確認送出邏輯
  根本不存在**，屬於功能缺口而非驗證缺口，措辭已更正。

**如何抓到的**：使用者對v1.4的交付結果表示不信任，要求重新自我稽核。
這次沒有只回頭檢查程式碼能不能編譯/測試能不能過（那些已經反覆驗證過，
結果一直是對的），而是改為**逐一核對文件裡的「敘述性宣稱」跟實際程式碼內容
是否相符**——例如「首頁讀取portfolio」這種功能性描述，光是build成功、
API測試回200，並不代表這句話是真的，必須直接讀取前端原始碼裡有沒有
真的呼叫該API，才能確認宣稱屬實。這是先前幾輪驗證的方法論死角：
只驗證「能不能跑」，沒驗證「文件講的功能是不是真的存在」。

**驗證方式**：直接讀取`src/app/`下所有`page.tsx`原始碼，逐一搜尋
`useQuery`/`fetch`/`axios`/`api.`呼叫模式，確認每個頁面是否真的有串接後端；
10個ERP頁面（analytics/customers/dashboard/equipment/inventory/nesting/
production/products/purchasing/quotations）全部確認有真實API呼叫，
login頁面確認有呼叫`api.login()`，僅公開首頁的portfolio區塊與詢價表單
送出邏輯這兩處是純前端假動作。

### v1.4（2026-08-17，同日第二輪）

**修正項目：前端Next.js大版本升級至16.3.1（徹底解決npm audit最後一項漏洞），
並在升級過程中發現並修復第3個新bug（#13：backend/Dockerfile缺少PYTHONPATH）**

- **前端大版本升級**：`next` 14.2.35 → **16.3.1**，`eslint` 8.x → **9.x**（Next16的
  `eslint-config-next`要求`eslint>=9.0.0`），`eslint-config-next`同步升到16.3.1。
  **驗證**：`npm install`乾淨解析無衝突 → `npm run build`真實跑過，16頁面零錯誤編譯（實際路由：15個page.tsx+Next自動產生的/_not-found）
  （Next16改用Turbopack建置）→ `npm audit`從「1項需跨大版本才能解決的漏洞」變成
  **0 vulnerabilities**。

- **Next16破壞性變更處理**：
  - `next lint`指令在Next16已被移除（CLI指令清單裡已無`lint`），原本`package.json`
    的`"lint": "next lint"`會直接失敗。已改用ESLint 9的flat config：新增
    `frontend/eslint.config.mjs`直接引入`eslint-config-next`的扁平設定匯出，
    `lint`腳本改為`eslint .`，真實跑過確認可運作（0 errors，4個既有warning原樣呈現，
    未動程式碼邏輯——這4個warning屬於既有程式碼的`useEffect`依賴陣列與
    `window.location.href`用法，不在本次「大版本升級」範圍內一併重構，
    詳見下方「後續可優化方向」）
  - `tsconfig.json`的`jsx`設定被Next16建置流程自動從`preserve`改為`react-jsx`
    （Next16要求React automatic runtime），這是建置工具自動完成的必要調整，非人工手動改動

- **bug#13（阻斷性，本輪新發現）**：`backend/Dockerfile`沒有設定`PYTHONPATH`。
  README步驟`docker compose exec backend python scripts/seed_data.py`
  （建立管理員帳號與8種角色種子資料的必要步驟）在真實容器環境下會直接
  `ModuleNotFoundError: No module named 'app'`——因為Python直接以檔案路徑執行
  `.py`腳本時，`sys.path[0]`會是該腳本自己所在的`scripts/`目錄，而不是Docker的
  `WORKDIR /app`，這跟v1.3修復的`alembic.ini`bug#11是同一類路徑問題的不同發生點。
  **修復**：`Dockerfile`加入`ENV PYTHONPATH=/app`。
  **驗證**：不能用「指令列手動加PYTHONPATH」這種方式驗證（那樣沒意義，因為Docker
  容器裡使用者不會手動加），而是**匯出持久性環境變數**模擬Docker `ENV`指令的效果，
  用venv裡的python執行`python scripts/seed_data.py`（不在指令上加任何前綴），
  確認8種角色與管理員帳號正確建立；並接續测试登入取得JWT、建立customer、
  bug#12回歸測試（final_price=4440正確）、bug#6回歸測試（products端點200）全數通過。

- **既有bug回歸測試（本輪第二次獨立驗證環境）**：bug#11（alembic migration）、
  bug#12（報價單手動定價）、bug#6（products路由註冊）皆在**另一個全新的獨立目錄**
  （非v1.3驗證時用的目錄）重新確認未復發。

**驗證方式**：與v1.3相同的「全新環境三重驗證」原則——本輪額外新增一個完全獨立的
`final_v2`驗證目錄（第4個獨立驗證環境，累計本專案歷史上已用超過4組全新
PostgreSQL+venv+npm環境交叉驗證過）。

### v1.3（2026-08-17）

**修正項目：發現並修復2個新的真實bug（#11、#12），補齊pytest依賴缺口，前端安全性更新，建立缺失的.gitignore**

此輪從完全乾淨環境（新裝PostgreSQL 16 + Redis + 全新Python venv + 全新npm install）重跑
一遍完整流程，並在流程中發現以下問題：

- **bug#11（阻斷性）**：`backend/alembic.ini` 缺少 `prepend_sys_path = .`。
  照README步驟執行 `alembic upgrade head`（無論在docker容器內或本機）會直接
  `ModuleNotFoundError: No module named 'app'`，因為cwd不會自動被加入sys.path。
  **修復**：`alembic.ini`加入`prepend_sys_path = .`。
  **驗證**：不設PYTHONPATH環境變數、完全比照README指令重跑，確認29張表成功建立。

- **bug#12（極高，資料完整性）**：`quotation/router.py` 建立報價單時，若品項使用
  `unit_price`手動定價（業務不透過AI試算），該品項金額不會被計入報價單header的
  `final_price`，導致PDF匯出時「品項顯示888元、總額顯示0元」的資料矛盾。
  根本原因：`total_material`/`total_processing`只在`item.unit_price is None`
  （AI自動試算）分支才累加，手動定價分支完全沒有累加任何東西進總額。
  **修復**：改用「所有品項小計（unit_price×quantity）加總」作為header的final_price，
  不論該品項是AI試算或業務手動定價都會正確計入。
  **驗證**：分別測試純AI試算/純手動定價/兩者混合單，並直接查資料庫核對，
  三種情境final_price數字均正確（純手動5件×888=4440；混合單200+928.85=1128.85）。

- **測試依賴缺口**：`requirements.txt`從未包含`pytest`，乾淨環境（無殘留全域套件）
  下`pip install -r requirements.txt`後直接跑`pytest`會找不到指令。
  **修復**：新增`backend/requirements-dev.txt`（`-r requirements.txt` + pytest +
  pytest-asyncio），生產映像檔不受影響，開發/CI環境另外安裝即可。

- **前端安全性**：`npm install`時警告`next@14.1.0`存在已知安全漏洞
  （官方2025-12-11公告）。已升級至同一大版本內最新的修補版`14.2.35`
  （真實查詢npm registry確認），並重新跑`npm run build`確認16頁面仍零錯誤編譯。
  註：`npm audit`顯示還有一項需升級至Next 16（跨大版本）才能完全解決的漏洞，
  Next 14→16屬breaking change，需要專門的App Router回歸測試，
  此輪判斷不在未經確認的情況下貿然跨大版本升級，列入下方「後續可優化方向」。

- **專案衛生**：專案根目錄原本完全沒有`.gitignore`，代表若照README指示`git push`，
  `.env`（含資料庫密碼）、`node_modules`、`venv`都會被誤傳上GitHub。已建立`.gitignore`
  涵蓋機敏檔案、Python/Node產物、編輯器與OS暫存檔。

- **既有bug回歸測試**：本輪同時對v1.0/v1.1已修復的bug（#1大小寫、#6路由註冊、
  #7報價dict展開順序）重新用真實HTTP request測試，確認皆未復發。

**驗證方式**：全程使用全新PostgreSQL 16使用者/資料庫、全新Python venv、全新npm install，
非沿用先前對話的殘留環境；且最終將修好的內容打包成zip後，**重新解壓縮到另一個獨立目錄，
從零建立第二個venv、第二個資料庫，重跑一次migration+pytest+API測試**，確認zip本身
（而非開發過程中的工作目錄）就是可用的成品。

### v1.2（2026-08-13）

**修正項目：完整補齊 v1.0 遺漏的 9 個歷史bug詳細記錄，並同步三份文件（README.md / MASTER_SPEC.md / MVP_CHECKLIST.md）與zip實際內容一致**

此版本無程式碼變更，純文件同步。詳細bug清單見下方「v1.0 完整bug清單」。

### v1.1（2026-08-12）

**修正項目：`backend/alembic/env.py` 忽略 `.env` 設定**

- **問題**：`env.py` 從未讀取 `app.config.settings.DATABASE_URL`，連線字串永遠使用
  `alembic.ini` 裡寫死的 `postgresql+asyncpg://erp_user:erp_pass_2025@localhost:5432/acrylic_erp`。
- **實際影響**：`docker-compose.yml` 中 backend 容器的 `DATABASE_URL` host 為 `db`
  （docker 內部服務名稱），與 `alembic.ini` 寫死的 `localhost` 不一致，導致
  `docker compose exec backend alembic upgrade head`（README第3步）連線失敗。
- **為何先前驗證未發現**：先前測試沿用與 `alembic.ini` 預設值相同的資料庫使用者名稱/密碼，
  巧合繞過此問題；本次驗證刻意更換使用者名稱（`acrylic_erp` 取代 `erp_user`），才重現此錯誤。
- **修復方式**：`env.py` 內於 `fileConfig()` 之後、`target_metadata` 定義之前，
  加入 `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)`，
  強制以 `.env` / 環境變數為連線字串唯一來源。
- **驗證方式**：真實安裝 PostgreSQL 16、刻意建立與 `alembic.ini` 預設值不同的資料庫使用者
  （`acrylic_erp` / `different_pass_2026` / `acrylic_erp_bugcheck`），修正前重現連線失敗
  （`InvalidPasswordError: password authentication failed for user "erp_user"`），
  修正後重跑確認29張業務表 + `alembic_version` 共30張表成功建立於正確資料庫；
  逐檔案比對確認除 `env.py` 外其餘100個檔案內容與前版完全一致。
- **交叉驗證**：與另一獨立對話框各自驗證出的修正邏輯完全等價，且兩份zip除 `env.py` 外其餘
  100個檔案逐檔比對完全一致，互相印證結果可信。
- **影響範圍**：僅 `backend/alembic/env.py` 一個檔案，其餘100個檔案內容不變。

### v1.0（基準版本）— 完整bug清單

> ⚠️ **本節數字為當時的記載，v2.0 重新量測後證實其中三項是錯的，請以本檔開頭的表格為準：**
> 實際是 110 個檔案（64 Python ＋ 25 TS/TSX），v1.7 移除 `setup-admin` 後端點數應為 61 而非 62。
> 保留原文不改寫，是為了留下「數字如何一路被複製下去」的完整軌跡。

108個檔案（63 Python，含2個測試檔案 + 25 TypeScript/TSX + .gitignore/docker-compose.yml/
eslint.config.mjs等設定檔），涵蓋12業務模組、62個業務API端點（不含/health，共63個HTTP端點）、29張資料表。
（v1.4新增eslint.config.mjs因應Next16改用flat config，檔案數107→108）
以下10個bug均以「真實PostgreSQL + 真實uvicorn + 真實HTTP request」端到端測試方式發現與驗證，
非靜態程式碼推論：

| # | 檔案 | 問題 | 嚴重度 |
|---|---|---|---|
| 1 | `app/database.py` | `settings.database_url`（小寫）對不上 `config.py` 的 `DATABASE_URL`（大寫），且引用不存在的 `settings.environment`，整個後端無法連接資料庫 | 🔴 阻斷性 |
| 2 | `app/modules/nesting/router.py` | `NestPart()` 呼叫缺少必填 `label` 參數，每次呼叫 `/calculate` 直接500 | 🔴 高 |
| 3 | `requirements.txt` | `passlib[bcrypt]==1.7.4` 未鎖定 `bcrypt` 版本，`pip install` 會裝到不相容的 bcrypt 5.x，導致所有密碼雜湊操作崩潰 | 🔴 阻斷性 |
| 4 | `backend/.env.example` + `app/config.py` | `.env.example` 含 `MINIO_*`、`ENVIRONMENT` 等 `Settings` 未定義欄位，Pydantic v2 預設拒絕多餘欄位，照README標準流程操作會直接啟動失敗 | 🔴 阻斷性 |
| 5 | `app/tasks/celery_app.py` | `settings.redis_url`（小寫）對不上 `REDIS_URL`（大寫），Celery worker 無法連接 Redis | 🟡 中 |
| 6 | `app/main.py` | `products/BOM` 模組的 `router.py` 檔案本身完整無誤，但從未被註冊掛載，整個模組（物料/產品/BOM）API完全無法存取 | 🔴 高 |
| 7 | `app/modules/quotation/router.py` | `{"unit_price": x, **item.model_dump()}` 的 dict 展開順序錯誤，計算好的價格被使用者傳入的 `None` 覆蓋。**API回應顯示成功，但資料庫查詢是0 rows**——靜默資料遺失，使用者以為報價單已存但實際沒有 | 🔴 極高（資料完整性） |
| 8 | `requirements.txt` | 完全缺少 `email-validator` 套件，但 `auth/router.py` 註冊功能用了需要它的 `EmailStr` 型別，容器化環境（乾淨pip安裝）下會啟動失敗 | 🔴 阻斷性 |
| 9 | `frontend/src/app/layout.tsx` | 使用 `next/font/google` 抓取Google Inter字型，`npm run build` 編譯期需連網，Docker建置環境的網路限制（防火牆/代理）可能導致建置失敗；已改用系統字型堆疊消除此外部依賴 | 🟡 中（風險性修正） |
| 10 | `backend/alembic/env.py` | 見上方 v1.1 章節 | 🔴 阻斷性 |

**額外新增功能**：`POST /api/v1/nesting/compare-presets`（9種板型自動比較找最省片數），
從先前的獨立版本移植並實測驗證通過。

**完整驗證涵蓋範圍**：
- 全部12業務模組、62個業務端點：真實PostgreSQL + JWT認證 + HTTP請求測試
- 裁切引擎：17項pytest測試全數通過（`backend/tests/test_nesting_bfd.py`，2026-08-13針對目前版本nesting_bfd.py重新撰寫並實測，涵蓋核心排版邏輯與compare-presets板型比較功能）
- 前端：`npm run build`，**16**個頁面編譯零錯誤（v1.4重新逐一清點路由後修正此數字，原「17」為v1.0基準就存在的錯誤，本輪才發現並修正）
- PDF匯出：實際產生合法PDF檔案並驗證格式
- Docker設定：`docker compose config`（真實Docker daemon）驗證yaml語法正確；
  `docker build` 驗證至映像檔拉取步驟（受限於驗證環境網路白名單，無法完整跑通 `docker compose up`，
  屬驗證環境限制，非程式碼問題）

**下次新增修正時，請依此格式在上方新增一節，並同步更新 `MASTER_SPEC.md` 對應章節。**
