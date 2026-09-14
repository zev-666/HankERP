# 壓克力展示架智慧工廠 ERP SaaS 平台
## 世界級技術規格書 v1.0
### 桃園龜山 · 20年複合式壓克力製造商 · 數位轉型藍圖

---

## 一、專案定位與目標

**公司背景**
- 位置：台灣桃園龜山
- 經驗：20年以上壓克力展示架製造
- 特色：複合式製程（壓克力 + 木工 + 鐵件 + LED + 噴漆）
- 客戶：Electrolux、好奇寶寶、酒商、Oral-B 等大品牌
- 設備：CNC、CO₂雷射、大裁板機、電腦壓克力裁板機、圓聚切割機

**核心目標**
從傳統師傅工廠 → 數位化智慧製造商 → 可商業化SaaS平台

**12大系統模組**
> 註（v1.6補充）：以下是最初規劃的12個**概念性**業務模組，不完全對應後端`app/modules/`
> 資料夾數（實際為10個資料夾+獨立的`app/auth/`＝11個程式碼模組）。例如「官方網站」是前端
> `(public)/`路由而非獨立backend模組，「剩料回收管理」實作在`inventory`模組裡，
> 「CNC與雷射加工管理」分散在`equipment`與`production`模組裡，不是每個概念模組都有
> 一對一的獨立資料夾。
1. 官方網站 + B2B詢價入口
2. 作品展示系統（案例管理）
3. CRM客戶管理
4. BOM系統（多層BOM + 版本控管）
5. 原料庫存系統（含板材剩料管理）
6. 採購管理系統
7. 生產工單系統
8. CNC與雷射加工管理（設備台帳）
9. 壓克力裁切最佳化系統（2D Nesting）
10. 剩料回收管理系統
11. AI自動報價系統
12. 財務成本分析系統

---

## 二、技術堆疊（完整版）

### 前端
```
框架：Next.js 14 (App Router)
UI：Tailwind CSS + shadcn/ui
狀態管理：Zustand + React Query (TanStack)
圖表：Recharts + D3.js
表格：TanStack Table
表單：React Hook Form + Zod
地圖：無（台灣在地部署）
PWA：next-pwa（工廠平板離線使用）
2D排版視覺化：Konva.js（裁切圖拖曳介面）
```

### 後端
```
主框架：FastAPI (Python 3.11+)
ORM：SQLAlchemy 2.0 + Alembic（資料庫遷移）
任務佇列：Celery + Redis（非同步AI報價、排版計算）
WebSocket：FastAPI WebSocket（MES即時回報）
驗證：python-jose (JWT) + passlib (bcrypt)
文件：自動生成 OpenAPI / Swagger
```

### 資料庫
```
主資料庫：PostgreSQL 15（交易型資料，ACID保證）
快取：Redis 7（Session、排版計算快取）
物件儲存：MinIO（自架）/ AWS S3（雲端）→ 圖片、CAD、PDF
搜尋：Meilisearch（產品、客戶全文搜尋）
時間序列：InfluxDB（未來IoT設備數據）
```

### AI / 裁切優化
```
報價引擎：
  Phase 1：規則引擎（Python類）
  Phase 2：scikit-learn 回歸模型
  Phase 3：LangChain + OpenAI API

裁切排版：
  Phase 1：Best-fit Decreasing (BFD) 啟發式演算法
  Phase 2：遺傳演算法 (DEAP library)
  Phase 3：Deep Reinforcement Learning (Stable-Baselines3)

CAD解析：
  PDF解析：PyMuPDF
  DXF解析：ezdxf
  圖像OCR：Tesseract / PaddleOCR
```

### DevOps
```
容器：Docker + Docker Compose（開發）/ Kubernetes（生產）
CI/CD：GitHub Actions
雲端：AWS Taiwan (ap-east-1) / GCP Taiwan
監控：Prometheus + Grafana
Log：ELK Stack（Elasticsearch + Logstash + Kibana）
API文件：Swagger UI（自動）
```

---

## 三、PostgreSQL 資料庫完整 Schema

### 3.1 使用者與權限
```sql
-- 租戶（未來多廠支援）
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(50) UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 角色
CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  name VARCHAR(50) NOT NULL,       -- 'admin','sales','engineer','warehouse','production','purchase','qc','finance'
  display_name VARCHAR(100),
  permissions JSONB DEFAULT '{}'   -- {module: [read, write, approve, export]}
);

-- 使用者
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  email VARCHAR(200) UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  full_name VARCHAR(100),
  role_id UUID REFERENCES roles(id),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ
);

-- 稽核日誌
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  action VARCHAR(50),              -- CREATE/UPDATE/DELETE/APPROVE
  table_name VARCHAR(100),
  record_id UUID,
  old_values JSONB,
  new_values JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 客戶與CRM
```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  code VARCHAR(20) UNIQUE,         -- C001, C002...
  name VARCHAR(200) NOT NULL,
  company_type VARCHAR(50),        -- '品牌商','代理商','零售商'
  industry VARCHAR(100),           -- '彩妝','家電','酒類','嬰兒用品'
  tax_id VARCHAR(20),
  contact_name VARCHAR(100),
  contact_email VARCHAR(200),
  contact_phone VARCHAR(50),
  billing_address TEXT,
  shipping_address TEXT,
  credit_limit NUMERIC(12,2),
  payment_terms INTEGER DEFAULT 30, -- 付款天數
  tier VARCHAR(20) DEFAULT 'standard', -- 'vip','preferred','standard'
  notes TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  name VARCHAR(100) NOT NULL,
  title VARCHAR(100),
  email VARCHAR(200),
  phone VARCHAR(50),
  is_primary BOOLEAN DEFAULT FALSE
);

CREATE TABLE crm_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  activity_type VARCHAR(50),       -- 'call','email','visit','sample_sent'
  subject VARCHAR(200),
  content TEXT,
  outcome VARCHAR(100),
  next_action TEXT,
  next_action_date DATE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.3 產品與BOM
```sql
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  sku VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  name_en VARCHAR(200),
  product_type VARCHAR(50),        -- 'standard','custom','semi'
  category VARCHAR(100),           -- '彩妝架','酒類櫃','家電展示架'
  description TEXT,
  thumbnail_url TEXT,
  standard_cost NUMERIC(12,2),
  list_price NUMERIC(12,2),
  unit VARCHAR(20) DEFAULT '台',
  lead_time_days INTEGER,
  min_order_qty INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- BOM主檔（支援版本）
CREATE TABLE bom_headers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id),
  version INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) DEFAULT 'draft',  -- 'draft','active','obsolete'
  effective_date DATE,
  expire_date DATE,
  notes TEXT,
  created_by UUID REFERENCES users(id),
  approved_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, version)
);

-- BOM明細
CREATE TABLE bom_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bom_id UUID REFERENCES bom_headers(id),
  line_no INTEGER,
  material_id UUID REFERENCES materials(id),
  quantity NUMERIC(12,4) NOT NULL,
  unit VARCHAR(20),
  wastage_rate NUMERIC(5,4) DEFAULT 0,  -- 0.05 = 5%損耗
  cut_length NUMERIC(10,2),            -- 需裁切長度(mm)
  cut_width NUMERIC(10,2),             -- 需裁切寬度(mm)
  notes TEXT,
  is_optional BOOLEAN DEFAULT FALSE,
  substitute_material_id UUID REFERENCES materials(id)
);
```

### 3.4 材料與庫存
```sql
-- 物料主檔
CREATE TABLE materials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  code VARCHAR(50) UNIQUE,
  name VARCHAR(200) NOT NULL,
  material_type VARCHAR(50),    -- 'acrylic','wood','metal','led','paint','hardware'
  -- 壓克力專屬欄位
  thickness_mm NUMERIC(5,2),   -- 2, 3, 5, 8, 10...
  color VARCHAR(100),           -- '透明','白色','黑色','霧面','彩色'
  standard_length_mm NUMERIC(8,2) DEFAULT 2000,  -- 200cm
  standard_width_mm NUMERIC(8,2) DEFAULT 1000,   -- 100cm
  -- 通用欄位
  unit VARCHAR(20),             -- '才','片','支','kg','m'
  unit_cost NUMERIC(12,4),      -- 每單位成本
  cost_per_sqm NUMERIC(12,4),   -- 每才成本（壓克力用）
  supplier_id UUID,
  min_stock_qty NUMERIC(12,2),  -- 安全庫存
  reorder_point NUMERIC(12,2),  -- 補貨點
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 庫存餘額
CREATE TABLE inventory_balances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  material_id UUID REFERENCES materials(id),
  warehouse_code VARCHAR(20),   -- 'RAW','WIP','FG','REMNANT','SCRAP'
  location_code VARCHAR(50),    -- 貨架位置
  qty_on_hand NUMERIC(14,4) DEFAULT 0,
  qty_reserved NUMERIC(14,4) DEFAULT 0,
  qty_available NUMERIC(14,4) GENERATED ALWAYS AS (qty_on_hand - qty_reserved) STORED,
  last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 庫存異動（完整追溯）
CREATE TABLE inventory_transactions (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  transaction_type VARCHAR(30),  -- 'RECEIPT','ISSUE','TRANSFER','ADJUST','SCRAP'
  material_id UUID REFERENCES materials(id),
  warehouse_code VARCHAR(20),
  qty NUMERIC(14,4),             -- 正數=入庫，負數=出庫
  unit_cost NUMERIC(12,4),
  source_type VARCHAR(30),       -- 'PO','WO','SO','MANUAL'
  source_id UUID,                -- 對應單據ID
  lot_number VARCHAR(100),
  notes TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 壓克力板材庫存（特殊欄位）
CREATE TABLE sheet_stocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  material_id UUID REFERENCES materials(id),
  batch_no VARCHAR(100),
  actual_length_mm NUMERIC(8,2),
  actual_width_mm NUMERIC(8,2),
  quantity INTEGER DEFAULT 1,
  is_remnant BOOLEAN DEFAULT FALSE,
  remnant_grade VARCHAR(10),     -- 'A','B','C'（A=可用，C=待報廢）
  parent_stock_id UUID REFERENCES sheet_stocks(id),
  source_wo_id UUID,             -- 來自哪個工單的剩料
  location_code VARCHAR(50),
  status VARCHAR(20) DEFAULT 'available', -- 'available','reserved','used','scrapped'
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.5 採購系統
```sql
CREATE TABLE suppliers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  code VARCHAR(20) UNIQUE,
  name VARCHAR(200) NOT NULL,
  contact_name VARCHAR(100),
  contact_email VARCHAR(200),
  contact_phone VARCHAR(50),
  payment_terms INTEGER DEFAULT 30,
  lead_time_days INTEGER,
  rating INTEGER DEFAULT 3,     -- 1-5星
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE purchase_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  po_number VARCHAR(30) UNIQUE,   -- PO-2025-001
  supplier_id UUID REFERENCES suppliers(id),
  status VARCHAR(20) DEFAULT 'draft', -- 'draft','sent','confirmed','received','closed'
  order_date DATE DEFAULT CURRENT_DATE,
  expected_date DATE,
  total_amount NUMERIC(14,2),
  currency VARCHAR(10) DEFAULT 'TWD',
  notes TEXT,
  created_by UUID REFERENCES users(id),
  approved_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE po_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  po_id UUID REFERENCES purchase_orders(id),
  line_no INTEGER,
  material_id UUID REFERENCES materials(id),
  ordered_qty NUMERIC(12,4),
  received_qty NUMERIC(12,4) DEFAULT 0,
  unit_price NUMERIC(12,4),
  unit VARCHAR(20),
  -- 壓克力板材特殊欄位
  sheet_thickness_mm NUMERIC(5,2),
  sheet_length_mm NUMERIC(8,2),
  sheet_width_mm NUMERIC(8,2),
  sheet_color VARCHAR(100),
  notes TEXT
);
```

### 3.6 生產工單系統
```sql
CREATE TABLE work_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  wo_number VARCHAR(30) UNIQUE,   -- WO-2025-001
  sales_order_id UUID,
  product_id UUID REFERENCES products(id),
  bom_id UUID REFERENCES bom_headers(id),
  quantity INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'draft',
     -- 'draft','released','in_progress','completed','closed'
  priority INTEGER DEFAULT 5,    -- 1=最高，10=最低
  planned_start DATE,
  planned_end DATE,
  actual_start TIMESTAMPTZ,
  actual_end TIMESTAMPTZ,
  notes TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE wo_operations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wo_id UUID REFERENCES work_orders(id),
  op_seq INTEGER,
  op_name VARCHAR(100),           -- 'CNC裁切','雷射雕刻','噴漆','組裝','包裝'
  machine_id UUID REFERENCES equipment(id),
  setup_time_min INTEGER,
  run_time_per_unit_min NUMERIC(8,2),
  status VARCHAR(20) DEFAULT 'pending',
  actual_start TIMESTAMPTZ,
  actual_end TIMESTAMPTZ,
  operator_id UUID REFERENCES users(id),
  good_qty INTEGER DEFAULT 0,
  scrap_qty INTEGER DEFAULT 0
);

CREATE TABLE wo_material_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wo_id UUID REFERENCES work_orders(id),
  material_id UUID REFERENCES materials(id),
  sheet_stock_id UUID REFERENCES sheet_stocks(id),
  planned_qty NUMERIC(12,4),
  issued_qty NUMERIC(12,4),
  issued_at TIMESTAMPTZ,
  issued_by UUID REFERENCES users(id)
);
```

### 3.7 裁切最佳化系統
```sql
CREATE TABLE nesting_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  wo_id UUID REFERENCES work_orders(id),
  material_id UUID REFERENCES materials(id),
  sheet_length_mm NUMERIC(8,2),
  sheet_width_mm NUMERIC(8,2),
  algorithm_version VARCHAR(20),   -- 'bfd_v1','ga_v2','drl_v3'
  utilization_rate NUMERIC(5,4),   -- 0.9234 = 92.34%
  total_waste_area_mm2 NUMERIC(14,2),
  sheets_used INTEGER,
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE nesting_parts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nesting_job_id UUID REFERENCES nesting_jobs(id),
  bom_item_id UUID REFERENCES bom_items(id),
  part_length_mm NUMERIC(8,2),
  part_width_mm NUMERIC(8,2),
  quantity INTEGER,
  can_rotate BOOLEAN DEFAULT TRUE
);

CREATE TABLE nesting_placements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nesting_job_id UUID REFERENCES nesting_jobs(id),
  sheet_index INTEGER,             -- 第幾張板
  part_id UUID REFERENCES nesting_parts(id),
  x_mm NUMERIC(8,2),              -- 放置座標
  y_mm NUMERIC(8,2),
  rotated BOOLEAN DEFAULT FALSE,
  cutting_path_json JSONB          -- G-code路徑
);

-- 剩料登記
CREATE TABLE remnant_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  sheet_stock_id UUID REFERENCES sheet_stocks(id),
  nesting_job_id UUID REFERENCES nesting_jobs(id),
  length_mm NUMERIC(8,2),
  width_mm NUMERIC(8,2),
  area_mm2 NUMERIC(14,2) GENERATED ALWAYS AS (length_mm * width_mm) STORED,
  grade VARCHAR(10),
  notes TEXT,
  status VARCHAR(20) DEFAULT 'available',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.8 報價與銷售訂單
```sql
CREATE TABLE quotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  quote_number VARCHAR(30) UNIQUE,
  customer_id UUID REFERENCES customers(id),
  status VARCHAR(20) DEFAULT 'draft',
     -- 'draft','sent','accepted','rejected','expired'
  valid_until DATE,
  currency VARCHAR(10) DEFAULT 'TWD',
  -- AI報價相關
  ai_generated BOOLEAN DEFAULT FALSE,
  ai_confidence NUMERIC(5,4),      -- AI信心分數
  ai_model_version VARCHAR(50),
  -- 成本分解
  material_cost NUMERIC(12,2),
  processing_cost NUMERIC(12,2),
  overhead_cost NUMERIC(12,2),
  profit_margin NUMERIC(5,4),
  final_price NUMERIC(14,2),
  -- 追蹤
  won_at TIMESTAMPTZ,
  lost_reason TEXT,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE quotation_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_id UUID REFERENCES quotations(id),
  line_no INTEGER,
  product_id UUID REFERENCES products(id),
  description TEXT,
  quantity INTEGER,
  unit_price NUMERIC(12,2),
  -- 壓克力計算明細
  acrylic_sqm NUMERIC(8,4),        -- 估算用料（才）
  acrylic_cost_per_sqm NUMERIC(8,2),
  cnc_minutes NUMERIC(8,2),
  laser_meters NUMERIC(8,2),
  assembly_hours NUMERIC(6,2)
);
```

### 3.9 設備管理
```sql
CREATE TABLE equipment (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  code VARCHAR(30) UNIQUE,
  name VARCHAR(100) NOT NULL,
  equipment_type VARCHAR(50),   -- 'cnc','laser','saw','spray','drill','polish'
  model VARCHAR(100),
  serial_number VARCHAR(100),
  hourly_rate NUMERIC(8,2),     -- 每小時機台成本
  power_kw NUMERIC(6,2),
  purchase_date DATE,
  warranty_expire DATE,
  status VARCHAR(20) DEFAULT 'active',
  notes TEXT
);

CREATE TABLE maintenance_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  equipment_id UUID REFERENCES equipment(id),
  maintenance_type VARCHAR(30),  -- 'preventive','corrective','inspection'
  description TEXT,
  technician VARCHAR(100),
  cost NUMERIC(10,2),
  downtime_hours NUMERIC(6,2),
  performed_at TIMESTAMPTZ,
  next_maintenance_date DATE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.10 官網內容管理
```sql
CREATE TABLE portfolio_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  title VARCHAR(200) NOT NULL,
  client_name VARCHAR(200),
  industry VARCHAR(100),
  product_type VARCHAR(100),
  -- 規格
  dimensions VARCHAR(200),
  materials TEXT,
  process_methods TEXT[],        -- ['CNC','雷射','噴漆','LED']
  -- 圖片
  cover_image_url TEXT,
  gallery_urls TEXT[],
  -- SEO
  slug VARCHAR(200) UNIQUE,
  meta_description TEXT,
  -- 內容
  challenge TEXT,
  solution TEXT,
  result TEXT,
  is_featured BOOLEAN DEFAULT FALSE,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 3.11 線上詢價（v2.0 新增）

官網訪客送出的詢價需求。這是全系統唯一「未登入即可寫入資料庫」的入口，
因此 router 端必須套 rate limit，且 `tenant_id` 由後端填入、不接受前端傳值。

```sql
CREATE TABLE inquiries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  -- 聯絡資訊（訪客填寫，全部視為不可信輸入）
  name VARCHAR(100) NOT NULL,
  company VARCHAR(200),
  email VARCHAR(200) NOT NULL,
  phone VARCHAR(50),
  -- 需求內容
  product_type VARCHAR(100),
  quantity VARCHAR(100),            -- 自由文字，例如「約100台」
  description TEXT,
  -- 業務處理
  status VARCHAR(20) NOT NULL DEFAULT 'new',
     -- 'new','contacted','quoted','won','lost','spam'
  assigned_to UUID REFERENCES users(id),
  internal_notes TEXT,
  converted_customer_id UUID REFERENCES customers(id),
  -- 來源追溯
  source_page VARCHAR(200),
  priority INTEGER DEFAULT 5,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_inquiries_status_created ON inquiries (status, created_at);
```

### 3.12 成品（FG）庫存支援（v2.0 結構變更）

`inventory_balances` 與 `inventory_transactions` 原本只有 `material_id`，
只認得 `materials` 主檔。但**完工入庫存放的是成品，成品屬 `products` 主檔**，
導致「工單完工入庫」在資料模型層面根本做不出來——這是規格層面的缺口，不是實作偷懶。

```sql
ALTER TABLE inventory_balances     ADD COLUMN product_id UUID REFERENCES products(id);
ALTER TABLE inventory_transactions ADD COLUMN product_id UUID REFERENCES products(id);
ALTER TABLE inventory_balances     ALTER COLUMN material_id DROP NOT NULL;
ALTER TABLE inventory_transactions ALTER COLUMN material_id DROP NOT NULL;

-- 恰有一個有值，等同一個輕量的 item master
ALTER TABLE inventory_balances ADD CONSTRAINT ck_inventory_balances_material_xor_product
  CHECK ((material_id IS NOT NULL AND product_id IS NULL)
      OR (material_id IS NULL AND product_id IS NOT NULL));
-- inventory_transactions 同上

ALTER TABLE work_orders ADD COLUMN completed_qty INTEGER NOT NULL DEFAULT 0;
```

倉別慣例：`RAW`＝原料、`WIP`＝在製、`FG`＝成品、`REMNANT`＝剩料、`SCRAP`＝報廢。
發料寫 `ISSUE`（qty 為負），完工入庫寫 `RECEIPT`（qty 為正），`source_type='WO'`、
`source_id` 指向工單，異動可完整回溯到單據。

---

## 四、FastAPI 後端架構

### 專案結構
```
backend/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 設定管理
│   ├── database.py             # SQLAlchemy 設定
│   ├── auth/
│   │   ├── router.py           # /auth/login, /auth/refresh
│   │   ├── dependencies.py     # get_current_user
│   │   └── security.py         # JWT工具
│   ├── modules/
│   │   ├── customers/          # CRM
│   │   ├── products/           # 產品/BOM
│   │   ├── inventory/          # 庫存
│   │   ├── purchasing/         # 採購
│   │   ├── production/         # 工單/生產
│   │   ├── nesting/            # 裁切最佳化
│   │   ├── quotation/          # 報價
│   │   ├── equipment/          # 設備
│   │   ├── portfolio/          # 官網作品
│   │   └── analytics/          # 成本分析
│   ├── ai/
│   │   ├── quote_engine.py     # 報價規則引擎
│   │   ├── nesting_bfd.py      # BFD啟發式排版
│   │   └── nesting_ga.py       # 遺傳演算法排版
│   ├── tasks/
│   │   └── celery_app.py       # 非同步任務
│   └── models/                 # SQLAlchemy Models
├── alembic/                    # 資料庫遷移
├── tests/
├── requirements.txt
└── Dockerfile
```

### 核心 API 路由設計
```
認證
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

客戶管理
GET    /api/v1/customers
POST   /api/v1/customers
GET    /api/v1/customers/{id}
PUT    /api/v1/customers/{id}
GET    /api/v1/customers/{id}/activities
POST   /api/v1/customers/{id}/activities

產品/BOM
GET    /api/v1/products
POST   /api/v1/products
GET    /api/v1/bom/{product_id}
POST   /api/v1/bom
POST   /api/v1/bom/{id}/approve
GET    /api/v1/bom/{id}/expand      # 完整展開BOM

庫存
GET    /api/v1/inventory/balance
POST   /api/v1/inventory/transaction  # 入/出庫
GET    /api/v1/inventory/sheets        # 板材庫存
GET    /api/v1/inventory/remnants      # 剩料清單
PUT    /api/v1/inventory/remnants/{id} # 更新剩料狀態

採購
GET    /api/v1/purchase-orders
POST   /api/v1/purchase-orders
POST   /api/v1/purchase-orders/{id}/receive  # 進貨驗收

生產工單
GET    /api/v1/work-orders
POST   /api/v1/work-orders
POST   /api/v1/work-orders/{id}/release
POST   /api/v1/work-orders/{id}/operations/{op_id}/start
POST   /api/v1/work-orders/{id}/operations/{op_id}/complete
GET    /api/v1/work-orders/{id}/material-plan

裁切優化（非同步）
POST   /api/v1/nesting/calculate        # 觸發計算，返回task_id
GET    /api/v1/nesting/result/{task_id} # 輪詢結果
GET    /api/v1/nesting/jobs/{id}        # 查看排版詳情
GET    /api/v1/nesting/jobs/{id}/export # 匯出切割圖

報價
POST   /api/v1/quotations
POST   /api/v1/quotations/ai-estimate   # AI快速估價
GET    /api/v1/quotations/{id}
POST   /api/v1/quotations/{id}/convert-to-order
GET    /api/v1/quotations/{id}/pdf      # 產生PDF報價單

設備
GET    /api/v1/equipment
POST   /api/v1/equipment
POST   /api/v1/equipment/{id}/maintenance

分析報表
GET    /api/v1/analytics/dashboard      # 廠長儀表板
GET    /api/v1/analytics/material-utilization  # 板材利用率
GET    /api/v1/analytics/cost-breakdown        # 成本分解
GET    /api/v1/analytics/production-oee        # 設備稼動率
```

---

## 五、Next.js 前端架構

### 專案結構
```
frontend/
├── app/
│   ├── (public)/               # 官方網站（無需登入）
│   │   ├── page.tsx            # 首頁
│   │   ├── portfolio/          # 作品案例
│   │   ├── products/           # 產品中心
│   │   ├── about/              # 關於我們
│   │   ├── quote/              # 線上詢價
│   │   └── contact/            # 聯絡
│   ├── (erp)/                  # ERP系統（需登入）
│   │   ├── dashboard/          # 儀表板
│   │   ├── crm/                # 客戶管理
│   │   ├── quotations/         # 報價管理
│   │   ├── products/           # 產品/BOM
│   │   ├── inventory/          # 庫存管理
│   │   ├── purchasing/         # 採購管理
│   │   ├── production/         # 生產管理
│   │   ├── nesting/            # 裁切排版工作台
│   │   ├── equipment/          # 設備管理
│   │   └── analytics/          # 報表分析
│   ├── (mes)/                  # MES平板介面（輕量）
│   │   ├── scan/               # 掃碼報工
│   │   ├── workorder/          # 工單執行
│   │   └── quality/            # 品質回報
│   └── api/                    # Next.js API Routes（代理用）
├── components/
│   ├── ui/                     # shadcn/ui基礎元件
│   ├── erp/                    # ERP專用元件
│   │   ├── BomTree.tsx         # BOM樹狀結構
│   │   ├── NestingCanvas.tsx   # 裁切視覺化（Konva.js）
│   │   ├── InventoryHeatmap.tsx # 庫存熱力圖
│   │   └── QuoteBuilder.tsx    # 報價建立精靈
│   └── portal/                 # 官網元件
├── lib/
│   ├── api.ts                  # API客戶端
│   └── auth.ts                 # 認證工具
└── types/
    └── index.ts                # TypeScript型別定義
```

---

## 六、壓克力裁切最佳化演算法（核心）

### Phase 1: Best-Fit Decreasing (BFD)
```python
# app/ai/nesting_bfd.py
from dataclasses import dataclass
from typing import List, Tuple
import copy

@dataclass
class Part:
    id: str
    length: float    # mm
    width: float     # mm
    quantity: int
    can_rotate: bool = True

@dataclass
class Sheet:
    length: float    # 原板長 (mm), 預設 2000
    width: float     # 原板寬 (mm), 預設 1000
    placements: list = None
    free_rects: list = None

    def __post_init__(self):
        self.placements = []
        self.free_rects = [(0, 0, self.length, self.width)]

class BFDNestingEngine:
    """
    Guillotine Best Fit Decreasing 2D 排版算法
    適合壓克力工廠的矩形排版需求
    """
    def __init__(self, sheet_length: float = 2000, sheet_width: float = 1000,
                 kerf: float = 3):  # 刀縫3mm
        self.sheet_length = sheet_length
        self.sheet_width = sheet_width
        self.kerf = kerf

    def nest(self, parts: List[Part]) -> dict:
        """
        輸入：零件清單
        輸出：排版結果（利用率、切割圖、需幾張板）
        """
        # 展開所有零件（考慮數量）
        all_parts = []
        for part in parts:
            for _ in range(part.quantity):
                all_parts.append(copy.deepcopy(part))
                all_parts[-1].quantity = 1

        # 依面積降序排列（大的先放）
        all_parts.sort(key=lambda p: p.length * p.width, reverse=True)

        sheets = [Sheet(self.sheet_length, self.sheet_width)]
        placements = []

        for part in all_parts:
            placed = False
            for sheet in sheets:
                result = self._try_place(sheet, part)
                if result:
                    placements.append({
                        'part_id': part.id,
                        'sheet_index': sheets.index(sheet),
                        'x': result[0], 'y': result[1],
                        'rotated': result[2]
                    })
                    placed = True
                    break

            if not placed:
                # 開新板
                new_sheet = Sheet(self.sheet_length, self.sheet_width)
                result = self._try_place(new_sheet, part)
                if result:
                    placements.append({
                        'part_id': part.id,
                        'sheet_index': len(sheets),
                        'x': result[0], 'y': result[1],
                        'rotated': result[2]
                    })
                    sheets.append(new_sheet)

        # 計算利用率
        total_part_area = sum(p.length * p.width for p in all_parts)
        total_sheet_area = len(sheets) * self.sheet_length * self.sheet_width
        utilization = total_part_area / total_sheet_area

        return {
            'sheets_used': len(sheets),
            'utilization_rate': round(utilization, 4),
            'placements': placements,
            'waste_area_mm2': total_sheet_area - total_part_area,
            'remnants': self._calculate_remnants(sheets, placements)
        }

    def _try_place(self, sheet: Sheet, part: Part) -> Tuple:
        """嘗試將零件放入板材，返回(x, y, rotated)或None"""
        orientations = [(part.length, part.width, False)]
        if part.can_rotate and part.length != part.width:
            orientations.append((part.width, part.length, True))

        best_rect = None
        best_area = float('inf')
        best_orientation = None

        for pl, pw, rotated in orientations:
            for rect in sheet.free_rects:
                rx, ry, rw, rh = rect
                if pl + self.kerf <= rw and pw + self.kerf <= rh:
                    # Best-fit: 選剩餘面積最小的
                    remaining = rw * rh - pl * pw
                    if remaining < best_area:
                        best_area = remaining
                        best_rect = rect
                        best_orientation = (pl, pw, rotated, rx, ry)

        if best_rect and best_orientation:
            pl, pw, rotated, x, y = best_orientation
            self._split_rect(sheet, best_rect, x, y, pl, pw)
            return (x, y, rotated)
        return None

    def _split_rect(self, sheet, rect, x, y, part_l, part_w):
        """Guillotine切割：放置後分割剩餘空間"""
        rx, ry, rw, rh = rect
        sheet.free_rects.remove(rect)
        # 右側剩餘
        if rw - part_l - self.kerf > 10:  # >10mm才算可用
            sheet.free_rects.append((x + part_l + self.kerf, ry,
                                     rw - part_l - self.kerf, rh))
        # 下方剩餘
        if rh - part_w - self.kerf > 10:
            sheet.free_rects.append((rx, y + part_w + self.kerf,
                                     rw, rh - part_w - self.kerf))

    def _calculate_remnants(self, sheets, placements):
        """計算可回收剩料"""
        remnants = []
        for i, sheet in enumerate(sheets):
            for rect in sheet.free_rects:
                x, y, w, h = rect
                if w >= 50 and h >= 50:  # 5cm x 5cm以上才值得回收
                    remnants.append({
                        'sheet_index': i,
                        'x': x, 'y': y,
                        'length_mm': w, 'width_mm': h,
                        'area_mm2': w * h
                    })
        return remnants
```

---

## 七、AI報價引擎（Phase 1 規則版）

```python
# app/ai/quote_engine.py
from dataclasses import dataclass
from typing import Dict, List

# 壓克力板材單價表（每才 = 30x30 cm）
ACRYLIC_PRICE_PER_CAI = {
    ('transparent', 2): 120,
    ('transparent', 3): 145,
    ('transparent', 5): 185,
    ('transparent', 8): 280,
    ('white', 2): 130,
    ('white', 3): 158,
    ('white', 5): 200,
    ('black', 3): 160,
    ('black', 5): 210,
    ('frosted', 3): 170,
    ('frosted', 5): 230,
}

# 加工成本（每分鐘）
PROCESSING_COST = {
    'cnc_cut': 8,           # CNC裁切 $8/分鐘
    'laser_engrave': 12,    # 雷射雕刻 $12/分鐘
    'laser_cut': 10,        # 雷射裁切 $10/分鐘
    'drilling': 5,          # 鑽孔 $5/分鐘
    'polishing': 6,         # 拋光 $6/分鐘
    'assembly': 4,          # 組裝 $4/分鐘（人工）
    'painting': 15,         # 噴漆 $15/分鐘（含材料）
    'quality_check': 2,     # 品檢 $2/分鐘
}

# 一才 = 30cm x 30cm = 0.09 m²
CAI_TO_MM2 = 300 * 300  # mm²

class QuoteEngine:
    def __init__(self, overhead_rate: float = 0.25, target_margin: float = 0.35):
        self.overhead_rate = overhead_rate    # 25% 管銷攤提
        self.target_margin = target_margin   # 35% 目標毛利

    def calculate_acrylic_cost(self, bom_items: List[Dict]) -> float:
        """計算壓克力材料成本"""
        total = 0
        for item in bom_items:
            if item['type'] != 'acrylic':
                continue
            area_mm2 = item['length_mm'] * item['width_mm'] * item['quantity']
            area_cai = area_mm2 / CAI_TO_MM2
            # 加10%損耗
            area_with_waste = area_cai * 1.10
            color = item.get('color', 'transparent')
            thickness = item['thickness_mm']
            price_per_cai = ACRYLIC_PRICE_PER_CAI.get(
                (color, thickness), 200
            )
            total += area_with_waste * price_per_cai
        return round(total, 2)

    def calculate_processing_cost(self, operations: List[Dict]) -> float:
        """計算加工成本"""
        total = 0
        for op in operations:
            op_type = op['type']
            minutes = op['estimated_minutes']
            quantity = op.get('quantity', 1)
            rate = PROCESSING_COST.get(op_type, 5)
            total += minutes * quantity * rate
        return round(total, 2)

    def generate_quote(self, bom_items: List[Dict],
                      operations: List[Dict],
                      quantity: int = 1) -> Dict:
        material_cost = self.calculate_acrylic_cost(bom_items) * quantity
        processing_cost = self.calculate_processing_cost(operations) * quantity
        overhead_cost = (material_cost + processing_cost) * self.overhead_rate

        subtotal = material_cost + processing_cost + overhead_cost
        final_price = subtotal / (1 - self.target_margin)

        return {
            'quantity': quantity,
            'material_cost': material_cost,
            'processing_cost': processing_cost,
            'overhead_cost': round(overhead_cost, 2),
            'subtotal': round(subtotal, 2),
            'profit_margin': self.target_margin,
            'final_price': round(final_price, 2),
            'unit_price': round(final_price / quantity, 2),
            'breakdown': {
                'acrylic': self.calculate_acrylic_cost(bom_items),
                'cnc_laser': sum(
                    PROCESSING_COST.get(op['type'], 5) * op['estimated_minutes']
                    for op in operations if op['type'] in ['cnc_cut','laser_cut','laser_engrave']
                ),
                'assembly': sum(
                    PROCESSING_COST['assembly'] * op['estimated_minutes']
                    for op in operations if op['type'] == 'assembly'
                ),
            }
        }
```

---

## 八、MVP 開發計畫（6個月）

### Sprint 0（Week 1-2）：環境建置
- [ ] 建立 GitHub Monorepo（frontend/ + backend/）
- [ ] Docker Compose 開發環境
- [ ] PostgreSQL + Alembic 初始化
- [ ] 基本RBAC認證（FastAPI + JWT）
- [ ] Next.js 專案架構 + shadcn/ui
- [ ] CI/CD Pipeline（GitHub Actions）

### Sprint 1（Week 3-4）：官網上線
- [ ] 首頁（公司介紹 + 品牌案例輪播）
- [ ] 作品展示頁面（portfolio_cases表）
- [ ] 線上詢價表單（email通知）
- [ ] 關於我們 + 設備介紹頁
- [ ] SEO基礎（meta、sitemap、robots.txt）
- [ ] 響應式設計（手機/平板）

### Sprint 2（Week 5-6）：物料主檔
- [ ] 材料主檔 CRUD（壓克力板、木料、鐵件）
- [ ] 客戶主檔 CRUD（含聯絡人）
- [ ] 產品主檔 CRUD
- [ ] 基礎BOM建立（單層）
- [ ] 供應商主檔

### Sprint 3（Week 7-8）：庫存系統
- [ ] 板材庫存管理（入庫、查詢、庫存餘額）
- [ ] 庫存異動記錄（完整追溯）
- [ ] 安全庫存預警
- [ ] 剩料入庫登記
- [ ] 庫存盤點功能

### Sprint 4（Week 9-10）：採購+報價
- [ ] 採購單 CRUD + 審批流程
- [ ] 進貨驗收（含品質備注）
- [ ] 報價單建立（手動填寫成本）
- [ ] 報價單PDF匯出（WeasyPrint）
- [ ] AI報價規則引擎（Phase 1）

### Sprint 5（Week 11-12）：工單系統
- [ ] 工單建立 + BOM展開
- [ ] 工序管理（CNC/雷射/組裝）
- [ ] 工單發料（從庫存扣料）
- [ ] MES報工介面（平板大按鈕）
- [ ] 工單完工入庫

### Sprint 6（Week 13-14）：裁切優化
- [ ] BFD排版引擎（Python）
- [ ] 裁切視覺化工作台（Konva.js）
- [ ] 利用率計算 + 報表
- [ ] 剩料自動入庫
- [ ] 排版結果匯出（切割指示圖PNG）

### Sprint 7（Week 15-16）：儀表板+上線
- [ ] 廠長儀表板（Recharts圖表）
- [ ] 材料利用率月報
- [ ] 訂單達交率追蹤
- [ ] 系統整合測試
- [ ] 正式部署（AWS Taiwan）
- [ ] 使用者教育訓練

---

## 九、RBAC 權限矩陣

| 角色 | 報價 | BOM | 庫存 | 採購 | 工單/MES | 設備 | 成本 | 管理 |
|------|------|-----|------|------|----------|------|------|------|
| 系統管理員 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 廠長/總經理 | 讀 | 讀 | 讀 | 讀 | 讀 | 讀 | ✅ | 讀 |
| 業務/報價 | ✅ | 讀 | 讀 | ✗ | ✗ | ✗ | ✗ | ✗ |
| 工程師 | ✗ | ✅ | 讀 | ✗ | ✗ | ✗ | ✗ | ✗ |
| 生管 | ✗ | 讀 | 讀 | 讀 | ✅ | 讀 | ✗ | ✗ |
| 倉管 | ✗ | ✗ | ✅ | 讀 | 讀 | ✗ | ✗ | ✗ |
| 採購 | ✗ | 讀 | 讀 | ✅ | ✗ | ✗ | ✗ | ✗ |
| 現場作業員 | ✗ | ✗ | ✗ | ✗ | MES報工 | ✗ | ✗ | ✗ |
| 品管 | ✗ | ✗ | 讀 | ✗ | 品質回報 | ✗ | ✗ | ✗ |

> **實作對照（v2.0 修正）**：本表規劃 9 種角色，但 `backend/scripts/seed_data.py`
> 自 v1.0 起只建立 8 種，**品管（qc）角色從未進過資料庫**——規格書與實作長期不一致，
> 且歷來驗證都只檢查「8 種角色是否正確建立」，沒有回頭核對「8」是否等於本表的角色數。
> v2.0 已於 seed 補上 `qc`，實測建立 9 種。
> 對應的 `Role.name` 依序為：
> `admin` / `owner` / `sales` / `engineer` / `planner` / `warehouse` / `purchaser` / `operator` / `qc`。

---

## 十、Claude Code 開發指令（完整版）

### 初始化專案
```bash
# 建立 Monorepo
mkdir acrylic-erp && cd acrylic-erp
git init

# 後端
mkdir backend && cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary \
  python-jose passlib celery redis python-multipart \
  pillow reportlab ezdxf pymupdf pydantic-settings

# 前端
cd ../
npx create-next-app@latest frontend \
  --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
npx shadcn-ui@latest init
npx shadcx-ui@latest add button card table form dialog \
  select dropdown-menu badge tabs sheet
npm install @tanstack/react-table @tanstack/react-query \
  react-hook-form zod zustand recharts konva react-konva \
  next-pwa lucide-react
```

### Claude Code Slash Commands（在Claude Project中使用）
```
/create-module inventory
→ 產生完整庫存模組（Model + Schema + Router + Service）

/create-api-route POST /api/v1/nesting/calculate
→ 產生裁切計算API端點

/create-component NestingCanvas
→ 產生裁切視覺化React元件

/generate-migration add_remnant_inventory
→ 產生Alembic資料庫遷移腳本

/create-test inventory_service
→ 產生pytest單元測試
```

### Cursor 開發指令（.cursor/rules）
```markdown
# Acrylic ERP Development Rules

You are building an ERP system for a Taiwanese acrylic display manufacturer.

## Backend Rules
- Always use FastAPI with async/await
- Use SQLAlchemy 2.0 ORM style
- Every endpoint needs JWT authentication via Depends(get_current_user)
- Log all write operations to audit_logs table
- Return structured JSON: {data: ..., message: ..., success: bool}
- Handle PostgreSQL connection with connection pooling

## Frontend Rules  
- Use shadcn/ui components, never custom raw HTML
- All forms must use React Hook Form + Zod validation
- API calls via TanStack Query (useQuery/useMutation)
- Zustand for global state (user, permissions)
- Always check permissions before rendering admin buttons

## Acrylic Domain Rules
- Sheet sizes are in mm (2000x1000 standard)
- 1 才 (cai) = 300mm x 300mm = 90,000 mm²
- Always store quantity with 4 decimal places
- BOM wastage_rate is decimal (0.05 = 5%)
- Nesting utilization_rate is decimal (0.924 = 92.4%)
```

---

## 十一、三年擴充藍圖

### 第一年（月1-12）：核心ERP落地
- 官網 + CRM + BOM + 庫存 + 採購 + 工單 ✅
- 裁切優化（BFD演算法）✅
- AI報價（規則引擎）✅
- 廠長儀表板 ✅

### 第二年（月13-24）：智慧製造
- APS高級排程（插單、設備故障重排）
- AI報價2.0（機器學習，歷史案例推薦）
- 設備OEE計算與分析
- 客戶自助訂單查詢Portal
- 供應商協作入口
- 裁切優化2.0（遺傳演算法）

### 第三年（月25-36）：生態擴充
- AI品質視覺檢測（壓克力刮傷/氣泡辨識）
- 設備IoT連線（CNC稼動率實時監控）
- 裁切優化3.0（深度強化學習DRL）
- 多廠區支援（SaaS多租戶商業化）
- CAD圖面自動解析 → BOM生成
- 智慧補料（預測性MRP）

---

## 十二、Claude Project 使用說明

**建立專案後，上傳此文件，並貼入以下系統提示：**

```
你是一位資深全棧工程師，正在建構「壓克力展示架智慧工廠ERP系統」。

技術棧：
- 後端：FastAPI + SQLAlchemy + PostgreSQL + Celery + Redis
- 前端：Next.js 14 + Tailwind CSS + shadcn/ui + TanStack Query
- 裁切優化：Python 2D Nesting（BFD → GA → DRL）
- AI報價：規則引擎 → 機器學習模型

開發原則：
1. 每次只做一個功能模組
2. 先寫SQLAlchemy Model → 然後Pydantic Schema → 然後Service層 → 最後Router
3. 前端：先shadcn/ui元件 → 然後API整合 → 然後狀態管理
4. 壓克力業務邏輯：1才=30cmx30cm，板材標準2000x1000mm，刀縫3mm
5. 所有金額以新台幣TWD計算，數量保留4位小數

當前開發重點：[依Sprint填入當前任務]

請根據上傳的MASTER_SPEC.md規格書進行開發。
```

---

## 十三、版本紀錄與目前實際完成狀態

> 本節與 `acrylic-erp-verified.zip` 內 `README.md` 的「版本紀錄」章節同步維護，
> 兩份文件內容應保持一致。任何一方修改後，務必回填另一方，
> 避免多對話/多工作階段並行開發時版本分岔。**詳細技術修復內容以 README.md 為主，本節僅列摘要。**

### 目前狀態總覽（供新對話框快速銜接，取代逐行閱讀本規格書一至十二章的完成度判斷）

- **基準交付物**：GitHub 儲存庫 `zev-666/HankERP`（v2.0 起以 git 為單一事實來源，
  不再用 zip 傳遞版本）。**131 個受版控檔案**（70 Python ＋ 34 TypeScript/TSX ＋ 設定與文件），
  涵蓋 **13 個業務模組、68 個業務 API 端點（不含 `/health`，共 69 個 HTTP 端點）、
  30 張業務資料表（＋`alembic_version` 共 31 張）、23 條前端路由（21 靜態 ＋ 2 動態）**
- **前端技術棧**：Next.js **16.3.5**（v2.0 因 Next 16.3.1 被揭露 RCE 漏洞而升級），
  `npm audit` 0 vulnerabilities、`eslint . --max-warnings=0` 0 error 0 warning
- **⚠️ 數字保鮮期**：以上每個數字都是 v2.0 當下量出來的。
  本專案歷史上最常見的錯誤就是沿用上一版文件的數字而不重新量測
  （「52個端點」錯了六版、「17個頁面」錯了四版、「62個端點」在 v1.7 移除
  `setup-admin` 後又錯了一版、「npm audit 0 漏洞」一個月後變成 3 項含 critical）。
  **任何一次交付前都必須重新量測**，量法見 `CONTRIBUTING.md`
- **驗證方式**：全程使用全新安裝的 PostgreSQL 16 ＋ Redis ＋ 全新 Python venv ＋ 全新
  `npm ci`（非沿用殘留環境）＋ 真實 uvicorn ＋ 真實 HTTP request ＋ JWT 認證，
  非靜態程式碼推論；前端另以真實 `npm run build` 與真實 `next start` ＋ curl HTML，
  確認 API 內容確實出現在渲染後的頁面裡（**build 成功與 API 回 200 都不能證明前後端有串接**）
- **已完整端到端測試的模組**：nesting（含9板型比較）、customers、inventory（含成品 FG 倉）、
  analytics、products/BOM、purchasing、production（含 MES 報工、發料扣庫存、完工入庫）、
  quotation（含 PDF 匯出＋資料持久化驗證）、equipment、portfolio（含官網前端串接）、
  inquiries（官網送出→落庫→後台→轉客戶）
- **核心業務流程（v2.0 起全線打通）**：
  `官網詢價 → 詢價管理 → 轉客戶 → 報價 → PDF`；
  `產品+BOM → 工單 → 發料(扣RAW倉) → MES報工 → 完工入庫(進FG倉)`。
  v2.0 之前「發料」與「完工入庫」兩個環節不存在，生產與庫存兩個模組從未串接
- **資安稽核狀態**：`pip-audit` 0 已知漏洞、`bandit` 0 Medium/High、`npm audit` 0 漏洞
  （v2.0 重新掃描確認，非引用 v1.7 的舊結論）；已移除無身份驗證的管理員建立端點、
  正式環境弱密鑰啟動防呆、PostgreSQL/Redis 不對外曝露 port、
  `/login` 與官網公開詢價端點皆有 rate limiting、容器非 root 執行、前端安全標頭
- **Celery 基礎設施狀態（v1.9）**：`autodiscover_tasks` 命名慣例 bug 已修正
  （原本 worker 完全找不到任何 task），已用與正式部署一致的 `--concurrency=4`
  （prefork 多進程池）驗證。但 `calculate_nesting_async`、`batch_optimize_multiple_orders`
  仍是死程式碼，沒有任何 router 呼叫，屬預留的未來擴充能力
- **工程基礎建設（v2.0 新增）**：
  `.github/workflows/ci.yml`（CI 真的起 PostgreSQL 跑 migration ＋ seed ＋ 端到端 HTTP 測試，
  並印出當下實際端點數）、`backend/scripts/verify_e2e.py`（可重複執行的端到端驗證，
  本機與 CI 共用）、`CLAUDE.md`（AI 協作指引：工程規則 ＋ ERP 顧問決策框架）、
  `CONTRIBUTING.md`、`LICENSE`
- **已知限制**：
  1. 真正的 `docker compose up` 完整流程尚未在容器化環境驗證過（歷來各驗證沙盒
     皆無法連線 Docker Hub 拉取基礎映像檔），僅驗證過 `docker-compose.yml` 語法、
     `db`/`redis` 無 port 曝露、`Dockerfile` 建置流程至映像檔拉取步驟為止；
     使用者本機的 Docker Desktop 環境應無此網路限制
  2. Celery 的兩個 task（見上）仍是死程式碼
  3. `equipment/{id}/status` 的 `status` 為 query 參數而非 JSON body，與其餘端點慣例不一致
  4. 作品 slug 保留中文字元，URL 會被百分比編碼，不利分享與 SEO
     （v2.0 已修好因此造成的詳情頁 404 bug，但 slug 生成規則本身未改）
  5. 詢價尚無 email／LINE 通知，業務需自行進後台查看
  6. 安全庫存預警、庫存盤點報表、供應商比價、報價轉銷售訂單仍未實作（見 `MVP_CHECKLIST.md`）

### 版本紀錄表

| 版本 | 日期 | 修正範圍 | 驗證方式 |
|---|---|---|---|
| v2.0 | 2026-09-14 | **三份上傳檔案合併為單一 GitHub repo（HankERP）**，並補完先前誠實標為❌的功能缺口：①線上詢價表單真的送出（新增 `inquiries` 表與模組、公開端點含 rate limit、後台管理頁、轉客戶冪等）②官網作品展示改讀真實 API（首頁不再是寫死的4筆假資料，新增 `/portfolio` 列表與 `/portfolio/[slug]` 詳情、後台作品管理頁）③工單發料扣庫存＋完工入庫（含資料庫結構變更：`inventory_balances`/`inventory_transactions` 新增 `product_id` 並以 CHECK 約束保證與 `material_id` 互斥，`work_orders` 新增 `completed_qty`）④新增 `/about` 與 SEO（sitemap/robots）⑤seed 補上品管角色（8→9種）。**重新量測後發現三項文件數字再度過期**：端點 62→61（v1.7 移除 setup-admin 後未重數）、檔案 108→110、`npm audit` 0→3（含 Next.js critical RCE，已升級 16.3.1→16.3.5）。**新修復 4 個 bug**：#14 Next 16 動態路由參數未解碼導致作品詳情頁一律404、#15 `seed_data.py` 在容器外必定失敗、#16 seed 重跑會 IntegrityError、#17 前端結構化錯誤明細被吃成 `[object Object]`。另清掉存在已久的 4 個 ESLint warning，新增 CI workflow、端到端驗證腳本、CLAUDE.md、CONTRIBUTING.md、LICENSE | 全新 PostgreSQL 16＋全新 venv＋全新 `npm ci`；真實 uvicorn 讀 `/openapi.json` 數端點（68＋health）、真實 `npm run build` 數路由（23）、真實查 `information_schema` 數表（30＋alembic_version）、`pytest -q` 17 passed、`eslint --max-warnings=0` 全綠、`npm audit` 0 漏洞；`scripts/verify_e2e.py` 13 個端到端情境全通過（含庫存不足整批擋下、工序未完成不准入庫、重複入庫擋下、重複轉客戶冪等等「故意失敗」案例）；真實 `next start` ＋ curl HTML 確認官網前後端確實串接 |
| v1.9 | 2026-08-31～09-09 | Celery worker基礎設施稽核：`celery_app.py`的`autodiscover_tasks(["app.tasks"])`命名慣例與`nesting_tasks.py`檔名不符，導致真正啟動worker後完全找不到任何task（若接上`.delay()`會回報`NotRegistered`）；改用明確import修正。另修正`calculate_nesting_async`缺label欄位會`TypeError`崩潰的問題，並將`main.py`與`auth/router.py`各自獨立的`Limiter`實例整合為共用單一實例。**後續追加**：先前僅用`--pool=solo`驗證，與`docker-compose.yml`實際部署的`--concurrency=4`（prefork多進程池）存在差異；改用完全一致的部署指令重新測試，確認prefork模式下單一任務與4個任務並行皆正確完成；同時修正worker啟動時的`CPendingDeprecationWarning`（`broker_connection_retry_on_startup`未明確設定） | 真實啟動`celery -A app.tasks.celery_app worker`背景程序（非僅測試底層函式），確認`[tasks]`啟動日誌列出task；用`.delay()`送出真實任務確認`received→succeeded`；**用與部署完全一致的`--concurrency=4`指令**重新驗證單一任務+4任務並行（received/succeeded各5次數字吻合）；確認`celery`服務與`backend`服務共用同一份已改為非root執行的Dockerfile；12模組HTTP回歸+17項pytest+前端16頁面build全部重跑確認無破壞 |
| v1.8 | 2026-08-26 | 重新從頭驗證時發現3個問題：①`pip`本身24.0版CVE，升級至26.2.1 ②v1.7新增的`docker-compose.yml`資安機制要求根目錄`.env`設定`SECRET_KEY`，但README步驟1從未提及要建立此檔案，照文件操作會在步驟2卡住 ③README長期提及不存在的MinIO服務，純屬文件殘留 | 完全依照修正後README步驟逐字操作（而非用已知捷徑指令繞過），重現「照文件操作會卡住」的問題後修正，再重新走一次完整步驟確認成功 |
| v1.7 | 2026-08-21 | **資安漏洞稽核**：`pip-audit`掃描出44個依賴套件已知漏洞（python-jose/starlette/python-multipart/pillow），全部升級或移除歸零；`bandit`靜態分析抓到`POST /setup-admin`完全無身份驗證且密碼寫死的高風險端點，直接移除；`SECRET_KEY`預設弱值加上正式環境啟動防呆檢查；`docker-compose.yml`的PostgreSQL/Redis直接對外曝露port（Redis無密碼是已知大規模掃描攻擊入侵管道）已移除；加上`slowapi`做rate limiting防暴力破解；容器改為非root使用者執行；前端補上安全標頭(CSP/HSTS等) | `pip-audit`44→0漏洞、`bandit`2→0問題、`npm audit`0漏洞；真實暴力破解模擬（第6次登入429正確擋下）；正式環境弱密鑰啟動防呆機制實測生效；`docker compose config`確認db/redis無port曝露 |
| v1.6 | 2026-08-19 | 抓到本專案史上最大文件錯誤：「52個API端點」自v1.0基準起就是錯的，真實數字是62個業務端點（63個含/health），六輪對話都沒抓到。用grep+Python精確解析+真實OpenAPI schema三種方法交叉驗證後修正全部文件 | 三種獨立方法交叉驗證（grep裝飾器/Python解析prefix+path/真實啟動伺服器讀取FastAPI OpenAPI schema），一次性收集問題後統一修正、只打包驗證一次 |
| v1.5 | 2026-08-18 | 使用者要求重新自我稽核後，抓到3個「文件宣稱與程式碼實際不符」問題（非新bug，是文件本身寫錯）：①「17個頁面」數字自v1.0基準起就是錯的，實際應為16個，一路延續到v1.4都沒被抓出來 ②README宣稱「官網首頁讀取portfolio」，實際首頁案例區塊是寫死假資料，完全沒呼叫`/api/v1/public/portfolio`，且`(public)/portfolio/`是空資料夾 ③`/quote`詢價表單送出按鈕沒有任何API呼叫，純前端UI假動作 | 直接讀取所有`page.tsx`原始碼，逐一搜尋API呼叫模式核對文件宣稱是否屬實，而非僅驗證build/test能否通過 |
| v1.4 | 2026-08-17 | 前端Next.js大版本升級14→16.3.1（npm audit漏洞歸零）；升級過程中發現並修復bug#13（Dockerfile缺PYTHONPATH，導致seed_data.py在容器內ModuleNotFoundError）；`next lint`移除改用ESLint9 flat config | 第4組獨立全新環境（PostgreSQL+venv+npm）端到端測試，含bug#6/#11/#12回歸測試 |
| v1.3 | 2026-08-17 | 發現並修復2個新bug：①`alembic.ini`缺少`prepend_sys_path`導致migration照README步驟執行會失敗 ②報價單手動定價品項未被計入header總額（資料完整性問題）。另補齊pytest依賴缺口、前端Next.js安全性更新至14.2.35、建立缺失的.gitignore | 全新PostgreSQL+venv+npm環境端到端測試，並將打包後的zip重新解壓縮到獨立目錄二次驗證 |
| v1.2 | 2026-08-13 | 文件同步：補齊v1.0完整10項bug清單，同步README.md/MASTER_SPEC.md/MVP_CHECKLIST.md與zip實際狀態 | 逐檔案比對，無程式碼變更 |
| v1.1 | 2026-08-12 | `backend/alembic/env.py` 未讀取 `.env`，導致 docker-compose 環境下 migration 連線失敗 | 真實PostgreSQL + 乾淨venv + 端到端HTTP測試，並與獨立對話框交叉驗證修正邏輯等價 |
| v1.0 | （基準） | 10個歷史bug修復：①database.py大小寫 ②nesting label參數缺失 ③bcrypt版本未鎖定 ④.env.example含未定義欄位 ⑤celery_app.py大小寫 ⑥products/BOM router未註冊 ⑦報價unit_price被None覆蓋(靜默資料遺失) ⑧email-validator缺失 ⑨Google字型建置期外部依賴 ⑩見v1.1。另新增compare-presets板型比較功能 | 真實PostgreSQL + 真實uvicorn + 真實HTTP request，12模組62端點逐一測試 |

**下次新增修正時，請依此格式在表格新增一列，並在 README.md 補上對應的詳細段落。**

