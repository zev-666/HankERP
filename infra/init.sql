-- 初始化種子資料：啟用必要的PostgreSQL擴充
-- 正式資料表結構由 Alembic migration 建立，此檔案只在容器第一次啟動時執行

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
