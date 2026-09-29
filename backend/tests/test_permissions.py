"""
RBAC 權限表的靜態驗證（v2.2）。

這支測試不需要資料庫，也不發 HTTP request，驗的是三件事：

1. **覆蓋率**：app 上註冊的每一支路由，在 PERMISSION_MAP 裡都有登記。
   這是最重要的一項——`enforce_permissions` 採預設拒絕，漏登記的端點
   會在執行期 403，這裡讓它在 CI 就先炸出來。
2. **無陳舊項目**：PERMISSION_MAP 裡不存在「指向已刪除端點」的殘留規則。
3. **矩陣正確**：seed_data.ROLES 套上這張表之後，每個角色實際能存取的
   端點數與具體的邊界案例符合預期。

實際的 403 行為由 scripts/verify_rbac.py 以真實 HTTP request 驗證，
兩者互補：這裡驗「表對不對」，那裡驗「表有沒有真的生效」。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.permissions import (  # noqa: E402
    AUTHENTICATED,
    PERMISSION_MAP,
    PUBLIC,
    has_permission,
    satisfies,
)
from scripts.seed_data import ROLES  # noqa: E402

ROLE_PERMS = {r["name"]: r["permissions"] for r in ROLES}
PROTECTED = {k: v for k, v in PERMISSION_MAP.items() if v not in (PUBLIC, AUTHENTICATED)}


def _app_routes() -> set[tuple[str, str]]:
    """app 上所有一般 HTTP 路由的 (method, 路徑模板)，排除文件與靜態路由。"""
    from app.main import app

    skip_paths = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}
    routes = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods or path in skip_paths:
            continue
        for m in methods:
            if m in ("HEAD", "OPTIONS"):
                continue
            routes.add((m, path))
    return routes


# ── 1. 覆蓋率與陳舊項目 ────────────────────────────────────────────────

def test_每支路由都有登記權限規則():
    missing = sorted(_app_routes() - set(PERMISSION_MAP))
    assert not missing, (
        "以下端點沒有在 PERMISSION_MAP 登記，執行期會被預設拒絕擋下：\n  "
        + "\n  ".join(f"{m} {p}" for m, p in missing)
    )


def test_權限表沒有指向不存在端點的殘留規則():
    stale = sorted(set(PERMISSION_MAP) - _app_routes())
    assert not stale, (
        "以下規則對應的端點已不存在，請一併移除：\n  "
        + "\n  ".join(f"{m} {p}" for m, p in stale)
    )


def test_端點分類數量符合預期():
    public = [k for k, v in PERMISSION_MAP.items() if v is PUBLIC]
    auth_only = [k for k, v in PERMISSION_MAP.items() if v is AUTHENTICATED]
    # 7 支公開：/health、login、forgot-password、reset-password、
    # 官網詢價送出、官網作品列表、官網作品詳情
    assert len(public) == 7, sorted(public)
    # 1 支僅需登入不看角色：變更自己的密碼
    assert len(auth_only) == 1, sorted(auth_only)
    assert len(PROTECTED) == 61


# ── 2. 權限判斷函式本身 ────────────────────────────────────────────────

def test_萬用字元與精確比對():
    assert has_permission({"*": ["*"]}, "inventory", "write")
    assert has_permission({"inventory": ["read", "write"]}, "inventory", "write")
    assert not has_permission({"inventory": ["read"]}, "inventory", "write")
    assert not has_permission({"inventory": ["read"]}, "production", "read")


@pytest.mark.parametrize("perms", [None, {}, {"nesting": []}])
def test_沒有權限就一支都不能碰(perms):
    accessible = [k for k, rule in PROTECTED.items() if satisfies(perms, rule)]
    assert accessible == [], accessible


# ── 3. 角色矩陣 ───────────────────────────────────────────────────────

# 每個角色實際可存取的受管控端點數。
# 數字本身不是重點，重點是它被釘住了：日後任何人改動 ROLES 或
# PERMISSION_MAP，只要影響到權限範圍就會在這裡亮紅燈，必須有意識地更新。
EXPECTED_ACCESSIBLE = {
    "admin": 61,
    "owner": 31,
    "sales": 30,
    "engineer": 21,
    "planner": 21,
    "warehouse": 18,
    "purchaser": 11,
    "operator": 5,
    "qc": 12,
}


def test_角色數為九():
    assert len(ROLES) == 9
    assert set(ROLE_PERMS) == set(EXPECTED_ACCESSIBLE)


@pytest.mark.parametrize("role_name,expected", sorted(EXPECTED_ACCESSIBLE.items()))
def test_每個角色可存取的端點數(role_name, expected):
    perms = ROLE_PERMS[role_name]
    actual = sum(1 for rule in PROTECTED.values() if satisfies(perms, rule))
    assert actual == expected


def test_管理員可存取全部受管控端點():
    perms = ROLE_PERMS["admin"]
    denied = [k for k, rule in PROTECTED.items() if not satisfies(perms, rule)]
    assert denied == []


# 邊界案例：這些是權限矩陣真正的意圖，數字對不代表分配對。
# 格式：(角色, method, 路徑, 應否放行)
BOUNDARY_CASES = [
    # 只有 admin 能開帳號——這支先前是公開端點且接受前端指定 role_name
    ("admin", "POST", "/api/v1/auth/register", True),
    ("owner", "POST", "/api/v1/auth/register", False),
    ("sales", "POST", "/api/v1/auth/register", False),

    # 業務要報價，就必須讀得到 BOM 與庫存，否則功能會壞掉
    ("sales", "GET", "/api/v1/products/{product_id}/bom", True),
    ("sales", "GET", "/api/v1/inventory/balance", True),
    # 但不能改料、不能看成本分析
    ("sales", "POST", "/api/v1/materials", False),
    ("sales", "GET", "/api/v1/analytics/cost-breakdown", False),

    # 核准類動作只給 admin 與廠長
    ("owner", "POST", "/api/v1/bom/{bom_id}/approve", True),
    ("owner", "POST", "/api/v1/purchase-orders/{po_id}/confirm", True),
    ("engineer", "POST", "/api/v1/bom/{bom_id}/approve", False),
    ("planner", "POST", "/api/v1/purchase-orders/{po_id}/confirm", False),
    # 廠長是唯讀 ＋ 核准，不能寫
    ("owner", "POST", "/api/v1/customers", False),
    ("owner", "POST", "/api/v1/work-orders", False),

    # 作業員只能報工，其餘全擋
    ("operator", "POST", "/api/v1/work-orders/{wo_id}/operations/{op_id}/start", True),
    ("operator", "POST", "/api/v1/work-orders/{wo_id}/operations/{op_id}/complete", True),
    ("operator", "GET", "/api/v1/work-orders/{wo_id}", True),
    ("operator", "POST", "/api/v1/work-orders", False),
    ("operator", "GET", "/api/v1/inventory/balance", False),
    ("operator", "GET", "/api/v1/analytics/dashboard", False),

    # 品管能回報品質，不能報工也不能改庫存
    ("qc", "GET", "/api/v1/work-orders", True),
    ("qc", "POST", "/api/v1/work-orders/{wo_id}/operations/{op_id}/start", False),
    ("qc", "POST", "/api/v1/inventory/receipt", False),

    # 收貨：倉管與採購都可以（NEEDS_FACTORY_VERIFICATION，暫定）
    ("warehouse", "POST", "/api/v1/purchase-orders/{po_id}/receive", True),
    ("purchaser", "POST", "/api/v1/purchase-orders/{po_id}/receive", True),
    ("planner", "POST", "/api/v1/purchase-orders/{po_id}/receive", False),

    # 發料同時動工單與庫存，生管或倉管皆可
    ("planner", "POST", "/api/v1/work-orders/{wo_id}/issue-materials", True),
    ("warehouse", "POST", "/api/v1/work-orders/{wo_id}/issue-materials", True),
    ("qc", "POST", "/api/v1/work-orders/{wo_id}/issue-materials", False),

    # 詢價轉客戶要同時具備兩個模組的寫入權限
    ("sales", "POST", "/api/v1/inquiries/{inquiry_id}/convert-to-customer", True),
    ("owner", "POST", "/api/v1/inquiries/{inquiry_id}/convert-to-customer", False),

    # 裁切：工程師與生管都能算
    ("engineer", "POST", "/api/v1/nesting/calculate", True),
    ("planner", "POST", "/api/v1/nesting/calculate", True),
    ("warehouse", "POST", "/api/v1/nesting/calculate", False),

    # 對外發佈作品比一般編輯高一級
    ("sales", "POST", "/api/v1/portfolio", True),
    ("sales", "POST", "/api/v1/portfolio/{case_id}/publish", False),
]


@pytest.mark.parametrize("role_name,method,path,allowed", BOUNDARY_CASES)
def test_權限矩陣邊界案例(role_name, method, path, allowed):
    rule = PERMISSION_MAP[(method, path)]
    assert satisfies(ROLE_PERMS[role_name], rule) is allowed
