"""
EduManage Pro - Enterprise Inventory & Fixed Asset Repository
Complete database operations for Categories, Products, Suppliers, Locations,
Stock Levels, Purchase Orders, Purchases (with Accounting Expense posting),
Stock Adjustments, Stock Transfers, Sales/Disposals (with Accounting Income),
Fixed Assets, Low-Stock Alerts, and Audit Ledger.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.accounting import AccountCategory, AccountTransaction
from app.models.inventory import (
    FixedAsset,
    InventoryCategory,
    InventoryDisposalSale,
    InventoryItem,
    InventoryLocation,
    InventoryPurchase,
    InventoryPurchaseItem,
    InventoryPurchaseOrder,
    InventoryPurchaseOrderItem,
    InventoryStock,
    InventoryStockAdjustment,
    InventoryStockTransfer,
    InventorySupplier,
    InventoryTransaction,
)
from app.repositories.accounting_repository import AccountingRepository
from app.services.accounting_service import AccountingService


class InventoryRepository:
    """Repository handling all Inventory, Procurement, Stock, and Fixed Asset workflows."""

    @staticmethod
    def _refresh_item_status(item: InventoryItem) -> None:
        if item.status == "Discontinued":
            return
        qty = int(item.quantity_in_stock or 0)
        reorder = int(item.reorder_level or 0)
        if qty <= 0:
            item.status = "Out of Stock"
        elif qty <= reorder:
            item.status = "Low Stock"
        else:
            item.status = "In Stock"

    @staticmethod
    def _resolve_account_category(session: Session, preferred_code: str, trans_type: str) -> AccountCategory:
        cat = AccountingRepository.get_category_by_code(session, preferred_code)
        if cat:
            return cat
        AccountingService.seed_default_categories(session)
        cat = AccountingRepository.get_category_by_code(session, preferred_code)
        if cat:
            return cat
        fallback = "EXP-MISC" if trans_type == "Expense" else "INC-MISC"
        cat = AccountingRepository.get_category_by_code(session, fallback)
        if cat:
            return cat
        cat = session.query(AccountCategory).filter(AccountCategory.type == trans_type).first()
        if cat:
            return cat
        created = AccountingRepository.create_category(
            session,
            {
                "name": "Inventory & Asset Purchases" if trans_type == "Expense" else "Inventory Sales & Scrap Recovery",
                "code": preferred_code,
                "type": trans_type,
                "description": "Auto-created inventory accounting category",
                "is_system": True,
            },
        )
        return created

    @staticmethod
    def _post_accounting_entry(
        session: Session,
        trans_type: str,
        category_code: str,
        amount: float,
        party_name: str,
        reference_no: str,
        description: str,
        tx_date: Optional[date] = None,
        payment_method: str = "Cash",
        actor_username: str = "admin",
        idempotency_key: Optional[str] = None,
    ) -> Optional[AccountTransaction]:
        if float(amount or 0.0) <= 0:
            return None
        cat = InventoryRepository._resolve_account_category(session, category_code, trans_type)
        tx, err = AccountingService.record_transaction(
            session,
            {
                "type": trans_type,
                "entry_kind": "Standard",
                "category_id": cat.id,
                "transaction_date": tx_date or date.today(),
                "amount": float(amount),
                "payment_method": payment_method or "Cash",
                "reference_no": reference_no,
                "paid_to_received_from": party_name or "Vendor / Store",
                "description": description,
                "recorded_by": actor_username,
                "idempotency_key": idempotency_key,
            },
            actor_username=actor_username,
            commit=False,
        )
        if err:
            raise ValueError(f"Accounting integration error: {err}")
        return tx

    # -------------------------------------------------------------
    # 1. Categories
    # -------------------------------------------------------------
    @staticmethod
    def get_categories(session: Session, active_only: bool = False) -> List[InventoryCategory]:
        q = session.query(InventoryCategory).options(joinedload(InventoryCategory.items)).filter(
            InventoryCategory.is_deleted == False
        )
        if active_only:
            q = q.filter(InventoryCategory.is_active == True)
        return q.order_by(InventoryCategory.name.asc()).all()

    @staticmethod
    def create_category(
        session: Session,
        name: str,
        code: str,
        description: Optional[str] = None,
        default_account_code: Optional[str] = "EXP-INV",
        is_active: bool = True,
    ) -> InventoryCategory:
        cat = InventoryCategory(
            name=name.strip(),
            code=code.strip().upper(),
            description=description.strip() if description else None,
            default_account_code=default_account_code,
            is_active=is_active,
        )
        session.add(cat)
        session.commit()
        session.refresh(cat)
        return cat

    @staticmethod
    def update_category(session: Session, category_id: int, **kwargs) -> Optional[InventoryCategory]:
        cat = session.query(InventoryCategory).filter(InventoryCategory.id == category_id).first()
        if not cat:
            return None
        for k, v in kwargs.items():
            if hasattr(cat, k):
                setattr(cat, k, v)
        session.commit()
        session.refresh(cat)
        return cat

    # -------------------------------------------------------------
    # 2. Suppliers
    # -------------------------------------------------------------
    @staticmethod
    def get_suppliers(session: Session, status: Optional[str] = None) -> List[InventorySupplier]:
        q = session.query(InventorySupplier).filter(InventorySupplier.is_deleted == False)
        if status:
            q = q.filter(InventorySupplier.status == status)
        return q.order_by(InventorySupplier.name.asc()).all()

    @staticmethod
    def create_supplier(
        session: Session,
        name: str,
        supplier_code: Optional[str] = None,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        tax_id: Optional[str] = None,
        payment_terms: str = "Net 30",
        bank_details: Optional[str] = None,
        rating: int = 5,
        status: str = "Active",
        notes: Optional[str] = None,
    ) -> InventorySupplier:
        code = supplier_code.strip().upper() if supplier_code else f"SUP-{uuid.uuid4().hex[:6].upper()}"
        sup = InventorySupplier(
            supplier_code=code,
            name=name.strip(),
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address,
            tax_id=tax_id,
            payment_terms=payment_terms,
            bank_details=bank_details,
            rating=rating,
            status=status,
            notes=notes,
        )
        session.add(sup)
        session.commit()
        session.refresh(sup)
        return sup

    @staticmethod
    def update_supplier(session: Session, supplier_id: int, **kwargs) -> Optional[InventorySupplier]:
        sup = session.query(InventorySupplier).filter(InventorySupplier.id == supplier_id).first()
        if not sup:
            return None
        for k, v in kwargs.items():
            if hasattr(sup, k):
                setattr(sup, k, v)
        session.commit()
        session.refresh(sup)
        return sup

    # -------------------------------------------------------------
    # 3. Warehouses / Store Locations & Stock Balances
    # -------------------------------------------------------------
    @staticmethod
    def get_locations(session: Session, active_only: bool = False) -> List[InventoryLocation]:
        q = session.query(InventoryLocation).options(joinedload(InventoryLocation.department)).filter(
            InventoryLocation.is_deleted == False
        )
        if active_only:
            q = q.filter(InventoryLocation.is_active == True)
        return q.order_by(InventoryLocation.name.asc()).all()

    @staticmethod
    def create_location(
        session: Session,
        name: str,
        code: Optional[str] = None,
        location_type: str = "Central Store",
        department_id: Optional[int] = None,
        manager_name: Optional[str] = None,
        address: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> InventoryLocation:
        loc_code = code.strip().upper() if code else f"LOC-{uuid.uuid4().hex[:5].upper()}"
        loc = InventoryLocation(
            code=loc_code,
            name=name.strip(),
            location_type=location_type,
            department_id=department_id,
            manager_name=manager_name,
            address=address,
            is_active=True,
            notes=notes,
        )
        session.add(loc)
        session.commit()
        session.refresh(loc)
        return loc

    @staticmethod
    def ensure_default_location(session: Session) -> InventoryLocation:
        loc = session.query(InventoryLocation).filter(InventoryLocation.is_deleted == False).order_by(
            InventoryLocation.id.asc()
        ).first()
        if loc:
            return loc
        return InventoryRepository.create_location(
            session,
            name="Central Campus Store",
            code="MAIN-STR",
            location_type="Central Store",
        )

    @staticmethod
    def _adjust_stock_balance(
        session: Session,
        item: InventoryItem,
        delta: int,
        location_id: Optional[int] = None,
        bin_shelf: Optional[str] = None,
    ) -> int:
        """Applies signed quantity change to both InventoryItem and InventoryStock(item, location)."""
        new_item_qty = int(item.quantity_in_stock or 0) + int(delta)
        if new_item_qty < 0:
            raise ValueError(
                f"Insufficient stock for '{item.name}'. Available: {item.quantity_in_stock}, Requested reduction: {abs(delta)}."
            )
        item.quantity_in_stock = new_item_qty
        InventoryRepository._refresh_item_status(item)

        if location_id is not None:
            st = session.query(InventoryStock).filter(
                InventoryStock.item_id == item.id,
                InventoryStock.location_id == location_id,
            ).first()
            if not st:
                if delta < 0:
                    raise ValueError(f"No stock available for '{item.name}' at selected location ID {location_id}.")
                st = InventoryStock(
                    item_id=item.id,
                    location_id=location_id,
                    quantity_on_hand=delta,
                    bin_shelf=bin_shelf,
                )
                session.add(st)
            else:
                new_loc_qty = int(st.quantity_on_hand or 0) + int(delta)
                if new_loc_qty < 0:
                    raise ValueError(
                        f"Insufficient stock for '{item.name}' at location ID {location_id}. "
                        f"Available: {st.quantity_on_hand}, Requested reduction: {abs(delta)}."
                    )
                st.quantity_on_hand = new_loc_qty
        return new_item_qty

    @staticmethod
    def get_stock_levels(
        session: Session,
        item_id: Optional[int] = None,
        location_id: Optional[int] = None,
    ) -> List[InventoryStock]:
        q = session.query(InventoryStock).options(
            joinedload(InventoryStock.item).joinedload(InventoryItem.category),
            joinedload(InventoryStock.location),
        )
        if item_id:
            q = q.filter(InventoryStock.item_id == item_id)
        if location_id:
            q = q.filter(InventoryStock.location_id == location_id)
        return q.order_by(InventoryStock.location_id.asc(), InventoryStock.item_id.asc()).all()

    # -------------------------------------------------------------
    # 4. Products / Inventory Items
    # -------------------------------------------------------------
    @staticmethod
    def get_products(
        session: Session,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[InventoryItem]:
        q = session.query(InventoryItem).options(
            joinedload(InventoryItem.category),
            joinedload(InventoryItem.department),
            joinedload(InventoryItem.preferred_supplier),
            joinedload(InventoryItem.stock_records).joinedload(InventoryStock.location),
        ).filter(InventoryItem.is_deleted == False)
        if category_id:
            q = q.filter(InventoryItem.category_id == category_id)
        if status and status != "All":
            q = q.filter(InventoryItem.status == status)
        if search:
            pat = f"%{search.strip()}%"
            q = q.filter(
                (InventoryItem.name.ilike(pat))
                | (InventoryItem.item_code.ilike(pat))
                | (InventoryItem.sku.ilike(pat))
                | (InventoryItem.barcode.ilike(pat))
            )
        return q.order_by(InventoryItem.name.asc()).all()

    @staticmethod
    def get_product_by_id(session: Session, item_id: int) -> Optional[InventoryItem]:
        return session.query(InventoryItem).options(
            joinedload(InventoryItem.category),
            joinedload(InventoryItem.department),
            joinedload(InventoryItem.preferred_supplier),
            joinedload(InventoryItem.stock_records).joinedload(InventoryStock.location),
        ).filter(InventoryItem.id == item_id).first()

    @staticmethod
    def create_product(
        session: Session,
        item_code: str,
        name: str,
        category_id: int,
        item_type: str = "Consumable",
        unit: str = "Pcs",
        quantity_in_stock: int = 0,
        reorder_level: int = 5,
        max_stock_level: Optional[int] = None,
        unit_cost: float = 0.0,
        selling_price: float = 0.0,
        sku: Optional[str] = None,
        barcode: Optional[str] = None,
        department_id: Optional[int] = None,
        preferred_supplier_id: Optional[int] = None,
        storage_location: Optional[str] = None,
        supplier_name: Optional[str] = None,
        condition: str = "Good",
        description: Optional[str] = None,
        location_id: Optional[int] = None,
    ) -> InventoryItem:
        if quantity_in_stock < 0 or reorder_level < 0 or unit_cost < 0 or selling_price < 0:
            raise ValueError("Quantities and unit prices cannot be negative.")
        sup_name = supplier_name
        if preferred_supplier_id and not sup_name:
            sup = session.query(InventorySupplier).filter(InventorySupplier.id == preferred_supplier_id).first()
            if sup:
                sup_name = sup.name

        item = InventoryItem(
            item_code=item_code.strip().upper(),
            sku=sku.strip().upper() if sku else item_code.strip().upper(),
            barcode=barcode.strip() if barcode else None,
            name=name.strip(),
            item_type=item_type,
            category_id=category_id,
            department_id=department_id,
            preferred_supplier_id=preferred_supplier_id,
            unit=unit.strip() or "Pcs",
            quantity_in_stock=int(quantity_in_stock),
            reorder_level=int(reorder_level),
            max_stock_level=max_stock_level,
            unit_cost=float(unit_cost or 0.0),
            selling_price=float(selling_price or 0.0),
            storage_location=storage_location,
            supplier_name=sup_name,
            condition=condition,
            description=description,
        )
        InventoryRepository._refresh_item_status(item)
        session.add(item)
        session.flush()

        if int(quantity_in_stock) > 0:
            loc_id = location_id or InventoryRepository.ensure_default_location(session).id
            session.add(
                InventoryStock(
                    item_id=item.id,
                    location_id=loc_id,
                    quantity_on_hand=int(quantity_in_stock),
                )
            )
            session.add(
                InventoryTransaction(
                    reference_no=f"OPEN-{item.id}-{uuid.uuid4().hex[:5].upper()}",
                    item_id=item.id,
                    location_id=loc_id,
                    transaction_type="Purchase",
                    quantity=int(quantity_in_stock),
                    balance_after=int(quantity_in_stock),
                    unit_cost=float(unit_cost or 0.0),
                    total_cost=round(int(quantity_in_stock) * float(unit_cost or 0.0), 2),
                    transaction_date=date.today(),
                    remarks="Opening Stock",
                )
            )

        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def update_product(session: Session, item_id: int, **kwargs) -> Optional[InventoryItem]:
        item = session.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            return None
        for k, v in kwargs.items():
            if hasattr(item, k):
                setattr(item, k, v)
        InventoryRepository._refresh_item_status(item)
        session.commit()
        session.refresh(item)
        return item

    # -------------------------------------------------------------
    # 5. Purchase Orders
    # -------------------------------------------------------------
    @staticmethod
    def get_purchase_orders(session: Session, status: Optional[str] = None) -> List[InventoryPurchaseOrder]:
        q = session.query(InventoryPurchaseOrder).options(
            joinedload(InventoryPurchaseOrder.supplier),
            joinedload(InventoryPurchaseOrder.location),
            joinedload(InventoryPurchaseOrder.items).joinedload(InventoryPurchaseOrderItem.item),
        ).filter(InventoryPurchaseOrder.is_deleted == False)
        if status and status != "All":
            q = q.filter(InventoryPurchaseOrder.status == status)
        return q.order_by(InventoryPurchaseOrder.order_date.desc(), InventoryPurchaseOrder.id.desc()).all()

    @staticmethod
    def create_purchase_order(
        session: Session,
        supplier_id: int,
        lines: List[Dict[str, Any]],
        location_id: Optional[int] = None,
        order_date: Optional[date] = None,
        expected_delivery_date: Optional[date] = None,
        tax_amount: float = 0.0,
        discount_amount: float = 0.0,
        shipping_cost: float = 0.0,
        status: str = "Approved",
        created_by: str = "admin",
        notes: Optional[str] = None,
    ) -> InventoryPurchaseOrder:
        if not lines:
            raise ValueError("Purchase Order must contain at least one product line item.")

        subtotal = 0.0
        for ln in lines:
            qty = int(ln["ordered_qty"])
            cost = float(ln["unit_cost"])
            if qty <= 0 or cost < 0:
                raise ValueError("PO quantity must be positive and unit cost non-negative.")
            subtotal += qty * cost

        total = max(0.0, round(subtotal + float(tax_amount or 0.0) + float(shipping_cost or 0.0) - float(discount_amount or 0.0), 2))
        po_no = f"PO-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        po = InventoryPurchaseOrder(
            po_number=po_no,
            supplier_id=supplier_id,
            location_id=location_id,
            order_date=order_date or date.today(),
            expected_delivery_date=expected_delivery_date,
            subtotal=round(subtotal, 2),
            tax_amount=float(tax_amount or 0.0),
            discount_amount=float(discount_amount or 0.0),
            shipping_cost=float(shipping_cost or 0.0),
            total_amount=total,
            status=status,
            approved_by=created_by if status in ("Approved", "Ordered") else None,
            approved_at=datetime.utcnow() if status in ("Approved", "Ordered") else None,
            created_by=created_by,
            notes=notes,
        )
        session.add(po)
        session.flush()

        for ln in lines:
            qty = int(ln["ordered_qty"])
            cost = float(ln["unit_cost"])
            session.add(
                InventoryPurchaseOrderItem(
                    po_id=po.id,
                    item_id=ln["item_id"],
                    ordered_qty=qty,
                    received_qty=0,
                    unit_cost=cost,
                    line_total=round(qty * cost, 2),
                )
            )

        session.commit()
        session.refresh(po)
        return po

    @staticmethod
    def update_purchase_order_status(
        session: Session,
        po_id: int,
        status: str,
        approved_by: Optional[str] = None,
    ) -> Optional[InventoryPurchaseOrder]:
        po = session.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.id == po_id).first()
        if not po:
            return None
        po.status = status
        if status in ("Approved", "Ordered") and not po.approved_by:
            po.approved_by = approved_by or "admin"
            po.approved_at = datetime.utcnow()
        session.commit()
        session.refresh(po)
        return po

    # -------------------------------------------------------------
    # 6. Purchases & Accounting Expense Integration
    # -------------------------------------------------------------
    @staticmethod
    def get_purchases(session: Session) -> List[InventoryPurchase]:
        return session.query(InventoryPurchase).options(
            joinedload(InventoryPurchase.supplier),
            joinedload(InventoryPurchase.location),
            joinedload(InventoryPurchase.purchase_order),
            joinedload(InventoryPurchase.accounting_tx),
            joinedload(InventoryPurchase.items).joinedload(InventoryPurchaseItem.item),
        ).filter(InventoryPurchase.is_deleted == False).order_by(
            InventoryPurchase.purchase_date.desc(), InventoryPurchase.id.desc()
        ).all()

    @staticmethod
    def record_purchase(
        session: Session,
        supplier_id: int,
        lines: List[Dict[str, Any]],
        location_id: Optional[int] = None,
        purchase_order_id: Optional[int] = None,
        invoice_no: Optional[str] = None,
        purchase_date: Optional[date] = None,
        tax_amount: float = 0.0,
        discount_amount: float = 0.0,
        paid_amount: Optional[float] = None,
        payment_method: str = "Cash",
        post_to_accounting: bool = True,
        account_category_code: str = "EXP-INV",
        received_by: str = "admin",
        notes: Optional[str] = None,
    ) -> InventoryPurchase:
        if not lines:
            raise ValueError("Purchase must contain at least one product item.")

        resolved_loc_id = location_id or InventoryRepository.ensure_default_location(session).id
        supplier = session.query(InventorySupplier).filter(InventorySupplier.id == supplier_id).first()
        if not supplier:
            raise ValueError("Selected supplier not found.")

        subtotal = 0.0
        for ln in lines:
            qty = int(ln["quantity"])
            cost = float(ln["unit_cost"])
            if qty <= 0 or cost < 0:
                raise ValueError("Purchase quantity must be positive and unit cost non-negative.")
            subtotal += qty * cost

        total = max(0.0, round(subtotal + float(tax_amount or 0.0) - float(discount_amount or 0.0), 2))
        paid = total if paid_amount is None else round(min(total, max(0.0, float(paid_amount))), 2)
        if paid >= total and total > 0:
            pay_status = "Paid"
        elif paid > 0:
            pay_status = "Partial"
        else:
            pay_status = "Unpaid"

        p_no = f"PUR-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        pur_dt = purchase_date or date.today()

        pur = InventoryPurchase(
            purchase_no=p_no,
            purchase_order_id=purchase_order_id,
            supplier_id=supplier_id,
            location_id=resolved_loc_id,
            invoice_no=invoice_no,
            purchase_date=pur_dt,
            subtotal=round(subtotal, 2),
            tax_amount=float(tax_amount or 0.0),
            discount_amount=float(discount_amount or 0.0),
            total_amount=total,
            paid_amount=paid,
            payment_method=payment_method,
            payment_status=pay_status,
            status="Received",
            account_category_code=account_category_code,
            received_by=received_by,
            notes=notes,
        )
        session.add(pur)
        session.flush()

        # Accounting Expense Integration
        expense_amount = paid if paid > 0 else total
        acc_tx = None
        if post_to_accounting and expense_amount > 0:
            acc_tx = InventoryRepository._post_accounting_entry(
                session=session,
                trans_type="Expense",
                category_code=account_category_code,
                amount=expense_amount,
                party_name=supplier.name,
                reference_no=p_no,
                description=f"Inventory Purchase {p_no} from {supplier.name}" + (f" (Invoice: {invoice_no})" if invoice_no else ""),
                tx_date=pur_dt,
                payment_method=payment_method,
                actor_username=received_by,
                idempotency_key=f"INV-PUR-{p_no}",
            )
            if acc_tx:
                pur.accounting_tx_id = acc_tx.id

        # Increment item & warehouse stock + ledger entries
        for ln in lines:
            qty = int(ln["quantity"])
            cost = float(ln["unit_cost"])
            item = session.query(InventoryItem).filter(InventoryItem.id == ln["item_id"]).first()
            if not item:
                raise ValueError(f"Inventory item ID {ln['item_id']} not found.")
            if cost > 0:
                item.unit_cost = cost
            new_bal = InventoryRepository._adjust_stock_balance(session, item, qty, location_id=resolved_loc_id)
            session.add(
                InventoryPurchaseItem(
                    purchase_id=pur.id,
                    item_id=item.id,
                    quantity=qty,
                    unit_cost=cost,
                    line_total=round(qty * cost, 2),
                )
            )
            session.add(
                InventoryTransaction(
                    reference_no=f"{p_no}-{item.id}-{uuid.uuid4().hex[:3].upper()}",
                    item_id=item.id,
                    location_id=resolved_loc_id,
                    transaction_type="Purchase",
                    quantity=qty,
                    balance_after=new_bal,
                    unit_cost=cost,
                    total_cost=round(qty * cost, 2),
                    transaction_date=pur_dt,
                    issued_to=supplier.name,
                    recorded_by=received_by,
                    accounting_tx_id=acc_tx.id if acc_tx else None,
                    remarks=f"GRN {p_no}",
                )
            )

        # Sync linked Purchase Order if supplied
        if purchase_order_id:
            po = session.query(InventoryPurchaseOrder).options(
                joinedload(InventoryPurchaseOrder.items)
            ).filter(InventoryPurchaseOrder.id == purchase_order_id).first()
            if po:
                qty_by_item = {}
                for ln in lines:
                    qty_by_item[ln["item_id"]] = qty_by_item.get(ln["item_id"], 0) + int(ln["quantity"])
                for po_item in po.items:
                    if po_item.item_id in qty_by_item:
                        po_item.received_qty = min(po_item.ordered_qty, int(po_item.received_qty or 0) + qty_by_item[po_item.item_id])
                if all(pi.received_qty >= pi.ordered_qty for pi in po.items):
                    po.status = "Received"
                elif any(pi.received_qty > 0 for pi in po.items):
                    po.status = "Partially Received"

        session.commit()
        session.refresh(pur)
        return pur

    @staticmethod
    def cancel_purchase(
        session: Session,
        purchase_id: int,
        reason: str,
        actor_username: str = "admin",
    ) -> Optional[InventoryPurchase]:
        pur = session.query(InventoryPurchase).options(
            joinedload(InventoryPurchase.items)
        ).filter(InventoryPurchase.id == purchase_id).first()
        if not pur:
            return None
        if pur.status == "Cancelled":
            raise ValueError("Purchase has already been cancelled.")
        if not reason or not reason.strip():
            raise ValueError("Cancellation reason is mandatory.")

        # Reverse stock additions
        for pi in pur.items:
            item = session.query(InventoryItem).filter(InventoryItem.id == pi.item_id).first()
            if item:
                new_bal = InventoryRepository._adjust_stock_balance(
                    session, item, -int(pi.quantity), location_id=pur.location_id
                )
                session.add(
                    InventoryTransaction(
                        reference_no=f"CXL-{pur.purchase_no}-{item.id}-{uuid.uuid4().hex[:3].upper()}",
                        item_id=item.id,
                        location_id=pur.location_id,
                        transaction_type="Adjustment",
                        quantity=int(pi.quantity),
                        balance_after=new_bal,
                        unit_cost=float(pi.unit_cost or 0.0),
                        total_cost=float(pi.line_total or 0.0),
                        transaction_date=date.today(),
                        recorded_by=actor_username,
                        remarks=f"Purchase {pur.purchase_no} cancelled: {reason}",
                    )
                )

        if pur.accounting_tx_id:
            AccountingService.reverse_transaction(
                session,
                pur.accounting_tx_id,
                reason=f"Purchase {pur.purchase_no} cancelled: {reason}",
                actor_username=actor_username,
                commit=False,
            )

        pur.status = "Cancelled"
        pur.notes = f"{pur.notes + ' | ' if pur.notes else ''}Cancelled: {reason}"
        session.commit()
        session.refresh(pur)
        return pur

    # -------------------------------------------------------------
    # 7. Stock Adjustment & Stock Transfer
    # -------------------------------------------------------------
    @staticmethod
    def get_adjustments(session: Session) -> List[InventoryStockAdjustment]:
        return session.query(InventoryStockAdjustment).options(
            joinedload(InventoryStockAdjustment.item),
            joinedload(InventoryStockAdjustment.location),
        ).filter(InventoryStockAdjustment.is_deleted == False).order_by(
            InventoryStockAdjustment.adjustment_date.desc(), InventoryStockAdjustment.id.desc()
        ).all()

    @staticmethod
    def record_stock_adjustment(
        session: Session,
        item_id: int,
        adjustment_type: str,
        quantity_delta: int,
        reason: str,
        location_id: Optional[int] = None,
        adjustment_date: Optional[date] = None,
        approved_by: str = "admin",
        notes: Optional[str] = None,
    ) -> InventoryStockAdjustment:
        if quantity_delta == 0:
            raise ValueError("Adjustment quantity change cannot be zero.")
        if adjustment_type in ("Decrease", "Damage / Write-Off", "Expiry") and quantity_delta > 0:
            quantity_delta = -abs(quantity_delta)
        elif adjustment_type == "Increase" and quantity_delta < 0:
            quantity_delta = abs(quantity_delta)

        item = session.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            raise ValueError("Product not found.")

        prev_qty = int(item.quantity_in_stock or 0)
        new_qty = InventoryRepository._adjust_stock_balance(session, item, quantity_delta, location_id=location_id)
        adj_no = f"ADJ-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        adj_dt = adjustment_date or date.today()

        adj = InventoryStockAdjustment(
            adjustment_no=adj_no,
            item_id=item_id,
            location_id=location_id,
            adjustment_type=adjustment_type,
            previous_qty=prev_qty,
            quantity_change=quantity_delta,
            new_qty=new_qty,
            adjustment_date=adj_dt,
            reason=reason.strip(),
            approved_by=approved_by,
            notes=notes,
        )
        session.add(adj)

        tx_type = "Damage" if "Damage" in adjustment_type or "Expiry" in adjustment_type else "Adjustment"
        abs_qty = abs(quantity_delta)
        u_cost = float(item.unit_cost or 0.0)
        session.add(
            InventoryTransaction(
                reference_no=f"TX-{adj_no}",
                item_id=item_id,
                location_id=location_id,
                transaction_type=tx_type,
                quantity=abs_qty,
                balance_after=new_qty,
                unit_cost=u_cost,
                total_cost=round(abs_qty * u_cost, 2),
                transaction_date=adj_dt,
                recorded_by=approved_by,
                remarks=f"{adjustment_type}: {reason}",
            )
        )
        session.commit()
        session.refresh(adj)
        return adj

    @staticmethod
    def get_transfers(session: Session) -> List[InventoryStockTransfer]:
        return session.query(InventoryStockTransfer).options(
            joinedload(InventoryStockTransfer.item),
            joinedload(InventoryStockTransfer.from_location),
            joinedload(InventoryStockTransfer.to_location),
        ).filter(InventoryStockTransfer.is_deleted == False).order_by(
            InventoryStockTransfer.transfer_date.desc(), InventoryStockTransfer.id.desc()
        ).all()

    @staticmethod
    def create_stock_transfer(
        session: Session,
        item_id: int,
        from_location_id: int,
        to_location_id: int,
        quantity: int,
        transfer_date: Optional[date] = None,
        transferred_by: str = "admin",
        received_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> InventoryStockTransfer:
        if from_location_id == to_location_id:
            raise ValueError("Source and destination store locations must be different.")
        if quantity <= 0:
            raise ValueError("Transfer quantity must be positive.")

        item = session.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            raise ValueError("Product not found.")

        src_stock = session.query(InventoryStock).filter(
            InventoryStock.item_id == item_id,
            InventoryStock.location_id == from_location_id,
        ).first()
        if not src_stock or src_stock.quantity_on_hand < quantity:
            avail = src_stock.quantity_on_hand if src_stock else 0
            raise ValueError(f"Insufficient stock at source location. Available: {avail}, Requested: {quantity}.")

        src_stock.quantity_on_hand -= quantity

        dst_stock = session.query(InventoryStock).filter(
            InventoryStock.item_id == item_id,
            InventoryStock.location_id == to_location_id,
        ).first()
        if not dst_stock:
            dst_stock = InventoryStock(
                item_id=item_id,
                location_id=to_location_id,
                quantity_on_hand=quantity,
            )
            session.add(dst_stock)
        else:
            dst_stock.quantity_on_hand += quantity

        trf_no = f"TRF-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        trf_dt = transfer_date or date.today()
        trf = InventoryStockTransfer(
            transfer_no=trf_no,
            item_id=item_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            quantity=quantity,
            transfer_date=trf_dt,
            transferred_by=transferred_by,
            received_by=received_by,
            status="Completed",
            notes=notes,
        )
        session.add(trf)

        u_cost = float(item.unit_cost or 0.0)
        session.add(
            InventoryTransaction(
                reference_no=f"OUT-{trf_no}",
                item_id=item_id,
                location_id=from_location_id,
                transaction_type="Transfer Out",
                quantity=quantity,
                balance_after=item.quantity_in_stock,
                unit_cost=u_cost,
                total_cost=round(quantity * u_cost, 2),
                transaction_date=trf_dt,
                recorded_by=transferred_by,
                remarks=f"Transfer {trf_no} to Location #{to_location_id}",
            )
        )
        session.add(
            InventoryTransaction(
                reference_no=f"IN-{trf_no}",
                item_id=item_id,
                location_id=to_location_id,
                transaction_type="Transfer In",
                quantity=quantity,
                balance_after=item.quantity_in_stock,
                unit_cost=u_cost,
                total_cost=round(quantity * u_cost, 2),
                transaction_date=trf_dt,
                recorded_by=received_by or transferred_by,
                remarks=f"Transfer {trf_no} from Location #{from_location_id}",
            )
        )
        session.commit()
        session.refresh(trf)
        return trf

    # -------------------------------------------------------------
    # 8. Sales & Disposals (with Accounting Income on Sale)
    # -------------------------------------------------------------
    @staticmethod
    def get_disposals_sales(session: Session) -> List[InventoryDisposalSale]:
        return session.query(InventoryDisposalSale).options(
            joinedload(InventoryDisposalSale.item),
            joinedload(InventoryDisposalSale.location),
            joinedload(InventoryDisposalSale.accounting_tx),
        ).filter(InventoryDisposalSale.is_deleted == False).order_by(
            InventoryDisposalSale.transaction_date.desc(), InventoryDisposalSale.id.desc()
        ).all()

    @staticmethod
    def record_disposal_or_sale(
        session: Session,
        item_id: int,
        record_type: str,
        quantity: int,
        unit_price: float = 0.0,
        location_id: Optional[int] = None,
        buyer_or_recipient: Optional[str] = None,
        payment_method: str = "Cash",
        transaction_date: Optional[date] = None,
        reason: Optional[str] = None,
        post_to_accounting: bool = True,
        recorded_by: str = "admin",
        notes: Optional[str] = None,
    ) -> InventoryDisposalSale:
        if quantity <= 0 or unit_price < 0:
            raise ValueError("Quantity must be positive and unit price cannot be negative.")
        item = session.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if not item:
            raise ValueError("Product not found.")

        new_bal = InventoryRepository._adjust_stock_balance(session, item, -int(quantity), location_id=location_id)
        total_amt = round(int(quantity) * float(unit_price or 0.0), 2)
        ref_no = f"DIS-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"
        tx_dt = transaction_date or date.today()

        rec = InventoryDisposalSale(
            reference_no=ref_no,
            record_type=record_type,
            item_id=item_id,
            location_id=location_id,
            quantity=int(quantity),
            unit_price=float(unit_price or 0.0),
            total_amount=total_amt,
            buyer_or_recipient=buyer_or_recipient,
            payment_method=payment_method,
            transaction_date=tx_dt,
            reason=reason,
            recorded_by=recorded_by,
            notes=notes,
        )
        session.add(rec)
        session.flush()

        acc_tx = None
        if post_to_accounting and record_type == "Sale" and total_amt > 0:
            acc_tx = InventoryRepository._post_accounting_entry(
                session=session,
                trans_type="Income",
                category_code="INC-INV",
                amount=total_amt,
                party_name=buyer_or_recipient or "Walk-in / Student",
                reference_no=ref_no,
                description=f"Inventory Sale {ref_no}: {quantity}x {item.name}",
                tx_date=tx_dt,
                payment_method=payment_method,
                actor_username=recorded_by,
                idempotency_key=f"INV-SALE-{ref_no}",
            )
            if acc_tx:
                rec.accounting_tx_id = acc_tx.id

        ledger_type = "Sale" if record_type == "Sale" else ("Disposal" if record_type == "Disposal" else "Issue")
        session.add(
            InventoryTransaction(
                reference_no=f"TX-{ref_no}",
                item_id=item_id,
                location_id=location_id,
                transaction_type=ledger_type,
                quantity=int(quantity),
                balance_after=new_bal,
                unit_cost=float(unit_price or item.unit_cost or 0.0),
                total_cost=total_amt if total_amt > 0 else round(int(quantity) * float(item.unit_cost or 0.0), 2),
                transaction_date=tx_dt,
                issued_to=buyer_or_recipient,
                recorded_by=recorded_by,
                accounting_tx_id=acc_tx.id if acc_tx else None,
                remarks=reason or record_type,
            )
        )
        session.commit()
        session.refresh(rec)
        return rec

    # -------------------------------------------------------------
    # 9. Fixed Assets Registry
    # -------------------------------------------------------------
    @staticmethod
    def get_assets(
        session: Session,
        status: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> List[FixedAsset]:
        q = session.query(FixedAsset).options(
            joinedload(FixedAsset.category),
            joinedload(FixedAsset.department),
            joinedload(FixedAsset.assigned_staff),
            joinedload(FixedAsset.assigned_teacher),
            joinedload(FixedAsset.accounting_tx),
        ).filter(FixedAsset.is_deleted == False)
        if status and status != "All":
            q = q.filter(FixedAsset.status == status)
        if department_id:
            q = q.filter(FixedAsset.department_id == department_id)
        return q.order_by(FixedAsset.purchase_date.desc(), FixedAsset.id.desc()).all()

    @staticmethod
    def register_asset(
        session: Session,
        name: str,
        location: str,
        asset_id: Optional[str] = None,
        category_id: Optional[int] = None,
        item_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        serial_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model_no: Optional[str] = None,
        purchase_date: Optional[date] = None,
        cost: float = 0.0,
        salvage_value: float = 0.0,
        location_id: Optional[int] = None,
        department_id: Optional[int] = None,
        department_name: Optional[str] = None,
        assigned_staff_id: Optional[int] = None,
        assigned_teacher_id: Optional[int] = None,
        assigned_employee: Optional[str] = None,
        warranty: Optional[str] = None,
        warranty_expiry_date: Optional[date] = None,
        status: str = "Active",
        post_to_accounting: bool = False,
        payment_method: str = "Bank",
        recorded_by: str = "admin",
        notes: Optional[str] = None,
    ) -> FixedAsset:
        if cost < 0 or salvage_value < 0:
            raise ValueError("Asset cost and salvage value cannot be negative.")
        a_code = asset_id.strip().upper() if asset_id else f"AST-{date.today().year}-{uuid.uuid4().hex[:5].upper()}"
        p_dt = purchase_date or date.today()

        asset = FixedAsset(
            asset_id=a_code,
            name=name.strip(),
            category_id=category_id,
            item_id=item_id,
            supplier_id=supplier_id,
            serial_number=serial_number.strip() if serial_number else None,
            manufacturer=manufacturer,
            model_no=model_no,
            purchase_date=p_dt,
            cost=float(cost or 0.0),
            salvage_value=float(salvage_value or 0.0),
            location=location.strip(),
            location_id=location_id,
            department_id=department_id,
            department_name=department_name,
            assigned_staff_id=assigned_staff_id,
            assigned_teacher_id=assigned_teacher_id,
            assigned_employee=assigned_employee,
            warranty=warranty,
            warranty_expiry_date=warranty_expiry_date,
            status=status,
            notes=notes,
        )
        session.add(asset)
        session.flush()

        if post_to_accounting and float(cost or 0.0) > 0:
            acc_tx = InventoryRepository._post_accounting_entry(
                session=session,
                trans_type="Expense",
                category_code="EXP-INV",
                amount=float(cost),
                party_name=manufacturer or "Asset Vendor",
                reference_no=a_code,
                description=f"Fixed Asset Acquisition {a_code}: {asset.name}",
                tx_date=p_dt,
                payment_method=payment_method,
                actor_username=recorded_by,
                idempotency_key=f"INV-AST-{a_code}",
            )
            if acc_tx:
                asset.accounting_tx_id = acc_tx.id

        session.commit()
        session.refresh(asset)
        return asset

    @staticmethod
    def update_asset(session: Session, id_pk: int, **kwargs) -> Optional[FixedAsset]:
        asset = session.query(FixedAsset).filter(FixedAsset.id == id_pk).first()
        if not asset:
            return None
        for k, v in kwargs.items():
            if hasattr(asset, k):
                setattr(asset, k, v)
        session.commit()
        session.refresh(asset)
        return asset

    @staticmethod
    def assign_asset_to_employee(
        session: Session,
        id_pk: int,
        assigned_employee: str,
        assigned_staff_id: Optional[int] = None,
        assigned_teacher_id: Optional[int] = None,
        department_id: Optional[int] = None,
        department_name: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Optional[FixedAsset]:
        asset = session.query(FixedAsset).filter(FixedAsset.id == id_pk).first()
        if not asset:
            return None
        asset.assigned_employee = assigned_employee.strip()
        asset.assigned_staff_id = assigned_staff_id
        asset.assigned_teacher_id = assigned_teacher_id
        if department_id is not None:
            asset.department_id = department_id
        if department_name:
            asset.department_name = department_name
        if location:
            asset.location = location.strip()
        if asset.status == "Active":
            asset.status = "In Use"
        session.commit()
        session.refresh(asset)
        return asset

    # -------------------------------------------------------------
    # 10. Low-Stock Alerts, Warranty Alerts, Ledger & KPIs
    # -------------------------------------------------------------
    @staticmethod
    def get_low_stock_alerts(session: Session) -> List[Dict[str, Any]]:
        items = session.query(InventoryItem).options(
            joinedload(InventoryItem.category),
            joinedload(InventoryItem.preferred_supplier),
        ).filter(
            InventoryItem.is_deleted == False,
            InventoryItem.low_stock_alert_enabled == True,
            InventoryItem.status != "Discontinued",
            InventoryItem.quantity_in_stock <= InventoryItem.reorder_level,
        ).order_by(InventoryItem.quantity_in_stock.asc(), InventoryItem.name.asc()).all()

        alerts = []
        for it in items:
            qty = int(it.quantity_in_stock or 0)
            reorder = int(it.reorder_level or 0)
            severity = "CRITICAL (OUT OF STOCK)" if qty == 0 else "LOW STOCK"
            target_level = it.max_stock_level if it.max_stock_level and it.max_stock_level > reorder else max(reorder * 2, reorder + 5)
            suggested_reorder_qty = max(1, int(target_level) - qty)
            alerts.append(
                {
                    "item_id": it.id,
                    "item_code": it.item_code,
                    "name": it.name,
                    "category": it.category.name if it.category else "-",
                    "quantity_in_stock": qty,
                    "reorder_level": reorder,
                    "suggested_reorder_qty": suggested_reorder_qty,
                    "unit": it.unit,
                    "supplier": it.preferred_supplier.name if it.preferred_supplier else (it.supplier_name or "-"),
                    "severity": severity,
                }
            )
        return alerts

    @staticmethod
    def get_warranty_alerts(session: Session, within_days: int = 30) -> List[FixedAsset]:
        cutoff = date.today() + timedelta(days=within_days)
        return session.query(FixedAsset).filter(
            FixedAsset.is_deleted == False,
            FixedAsset.warranty_expiry_date.isnot(None),
            FixedAsset.warranty_expiry_date <= cutoff,
            FixedAsset.status.notin_(["Disposed", "Lost", "Retired"]),
        ).order_by(FixedAsset.warranty_expiry_date.asc()).all()

    @staticmethod
    def get_transactions(session: Session, limit: int = 200) -> List[InventoryTransaction]:
        return session.query(InventoryTransaction).options(
            joinedload(InventoryTransaction.item),
            joinedload(InventoryTransaction.location),
        ).filter(InventoryTransaction.is_deleted == False).order_by(
            InventoryTransaction.transaction_date.desc(), InventoryTransaction.id.desc()
        ).limit(limit).all()

    @staticmethod
    def get_inventory_stats(session: Session) -> Dict[str, Any]:
        items = session.query(InventoryItem).filter(InventoryItem.is_deleted == False).all()
        total_products = len(items)
        total_units = sum(int(i.quantity_in_stock or 0) for i in items)
        stock_valuation = sum(int(i.quantity_in_stock or 0) * float(i.unit_cost or 0.0) for i in items)
        low_stock_count = len(InventoryRepository.get_low_stock_alerts(session))
        out_of_stock_count = sum(1 for i in items if int(i.quantity_in_stock or 0) <= 0 and i.status != "Discontinued")

        suppliers_count = session.query(InventorySupplier).filter(InventorySupplier.is_deleted == False).count()
        open_pos = session.query(InventoryPurchaseOrder).filter(
            InventoryPurchaseOrder.is_deleted == False,
            InventoryPurchaseOrder.status.in_(["Draft", "Approved", "Ordered", "Partially Received"]),
        ).count()

        purchases = session.query(InventoryPurchase).filter(
            InventoryPurchase.is_deleted == False,
            InventoryPurchase.status == "Received",
        ).all()
        total_spend = sum(float(p.total_amount or 0.0) for p in purchases)

        assets = session.query(FixedAsset).filter(FixedAsset.is_deleted == False).all()
        total_assets = len(assets)
        asset_value = sum(float(a.cost or 0.0) for a in assets if a.status not in ("Disposed", "Lost"))

        return {
            "total_products": total_products,
            "total_units": total_units,
            "stock_valuation": round(stock_valuation, 2),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "suppliers_count": suppliers_count,
            "open_pos": open_pos,
            "total_purchases_spend": round(total_spend, 2),
            "total_assets": total_assets,
            "asset_valuation": round(asset_value, 2),
        }
