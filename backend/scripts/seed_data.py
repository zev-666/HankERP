"""
種子資料腳本：建立預設租戶、9種角色、管理員帳號

執行方式：
  容器內：docker compose exec backend python scripts/seed_data.py
  本機  ：cd backend && python scripts/seed_data.py

【v2.0 修正】以下 sys.path 修補是必要的：python 直接以檔案路徑執行 .py 時，
sys.path[0] 會是腳本自己所在的 scripts/ 目錄而非專案根目錄，於是 `import app`
會 ModuleNotFoundError。先前版本只在 backend/Dockerfile 加了 ENV PYTHONPATH=/app，
容器內可行，但任何人在本機照 README 執行這一行仍然會失敗。改在腳本內自我修補後，
容器與本機兩條路徑都不必再依賴外部環境變數。
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext  # noqa: E402
from sqlalchemy import select, func  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.user import Tenant, Role, User  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES = [
    {"name": "admin", "display_name": "系統管理員", "permissions": {"*": ["read", "write", "approve", "export"]}},
    {"name": "owner", "display_name": "廠長/總經理", "permissions": {"*": ["read"], "analytics": ["read", "export"]}},
    {"name": "sales", "display_name": "業務/報價專員", "permissions": {"quotation": ["read", "write"], "customers": ["read", "write"]}},
    {"name": "engineer", "display_name": "工程師", "permissions": {"products": ["read", "write"], "nesting": ["read", "write"]}},
    {"name": "planner", "display_name": "生管", "permissions": {"production": ["read", "write"], "purchasing": ["read"]}},
    {"name": "warehouse", "display_name": "倉管員", "permissions": {"inventory": ["read", "write"]}},
    {"name": "purchaser", "display_name": "採購專員", "permissions": {"purchasing": ["read", "write"]}},
    {"name": "operator", "display_name": "現場作業員", "permissions": {"production": ["mes_report"]}},
    # v2.0 補上：MASTER_SPEC 第九章 RBAC 權限矩陣規劃了9種角色（含品管），
    # 但此腳本先前只建立8種，品管角色從未真正進到資料庫——規格書與實作長期不一致。
    {"name": "qc", "display_name": "品管", "permissions": {"inventory": ["read"], "production": ["read", "quality_report"]}},
]

async def seed():
    async with AsyncSessionLocal() as db:
        # v2.0：改為可重複執行（idempotent）。先前版本每跑一次就多一個租戶、
        # 多一組角色、並在建立同一組管理員 email 時因 unique 約束直接爆錯，
        # 而錯誤訊息（IntegrityError）完全看不出「其實你已經建過了」。
        existing = (await db.execute(
            select(Tenant).where(Tenant.slug == "guishan-acrylic")
        )).scalar_one_or_none()
        if existing:
            role_count = (await db.execute(
                select(func.count(Role.id)).where(Role.tenant_id == existing.id)
            )).scalar()
            print("ℹ️  種子資料已存在，未重複建立")
            print(f"   租戶ID: {existing.id}（角色 {role_count} 種）")
            print(f"   管理員帳號: admin@guishan-acrylic.com")
            return

        tenant = Tenant(id=uuid.uuid4(), name="龜山壓克力製造", slug="guishan-acrylic")
        db.add(tenant)
        await db.flush()

        role_map = {}
        for r in ROLES:
            role = Role(id=uuid.uuid4(), tenant_id=tenant.id, name=r["name"],
                       display_name=r["display_name"], permissions=r["permissions"])
            db.add(role)
            role_map[r["name"]] = role
        await db.flush()

        admin = User(
            id=uuid.uuid4(), tenant_id=tenant.id,
            email="admin@guishan-acrylic.com",
            hashed_password=pwd_context.hash("ChangeMe123!"),
            full_name="系統管理員",
            role_id=role_map["admin"].id,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ 種子資料建立完成")
        print(f"   租戶ID: {tenant.id}")
        print(f"   角色: {len(ROLES)} 種（{'、'.join(r['display_name'] for r in ROLES)}）")
        print(f"   管理員帳號: admin@guishan-acrylic.com")
        print(f"   管理員密碼: ChangeMe123!（請立即修改）")

if __name__ == "__main__":
    asyncio.run(seed())
