"""
RBAC 執行層（v2.2）。

設計決策與理由
--------------
1. **集中式路由表，而非在每支 router 上掛裝飾器。**
   68 個端點散在 12 個 router 檔，逐支掛 `dependencies=[...]` 的問題是：
   權限規則會散落各處，沒有任何一個地方能一眼看出「誰能碰什麼」，
   而且新增端點時忘記掛上去不會有任何徵兆。
   這裡改成一張表 `PERMISSION_MAP`，key 是 (HTTP method, 路由模板)，
   查表用的是 `request.scope["route"].path`（FastAPI 解析後的模板字串，
   例如 "/api/v1/customers/{customer_id}"），不是使用者傳進來的原始路徑，
   所以不會被路徑變形繞過。

2. **預設拒絕（fail closed）。**
   表上查不到的端點一律 403。新增端點若忘了登記，第一次呼叫就會炸，
   而不是默默全開。這是刻意的：本專案歷史上最常見的問題正是
   「以為有做，其實沒接上」。

3. **不改 Model、不需要 migration。**
   `User.role` 本來就是 `relationship("Role", lazy="joined")`，
   `Role.permissions` 是既有的 JSON 欄位，取 user 時權限就一起載入了。

4. **沒有角色（role_id IS NULL）一律拒絕。**
   `User.role_id` 是 nullable，過去登入時會回一個資料庫裡根本不存在的
   假角色名 "viewer"。這裡不做任何寬容處理：沒有角色就不能碰業務端點。
"""
from __future__ import annotations

from typing import NamedTuple

from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.database import get_db
from app.models.user import User


# ── 規則型別 ──────────────────────────────────────────────────────────

class Need(NamedTuple):
    """需要單一權限。"""
    resource: str
    action: str


class AnyOf(NamedTuple):
    """需要其中任一權限（例如發料：生管或倉管都可以做）。"""
    needs: tuple[Need, ...]


class AllOf(NamedTuple):
    """需要全部權限（例如詢價轉客戶：同時動到詢價與客戶兩個模組）。"""
    needs: tuple[Need, ...]


PUBLIC = "PUBLIC"                  # 不需登入
AUTHENTICATED = "AUTHENTICATED"    # 只要登入即可，不看角色


def _any(*pairs: tuple[str, str]) -> AnyOf:
    return AnyOf(tuple(Need(r, a) for r, a in pairs))


def _all(*pairs: tuple[str, str]) -> AllOf:
    return AllOf(tuple(Need(r, a) for r, a in pairs))


# ── 權限對照表 ────────────────────────────────────────────────────────
# key: (HTTP method, FastAPI 路由模板)
# 這張表就是 MASTER_SPEC 第九章權限矩陣的可執行版本，兩者必須一致。

PERMISSION_MAP: dict[tuple[str, str], object] = {
    # ── 系統 ──
    ("GET", "/health"): PUBLIC,

    # ── 認證 ──
    ("POST", "/api/v1/auth/login"): PUBLIC,
    ("POST", "/api/v1/auth/forgot-password"): PUBLIC,
    ("POST", "/api/v1/auth/reset-password"): PUBLIC,
    ("POST", "/api/v1/auth/change-password"): AUTHENTICATED,
    # v2.2：自助註冊關閉。原本這支是公開端點且接受前端指定 role_name，
    # 任何人都能自己註冊成 admin，RBAC 做得再好也會被這支繞過。
    ("POST", "/api/v1/auth/register"): Need("admin", "write"),

    # ── 客戶 CRM ──
    ("GET", "/api/v1/customers"): Need("customers", "read"),
    ("POST", "/api/v1/customers"): Need("customers", "write"),
    ("GET", "/api/v1/customers/{customer_id}"): Need("customers", "read"),
    ("GET", "/api/v1/customers/{customer_id}/360"): Need("customers", "read"),
    ("PUT", "/api/v1/customers/{customer_id}"): Need("customers", "write"),
    ("GET", "/api/v1/customers/{customer_id}/activities"): Need("customers", "read"),
    ("POST", "/api/v1/customers/{customer_id}/activities"): Need("customers", "write"),

    # ── 報價 ──
    # ai-estimate 只做試算不落地，歸 read。
    ("POST", "/api/v1/quotations/ai-estimate"): Need("quotation", "read"),
    ("POST", "/api/v1/quotations"): Need("quotation", "write"),
    ("GET", "/api/v1/quotations"): Need("quotation", "read"),
    ("PATCH", "/api/v1/quotations/{quote_id}/status"): Need("quotation", "approve"),
    ("GET", "/api/v1/quotations/{quote_id}/pdf"): Need("quotation", "export"),

    # ── 產品 / 物料 / BOM ──
    ("GET", "/api/v1/materials"): Need("products", "read"),
    ("POST", "/api/v1/materials"): Need("products", "write"),
    ("GET", "/api/v1/products"): Need("products", "read"),
    ("POST", "/api/v1/products"): Need("products", "write"),
    ("GET", "/api/v1/products/{product_id}/bom"): Need("products", "read"),
    ("POST", "/api/v1/bom"): Need("products", "write"),
    ("POST", "/api/v1/bom/{bom_id}/approve"): Need("products", "approve"),
    ("GET", "/api/v1/bom/{bom_id}/expand"): Need("products", "read"),

    # ── 裁切最佳化 ──
    # calculate / compare-presets 都會寫 nesting_jobs，歸 write。
    ("POST", "/api/v1/nesting/calculate"): Need("nesting", "write"),
    ("POST", "/api/v1/nesting/compare-presets"): Need("nesting", "write"),
    ("GET", "/api/v1/nesting/jobs"): Need("nesting", "read"),
    ("GET", "/api/v1/nesting/jobs/{job_id}"): Need("nesting", "read"),

    # ── 庫存 ──
    ("GET", "/api/v1/inventory/balance"): Need("inventory", "read"),
    ("POST", "/api/v1/inventory/receipt"): Need("inventory", "write"),
    ("POST", "/api/v1/inventory/issue"): Need("inventory", "write"),
    ("GET", "/api/v1/inventory/sheets"): Need("inventory", "read"),
    ("POST", "/api/v1/inventory/sheets/receive"): Need("inventory", "write"),
    ("GET", "/api/v1/inventory/remnants"): Need("inventory", "read"),
    ("POST", "/api/v1/inventory/remnants"): Need("inventory", "write"),
    ("GET", "/api/v1/inventory/alerts/low-stock"): Need("inventory", "read"),

    # ── 採購 ──
    ("POST", "/api/v1/purchase-orders"): Need("purchasing", "write"),
    ("GET", "/api/v1/purchase-orders"): Need("purchasing", "read"),
    ("POST", "/api/v1/purchase-orders/{po_id}/confirm"): Need("purchasing", "approve"),
    # NEEDS_FACTORY_VERIFICATION：收貨實際由倉管或採購執行未確認，
    # 暫定兩者皆可（各自持有 purchasing:receive）。
    ("POST", "/api/v1/purchase-orders/{po_id}/receive"): Need("purchasing", "receive"),

    # ── 生產工單 / MES ──
    ("POST", "/api/v1/work-orders"): Need("production", "write"),
    ("GET", "/api/v1/work-orders"): Need("production", "read"),
    ("GET", "/api/v1/work-orders/{wo_id}"): Need("production", "read"),
    ("POST", "/api/v1/work-orders/{wo_id}/release"): Need("production", "write"),
    ("POST", "/api/v1/work-orders/{wo_id}/operations/{op_id}/start"): Need("production", "mes_report"),
    ("POST", "/api/v1/work-orders/{wo_id}/operations/{op_id}/complete"): Need("production", "mes_report"),
    ("GET", "/api/v1/work-orders/{wo_id}/material-plan"): Need("production", "read"),
    # NEEDS_FACTORY_VERIFICATION：發料同時動工單與庫存，暫定生管或倉管皆可。
    ("POST", "/api/v1/work-orders/{wo_id}/issue-materials"): _any(
        ("production", "write"), ("inventory", "write")
    ),
    ("POST", "/api/v1/work-orders/{wo_id}/complete"): Need("production", "write"),

    # ── 設備 ──
    ("POST", "/api/v1/equipment"): Need("equipment", "write"),
    ("GET", "/api/v1/equipment"): Need("equipment", "read"),
    ("POST", "/api/v1/equipment/{eq_id}/maintenance"): Need("equipment", "write"),
    ("PATCH", "/api/v1/equipment/{eq_id}/status"): Need("equipment", "write"),

    # ── 分析報表 ──
    ("GET", "/api/v1/analytics/dashboard"): Need("analytics", "read"),
    ("GET", "/api/v1/analytics/material-utilization"): Need("analytics", "read"),
    ("GET", "/api/v1/analytics/cost-breakdown"): Need("analytics", "read"),
    ("GET", "/api/v1/analytics/equipment-oee"): Need("analytics", "read"),

    # ── 線上詢價 ──
    ("POST", "/api/v1/public/inquiries"): PUBLIC,
    ("GET", "/api/v1/inquiries"): Need("inquiries", "read"),
    ("GET", "/api/v1/inquiries/{inquiry_id}"): Need("inquiries", "read"),
    ("PATCH", "/api/v1/inquiries/{inquiry_id}/status"): Need("inquiries", "write"),
    # 轉客戶會同時建立客戶資料，兩個模組的權限都要有。
    ("POST", "/api/v1/inquiries/{inquiry_id}/convert-to-customer"): _all(
        ("inquiries", "write"), ("customers", "write")
    ),

    # ── 作品展示 ──
    ("GET", "/api/v1/public/portfolio"): PUBLIC,
    ("GET", "/api/v1/public/portfolio/{slug}"): PUBLIC,
    ("GET", "/api/v1/portfolio"): Need("portfolio", "read"),
    ("POST", "/api/v1/portfolio"): Need("portfolio", "write"),
    # 發佈等於對外曝光，比一般編輯高一級。
    ("POST", "/api/v1/portfolio/{case_id}/publish"): Need("portfolio", "approve"),
}


# ── 權限判斷（純函式，可單獨測試，不需要資料庫）────────────────────────

def has_permission(permissions: dict | None, resource: str, action: str) -> bool:
    """`permissions` 為 Role.permissions 的 JSON 內容。支援 "*" 萬用字元。"""
    if not permissions:
        return False
    for key in (resource, "*"):
        actions = permissions.get(key)
        if not actions:
            continue
        if action in actions or "*" in actions:
            return True
    return False


def satisfies(permissions: dict | None, rule) -> bool:
    """判斷一組權限是否滿足規則。規則可為 Need / AnyOf / AllOf。"""
    if isinstance(rule, Need):
        return has_permission(permissions, rule.resource, rule.action)
    if isinstance(rule, AnyOf):
        return any(has_permission(permissions, n.resource, n.action) for n in rule.needs)
    if isinstance(rule, AllOf):
        return all(has_permission(permissions, n.resource, n.action) for n in rule.needs)
    raise TypeError(f"未知的權限規則型別：{type(rule)!r}")


def describe(rule) -> str:
    """把規則轉成給人看的字串，用在 403 訊息裡。"""
    if isinstance(rule, Need):
        return f"{rule.resource}:{rule.action}"
    if isinstance(rule, AnyOf):
        return " 或 ".join(f"{n.resource}:{n.action}" for n in rule.needs)
    if isinstance(rule, AllOf):
        return " 且 ".join(f"{n.resource}:{n.action}" for n in rule.needs)
    return str(rule)


# ── FastAPI 全域相依 ──────────────────────────────────────────────────

def _deny(status_code: int, message: str) -> HTTPException:
    # 專案統一回傳格式由 main.py 的 exception handler 轉換，
    # 這裡只負責帶出狀態碼與訊息。
    return HTTPException(status_code=status_code, detail=message)


async def enforce_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    掛在 FastAPI app 上的全域相依，每個請求都會先過這裡。

    查表用 `request.scope["route"].path`（路由模板），所以權限綁的是
    「哪一支端點」，不是使用者送進來的字串。
    """
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path is None:
        # 沒有對應路由（404）或不是一般 HTTP 路由，交給 FastAPI 處理。
        return

    method = request.method.upper()
    rule = PERMISSION_MAP.get((method, path))

    if rule is None:
        # 預設拒絕：新端點忘記登記時直接擋下，而不是默默全開。
        raise _deny(
            status.HTTP_403_FORBIDDEN,
            f"端點 {method} {path} 尚未登記權限規則，已依預設拒絕",
        )

    if rule is PUBLIC:
        return

    # 以下都需要登入。
    header = request.headers.get("authorization") or ""
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _deny(status.HTTP_401_UNAUTHORIZED, "需要登入")

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise _deny(status.HTTP_401_UNAUTHORIZED, "無效的認證憑證")

    user = (await db.execute(
        select(User).where(User.id == payload["sub"], User.is_active == True)  # noqa: E712
    )).scalar_one_or_none()
    if not user:
        raise _deny(status.HTTP_401_UNAUTHORIZED, "無效的認證憑證")

    if rule is AUTHENTICATED:
        return

    if user.role is None:
        raise _deny(
            status.HTTP_403_FORBIDDEN,
            "此帳號尚未指定角色，無法使用業務功能，請聯絡系統管理員",
        )

    if not satisfies(user.role.permissions, rule):
        raise _deny(
            status.HTTP_403_FORBIDDEN,
            f"權限不足：此操作需要 {describe(rule)}，"
            f"目前角色為「{user.role.display_name}」",
        )
