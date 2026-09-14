from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.rate_limit import limiter
from app.auth.router import router as auth_router
from app.modules.inventory.router import router as inventory_router
from app.modules.nesting.router import router as nesting_router
from app.modules.quotation.router import router as quotation_router
from app.modules.production.router import router as production_router
from app.modules.purchasing.router import router as purchasing_router
from app.modules.equipment.router import router as equipment_router
from app.modules.analytics.router import router as analytics_router
from app.modules.customers.router import router as customers_router
from app.modules.products.router import router as products_router
from app.modules.portfolio.router import router as portfolio_router, public_router as portfolio_public_router
from app.modules.inquiries.router import router as inquiries_router, public_router as inquiries_public_router

# 資安：正式環境關閉Swagger/ReDoc公開文件，避免完整API結構被公開偵查
app = FastAPI(
    title="壓克力展示架智慧工廠 ERP API",
    version="1.0.0",
    description="桃園龜山複合式壓克力製造商 ERP SaaS 平台",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# 資安：Rate Limiting，依來源IP限制請求頻率，防止暴力破解與資源耗盡攻擊
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載所有路由
for router in [
    auth_router, customers_router, inventory_router,
    nesting_router, quotation_router, production_router,
    purchasing_router, equipment_router, analytics_router,
    products_router, portfolio_router, portfolio_public_router,
    inquiries_router, inquiries_public_router,
]:
    app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Acrylic ERP API v1.0"}
