# 集中匯出所有 SQLAlchemy Models（供 Alembic 自動偵測）
from app.database import Base
from app.models.user import User, Role, Tenant, AuditLog
from app.models.customer import Customer, Contact, CrmActivity
from app.models.material import Material, SheetStock
from app.models.inventory import InventoryBalance, InventoryTransaction
from app.models.product import Product, BomHeader, BomItem
from app.models.supplier import Supplier
from app.models.purchasing import PurchaseOrder, PoItem
from app.models.production import WorkOrder, WoOperation, WoMaterialIssue
from app.models.nesting import NestingJob, NestingPart, NestingPlacement, RemnantInventory
from app.models.quotation import Quotation, QuotationItem
from app.models.equipment import Equipment, MaintenanceLog
from app.models.portfolio import PortfolioCase
from app.models.inquiry import Inquiry

__all__ = ["Base"]
