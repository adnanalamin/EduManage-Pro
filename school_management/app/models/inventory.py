"""
EduManage Pro - Inventory & Asset Management Models (SQLAlchemy)
Normalized models for Inventory Categories, Items/Assets, and Stock Ledger Transactions.
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, Text, Boolean,
    Numeric, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class InventoryCategory(Base, TimestampMixin, SoftDeleteMixin):
    """Classification category for school assets, lab equipment, furniture, and supplies."""
    __tablename__ = "inventory_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    items = relationship("InventoryItem", back_populates="category")

    def __repr__(self):
        return f"<InventoryCategory(code='{self.code}', name='{self.name}')>"


class InventoryItem(Base, TimestampMixin, SoftDeleteMixin):
    """Master catalog item or fixed asset tracked in campus inventory."""
    __tablename__ = "inventory_items"

    item_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("inventory_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    unit = Column(String(30), default="Pcs", nullable=False)
    quantity_in_stock = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=5, nullable=False)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    storage_location = Column(String(120), nullable=True)
    supplier_name = Column(String(150), nullable=True)
    condition = Column(String(30), default="Good", nullable=False)  # Good, Fair, Damaged, Retired
    status = Column(String(30), default="In Stock", nullable=False, index=True)  # In Stock, Low Stock, Out of Stock, Discontinued

    category = relationship("InventoryCategory", back_populates="items")
    department = relationship("Department")
    transactions = relationship("InventoryTransaction", back_populates="item")

    __table_args__ = (
        CheckConstraint(
            "quantity_in_stock >= 0 AND reorder_level >= 0 AND unit_cost >= 0",
            name="ck_inventory_item_nonneg",
        ),
        Index("idx_inventory_cat_status", "category_id", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<InventoryItem(code='{self.item_code}', name='{self.name}', qty={self.quantity_in_stock})>"


class InventoryTransaction(Base, TimestampMixin, SoftDeleteMixin):
    """Stock movement ledger recording purchases, classroom issues, returns, and write-offs."""
    __tablename__ = "inventory_transactions"

    reference_no = Column(String(60), unique=True, nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    transaction_type = Column(String(30), nullable=False, index=True)  # Purchase, Issue, Return, Adjustment, Damage
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    transaction_date = Column(Date, default=date.today, nullable=False, index=True)
    issued_to = Column(String(150), nullable=True)
    recorded_by = Column(String(80), default="admin", nullable=False)
    remarks = Column(Text, nullable=True)

    item = relationship("InventoryItem", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_cost >= 0 AND total_cost >= 0", name="ck_inventory_tx_valid"),
        Index("idx_inventory_tx_item_date", "item_id", "transaction_date"),
    )

    def __repr__(self):
        return f"<InventoryTransaction(ref='{self.reference_no}', type='{self.transaction_type}', qty={self.quantity})>"
