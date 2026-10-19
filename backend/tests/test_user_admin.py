"""
帳號管理（v2.3.8）不需要資料庫的檢查。

完整流程（建帳號、改角色、重設密碼、停用後立刻失效）用真實 HTTP 與資料庫驗證，
見 scripts/verify_users.py（CI 會跑）。這裡驗的是三件不靠資料庫就能確認的事：
1. 回應不會帶出密碼雜湊。
2. 管理員不能停用自己、不能改自己的角色、不能用「重設」繞過舊密碼改自己的密碼
   ——這些規則在碰資料庫之前就擋下。
3. 下拉選單的角色順序與 seed_data.ROLES 一致。
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.auth import user_admin  # noqa: E402
from scripts.seed_data import ROLES  # noqa: E402


def _user(role="admin", **kw):
    role_obj = SimpleNamespace(name=role, display_name={"admin": "系統管理員", "sales": "業務/報價專員"}.get(role, role))
    base = dict(id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="a@example.com", full_name="王小明",
                role=role_obj, role_id=uuid.uuid4(), is_active=True,
                hashed_password="$2b$12$abcdefghijklmnopqrstuv",
                created_at=datetime(2026, 10, 1, tzinfo=timezone.utc), last_login=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_user_out_never_contains_password_hash():
    out = user_admin.user_out(_user())
    assert "hashed_password" not in out
    assert "$2b$" not in str(out)
    assert out["role_name"] == "admin" and out["role_display_name"] == "系統管理員"
    assert out["last_login"] is None


def test_user_out_without_role():
    out = user_admin.user_out(SimpleNamespace(**{**vars(_user()), "role": None}))
    assert out["role_name"] is None and out["role_display_name"] is None


@pytest.mark.parametrize("kwargs, message", [
    ({"is_active": False}, "不能停用自己"),
    ({"role_name": "sales"}, "不能變更自己的角色"),
])
def test_admin_cannot_lock_self_out(kwargs, message):
    me = _user()
    with pytest.raises(HTTPException) as e:
        asyncio.run(user_admin.update_user(db=None, actor=me, target=me, **kwargs))
    assert e.value.status_code == 400 and message in e.value.detail
    assert me.is_active is True and me.role.name == "admin"


def test_admin_cannot_reset_own_password_without_old_one():
    me = _user()
    before = me.hashed_password
    with pytest.raises(HTTPException) as e:
        asyncio.run(user_admin.admin_reset_password(db=None, actor=me, target=me, new_password="whatever123"))
    assert e.value.status_code == 400
    assert me.hashed_password == before


def test_role_order_matches_seed_roles():
    assert user_admin.ROLE_ORDER == [r["name"] for r in ROLES]
