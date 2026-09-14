# 開發與交付規範

## 環境需求

| 項目 | 版本 | 備註 |
|---|---|---|
| Python | 3.11 | 3.12 未測試 |
| Node.js | 22 | Next 16 要求 ≥ 20 |
| PostgreSQL | 15 或 16 | 兩者皆已實測 |
| Redis | 7 | Celery broker |
| Docker | 選用 | `docker compose` 一鍵起全部服務 |

## 本機啟動（不用 Docker）

```bash
# 後端
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                # 改掉 DATABASE_URL 與 SECRET_KEY
alembic upgrade head
python scripts/seed_data.py                         # 可重複執行，不會重複建立
uvicorn app.main:app --reload --port 8000

# 前端（另開終端）
cd frontend
npm ci
cp .env.local.example .env.local
npm run dev
```

## 送出變更前的檢查清單

```bash
# 後端
cd backend && pytest -q
API_BASE=http://127.0.0.1:8000 python scripts/verify_e2e.py   # 需先啟動 uvicorn

# 前端
cd frontend && npx eslint . --max-warnings=0 && npm run build && npm audit --audit-level=high
```

以上全部通過，CI 才會綠。

## 文件同步規則（本專案最容易出事的地方）

三份文件必須互相一致，任何一份改動都要回填另外兩份：

| 文件 | 負責內容 |
|---|---|
| `README.md` | 版本紀錄（唯一事實來源）、啟動方式、已知限制 |
| `MASTER_SPEC.md` | 完整技術規格、資料庫 schema、RBAC 矩陣 |
| `MVP_CHECKLIST.md` | 各項功能的 ✅ / ⚠️ / ❌ 狀態 |

**任何寫進文件的數字，都必須是量出來的，不是抄上一版的。** 量法：

```bash
# API 端點數（啟動 uvicorn 後）
curl -s localhost:8000/openapi.json | python -c "import sys,json; s=json.load(sys.stdin); print(sum(len(v) for v in s['paths'].values()))"

# 前端頁面數
cd frontend && npm run build        # 看 Route 表

# 資料表數
psql -d acrylic_erp -tAc "select count(*) from information_schema.tables where table_schema='public'"
```

## 狀態標記定義

- ✅ 以真實環境（真 PostgreSQL + 真 HTTP request）端到端驗證通過
- ⚠️ 程式碼存在且能運作，但該項描述的細節未逐一驗證
- ❌ 尚未實作，或無證據顯示已完成

不要因為「build 過了」「測試綠了」就標 ✅。
build 成功只證明語法對，不證明前後端有接起來。

## Commit 訊息

```
<類型>: <一句話說明>

類型：feat / fix / docs / refactor / test / chore / security
```

修 bug 時在 commit body 寫清楚：問題是什麼、根因是什麼、**怎麼驗證修好了**。

## 分支

- `main` — 可部署狀態，CI 必須綠
- `feat/*`、`fix/*` — 功能與修補，經 PR 合併

## 絕對不要做的事

- 把 `.env`、`backend/.env`、`frontend/.env.local` 推上 GitHub（`.gitignore` 已涵蓋，但仍要自己確認）
- 在程式碼裡寫死密碼、API key 或客戶真實資料
- 修改 Model 卻不寫 Alembic migration
- 在文件裡寫沒有實測依據的數字
