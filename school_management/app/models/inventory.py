"""
EduManage Pro - Enterprise Inventory & Fixed Asset Management Models (SQLAlchemy)
Covers Categories, Products, Suppliers, Locations/Stores, Stock Balances,
Purchase Orders, Purchases (linked to Accounting Expenses), Stock Adjustments,
Stock Transfers, Sales/Disposals (linked to Accounting Income), Low-Stock Alerts,
and Fixed Asset Registry with Employee Assignment & Warranty Tracking.
"""

from datetime import date, datetime
from typing import List
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


INVENTORY_ITEM_TYPES: List[str] = [
    "Consumable",
    "Stationery",
    "Lab Supply",
    "Uniform",
    "Spare Part",
    "Fixed Asset",
    "Other",
]

PURCHASE_ORDER_STATUSES: List[str] = [
    "Draft",
    "Approved",
    "Ordered",
    "Partially Received",
    "Received",
    "Cancelled",
]

ADJUSTMENT_TYPES: List[str] = [
    "Increase",
    "Decrease",
    "Damage / Write-Off",
    "Audit Count",
    "Expiry",
]

DISPOSAL_SALE_TYPES: List[str] = [
    "Sale",
    "Disposal",
    "Issue / Consumption",
]

ASSET_STATUSES: List[str] = [
    "Active",
    "In Use",
    "Under Maintenance",
    "Disposed",
    "Lost",
    "Retired",
]


class InventoryCategory(Base, TimestampMixin, SoftDeleteMixin):
    """Classification category for school products, lab equipment, furniture, and supplies."""
    __tablename__ = "inventory_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    default_account_code = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    items = relationship("InventoryItem", back_populates="category")
    assets = relationship("FixedAsset", back_populates="category")

    def __repr__(self):
        return f"<InventoryCategory(code='{self.code}', name='{self.name}')>"


class InventorySupplier(Base, TimestampMixin, SoftDeleteMixin):
    """Approved vendor / supplier directory for procurement & purchase orders."""
    __tablename__ = "inventory_suppliers"

    supplier_code = Column(String(40), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    contact_person = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    tax_id = Column(String(60), nullable=True)
    payment_terms = Column(String(80), default="Net 30", nullable=False)
    bank_details = Column(String(255), nullable=True)
    rating = Column(Integer, default=5, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Inactive, Blacklisted
    notes = Column(Text, nullable=True)

    purchase_orders = relationship("InventoryPurchaseOrder", back_populates="supplier")
    purchases = relationship("InventoryPurchase", back_populates="supplier")

    def __repr__(self):
        return f"<InventorySupplier(code='{self.supplier_code}', name='{self.name}')>"


class InventoryLocation(Base, TimestampMixin, SoftDeleteMixin):
    """Campus stores, warehouses, labs, or stockrooms for multi-location stock & transfers."""
    __tablename__ = "inventory_locations"

    code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    location_type = Column(String(40), default="Central Store", nullable=False)  # Central Store, Department Store, Lab Store, Campus Annex
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    manager_name = Column(String(100), nullable=True)
    address = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    department = relationship("Department")
    stock_entries = relationship("InventoryStock", back_populates="location")

    def __repr__(self):
        return f"<InventoryLocation(code='{self.code}', name='{self.name}')>"


class InventoryItem(Base, TimestampMixin, SoftDeleteMixin):
    """Master product / catalog SKU tracked across campus stores and fixed asset acquisitions."""
    __tablename__ = "inventory_items"

    item_code = Column(String(50), unique=True, nullable=False, index=True)
    sku = Column(String(60), unique=True, nullable=True, index=True)
    barcode = Column(String(80), nullable=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    item_type = Column(String(40), default="Consumable", nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("inventory_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    preferred_supplier_id = Column(Integer, ForeignKey("inventory_suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    unit = Column(String(30), default="Pcs", nullable=False)
    quantity_in_stock = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=5, nullable=False)
    max_stock_level = Column(Integer, nullable=True)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    selling_price = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    storage_location = Column(String(120), nullable=True)
    supplier_name = Column(String(150), nullable=True)
    condition = Column(String(30), default="Good", nullable=False)  # Good, Fair, Damaged, Retired
    low_stock_alert_enabled = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="In Stock", nullable=False, index=True)  # In Stock, Low Stock, Out of Stock, Discontinued

    category = relationship("InventoryCategory", back_populates="items")
    department = relationship("Department")
    preferred_supplier = relationship("InventorySupplier")
    stock_records = relationship("InventoryStock", back_populates="item", cascade="all, delete-orphan")
    transactions = relationship("InventoryTransaction", back_populates="item")

    __table_args__ = (
        CheckConstraint(
            "quantity_in_stock >= 0 AND reorder_level >= 0 AND unit_cost >= 0 AND selling_price >= 0",
            name="ck_inventory_item_nonneg",
        ),
        Index("idx_inventory_cat_status", "category_id", "status", "is_deleted"),
    )

    @property
    def is_low_stock(self) -> bool:
        return bool(self.low_stock_alert_enabled) and int(self.quantity_in_stock or 0) <= int(self.reorder_level or 0)

    def __repr__(self):
        return f"<InventoryItem(code='{self.item_code}', name='{self.name}', qty={self.quantity_in_stock})>"


class InventoryStock(Base, TimestampMixin):
    """Per-location stock balance supporting stockroom tracking and stock transfers."""
    __tablename__ = "inventory_stocks"

    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    reserved_qty = Column(Integer, default=0, nullable=False)
    bin_shelf = Column(String(60), nullable=True)
    last_counted_date = Column(Date, nullable=True)

    item = relationship("InventoryItem", back_populates="stock_records")
    location = relationship("InventoryLocation", back_populates="stock_entries")

    __table_args__ = (
        UniqueConstraint("item_id", "location_id", name="uq_inventory_stock_item_loc"),
        CheckConstraint("quantity_on_hand >= 0 AND reserved_qty >= 0", name="ck_inventory_stock_nonneg"),
    )


class InventoryTransaction(Base, TimestampMixin, SoftDeleteMixin):
    """Immutable stock movement ledger across purchases, transfers, adjustments, issues, and disposals."""
    __tablename__ = "inventory_transactions"

    reference_no = Column(String(60), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_type = Column(String(30), nullable=False, index=True)  # Purchase, Issue, Return, Adjustment, Damage, Transfer In, Transfer Out, Sale, Disposal
    quantity = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=True)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    transaction_date = Column(Date, default=date.today, nullable=False, index=True)
    issued_to = Column(String(150), nullable=True)
    recorded_by = Column(String(80), default="admin", nullable=False)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    remarks = Column(Text, nullable=True)

    item = relationship("InventoryItem", back_populates="transactions")
    location = relationship("InventoryLocation")
    accounting_tx = relationship("AccountTransaction")

    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_cost >= 0 AND total_cost >= 0", name="ck_inventory_tx_valid"),
        Index("idx_inventory_tx_item_date", "item_id", "transaction_date"),
    )

    def __repr__(self):
        return f"<InventoryTransaction(ref='{self.reference_no}', type='{self.transaction_type}', qty={self.quantity})>"


class InventoryPurchaseOrder(Base, TimestampMixin, SoftDeleteMixin):
    """Formal Purchase Order (PO) workflow prior to goods receipt."""
    __tablename__ = "inventory_purchase_orders"

    po_number = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("inventory_suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    order_date = Column(Date, default=date.today, nullable=False, index=True)
    expected_delivery_date = Column(Date, nullable=True)
    subtotal = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    tax_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    shipping_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    status = Column(String(30), default="Draft", nullable=False, index=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_by = Column(String(100), default="admin", nullable=False)
    notes = Column(Text, nullable=True)

    supplier = relationship("InventorySupplier", back_populates="purchase_orders")
    location = relationship("InventoryLocation")
    items = relationship("InventoryPurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    purchases = relationship("InventoryPurchase", back_populates="purchase_order")

    __table_args__ = (
        CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND shipping_cost >= 0 AND total_amount >= 0",
            name="ck_inventory_po_nonneg",
        ),
    )


class InventoryPurchaseOrderItem(Base, TimestampMixin):
    """Line item inside an InventoryPurchaseOrder."""
    __tablename__ = "inventory_purchase_order_items"

    po_id = Column(Integer, ForeignKey("inventory_purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    ordered_qty = Column(Integer, nullable=False)
    received_qty = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    line_total = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)

    purchase_order = relationship("InventoryPurchaseOrder", back_populates="items")
    item = relationship("InventoryItem")

    __table_args__ = (
        CheckConstraint("ordered_qty > 0 AND received_qty >= 0 AND unit_cost >= 0 AND line_total >= 0", name="ck_inventory_poi_valid"),
    )


class InventoryPurchase(Base, TimestampMixin, SoftDeleteMixin):
    """Goods Receipt / Stock Purchase Invoice integrated with Accounting Expense vouchers."""
    __tablename__ = "inventory_purchases"

    purchase_no = Column(String(50), unique=True, nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("inventory_purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("inventory_suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_no = Column(String(80), nullable=True)
    purchase_date = Column(Date, default=date.today, nullable=False, index=True)
    subtotal = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    tax_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    payment_method = Column(String(30), default="Cash", nullable=False)
    payment_status = Column(String(20), default="Paid", nullable=False, index=True)  # Paid, Partial, Unpaid
    status = Column(String(20), default="Received", nullable=False, index=True)  # Received, Cancelled
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    account_category_code = Column(String(20), default="EXP-INV", nullable=True)
    received_by = Column(String(100), default="admin", nullable=False)
    notes = Column(Text, nullable=True)

    purchase_order = relationship("InventoryPurchaseOrder", back_populates="purchases")
    supplier = relationship("InventorySupplier", back_populates="purchases")
    location = relationship("InventoryLocation")
    accounting_tx = relationship("AccountTransaction")
    items = relationship("InventoryPurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0 AND paid_amount >= 0",
            name="ck_inventory_pur_nonneg",
        ),
    )


class InventoryPurchaseItem(Base, TimestampMixin):
    """Line item inside an InventoryPurchase receipt."""
    __tablename__ = "inventory_purchase_items"

    purchase_id = Column(Integer, ForeignKey("inventory_purchases.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    line_total = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)

    purchase = relationship("InventoryPurchase", back_populates="items")
    item = relationship("InventoryItem")

    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_cost >= 0 AND line_total >= 0", name="ck_inventory_pi_valid"),
    )


class InventoryStockAdjustment(Base, TimestampMixin, SoftDeleteMixin):
    """Auditable stock count reconciliation, damage write-off, or quantity adjustment."""
    __tablename__ = "inventory_stock_adjustments"

    adjustment_no = Column(String(50), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    adjustment_type = Column(String(40), nullable=False, index=True)  # Increase, Decrease, Damage / Write-Off, Audit Count, Expiry
    previous_qty = Column(Integer, nullable=False)
    quantity_change = Column(Integer, nullable=False)  # Signed delta (+ or -)
    new_qty = Column(Integer, nullable=False)
    adjustment_date = Column(Date, default=date.today, nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    approved_by = Column(String(100), default="admin", nullable=False)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    item = relationship("InventoryItem")
    location = relationship("InventoryLocation")
    accounting_tx = relationship("AccountTransaction")

    __table_args__ = (
        CheckConstraint("previous_qty >= 0 AND new_qty >= 0", name="ck_inventory_adj_nonneg"),
    )


class InventoryStockTransfer(Base, TimestampMixin, SoftDeleteMixin):
    """Inter-store / inter-department stock transfer tracking."""
    __tablename__ = "inventory_stock_transfers"

    transfer_no = Column(String(50), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    transfer_date = Column(Date, default=date.today, nullable=False, index=True)
    transferred_by = Column(String(100), default="admin", nullable=False)
    received_by = Column(String(100), nullable=True)
    status = Column(String(25), default="Completed", nullable=False, index=True)  # Pending, In Transit, Completed, Cancelled
    notes = Column(Text, nullable=True)

    item = relationship("InventoryItem")
    from_location = relationship("InventoryLocation", foreign_keys=[from_location_id])
    to_location = relationship("InventoryLocation", foreign_keys=[to_location_id])

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_inventory_trf_qty_pos"),
    )


class InventoryDisposalSale(Base, TimestampMixin, SoftDeleteMixin):
    """Stock sale, department issue, or scrap disposal record (with optional Accounting Income)."""
    __tablename__ = "inventory_disposals_sales"

    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    record_type = Column(String(30), nullable=False, index=True)  # Sale, Disposal, Issue / Consumption
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    buyer_or_recipient = Column(String(150), nullable=True)
    payment_method = Column(String(30), default="Cash", nullable=False)
    transaction_date = Column(Date, default=date.today, nullable=False, index=True)
    reason = Column(String(255), nullable=True)
    recorded_by = Column(String(100), default="admin", nullable=False)
    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    item = relationship("InventoryItem")
    location = relationship("InventoryLocation")
    accounting_tx = relationship("AccountTransaction")

    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0 AND total_amount >= 0", name="ck_inventory_disposal_valid"),
    )


class FixedAsset(Base, TimestampMixin, SoftDeleteMixin):
    """
    Fixed & Trackable School Asset Register:
    Includes Asset ID, Serial Number, Purchase Date, Cost, Location,
    Department, Assigned Employee, Warranty, Status, and Accounting link.
    """
    __tablename__ = "inventory_assets"

    asset_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("inventory_suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    purchase_id = Column(Integer, ForeignKey("inventory_purchases.id", ondelete="SET NULL"), nullable=True, index=True)

    serial_number = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    model_no = Column(String(100), nullable=True)
    purchase_date = Column(Date, default=date.today, nullable=False, index=True)
    cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    salvage_value = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)

    location = Column(String(150), nullable=False)
    location_id = Column(Integer, ForeignKey("inventory_locations.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    department_name = Column(String(100), nullable=True)

    assigned_staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_employee = Column(String(150), nullable=True, index=True)

    warranty = Column(String(120), nullable=True)  # e.g., "36 Months On-Site Warranty"
    warranty_expiry_date = Column(Date, nullable=True, index=True)
    status = Column(String(30), default="Active", nullable=False, index=True)  # Active, In Use, Under Maintenance, Disposed, Lost, Retired

    accounting_tx_id = Column(Integer, ForeignKey("account_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    category = relationship("InventoryCategory", back_populates="assets")
    item = relationship("InventoryItem")
    supplier = relationship("InventorySupplier")
    purchase = relationship("InventoryPurchase")
    stock_location = relationship("InventoryLocation")
    department = relationship("Department")
    assigned_staff = relationship("Staff")
    assigned_teacher = relationship("Teacher")
    accounting_tx = relationship("AccountTransaction")

    __table_args__ = (
        CheckConstraint("cost >= 0 AND salvage_value >= 0", name="ck_fixed_asset_cost_nonneg"),
        Index("idx_fixed_asset_status_dept", "status", "department_id"),
    )

    def __repr__(self):
        return f"<FixedAsset(asset_id='{self.asset_id}', name='{self.name}', status='{self.status}')>"
