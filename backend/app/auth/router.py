
import secrets
from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from app.database import get_db
from app.models.user import User, Role, Tenant
from app.auth.security import verify_password, create_access_token, get_password_hash
from app.auth.dependencies import get_current_user
from app.config import settings
from app.rate_limit import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["認證"])

# 密碼重設token暫存（正式環境建議改用Redis並設定過期時間）
_reset_tokens: dict[str, dict] = {}

def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("密碼至少需要8個字元")
    if not any(c.isdigit() for c in v):
        raise ValueError("密碼必須包含至少一個數字")
    return v

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    role: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_name: str = "sales"  # 預設角色，正式邀請流程應由管理員指定

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password_strength(v)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, request_body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request_body.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request_body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    
    token = create_access_token(data={"sub": str(user.id)})
    role_name = user.role.name if user.role else "viewer"
    return TokenResponse(access_token=token, user_name=user.full_name or user.email, role=role_name)

@router.post("/register", summary="註冊新使用者（需現有租戶與角色已存在）")
@limiter.limit("10/hour")
async def register(request: Request, request_body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == request_body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="此Email已被註冊")

    tenant_result = await db.execute(select(Tenant).limit(1))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=400, detail="尚未建立租戶，請先執行系統初始化")

    role_result = await db.execute(
        select(Role).where(Role.tenant_id == tenant.id, Role.name == request_body.role_name)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"找不到角色: {request_body.role_name}")

    new_user = User(
        tenant_id=tenant.id,
        email=request_body.email,
        hashed_password=get_password_hash(request_body.password),
        full_name=request_body.full_name,
        role_id=role.id,
    )
    db.add(new_user)
    await db.commit()
    return {"success": True, "message": "註冊成功，請使用此帳號登入", "email": request_body.email}

@router.post("/change-password", summary="登入後變更密碼")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密碼不正確")
    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()
    return {"success": True, "message": "密碼已更新，請使用新密碼重新登入"}

@router.post("/forgot-password", summary="忘記密碼：取得重設token")
@limiter.limit("3/hour")
async def forgot_password(request: Request, request_body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request_body.email, User.is_active == True))
    user = result.scalar_one_or_none()
    # 即使帳號不存在也回傳成功訊息，避免被用來枚舉有效Email
    if user:
        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = {
            "user_id": str(user.id),
            "expires_at": datetime.utcnow() + timedelta(minutes=30),
        }
        # 正式環境：此處應寄送Email給user.email，內容包含重設連結 /reset-password?token={token}
        # 資安修正：dev_only_token 只在非正式環境回傳，避免任何人對已知Email呼叫此端點
        # 就直接取得密碼重設token（等同帳號接管），不需要真的收到email
        response = {"success": True, "message": "若此Email存在，重設密碼連結已寄出"}
        if not settings.is_production:
            response["dev_only_token"] = token
        return response
    return {"success": True, "message": "若此Email存在，重設密碼連結已寄出"}

@router.post("/reset-password", summary="使用token重設密碼")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    record = _reset_tokens.get(request.token)
    if not record:
        raise HTTPException(status_code=400, detail="重設連結無效或已使用")
    if datetime.utcnow() > record["expires_at"]:
        del _reset_tokens[request.token]
        raise HTTPException(status_code=400, detail="重設連結已過期，請重新申請")

    result = await db.execute(select(User).where(User.id == record["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="找不到使用者")

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()
    del _reset_tokens[request.token]
    return {"success": True, "message": "密碼已重設，請使用新密碼登入"}


# ⚠️ 資安修正：原本這裡有一個 POST /setup-admin 端點，完全沒有身份驗證保護，
# 且用寫死的密碼「Admin@2025!」建立管理員帳號，任何人都能對外呼叫搶先建立管理員。
# 官方建立管理員的方式是 scripts/seed_data.py（透過伺服器執行權限執行，
# 見 README.md「快速啟動」第4步），這裡不需要也不該有對外開放的重複機制，已移除。
