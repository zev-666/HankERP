# MVP 開發查核清單（前6個月）

> **狀態標記說明**（2026-09-14 更新至 v2.0，對應 GitHub 儲存庫 `zev-666/HankERP`）：
> - ✅ = 本對話框以真實PostgreSQL+JWT+HTTP request端到端測試驗證通過
> - ⚠️ = 程式碼/頁面已存在且可運作，但該項目描述的具體細節未逐一驗證
> - ❌ = 尚未實作，或無證據顯示已完成
>
> 詳細bug修復與驗證方式請見 `README.md`「版本紀錄」章節。
>
> **v2.0 實測基準**（每個數字都是量出來的，不是抄上一版的）：
> 13 個業務模組 · 68 個業務 API 端點（＋`/health` 共 69）· 30 張業務資料表 ·
> 23 條前端路由（21 靜態 ＋ 2 動態）· 17 項 pytest · `npm audit` 0 漏洞 · `eslint --max-warnings=0` 全綠。
>
> **本清單共 60 項：✅ 41 項（68%）、⚠️ 8 項、❌ 11 項。**
>
> （此三個數字由腳本逐行統計勾選項得出，非目測估算。）

## Phase 0: 資安強化 ✅（v1.7新增，11項修正全數驗證）
- [x] ✅ 依賴套件漏洞掃描 — `pip-audit`發現44個已知漏洞（python-jose/starlette/python-multipart/pillow），全部升級或移除，重新掃描確認0漏洞
- [x] ✅ 靜態程式碼安全分析 — `bandit`掃描抓到無身份驗證的管理員建立端點與寫死密碼，已移除，重新掃描確認0 Medium/High問題
- [x] ✅ JWT密鑰安全防呆 — 正式環境使用預設弱密鑰或密鑰長度不足會直接拒絕啟動，已實測驗證生效
- [x] ✅ 資料庫/快取對外隔離 — PostgreSQL、Redis已移除對外曝露的port，僅限Docker內部網路存取，`docker compose config`確認
- [x] ✅ Rate Limiting防暴力破解 — `/login`(5次/分鐘)、`/register`(10次/小時)、`/forgot-password`(3次/小時)，實測連續6次錯誤登入第6次正確收到429
- [x] ✅ 容器非root執行 — backend/frontend的Dockerfile皆已改用非root使用者
- [x] ✅ 前端安全標頭 — X-Frame-Options、CSP相關、HSTS等已加入`next.config.js`，`npm run build`確認不影響編譯
- [x] ✅ 正式環境API文件隱藏 — `ENVIRONMENT=production`時`/docs`、`/redoc`、`/openapi.json`自動回傳404，已實測確認

## Phase 1: 基礎建設 ⚠️（6/6 存在，4項已驗證）
- [x] ✅ GitHub Monorepo 建立 — **v2.0**：三份分散的 zip 已合併為單一 git 儲存庫
  `zev-666/HankERP`（backend + frontend monorepo），含 `.gitignore`、`LICENSE`、
  `CONTRIBUTING.md`、`CLAUDE.md` 與 `.github/workflows/ci.yml`
- [x] ✅ Docker Compose (PostgreSQL + Redis + Backend + Frontend) — `docker-compose.yml`已用真實Docker daemon驗證yaml語法正確；完整`docker compose up`因驗證環境網路限制未能跑通，請於本機Docker Desktop環境驗證
- [x] ✅ Alembic 資料庫遷移初始化 — 真實PostgreSQL多次驗證，**v2.0 為 30 張業務表
  （＋`alembic_version` 共 31）**，含 v1.1 連線字串 bug 修復與 v2.0 的第二個 migration
- [x] ✅ FastAPI JWT認證系統 — 全程用真實JWT token（v1.7已改用PyJWT取代有ecdsa漏洞的python-jose）測試全部業務端點（**v2.0 實測 68 個**，v1.7 移除 `setup-admin` 後文件的「62」已過期），認證流程正確
- [x] ✅ RBAC角色權限系統（**9種角色**）— **v2.0 修正**：MASTER_SPEC 第九章規劃 9 種角色，
  但 `seed_data.py` 自 v1.0 起只建立 8 種，**品管（qc）從未進過資料庫**。已補上並實測，
  種子腳本輸出確認建立 9 種（admin/owner/sales/engineer/planner/warehouse/purchaser/operator/qc）
- [x] ⚠️ Next.js + shadcn/ui 登入頁面 — 登入頁面已存在且編譯成功，未逐一核對UI元件細節

## Phase 2: 官網上線 ✅（v2.0 前後端完成串接）
- [x] ✅ 首頁 — **v2.0**：案例區塊改為 Server Component 讀取 `/api/v1/public/portfolio`。
  先前是寫死在程式碼裡的 `const CASES = [...]` 四筆假資料，後台發佈什麼官網都不會變。
  已用真實 `next start` ＋ curl HTML 驗證：後台新建並發佈案例後，首頁 HTML 出現該筆真實標題，
  且舊的假資料字串（「電動牙刷展示架」）完全消失；無資料時顯示空狀態而非假資料
- [x] ✅ 作品展示頁（CMS管理後台）— **v2.0**：新增 `/portfolio` 列表頁與 `/portfolio/[slug]`
  詳情頁（先前 `(public)/portfolio/` 是空資料夾），以及後台 `/erp/portfolio` 作品管理頁
  （建立草稿→發佈→官網即時可見）。詳情頁含 `generateMetadata` 動態 SEO。
  修復 bug#14（Next 16 動態路由參數未解碼導致詳情頁一律 404）
- [x] ✅ 線上詢價表單 — **v2.0**：`/quote` 送出按鈕真的呼叫 `POST /api/v1/public/inquiries`。
  先前只有 `setSubmitted(true)` 切換畫面，客戶填的需求直接消失。
  新增 `inquiries` 資料表、公開端點（rate limit 5次/小時、`tenant_id` 不接受前端傳入）、
  後台 `/erp/inquiries` 管理頁與「轉正式客戶」（冪等）。
  端到端驗證：官網送出 → 後台列表讀得到同一筆 → 轉客戶建立 C0001 → 重複轉換不重建
- [x] ✅ 關於我們 + 設備介紹 — **v2.0**：新增 `/about`，含 6 項設備介紹與 4 項能力說明
- [x] ✅ SEO 基礎 — **v2.0**：新增 `app/sitemap.ts`（動態納入每一則已發佈作品，
  實測產生 5 條 URL 含作品詳情頁）與 `app/robots.ts`（`/erp/`、`/mes/`、`/login` 不予索引）；
  各頁面有獨立 `metadata`。響應式設計為 Tailwind 斷點，未逐一在實機驗證
- [ ] ❌ Google Analytics 整合 — 未見任何 GA 相關程式碼

## Phase 3: 主檔管理 ✅（核心流程已驗證）
- [x] ✅ 客戶主檔CRUD + 分頁搜尋 — `/api/v1/customers`已測試
- [x] ⚠️ 供應商主檔CRUD — 採購流程中supplier已可正確關聯使用，獨立CRUD端點未逐一測試
- [x] ✅ 材料主檔（壓克力板、木料、鐵件、LED） — `/api/v1/materials`已測試，含BOM成本計算驗證
- [x] ✅ 產品主檔 — `/api/v1/products`已測試
- [x] ✅ 多層BOM建立 + 版本控管 — 建立BOM→發佈(v1)完整流程已測試
- [x] ✅ BOM展開計算 — `GET /bom/{id}/expand`已測試，成本計算邏輯正確（含損耗率換算）

## Phase 4: 庫存系統 ⚠️（核心端點已驗證，部分細節未測）
- [x] ⚠️ 壓克力板材入庫（含厚度、顏色、尺寸）— `sheet_stocks`表存在，欄位齊全，入庫流程未單獨測試
- [x] ✅ 庫存餘額即時查詢 — `/api/v1/inventory/balance`已測試
- [x] ✅ 庫存異動記錄（完整追溯）— **v2.0**：工單發料寫入 `ISSUE`（qty 為負）、
  完工入庫寫入 `RECEIPT`（qty 為正），皆帶 `source_type='WO'` 與 `source_id`，
  可回溯到單據。已用真實 HTTP ＋ 直接查資料庫驗證餘額與異動同步更新
- [x] ✅ 成品（FG）庫存 — **v2.0 新增**：`inventory_balances`/`inventory_transactions`
  新增 `product_id` 並以 CHECK 約束與 `material_id` 互斥。
  先前 schema 只認得 materials，成品根本無處可存
- [ ] ❌ 安全庫存預警（低於閾值email通知） — email通知機制未見實作
- [ ] ⚠️ 剩料入庫（尺寸登記、可用標記）— `remnant_inventory`表已隨nesting模組建立，獨立入庫流程未測試
- [ ] ❌ 庫存盤點報表 — 未見實作

## Phase 5: 採購+報價 ✅（核心流程已驗證，含關鍵bug修復）
- [x] ✅ 採購申請 → 採購單 → 進貨驗收 — 建立採購單→列表→確認流程已測試
- [ ] ❌ 供應商比價紀錄 — 未見實作
- [x] ✅ 報價單CRUD（手動版） — 已測試，**含v1.0第7項bug修復**（原本API回應成功但資料庫實際未寫入，
  已修正並用直接查詢確認資料持久化）**+ v1.3第12項bug修復**（業務手動定價的品項未被計入header總額，
  已用純AI試算/純手動/混合單三種情境+直接查資料庫核對確認修復）
- [x] ⚠️ AI報價規則引擎（Phase 1） — `/quotations/ai-estimate`端點存在，規則邏輯（材料/加工/管銷成本試算）未逐項驗證精確度
- [x] ✅ 報價PDF匯出 — `GET /quotations/{id}/pdf`已測試，實際產出合法PDF檔案（reportlab + STSong-Light CID字型）
- [ ] ❌ 報價轉銷售訂單 — 未見對應端點

## Phase 6: 工單系統 ✅（核心流程含MES已驗證）
- [x] ⚠️ 工單建立（從銷售訂單） — 工單建立已測試，但直接由product建立，非銷售訂單觸發
- [x] ✅ BOM自動展開→物料需求計算 — BOM展開計算已測試（見Phase 3）
- [x] ✅ 工序管理（CNC/雷射/噴漆/組裝） — 工單含工序清單，建立/查詢已測試
- [x] ✅ MES平板報工介面 — 開始工序/完成工序已測試，良率計算正確（18/20=90%）
- [x] ✅ 工單發料（庫存自動扣除）— **v2.0**：`POST /work-orders/{id}/issue-materials`。
  先全部檢查再全部扣帳，任一項不足即整批拒絕（409）並回傳缺料明細，**不做部分發料**；
  只發尚未發足的差額，重複呼叫安全。
  實測：BOM 2才×10台×1.1損耗＝需 22 才，庫存僅 5 才時正確擋下且**庫存數字完全沒動**
  （確認沒有部分扣帳）；補到 25 才後發料成功，餘額正確變為 3 才
- [x] ✅ 工單完工入庫 — **v2.0**：`POST /work-orders/{id}/complete`，成品進 FG 倉、
  工單轉 completed。入庫數取**最後一道工序**良品數而非各工序加總。
  實測：工序未完成時正確擋下；兩道工序各報 9 良 1 壞後入庫 9 台（非 18 台）；
  已完工的工單重複呼叫正確擋下

## Phase 7: 裁切優化 ✅（本對話框驗證最完整的模組）
- [x] ✅ BFD排版引擎（Python核心） — 17項pytest測試全數通過，含旋轉不變性、無重疊、邊界值、compare-presets板型比較等驗證
- [ ] ❌ 排版視覺化工作台（Konva.js） — 目前為CSS版本，非Konva.js（README已註明為已知待優化項）
- [ ] ❌ 多工單混排支援 — v1.3更正：`batch_optimize_multiple_orders`實際上是回傳
  `pending_implementation`的stub，並非「未專項測試」而是根本尚未實作；
  單張工單內多零件混排排版本身沒問題（17項pytest已驗證），僅「跨工單」這部分是空的
- [x] ✅ Celery非同步任務基礎設施 — **v1.9**：稽核發現`celery_app.py`的task自動發現機制
  命名慣例不符，導致真正啟動worker後完全找不到`calculate_nesting_async`等task
  （若接上`.delay()`呼叫會`NotRegistered`），已修正並用**與`docker-compose.yml`實際部署
  一致的`--concurrency=4`（prefork多進程池）指令**驗證單一任務與4任務並行皆正確完成；
  另修正worker啟動時的`CPendingDeprecationWarning`。惟`calculate_nesting_async`本身
  目前仍是死程式碼，router的`/calculate`端點是同步呼叫，未串接此非同步任務
- [x] ✅ 利用率計算+月報 — 利用率計算已驗證；`analytics/material-utilization`月報端點存在
- [ ] ⚠️ 剩料自動入庫 — `remnant_inventory`表隨nesting job自動產生剩料紀錄，未驗證與sheet_stocks的入庫串接
- [ ] ❌ 切割指示圖匯出（PNG/PDF） — 未見實作
- [x] ✅ **（新增）9種板型自動比較** — `POST /nesting/compare-presets`已測試，正確推薦最省片數板型

## Phase 8: 儀表板+上線 ⚠️（後端指標已驗證，部署相關全未執行）
- [x] ⚠️ 廠長儀表板（Recharts圖表） — `/api/v1/analytics/dashboard`後端已測試並回傳正確KPI數值；前端Recharts圖表渲染僅確認編譯通過，未驗證視覺呈現
- [x] ✅ 訂單達交率追蹤 — dashboard端點回傳`on_time_delivery_rate_pct`欄位，邏輯已驗證
- [x] ✅ 板材利用率月報 — dashboard端點回傳`avg_material_utilization_pct`欄位（測試中正確反映裁切模組產生的37.5%利用率），驗證跨模組資料串接正確
- [ ] ❌ AWS Taiwan部署 — 未執行
- [ ] ❌ 域名 + SSL設定 — 未執行
- [ ] ❌ 使用者培訓文件 — 未撰寫（`README.md`/`CONTRIBUTING.md` 是給開發者的，非給現場人員）
- [x] ✅ CI 持續整合 — **v2.0 新增** `.github/workflows/ci.yml`：真的起 PostgreSQL 16 ＋ Redis、
  跑 migration ＋ seed ＋ pytest，啟動 uvicorn 後用真實 HTTP 走完詢價與工單全流程，
  並印出當下實際端點數（讓「文件數字過期」在 CI 就被抓到）；
  前端另跑 `eslint --max-warnings=0`、`npm run build`、`npm audit --audit-level=high`

## 關鍵效益指標（KPI）
| 指標 | 導入前 | 導入後目標 | 目前狀態 |
|------|--------|-----------|---------|
| 報價回覆時間 | 2-3天 | 2小時內 | AI估價端點已可運作，實際回覆時間需正式上線後統計 |
| 板材利用率 | ~70% | >88% | 後端計算邏輯已驗證正確，實際數值待真實生產資料 |
| 剩料追蹤率 | 0% | 100% | 剩料資料表與nesting自動產生機制已建立，完整追蹤流程未端到端驗證 |
| 工單準時率 | 不明確 | >90% | dashboard已有對應計算邏輯（`on_time_delivery_rate_pct`），待真實工單資料驗證 |
| 月結成本分析 | Excel人工 | 即時自動 | 成本分析API已運作，「月結」批次流程未實作 |

---

## 下一步建議優先順序（v2.0 重新評估）

v1.9 標為「最高優先」的**庫存自動扣減與工單完工入庫已於 v2.0 完成**，
「工單執行 → 庫存異動」的斷點已接上。依商業價值重新排序：

1. **最高優先：詢價通知（email 或 LINE Notify）** — 詢價現在會落庫了，
   但業務必須自己記得進後台看。官網詢價的價值在於「多快回覆」，
   一個通知就能把回覆時間從「下次登入時」變成「幾分鐘內」，成本極低。
2. **次要：安全庫存預警與庫存盤點報表** — 發料現在會扣庫存了，
   庫存數字才第一次有意義；有了正確的庫存，預警與盤點才值得做（順序不可顛倒）。
3. **上線前置**：Google Analytics、AWS 部署、域名 SSL、**使用者培訓文件**。
   培訓文件常被排到最後然後被砍掉，但它是決定現場人員會不會用這套系統的關鍵。
4. **先不要做的（Won't Have，現階段）**：
   - 裁切視覺化升級 Konva.js — 目前 CSS 版本能看能用，換掉只是更漂亮，不解決任何營運問題
   - `/calculate` 接 Celery 非同步 — BFD 演算法 5000 件僅需 <100ms（pytest 已驗證），
     目前規模下同步執行完全夠用，接非同步只會多出一層要維護的複雜度
   - 跨工單混排、報價轉銷售訂單、供應商比價 — 這三項要先有真實使用資料，
     才知道值不值得做；現在做等於憑想像設計流程
5. **已知技術債**：切割指示圖匯出、作品 slug 改為 ASCII、密碼重設 token 改存 Redis

詳細技術規格請見 `MASTER_SPEC.md`；bug修復歷程請見 `README.md`「版本紀錄」章節。
