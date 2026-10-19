"""
帳號管理（v2.3.8）：管理員在 ERP 畫面建立員工帳號、改角色、停用、重設密碼。

設計決定
--------
- **停用，不刪除。** 員工離職就停用：登入與既有登入狀態立刻失效
  （`get_current_user` 與 `enforce_permissions` 每個請求都檢查 is_active），
  但帳號留著，日後查「這張單是誰建的」還找得到人。
- **管理員不能把自己鎖在外面。** 不能停用自己、不能改自己的角色；
  因為操作者本身一定是啟用中的管理員，這條規則也保證系統至少留一個管理員。
- **管理員重設自己的密碼要走「變更密碼」**（需要輸入舊密碼），
  避免有人趁管理員離開座位時直接改掉密碼。
- **只看得到、改得到自己租戶的帳號**；別的租戶的帳號一律當作不存在（404）。
- 回應一律經過 `user_out()`，不會帶出密碼雜湊。

已知限制：重設密碼不會讓對方「已登入的畫面」立刻登出（登入憑證有效 60 分鐘）。
要立刻踢掉某人，請用停用。
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_password_hash
from app.models.user import Role, User


def user_out(u: User) -> dict:
    """對外的帳號資料。刻意逐欄列出，不回 ORM 物件（不會帶出 hashed_password）。"""
    return {
        "id": str(u.id),
        "email": u.email,
        "full_name": u.full_name,
        "role_name": u.role.name if u.role else None,
        "role_display_name": u.role.display_name if u.role else None,
        "is_active": bool(u.is_active),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
    }


def role_out(r: Role) -> dict:
    return {"name": r.name, "display_name": r.display_name}


async def list_users(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    rows = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.is_active.desc(), User.created_at)
    )
    return list(rows.scalars().unique())


async def list_roles(db: AsyncSession, tenant_id: uuid.UUID) -> list[Role]:
    rows = await db.execute(select(Role).where(Role.tenant_id == tenant_id))
    roles = list(rows.scalars())
    order = {name: i for i, name in enumerate(ROLE_ORDER)}
    return sorted(roles, key=lambda r: order.get(r.name, len(order)))


# 下拉選單的順序，與 scripts/seed_data.py 的 ROLES 相同（tests/test_user_admin.py 檢查兩者一致）。
# 不在執行期 import seed_data：那是部署用腳本，不該被 API 程式載入。
ROLE_ORDER = ["admin", "owner", "sales", "engineer", "planner", "warehouse", "purchaser", "operator", "qc"]


async def get_user_in_tenant(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = (await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到這個帳號")
    return user


async def _role_by_name(db: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    role = (await db.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )).scalar_one_or_none()
    if not role:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"找不到角色：{name}")
    return role


async def update_user(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    full_name: str | None = None,
    role_name: str | None = None,
    is_active: bool | None = None,
) -> User:
    is_self = target.id == actor.id
    if is_self and is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能停用自己的帳號")
    if is_self and role_name is not None and role_name != (actor.role.name if actor.role else None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能變更自己的角色，請由另一位管理員處理")

    if full_name is not None:
        target.full_name = full_name
    if role_name is not None:
        role = await _role_by_name(db, actor.tenant_id, role_name)
        target.role_id = role.id
        target.role = role
    if is_active is not None:
        target.is_active = is_active
    await db.flush()
    return target


async def admin_reset_password(db: AsyncSession, actor: User, target: User, new_password: str) -> None:
    if target.id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "要改自己的密碼請用「變更密碼」，需要輸入目前的密碼",
        )
    target.hashed_password = get_password_hash(new_password)
    await db.flush()
