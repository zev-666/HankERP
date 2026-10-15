from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_commit_route import CommitBeforeResponseRoute
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import (
    TransactionCreate, TransactionOut, SheetStockCreate,
    SheetStockOut, InventoryBalanceOut, RemnantCreate
)

router = APIRouter(route_class=CommitBeforeResponseRoute, prefix="/api/v1/inventory", tags=["庫存管理"])
svc = InventoryService()

@router.get("/balance", summary="庫存餘額查詢")
async def get_balances(
    warehouse_code: Optional[str] = Query(None),
    material_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await svc.get_balances(db, current_user.tenant_id, warehouse_code, material_id)
    return {"success": True, "data": [_balance_row(b) for b in items], "total": len(items)}


def _balance_row(b) -> dict:
    """
    v2.3.3：明確列出回傳欄位。

    先前直接回傳 ORM 物件，FastAPI 轉 JSON 時只帶出資料庫欄位，
    `qty_available` 是模型上的 @property（庫存量 − 保留量）不會出現，
    前端「可用量」整欄空白。這裡保留原本每個欄位的型別（數量為數字、ID 為字串），
    只補上 qty_available，避免影響既有使用者（例如 scripts/verify_e2e.py）。
    """
    return {
        "id": str(b.id),
        "tenant_id": str(b.tenant_id) if b.tenant_id else None,
        "material_id": str(b.material_id) if b.material_id else None,
        "product_id": str(b.product_id) if b.product_id else None,
        "warehouse_code": b.warehouse_code,
        "location_code": b.location_code,
        "qty_on_hand": float(b.qty_on_hand or 0),
        "qty_reserved": float(b.qty_reserved or 0),
        "qty_available": float((b.qty_on_hand or 0) - (b.qty_reserved or 0)),
        "last_updated": b.last_updated.isoformat() if b.last_updated else None,
    }

@router.post("/receipt", summary="入庫登記")
async def receipt(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.qty <= 0:
        raise HTTPException(400, "入庫數量必須大於0")
    txn = await svc.create_transaction(db, current_user.tenant_id, current_user.id, data, "RECEIPT")
    return {"success": True, "message": "入庫成功", "transaction_id": txn.id}

@router.post("/issue", summary="出庫登記")
async def issue(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 確保qty是負數
    data.qty = -abs(data.qty)
    txn = await svc.create_transaction(db, current_user.tenant_id, current_user.id, data, "ISSUE")
    return {"success": True, "message": "出庫成功", "transaction_id": txn.id}

@router.get("/sheets", summary="板材庫存清單")
async def get_sheets(
    material_id: Optional[UUID] = Query(None),
    is_remnant: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheets = await svc.get_sheets(db, current_user.tenant_id, material_id, is_remnant)
    return {"success": True, "data": sheets}

@router.post("/sheets/receive", summary="壓克力板材入庫")
async def receive_sheets(
    data: SheetStockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sheet = await svc.receive_sheets(db, current_user.tenant_id, current_user.id, data)
    return {"success": True, "message": "板材入庫成功", "sheet_id": str(sheet.id)}

@router.get("/remnants", summary="剩料清單")
async def get_remnants(
    material_id: Optional[UUID] = Query(None),
    min_length: float = Query(0, description="最小長度mm"),
    min_width: float = Query(0, description="最小寬度mm"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remnants = await svc.get_remnants(db, current_user.tenant_id, material_id, min_length, min_width)
    return {"success": True, "data": remnants}

@router.post("/remnants", summary="剩料入庫登記")
async def add_remnant(
    data: RemnantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remnant = await svc.add_remnant(db, current_user.tenant_id, data)
    return {"success": True, "message": "剩料登記成功", "remnant_id": str(remnant.id)}

@router.get("/alerts/low-stock", summary="低庫存預警")
async def low_stock_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = await svc.get_low_stock_alerts(db, current_user.tenant_id)
    return {"success": True, "data": alerts, "total": len(alerts)}
