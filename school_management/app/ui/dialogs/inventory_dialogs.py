"""
EduManage Pro - Enterprise Inventory & Fixed Assets Dialogs
PySide6 modals for Categories, Products, Suppliers, Locations, Purchase Orders,
Purchases (with Accounting Expense integration), Stock Adjustments, Stock Transfers,
Sales/Disposals (with Accounting Income integration), and Fixed Assets.
"""

from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.models.inventory import (
    ADJUSTMENT_TYPES,
    ASSET_STATUSES,
    DISPOSAL_SALE_TYPES,
    INVENTORY_ITEM_TYPES,
)
from app.models.staff import Department, Staff, Teacher
from app.repositories.inventory_repository import InventoryRepository
from app.security.session import session as app_session


def _actor_username() -> str:
    if getattr(app_session, "current_user", None):
        return app_session.current_user.username
    return "admin"


class InventoryCategoryDialog(QDialog):
    """Create a product / asset category."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Add Inventory Category")
        self.resize(400, 240)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., STAT, LAB, ICT, FURN")
        form.addRow("Category Code:*", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Office Stationery")
        form.addRow("Category Name:*", self.name_edit)

        self.desc_edit = QLineEdit()
        form.addRow("Description:", self.desc_edit)
        layout.addLayout(form)

        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Save Category")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        if not code or not name:
            QMessageBox.warning(self, "Validation Error", "Category Code and Name are required.")
            return
        try:
            InventoryRepository.create_category(
                self.db, name=name, code=code, description=self.desc_edit.text().strip() or None
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))


class InventorySupplierDialog(QDialog):
    """Create or edit an approved vendor / supplier."""

    def __init__(self, parent=None, db_session=None, supplier=None):
        super().__init__(parent)
        self.db = db_session
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Add Supplier")
        self.resize(450, 390)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Auto-generated if blank")
        if self.supplier:
            self.code_edit.setText(self.supplier.supplier_code)
            self.code_edit.setEnabled(False)
        form.addRow("Supplier Code:", self.code_edit)

        self.name_edit = QLineEdit()
        if self.supplier:
            self.name_edit.setText(self.supplier.name)
        form.addRow("Supplier Name:*", self.name_edit)

        self.contact_edit = QLineEdit()
        if self.supplier and self.supplier.contact_person:
            self.contact_edit.setText(self.supplier.contact_person)
        form.addRow("Contact Person:", self.contact_edit)

        self.phone_edit = QLineEdit()
        if self.supplier and self.supplier.phone:
            self.phone_edit.setText(self.supplier.phone)
        form.addRow("Phone:", self.phone_edit)

        self.email_edit = QLineEdit()
        if self.supplier and self.supplier.email:
            self.email_edit.setText(self.supplier.email)
        form.addRow("Email:", self.email_edit)

        self.tax_edit = QLineEdit()
        if self.supplier and self.supplier.tax_id:
            self.tax_edit.setText(self.supplier.tax_id)
        form.addRow("TIN / VAT ID:", self.tax_edit)

        self.terms_edit = QLineEdit(self.supplier.payment_terms if self.supplier else "Net 30")
        form.addRow("Payment Terms:", self.terms_edit)

        self.addr_edit = QLineEdit()
        if self.supplier and self.supplier.address:
            self.addr_edit.setText(self.supplier.address)
        form.addRow("Address:", self.addr_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive", "Blacklisted"])
        if self.supplier:
            self.status_combo.setCurrentText(self.supplier.status)
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Save Supplier")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Supplier Name is required.")
            return
        try:
            if self.supplier:
                InventoryRepository.update_supplier(
                    self.db,
                    self.supplier.id,
                    name=name,
                    contact_person=self.contact_edit.text().strip() or None,
                    phone=self.phone_edit.text().strip() or None,
                    email=self.email_edit.text().strip() or None,
                    tax_id=self.tax_edit.text().strip() or None,
                    payment_terms=self.terms_edit.text().strip() or "Net 30",
                    address=self.addr_edit.text().strip() or None,
                    status=self.status_combo.currentText(),
                )
            else:
                InventoryRepository.create_supplier(
                    self.db,
                    name=name,
                    supplier_code=self.code_edit.text().strip() or None,
                    contact_person=self.contact_edit.text().strip() or None,
                    phone=self.phone_edit.text().strip() or None,
                    email=self.email_edit.text().strip() or None,
                    tax_id=self.tax_edit.text().strip() or None,
                    payment_terms=self.terms_edit.text().strip() or "Net 30",
                    address=self.addr_edit.text().strip() or None,
                    status=self.status_combo.currentText(),
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryLocationDialog(QDialog):
    """Create a warehouse / store location."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Add Store / Warehouse Location")
        self.resize(420, 270)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., LAB-STR, MAIN-STR")
        form.addRow("Store Code:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Science Lab Store")
        form.addRow("Location Name:*", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Central Store", "Department Store", "Lab Store", "Campus Annex"])
        form.addRow("Location Type:", self.type_combo)

        self.mgr_edit = QLineEdit()
        form.addRow("Storekeeper / Manager:", self.mgr_edit)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Save Location")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Location Name is required.")
            return
        try:
            InventoryRepository.create_location(
                self.db,
                name=name,
                code=self.code_edit.text().strip() or None,
                location_type=self.type_combo.currentText(),
                manager_name=self.mgr_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryProductDialog(QDialog):
    """Create or edit an inventory product / catalog SKU."""

    def __init__(self, parent=None, db_session=None, item=None):
        super().__init__(parent)
        self.db = db_session
        self.item = item
        self.setWindowTitle("Edit Product" if item else "Add Inventory Product")
        self.resize(480, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., PRD-001")
        if self.item:
            self.code_edit.setText(self.item.item_code)
            self.code_edit.setEnabled(False)
        form.addRow("Product Code:*", self.code_edit)

        self.barcode_edit = QLineEdit()
        if self.item and self.item.barcode:
            self.barcode_edit.setText(self.item.barcode)
        form.addRow("SKU / Barcode:", self.barcode_edit)

        self.name_edit = QLineEdit()
        if self.item:
            self.name_edit.setText(self.item.name)
        form.addRow("Product Name:*", self.name_edit)

        self.cat_combo = QComboBox()
        for c in InventoryRepository.get_categories(self.db):
            self.cat_combo.addItem(f"{c.name} ({c.code})", c.id)
        if self.item:
            idx = self.cat_combo.findData(self.item.category_id)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        form.addRow("Category:*", self.cat_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(INVENTORY_ITEM_TYPES)
        if self.item:
            self.type_combo.setCurrentText(self.item.item_type)
        form.addRow("Product Type:", self.type_combo)

        self.sup_combo = QComboBox()
        self.sup_combo.addItem("— Unspecified Supplier —", None)
        for sup in InventoryRepository.get_suppliers(self.db):
            self.sup_combo.addItem(sup.name, sup.id)
        if self.item and self.item.preferred_supplier_id:
            idx = self.sup_combo.findData(self.item.preferred_supplier_id)
            if idx >= 0:
                self.sup_combo.setCurrentIndex(idx)
        form.addRow("Preferred Supplier:", self.sup_combo)

        self.unit_edit = QLineEdit(self.item.unit if self.item else "Pcs")
        form.addRow("Unit (Pcs/Box/Ream):", self.unit_edit)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 1000000)
        self.qty_spin.setValue(self.item.quantity_in_stock if self.item else 0)
        if self.item:
            self.qty_spin.setEnabled(False)
        form.addRow("Opening Stock Qty:", self.qty_spin)

        self.reorder_spin = QSpinBox()
        self.reorder_spin.setRange(0, 100000)
        self.reorder_spin.setValue(self.item.reorder_level if self.item else 5)
        form.addRow("Low-Stock Reorder Level:", self.reorder_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10000000)
        self.cost_spin.setPrefix("৳ ")
        self.cost_spin.setValue(float(self.item.unit_cost) if self.item else 0.0)
        form.addRow("Unit Cost:", self.cost_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10000000)
        self.price_spin.setPrefix("৳ ")
        self.price_spin.setValue(float(self.item.selling_price) if self.item else 0.0)
        form.addRow("Selling Price:", self.price_spin)

        self.loc_edit = QLineEdit()
        if self.item and self.item.storage_location:
            self.loc_edit.setText(self.item.storage_location)
        form.addRow("Rack / Shelf Note:", self.loc_edit)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Save Product")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        cat_id = self.cat_combo.currentData()
        if not code or not name or not cat_id:
            QMessageBox.warning(self, "Validation Error", "Code, Product Name, and Category are required.")
            return
        try:
            if self.item:
                InventoryRepository.update_product(
                    self.db,
                    self.item.id,
                    name=name,
                    barcode=self.barcode_edit.text().strip() or None,
                    category_id=cat_id,
                    item_type=self.type_combo.currentText(),
                    preferred_supplier_id=self.sup_combo.currentData(),
                    unit=self.unit_edit.text().strip() or "Pcs",
                    reorder_level=self.reorder_spin.value(),
                    unit_cost=self.cost_spin.value(),
                    selling_price=self.price_spin.value(),
                    storage_location=self.loc_edit.text().strip() or None,
                )
            else:
                InventoryRepository.create_product(
                    self.db,
                    item_code=code,
                    name=name,
                    category_id=cat_id,
                    item_type=self.type_combo.currentText(),
                    preferred_supplier_id=self.sup_combo.currentData(),
                    unit=self.unit_edit.text().strip() or "Pcs",
                    quantity_in_stock=self.qty_spin.value(),
                    reorder_level=self.reorder_spin.value(),
                    unit_cost=self.cost_spin.value(),
                    selling_price=self.price_spin.value(),
                    barcode=self.barcode_edit.text().strip() or None,
                    storage_location=self.loc_edit.text().strip() or None,
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryPurchaseOrderDialog(QDialog):
    """Create a multi-line Purchase Order."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.lines = []
        self.setWindowTitle("Create Purchase Order (PO)")
        self.resize(560, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.sup_combo = QComboBox()
        for s in InventoryRepository.get_suppliers(self.db):
            self.sup_combo.addItem(f"{s.name} ({s.supplier_code})", s.id)
        form.addRow("Supplier:*", self.sup_combo)

        self.loc_combo = QComboBox()
        for loc in InventoryRepository.get_locations(self.db):
            self.loc_combo.addItem(loc.name, loc.id)
        form.addRow("Destination Store:", self.loc_combo)

        self.exp_date = QDateEdit()
        self.exp_date.setCalendarPopup(True)
        self.exp_date.setDate(QDate.currentDate().addDays(7))
        form.addRow("Expected Delivery:", self.exp_date)

        # Add line controls
        line_bar = QHBoxLayout()
        self.prod_combo = QComboBox()
        for p in InventoryRepository.get_products(self.db):
            self.prod_combo.addItem(f"{p.item_code} - {p.name}", (p.id, p.name, float(p.unit_cost or 0.0)))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000)
        self.qty_spin.setValue(10)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10000000)
        self.cost_spin.setPrefix("৳ ")
        add_line_btn = QPushButton("➕ Add Line")
        add_line_btn.clicked.connect(self._add_line)

        line_bar.addWidget(self.prod_combo, 3)
        line_bar.addWidget(self.qty_spin, 1)
        line_bar.addWidget(self.cost_spin, 2)
        line_bar.addWidget(add_line_btn)

        layout.addLayout(form)
        layout.addLayout(line_bar)

        self.lines_table = QTableWidget(0, 4)
        self.lines_table.setHorizontalHeaderLabels(["Product", "Ordered Qty", "Unit Cost", "Line Total"])
        self.lines_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.lines_table)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Delivery instructions / PO notes")
        layout.addWidget(self.notes_edit)

        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Create & Approve PO")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _add_line(self):
        data = self.prod_combo.currentData()
        if not isinstance(data, tuple):
            return
        item_id, name, default_cost = data
        cost = self.cost_spin.value() if self.cost_spin.value() > 0 else default_cost
        qty = self.qty_spin.value()
        self.lines.append({"item_id": item_id, "ordered_qty": qty, "unit_cost": cost})
        r = self.lines_table.rowCount()
        self.lines_table.insertRow(r)
        self.lines_table.setItem(r, 0, QTableWidgetItem(name))
        self.lines_table.setItem(r, 1, QTableWidgetItem(str(qty)))
        self.lines_table.setItem(r, 2, QTableWidgetItem(f"৳ {cost:,.2f}"))
        self.lines_table.setItem(r, 3, QTableWidgetItem(f"৳ {qty * cost:,.2f}"))

    def _save(self):
        sup_id = self.sup_combo.currentData()
        if not sup_id or not self.lines:
            QMessageBox.warning(self, "Validation Error", "Select a supplier and add at least one product line.")
            return
        qd = self.exp_date.date()
        exp_dt = date(qd.year(), qd.month(), qd.day())
        try:
            InventoryRepository.create_purchase_order(
                self.db,
                supplier_id=sup_id,
                lines=self.lines,
                location_id=self.loc_combo.currentData(),
                expected_delivery_date=exp_dt,
                status="Approved",
                created_by=_actor_username(),
                notes=self.notes_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryPurchaseDialog(QDialog):
    """Record a Purchase / Goods Receipt (optionally linked to a PO) & post Expense to Accounting."""

    def __init__(self, parent=None, db_session=None, purchase_order=None):
        super().__init__(parent)
        self.db = db_session
        self.po = purchase_order
        self.lines = []
        self.setWindowTitle("Record Inventory Purchase / Goods Receipt")
        self.resize(560, 520)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.sup_combo = QComboBox()
        for s in InventoryRepository.get_suppliers(self.db):
            self.sup_combo.addItem(f"{s.name} ({s.supplier_code})", s.id)
        if self.po:
            idx = self.sup_combo.findData(self.po.supplier_id)
            if idx >= 0:
                self.sup_combo.setCurrentIndex(idx)
        form.addRow("Supplier:*", self.sup_combo)

        self.loc_combo = QComboBox()
        for loc in InventoryRepository.get_locations(self.db):
            self.loc_combo.addItem(loc.name, loc.id)
        if self.po and self.po.location_id:
            idx = self.loc_combo.findData(self.po.location_id)
            if idx >= 0:
                self.loc_combo.setCurrentIndex(idx)
        form.addRow("Receive Into Store:", self.loc_combo)

        self.inv_edit = QLineEdit()
        self.inv_edit.setPlaceholderText("Vendor Bill / Invoice No")
        form.addRow("Supplier Invoice No:", self.inv_edit)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Bank", "Cash", "Card", "Mobile Banking", "Other"])
        form.addRow("Payment Method:", self.method_combo)

        self.post_acc_check = QCheckBox("Automatically post Purchase Expense voucher to School Accounting")
        self.post_acc_check.setChecked(True)
        form.addRow("Accounting Sync:", self.post_acc_check)

        layout.addLayout(form)

        # Product Line Adder
        line_bar = QHBoxLayout()
        self.prod_combo = QComboBox()
        for p in InventoryRepository.get_products(self.db):
            self.prod_combo.addItem(f"{p.item_code} - {p.name}", (p.id, p.name, float(p.unit_cost or 0.0)))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000)
        self.qty_spin.setValue(10)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10000000)
        self.cost_spin.setPrefix("৳ ")
        add_btn = QPushButton("➕ Add Item")
        add_btn.clicked.connect(self._add_line)
        line_bar.addWidget(self.prod_combo, 3)
        line_bar.addWidget(self.qty_spin, 1)
        line_bar.addWidget(self.cost_spin, 2)
        line_bar.addWidget(add_btn)
        layout.addLayout(line_bar)

        self.lines_table = QTableWidget(0, 4)
        self.lines_table.setHorizontalHeaderLabels(["Product", "Qty", "Unit Cost", "Total"])
        self.lines_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.lines_table)

        if self.po:
            for pi in self.po.items:
                rem = max(0, int(pi.ordered_qty) - int(pi.received_qty or 0))
                if rem > 0:
                    self._append_row(pi.item_id, pi.item.name if pi.item else f"Item #{pi.item_id}", rem, float(pi.unit_cost or 0.0))

        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Confirm Purchase & Post Accounting")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _append_row(self, item_id, name, qty, cost):
        self.lines.append({"item_id": item_id, "quantity": qty, "unit_cost": cost})
        r = self.lines_table.rowCount()
        self.lines_table.insertRow(r)
        self.lines_table.setItem(r, 0, QTableWidgetItem(name))
        self.lines_table.setItem(r, 1, QTableWidgetItem(str(qty)))
        self.lines_table.setItem(r, 2, QTableWidgetItem(f"৳ {cost:,.2f}"))
        self.lines_table.setItem(r, 3, QTableWidgetItem(f"৳ {qty * cost:,.2f}"))

    def _add_line(self):
        data = self.prod_combo.currentData()
        if not isinstance(data, tuple):
            return
        item_id, name, default_cost = data
        cost = self.cost_spin.value() if self.cost_spin.value() > 0 else default_cost
        self._append_row(item_id, name, self.qty_spin.value(), cost)

    def _save(self):
        sup_id = self.sup_combo.currentData()
        if not sup_id or not self.lines:
            QMessageBox.warning(self, "Validation Error", "Select a supplier and add at least one item.")
            return
        try:
            pur = InventoryRepository.record_purchase(
                self.db,
                supplier_id=sup_id,
                lines=self.lines,
                location_id=self.loc_combo.currentData(),
                purchase_order_id=self.po.id if self.po else None,
                invoice_no=self.inv_edit.text().strip() or None,
                payment_method=self.method_combo.currentText(),
                post_to_accounting=self.post_acc_check.isChecked(),
                received_by=_actor_username(),
            )
            msg = f"Purchase {pur.purchase_no} received!"
            if pur.accounting_tx:
                msg += f"\nAccounting Voucher: {pur.accounting_tx.voucher_no}"
            QMessageBox.information(self, "Purchase Recorded", msg)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryStockAdjustmentDialog(QDialog):
    """Record a stock adjustment (Increase, Decrease, Damage, Audit Count)."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Stock Adjustment")
        self.resize(430, 310)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.prod_combo = QComboBox()
        for p in InventoryRepository.get_products(self.db):
            self.prod_combo.addItem(f"{p.item_code} - {p.name} (In Stock: {p.quantity_in_stock})", p.id)
        form.addRow("Product:*", self.prod_combo)

        self.loc_combo = QComboBox()
        self.loc_combo.addItem("Global Catalog Only", None)
        for loc in InventoryRepository.get_locations(self.db):
            self.loc_combo.addItem(loc.name, loc.id)
        form.addRow("Store Location:", self.loc_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(ADJUSTMENT_TYPES)
        form.addRow("Adjustment Type:*", self.type_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(-100000, 100000)
        self.qty_spin.setValue(1)
        form.addRow("Quantity Change:", self.qty_spin)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Audit recount discrepancy / Damaged in transit...")
        form.addRow("Reason:*", self.reason_edit)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Apply Adjustment")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        item_id = self.prod_combo.currentData()
        reason = self.reason_edit.text().strip()
        if not item_id or not reason or self.qty_spin.value() == 0:
            QMessageBox.warning(self, "Validation Error", "Product, non-zero quantity, and reason are required.")
            return
        try:
            InventoryRepository.record_stock_adjustment(
                self.db,
                item_id=item_id,
                adjustment_type=self.type_combo.currentText(),
                quantity_delta=self.qty_spin.value(),
                reason=reason,
                location_id=self.loc_combo.currentData(),
                approved_by=_actor_username(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class InventoryStockTransferDialog(QDialog):
    """Transfer stock between two campus store locations."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Inter-Store Stock Transfer")
        self.resize(440, 310)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.prod_combo = QComboBox()
        for p in InventoryRepository.get_products(self.db):
            self.prod_combo.addItem(f"{p.item_code} - {p.name}", p.id)
        form.addRow("Product:*", self.prod_combo)

        locs = InventoryRepository.get_locations(self.db)
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        for loc in locs:
            self.from_combo.addItem(loc.name, loc.id)
            self.to_combo.addItem(loc.name, loc.id)
        if len(locs) > 1:
            self.to_combo.setCurrentIndex(1)
        form.addRow("From Location:*", self.from_combo)
        form.addRow("To Location:*", self.to_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000)
        self.qty_spin.setValue(5)
        form.addRow("Transfer Quantity:*", self.qty_spin)

        self.notes_edit = QLineEdit()
        form.addRow("Notes:", self.notes_edit)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Execute Transfer")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        item_id = self.prod_combo.currentData()
        from_id = self.from_combo.currentData()
        to_id = self.to_combo.currentData()
        if not item_id or not from_id or not to_id:
            QMessageBox.warning(self, "Validation Error", "Product, Source, and Destination locations are required.")
            return
        try:
            InventoryRepository.create_stock_transfer(
                self.db,
                item_id=item_id,
                from_location_id=from_id,
                to_location_id=to_id,
                quantity=self.qty_spin.value(),
                transferred_by=_actor_username(),
                notes=self.notes_edit.text().strip() or None,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Transfer Error", str(e))


class InventoryDisposalSaleDialog(QDialog):
    """Record a stock Sale, Scrap Disposal, or Departmental Consumption Issue."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Record Stock Sale / Disposal / Issue")
        self.resize(450, 380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(DISPOSAL_SALE_TYPES)
        form.addRow("Record Type:*", self.type_combo)

        self.prod_combo = QComboBox()
        for p in InventoryRepository.get_products(self.db):
            self.prod_combo.addItem(f"{p.item_code} - {p.name} (Avail: {p.quantity_in_stock})", (p.id, float(p.selling_price or 0.0)))
        form.addRow("Product:*", self.prod_combo)

        self.loc_combo = QComboBox()
        self.loc_combo.addItem("Global Catalog Stock", None)
        for loc in InventoryRepository.get_locations(self.db):
            self.loc_combo.addItem(loc.name, loc.id)
        form.addRow("From Store:", self.loc_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000)
        form.addRow("Quantity:*", self.qty_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 10000000)
        self.price_spin.setPrefix("৳ ")
        form.addRow("Unit Price (Sales):", self.price_spin)

        self.buyer_edit = QLineEdit()
        self.buyer_edit.setPlaceholderText("Buyer / Department / Scrap Dealer")
        form.addRow("Buyer / Recipient:", self.buyer_edit)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank", "Card", "Mobile Banking", "Other"])
        form.addRow("Payment Method:", self.method_combo)

        self.reason_edit = QLineEdit()
        form.addRow("Reason / Notes:", self.reason_edit)

        self.acc_check = QCheckBox("Post Sale Proceeds to Accounting Income (if Sale > 0)")
        self.acc_check.setChecked(True)
        form.addRow("Accounting Sync:", self.acc_check)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Confirm Record")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        p_data = self.prod_combo.currentData()
        if not isinstance(p_data, tuple):
            QMessageBox.warning(self, "Validation Error", "Please select a product.")
            return
        item_id, _ = p_data
        try:
            InventoryRepository.record_disposal_or_sale(
                self.db,
                item_id=item_id,
                record_type=self.type_combo.currentText(),
                quantity=self.qty_spin.value(),
                unit_price=self.price_spin.value(),
                location_id=self.loc_combo.currentData(),
                buyer_or_recipient=self.buyer_edit.text().strip() or None,
                payment_method=self.method_combo.currentText(),
                reason=self.reason_edit.text().strip() or None,
                post_to_accounting=self.acc_check.isChecked(),
                recorded_by=_actor_username(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class FixedAssetDialog(QDialog):
    """Register or edit a Fixed Asset with all required fields."""

    def __init__(self, parent=None, db_session=None, asset=None):
        super().__init__(parent)
        self.db = db_session
        self.asset = asset
        self.setWindowTitle("Edit Fixed Asset" if asset else "Register Fixed Asset")
        self.resize(500, 560)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.asset_id_edit = QLineEdit()
        self.asset_id_edit.setPlaceholderText("Auto-generated e.g. AST-2026-0001 if blank")
        if self.asset:
            self.asset_id_edit.setText(self.asset.asset_id)
            self.asset_id_edit.setEnabled(False)
        form.addRow("Asset ID:", self.asset_id_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Dell Optiplex 7010 / Smart Projector")
        if self.asset:
            self.name_edit.setText(self.asset.name)
        form.addRow("Asset Name:*", self.name_edit)

        self.serial_edit = QLineEdit()
        if self.asset and self.asset.serial_number:
            self.serial_edit.setText(self.asset.serial_number)
        form.addRow("Serial Number:", self.serial_edit)

        self.pdate_edit = QDateEdit()
        self.pdate_edit.setCalendarPopup(True)
        if self.asset and self.asset.purchase_date:
            pd = self.asset.purchase_date
            self.pdate_edit.setDate(QDate(pd.year, pd.month, pd.day))
        else:
            self.pdate_edit.setDate(QDate.currentDate())
        form.addRow("Purchase Date:*", self.pdate_edit)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 100000000)
        self.cost_spin.setPrefix("৳ ")
        self.cost_spin.setValue(float(self.asset.cost) if self.asset else 0.0)
        form.addRow("Acquisition Cost:*", self.cost_spin)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("e.g., Computer Lab 1, Principal Office")
        if self.asset:
            self.location_edit.setText(self.asset.location)
        form.addRow("Location:*", self.location_edit)

        self.dept_combo = QComboBox()
        self.dept_combo.addItem("— Administration / General —", (None, "Administration"))
        for dept in self.db.query(Department).filter(Department.is_deleted == False).order_by(Department.name.asc()).all():
            self.dept_combo.addItem(dept.name, (dept.id, dept.name))
        if self.asset and self.asset.department_id:
            for idx in range(self.dept_combo.count()):
                data = self.dept_combo.itemData(idx)
                if isinstance(data, tuple) and data[0] == self.asset.department_id:
                    self.dept_combo.setCurrentIndex(idx)
                    break
        form.addRow("Department:", self.dept_combo)

        self.emp_combo = QComboBox()
        self.emp_combo.setEditable(True)
        self.emp_combo.addItem("— Unassigned —", None)
        for st in self.db.query(Staff).filter(Staff.is_deleted == False).order_by(Staff.full_name.asc()).all():
            self.emp_combo.addItem(f"{st.full_name} (Staff - {st.position})", ("staff", st.id, st.full_name))
        for tc in self.db.query(Teacher).filter(Teacher.is_deleted == False).order_by(Teacher.full_name.asc()).all():
            self.emp_combo.addItem(f"{tc.full_name} (Teacher)", ("teacher", tc.id, tc.full_name))
        if self.asset and self.asset.assigned_employee:
            self.emp_combo.setEditText(self.asset.assigned_employee)
        form.addRow("Assigned Employee:", self.emp_combo)

        self.warranty_edit = QLineEdit()
        self.warranty_edit.setPlaceholderText("e.g., 36 Months On-Site Warranty")
        if self.asset and self.asset.warranty:
            self.warranty_edit.setText(self.asset.warranty)
        form.addRow("Warranty Terms:", self.warranty_edit)

        self.wexp_edit = QDateEdit()
        self.wexp_edit.setCalendarPopup(True)
        if self.asset and self.asset.warranty_expiry_date:
            wd = self.asset.warranty_expiry_date
            self.wexp_edit.setDate(QDate(wd.year, wd.month, wd.day))
        else:
            self.wexp_edit.setDate(QDate.currentDate().addYears(1))
        form.addRow("Warranty Expiry Date:", self.wexp_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(ASSET_STATUSES)
        if self.asset:
            self.status_combo.setCurrentText(self.asset.status)
        form.addRow("Status:*", self.status_combo)

        self.post_acc_check = QCheckBox("Post Asset Capital Expense voucher to School Accounting")
        self.post_acc_check.setChecked(self.asset is None)
        if self.asset:
            self.post_acc_check.setEnabled(False)
        form.addRow("Accounting Integration:", self.post_acc_check)

        layout.addLayout(form)
        btns = QHBoxLayout()
        c_btn = QPushButton("Cancel")
        c_btn.clicked.connect(self.reject)
        s_btn = QPushButton("Save Asset")
        s_btn.setDefault(True)
        s_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(c_btn)
        btns.addWidget(s_btn)
        layout.addLayout(btns)

    def _save(self):
        name = self.name_edit.text().strip()
        loc = self.location_edit.text().strip()
        if not name or not loc:
            QMessageBox.warning(self, "Validation Error", "Asset Name and Location are required.")
            return

        qd = self.pdate_edit.date()
        p_dt = date(qd.year(), qd.month(), qd.day())
        wqd = self.wexp_edit.date()
        w_dt = date(wqd.year(), wqd.month(), wqd.day())

        dept_data = self.dept_combo.currentData()
        dept_id = dept_data[0] if isinstance(dept_data, tuple) else None
        dept_name = dept_data[1] if isinstance(dept_data, tuple) else None

        emp_data = self.emp_combo.currentData()
        staff_id = emp_data[1] if isinstance(emp_data, tuple) and emp_data[0] == "staff" else None
        teacher_id = emp_data[1] if isinstance(emp_data, tuple) and emp_data[0] == "teacher" else None
        emp_name = (
            emp_data[2]
            if isinstance(emp_data, tuple)
            else (None if self.emp_combo.currentText().startswith("—") else self.emp_combo.currentText().strip() or None)
        )

        try:
            if self.asset:
                InventoryRepository.update_asset(
                    self.db,
                    self.asset.id,
                    name=name,
                    serial_number=self.serial_edit.text().strip() or None,
                    purchase_date=p_dt,
                    cost=self.cost_spin.value(),
                    location=loc,
                    department_id=dept_id,
                    department_name=dept_name,
                    assigned_staff_id=staff_id,
                    assigned_teacher_id=teacher_id,
                    assigned_employee=emp_name,
                    warranty=self.warranty_edit.text().strip() or None,
                    warranty_expiry_date=w_dt,
                    status=self.status_combo.currentText(),
                )
            else:
                InventoryRepository.register_asset(
                    self.db,
                    asset_id=self.asset_id_edit.text().strip() or None,
                    name=name,
                    serial_number=self.serial_edit.text().strip() or None,
                    purchase_date=p_dt,
                    cost=self.cost_spin.value(),
                    location=loc,
                    department_id=dept_id,
                    department_name=dept_name,
                    assigned_staff_id=staff_id,
                    assigned_teacher_id=teacher_id,
                    assigned_employee=emp_name,
                    warranty=self.warranty_edit.text().strip() or None,
                    warranty_expiry_date=w_dt,
                    status=self.status_combo.currentText(),
                    post_to_accounting=self.post_acc_check.isChecked(),
                    recorded_by=_actor_username(),
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
