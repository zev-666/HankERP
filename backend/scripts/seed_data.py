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
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext  # noqa: E402
from sqlalchemy import select, func  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.user import Tenant, Role, User  # noqa: E402

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_EMAIL = "admin@guishan-acrylic.com"

# v2.2 資安：管理員密碼不再寫死在原始碼裡。本 repo 是公開的，
# 先前的預設密碼等同公開在 GitHub 上，而正式站就是用它建起來的。
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD")

# v2.2：權限矩陣。這張表必須與 app/auth/permissions.py 的 PERMISSION_MAP
# 以及 MASTER_SPEC 第九章保持一致，三者任一改動都要同步另外兩處。
#
# 動作：read / write / approve / export，外加兩個現場專用動作
# mes_report（作業員報工）、quality_report（品管回報），
# 以及 receive（收貨，同時動採購單與庫存）。
ROLES = [
    {
        "name": "admin", "display_name": "系統管理員",
        # "*" 資源 + "*" 動作：涵蓋所有模組所有動作，含帳號管理（admin 資源）。
        "permissions": {"*": ["*"]},
    },
    {
        "name": "owner", "display_name": "廠長/總經理",
        # v2.2 變更：原本是 {"*": ["read"]} 純唯讀，意味著廠長連採購單都不能簽，
        # 所有核准都得用 admin 帳號——實務上會導致大家共用管理員密碼，
        # RBAC 等於白做。改為唯讀 ＋ 核准 ＋ 匯出，但不含帳號管理。
        "permissions": {
            "customers": ["read"],
            "quotation": ["read", "approve"],
            "products": ["read", "approve"],
            "nesting": ["read"],
            "inventory": ["read"],
            "purchasing": ["read", "approve"],
            "production": ["read"],
            "equipment": ["read"],
            "analytics": ["read", "export"],
            "inquiries": ["read"],
            "portfolio": ["read"],
        },
    },
    {
        "name": "sales", "display_name": "業務/報價專員",
        # v2.2 變更：補上 products / inventory / production 的讀取權限。
        # 沒有這些的話，業務報價時看不到 BOM 與現有庫存，報價功能會直接壞掉。
        "permissions": {
            "customers": ["read", "write"],
            "quotation": ["read", "write", "export"],
            "products": ["read"],
            "nesting": ["read"],
            "inventory": ["read"],
            "production": ["read"],
            "inquiries": ["read", "write"],
            "portfolio": ["read", "write"],
        },
    },
    {
        "name": "engineer", "display_name": "工程師",
        "permissions": {
            "quotation": ["read"],
            "products": ["read", "write"],
            "nesting": ["read", "write"],
            "inventory": ["read"],
            "production": ["read"],
            "equipment": ["read"],
        },
    },
    {
        "name": "planner", "display_name": "生管",
        # v2.2 變更：補上 nesting:write。排產要算裁切，原本只有工程師有。
        "permissions": {
            "products": ["read"],
            "nesting": ["read", "write"],
            "inventory": ["read"],
            "purchasing": ["read"],
            "production": ["read", "write"],
            "equipment": ["read"],
        },
    },
    {
        "name": "warehouse", "display_name": "倉管員",
        # receive：採購收貨。NEEDS_FACTORY_VERIFICATION——現場實際由倉管
        # 或採購執行尚未確認，暫定兩者皆可。
        "permissions": {
            "products": ["read"],
            "inventory": ["read", "write"],
            "purchasing": ["read", "receive"],
            "production": ["read"],
        },
    },
    {
        "name": "purchaser", "display_name": "採購專員",
        "permissions": {
            "products": ["read"],
            "inventory": ["read"],
            "purchasing": ["read", "write", "receive"],
        },
    },
    {
        "name": "operator", "display_name": "現場作業員",
        # v2.2 變更：補上 production:read。原本只有 mes_report，
        # 但報工前必須先讀得到工單與工序清單，否則作業員連要報哪一道都看不到。
        "permissions": {"production": ["read", "mes_report"]},
    },
    {
        # v2.0 補上：MASTER_SPEC 第九章 RBAC 權限矩陣規劃了9種角色（含品管），
        # 但此腳本先前只建立8種，品管角色從未真正進到資料庫——規格書與實作長期不一致。
        "name": "qc", "display_name": "品管",
        "permissions": {
            "products": ["read"],
            "inventory": ["read"],
            "production": ["read", "quality_report"],
            "equipment": ["read"],
        },
    },
]

async def _sync_roles(db, tenant_id) -> tuple[int, int]:
    """
    把 ROLES 同步進資料庫：缺的新增，已存在的更新 display_name 與 permissions。

    v2.2：先前的 idempotent 做法是「租戶已存在就整段跳過」，
    結果是既有資料庫的角色權限永遠停在第一次建立時的版本。
    RBAC 上線後這會變成真正的問題——權限矩陣改了，實際生效的卻還是舊的。
    回傳 (新增數, 更新數)。
    """
    existing_roles = {
        r.name: r for r in (await db.execute(
            select(Role).where(Role.tenant_id == tenant_id)
        )).scalars().all()
    }
    created = updated = 0
    for spec in ROLES:
        role = existing_roles.get(spec["name"])
        if role is None:
            db.add(Role(id=uuid.uuid4(), tenant_id=tenant_id, name=spec["name"],
                        display_name=spec["display_name"], permissions=spec["permissions"]))
            created += 1
            continue
        if role.display_name != spec["display_name"] or role.permissions != spec["permissions"]:
            role.display_name = spec["display_name"]
            role.permissions = spec["permissions"]
            updated += 1
    await db.flush()
    return created, updated


async def seed():
    if not ADMIN_PASSWORD:
        print("✗ 未設定環境變數 SEED_ADMIN_PASSWORD，拒絕建立管理員帳號。")
        print("  v2.2 起管理員密碼不再有寫死的預設值（本 repo 為公開儲存庫）。")
        print("  本機請在專案根目錄 .env 加入 SEED_ADMIN_PASSWORD=<自訂密碼>，")
        print("  CI 與正式環境請以環境變數或 secret 提供。")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        # v2.0：改為可重複執行（idempotent）。先前版本每跑一次就多一個租戶、
        # 多一組角色、並在建立同一組管理員 email 時因 unique 約束直接爆錯，
        # 而錯誤訊息（IntegrityError）完全看不出「其實你已經建過了」。
        existing = (await db.execute(
            select(Tenant).where(Tenant.slug == "guishan-acrylic")
        )).scalar_one_or_none()
        if existing:
            created, updated = await _sync_roles(db, existing.id)
            await db.commit()
            role_count = (await db.execute(
                select(func.count(Role.id)).where(Role.tenant_id == existing.id)
            )).scalar()
            print("ℹ️  種子資料已存在，未重複建立租戶與管理員")
            print(f"   租戶ID: {existing.id}（角色 {role_count} 種）")
            print(f"   角色同步：新增 {created} 種、更新權限 {updated} 種")
            print(f"   管理員帳號: {ADMIN_EMAIL}")
            return

        tenant = Tenant(id=uuid.uuid4(), name="龜山壓克力製造", slug="guishan-acrylic")
        db.add(tenant)
        await db.flush()

        await _sync_roles(db, tenant.id)
        role_map = {
            r.name: r for r in (await db.execute(
                select(Role).where(Role.tenant_id == tenant.id)
            )).scalars().all()
        }

        admin = User(
            id=uuid.uuid4(), tenant_id=tenant.id,
            email=ADMIN_EMAIL,
            hashed_password=pwd_context.hash(ADMIN_PASSWORD),
            full_name="系統管理員",
            role_id=role_map["admin"].id,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ 種子資料建立完成")
        print(f"   租戶ID: {tenant.id}")
        print(f"   角色: {len(ROLES)} 種（{'、'.join(r['display_name'] for r in ROLES)}）")
        print(f"   管理員帳號: {ADMIN_EMAIL}")
        print(f"   管理員密碼: 取自環境變數 SEED_ADMIN_PASSWORD（不在此列印）")

if __name__ == "__main__":
    asyncio.run(seed())
