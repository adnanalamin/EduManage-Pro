"""
EduManage Pro - Enterprise Inventory & Fixed Asset Management Page
7-Tab PySide6 GUI backed by real database records covering:
1. Products & Categories
2. Suppliers
3. Purchase Orders & Purchases (Accounting Expense Linked)
4. Stock Locations, Adjustments & Transfers
5. Sales & Disposals (Accounting Income Linked)
6. Fixed Assets (Asset ID, Serial, Purchase Date, Cost, Location, Dept, Employee, Warranty, Status)
7. Low-Stock Alerts & Inventory Reports (PDF + 8-Sheet Excel)
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database.connection import SessionLocal
from app.models.inventory import (
    ASSET_STATUSES,
    FixedAsset,
    InventoryItem,
    InventoryPurchase,
    InventoryPurchaseOrder,
    InventorySupplier,
)
from app.models.school import SchoolSetting
from app.reports.inventory_reports_pdf import InventoryReportsPDFGenerator
from app.repositories.inventory_repository import InventoryRepository
from app.security.session import session as app_session
from app.services.inventory_service import InventoryService
from app.ui.dialogs.inventory_dialogs import (
    FixedAssetDialog,
    InventoryCategoryDialog,
    InventoryDisposalSaleDialog,
    InventoryLocationDialog,
    InventoryProductDialog,
    InventoryPurchaseDialog,
    InventoryPurchaseOrderDialog,
    InventoryStockAdjustmentDialog,
    InventoryStockTransferDialog,
    InventorySupplierDialog,
)


class InventoryPage(QWidget):
    """Main PySide6 page for Enterprise Inventory, Procurement, Stock & Fixed Asset Management."""

    def __init__(self, parent=None, db_session=None):
        super().__init__(parent)
        self.db = db_session if db_session is not None else SessionLocal()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Enterprise Inventory & Fixed Asset Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        subtitle = QLabel(
            "Products, categories, suppliers, purchase orders, stock transfers & adjustments, "
            "disposals/sales, fixed assets, low-stock alerts & accounting integration"
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh Inventory")
        refresh_btn.setStyleSheet("background-color: #0F172A; color: white; padding: 6px 14px; font-weight: 600; border-radius: 6px;")
        refresh_btn.clicked.connect(self.refresh_all)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # KPI Cards
        self.kpi_layout = QHBoxLayout()
        self._build_kpi_cards()
        main_layout.addLayout(self.kpi_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 8px; }
            QTabBar::tab { padding: 8px 12px; font-weight: 600; font-size: 12px; }
            QTabBar::tab:selected { background: #1E3A8A; color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; }
        """)

        self.tab_products = QWidget()
        self._init_products_tab()
        self.tabs.addTab(self.tab_products, "📦 Products & Categories")

        self.tab_suppliers = QWidget()
        self._init_suppliers_tab()
        self.tabs.addTab(self.tab_suppliers, "🏭 Suppliers")

        self.tab_procurement = QWidget()
        self._init_procurement_tab()
        self.tabs.addTab(self.tab_procurement, "🧾 POs & Purchases")

        self.tab_stock = QWidget()
        self._init_stock_tab()
        self.tabs.addTab(self.tab_stock, "🏬 Stock, Adjustments & Transfers")

        self.tab_disposal = QWidget()
        self._init_disposal_tab()
        self.tabs.addTab(self.tab_disposal, "♻️ Sales & Disposals")

        self.tab_assets = QWidget()
        self._init_assets_tab()
        self.tabs.addTab(self.tab_assets, "🖥️ Fixed Assets")

        self.tab_alerts_reports = QWidget()
        self._init_alerts_reports_tab()
        self.tabs.addTab(self.tab_alerts_reports, "🚨 Alerts & Reports")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    def _build_kpi_cards(self):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = InventoryRepository.get_inventory_stats(self.db)
        cards = [
            ("Products / Units", f"{stats.get('total_products', 0)} / {stats.get('total_units', 0):,}", "#1E3A8A"),
            ("Stock Valuation", f"৳ {stats.get('stock_valuation', 0):,.0f}", "#059669"),
            ("Low-Stock Alerts", f"{stats.get('low_stock_count', 0)} ({stats.get('out_of_stock_count', 0)} Out)", "#DC2626"),
            ("Open POs / Spend", f"{stats.get('open_pos', 0)} / ৳ {stats.get('total_purchases_spend', 0):,.0f}", "#0369A1"),
            ("Fixed Assets / Value", f"{stats.get('total_assets', 0)} / ৳ {stats.get('asset_valuation', 0):,.0f}", "#4338CA"),
        ]
        for label, val, color in cards:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 6px 10px;
                }}
            """)
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(4, 2, 4, 2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
            val_lbl = QLabel(val)
            val_lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
            fl.addWidget(lbl)
            fl.addWidget(val_lbl)
            self.kpi_layout.addWidget(frame)

    # -------------------------------------------------------------
    # TAB 1: Products & Categories
    # -------------------------------------------------------------
    def _init_products_tab(self):
        layout = QVBoxLayout(self.tab_products)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_cat = QPushButton("➕ Add Category")
        add_cat.clicked.connect(self._add_category)

        add_prod = QPushButton("➕ Add Product")
        add_prod.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        add_prod.clicked.connect(self._add_product)

        edit_prod = QPushButton("✏️ Edit Selected Product")
        edit_prod.clicked.connect(self._edit_product)

        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("Search product code, SKU, name...")
        self.prod_search.textChanged.connect(self._filter_products)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories", None)
        self.cat_filter.currentIndexChanged.connect(self._filter_products)

        self.stock_status_filter = QComboBox()
        self.stock_status_filter.addItems(["All", "In Stock", "Low Stock", "Out of Stock", "Discontinued"])
        self.stock_status_filter.currentTextChanged.connect(self._filter_products)

        bar.addWidget(add_cat)
        bar.addWidget(add_prod)
        bar.addWidget(edit_prod)
        bar.addSpacing(8)
        bar.addWidget(self.prod_search)
        bar.addWidget(self.cat_filter)
        bar.addWidget(self.stock_status_filter)
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)

        self.cat_table = QTableWidget(0, 4)
        self.cat_table.setHorizontalHeaderLabels(["Code", "Category", "Items", "Active"])
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cat_table.setAlternatingRowColors(True)

        self.prod_table = QTableWidget(0, 9)
        self.prod_table.setHorizontalHeaderLabels([
            "ID", "Code", "Product Name", "Category", "Type", "In Stock", "Reorder", "Unit Cost", "Status"
        ])
        self.prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.prod_table.setAlternatingRowColors(True)

        splitter.addWidget(self.cat_table)
        splitter.addWidget(self.prod_table)
        splitter.setSizes([280, 740])
        layout.addWidget(splitter)

    def _add_category(self):
        if InventoryCategoryDialog(self, self.db).exec():
            self.refresh_all()

    def _add_product(self):
        if InventoryProductDialog(self, self.db).exec():
            self.refresh_all()

    def _edit_product(self):
        row = self.prod_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Product", "Please select a product row to edit.")
            return
        item_id = int(self.prod_table.item(row, 0).text())
        item = InventoryRepository.get_product_by_id(self.db, item_id)
        if item and InventoryProductDialog(self, self.db, item=item).exec():
            self.refresh_all()

    def _filter_products(self):
        prods = InventoryRepository.get_products(
            self.db,
            category_id=self.cat_filter.currentData(),
            status=self.stock_status_filter.currentText(),
            search=self.prod_search.text().strip() or None,
        )
        self.prod_table.setRowCount(len(prods))
        for r_idx, p in enumerate(prods):
            self.prod_table.setItem(r_idx, 0, QTableWidgetItem(str(p.id)))
            self.prod_table.setItem(r_idx, 1, QTableWidgetItem(p.item_code))
            self.prod_table.setItem(r_idx, 2, QTableWidgetItem(p.name))
            self.prod_table.setItem(r_idx, 3, QTableWidgetItem(p.category.name if p.category else "-"))
            self.prod_table.setItem(r_idx, 4, QTableWidgetItem(p.item_type))
            self.prod_table.setItem(r_idx, 5, QTableWidgetItem(f"{p.quantity_in_stock} {p.unit}"))
            self.prod_table.setItem(r_idx, 6, QTableWidgetItem(str(p.reorder_level)))
            self.prod_table.setItem(r_idx, 7, QTableWidgetItem(f"৳ {float(p.unit_cost or 0):,.2f}"))
            st = QTableWidgetItem(p.status)
            if p.status in ("Low Stock", "Out of Stock"):
                st.setForeground(QColor("#DC2626"))
            elif p.status == "In Stock":
                st.setForeground(QColor("#059669"))
            self.prod_table.setItem(r_idx, 8, st)

    # -------------------------------------------------------------
    # TAB 2: Suppliers
    # -------------------------------------------------------------
    def _init_suppliers_tab(self):
        layout = QVBoxLayout(self.tab_suppliers)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("➕ Add Supplier")
        add_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_supplier)
        edit_btn = QPushButton("✏️ Edit Selected Supplier")
        edit_btn.clicked.connect(self._edit_supplier)
        bar.addWidget(add_btn)
        bar.addWidget(edit_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.sup_table = QTableWidget(0, 8)
        self.sup_table.setHorizontalHeaderLabels([
            "ID", "Code", "Supplier Name", "Contact", "Phone", "Email", "Terms", "Status"
        ])
        self.sup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sup_table.setAlternatingRowColors(True)
        layout.addWidget(self.sup_table)

    def _add_supplier(self):
        if InventorySupplierDialog(self, self.db).exec():
            self.refresh_all()

    def _edit_supplier(self):
        row = self.sup_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Supplier", "Select a supplier row to edit.")
            return
        sup_id = int(self.sup_table.item(row, 0).text())
        sup = self.db.query(InventorySupplier).filter(InventorySupplier.id == sup_id).first()
        if sup and InventorySupplierDialog(self, self.db, supplier=sup).exec():
            self.refresh_all()

    # -------------------------------------------------------------
    # TAB 3: Purchase Orders & Purchases (Accounting Synced)
    # -------------------------------------------------------------
    def _init_procurement_tab(self):
        layout = QVBoxLayout(self.tab_procurement)
        layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Vertical)

        # Purchase Orders
        po_w = QWidget()
        po_lay = QVBoxLayout(po_w)
        po_lay.setContentsMargins(0, 0, 0, 0)
        po_bar = QHBoxLayout()
        new_po = QPushButton("📝 New Purchase Order")
        new_po.setStyleSheet("background-color: #0369A1; color: white; font-weight: bold;")
        new_po.clicked.connect(self._new_po)
        rcv_po = QPushButton("📦 Receive Selected PO as Purchase")
        rcv_po.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        rcv_po.clicked.connect(self._receive_selected_po)
        po_bar.addWidget(QLabel("<b>Purchase Orders</b>"))
        po_bar.addStretch()
        po_bar.addWidget(new_po)
        po_bar.addWidget(rcv_po)
        po_lay.addLayout(po_bar)

        self.po_table = QTableWidget(0, 7)
        self.po_table.setHorizontalHeaderLabels([
            "ID", "PO Number", "Order Date", "Supplier", "Store", "Total", "Status"
        ])
        self.po_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.po_table.setAlternatingRowColors(True)
        po_lay.addWidget(self.po_table)
        splitter.addWidget(po_w)

        # Purchases
        pur_w = QWidget()
        pur_lay = QVBoxLayout(pur_w)
        pur_lay.setContentsMargins(0, 0, 0, 0)
        pur_bar = QHBoxLayout()
        new_pur = QPushButton("🛒 Direct Purchase / GRN")
        new_pur.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        new_pur.clicked.connect(self._new_direct_purchase)
        cxl_pur = QPushButton("↩️ Cancel & Reverse Purchase Voucher")
        cxl_pur.clicked.connect(self._cancel_purchase)
        pur_bar.addWidget(QLabel("<b>Stock Purchases (Synced to School Accounting Expense Ledger)</b>"))
        pur_bar.addStretch()
        pur_bar.addWidget(new_pur)
        pur_bar.addWidget(cxl_pur)
        pur_lay.addLayout(pur_bar)

        self.pur_table = QTableWidget(0, 9)
        self.pur_table.setHorizontalHeaderLabels([
            "ID", "Purchase No", "Date", "Supplier", "Invoice No", "Total", "Method", "Accounting Voucher", "Status"
        ])
        self.pur_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pur_table.setAlternatingRowColors(True)
        pur_lay.addWidget(self.pur_table)
        splitter.addWidget(pur_w)

        layout.addWidget(splitter)

    def _new_po(self):
        if InventoryPurchaseOrderDialog(self, self.db).exec():
            self.refresh_all()

    def _receive_selected_po(self):
        row = self.po_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select PO", "Select a Purchase Order to receive goods.")
            return
        po_id = int(self.po_table.item(row, 0).text())
        po = self.db.query(InventoryPurchaseOrder).filter(InventoryPurchaseOrder.id == po_id).first()
        if po and InventoryPurchaseDialog(self, self.db, purchase_order=po).exec():
            self.refresh_all()

    def _new_direct_purchase(self):
        if InventoryPurchaseDialog(self, self.db).exec():
            self.refresh_all()

    def _cancel_purchase(self):
        row = self.pur_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Purchase", "Select a received purchase to cancel & reverse.")
            return
        pur_id = int(self.pur_table.item(row, 0).text())
        reason, ok = QInputDialog.getText(self, "Cancel & Reverse Purchase", "Mandatory Audit Cancellation Reason:")
        if ok and reason.strip():
            actor = app_session.current_user.username if getattr(app_session, "current_user", None) else "admin"
            try:
                InventoryRepository.cancel_purchase(self.db, pur_id, reason=reason.strip(), actor_username=actor)
                self.refresh_all()
            except Exception as e:
                QMessageBox.warning(self, "Cancellation Error", str(e))

    # -------------------------------------------------------------
    # TAB 4: Stock, Locations, Adjustments & Transfers
    # -------------------------------------------------------------
    def _init_stock_tab(self):
        layout = QVBoxLayout(self.tab_stock)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_loc = QPushButton("🏬 Add Store Location")
        add_loc.clicked.connect(self._add_location)
        adj_btn = QPushButton("⚖️ Stock Adjustment")
        adj_btn.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        adj_btn.clicked.connect(self._add_adjustment)
        trf_btn = QPushButton("🚚 Stock Transfer")
        trf_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        trf_btn.clicked.connect(self._add_transfer)
        bar.addWidget(add_loc)
        bar.addWidget(adj_btn)
        bar.addWidget(trf_btn)
        bar.addStretch()
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Vertical)
        self.stock_table = QTableWidget(0, 6)
        self.stock_table.setHorizontalHeaderLabels(["Store Code", "Location", "Product Code", "Product Name", "On Hand", "Bin / Shelf"])
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stock_table.setAlternatingRowColors(True)
        splitter.addWidget(self.stock_table)

        bottom_split = QSplitter(Qt.Horizontal)
        self.adj_table = QTableWidget(0, 6)
        self.adj_table.setHorizontalHeaderLabels(["Adj No", "Date", "Product", "Type", "Delta", "Reason"])
        self.adj_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.adj_table.setAlternatingRowColors(True)

        self.trf_table = QTableWidget(0, 6)
        self.trf_table.setHorizontalHeaderLabels(["Transfer No", "Date", "Product", "From", "To", "Qty"])
        self.trf_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trf_table.setAlternatingRowColors(True)

        bottom_split.addWidget(self.adj_table)
        bottom_split.addWidget(self.trf_table)
        splitter.addWidget(bottom_split)
        layout.addWidget(splitter)

    def _add_location(self):
        if InventoryLocationDialog(self, self.db).exec():
            self.refresh_all()

    def _add_adjustment(self):
        if InventoryStockAdjustmentDialog(self, self.db).exec():
            self.refresh_all()

    def _add_transfer(self):
        if InventoryStockTransferDialog(self, self.db).exec():
            self.refresh_all()

    # -------------------------------------------------------------
    # TAB 5: Sales & Disposals
    # -------------------------------------------------------------
    def _init_disposal_tab(self):
        layout = QVBoxLayout(self.tab_disposal)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("♻️ Record Sale / Disposal / Issue")
        add_btn.setStyleSheet("background-color: #4338CA; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_disposal_sale)
        bar.addWidget(add_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.disposal_table = QTableWidget(0, 9)
        self.disposal_table.setHorizontalHeaderLabels([
            "Ref No", "Date", "Type", "Product", "Qty", "Unit Price", "Total", "Buyer / Recipient", "Accounting Voucher"
        ])
        self.disposal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disposal_table.setAlternatingRowColors(True)
        layout.addWidget(self.disposal_table)

    def _add_disposal_sale(self):
        if InventoryDisposalSaleDialog(self, self.db).exec():
            self.refresh_all()

    # -------------------------------------------------------------
    # TAB 6: Fixed Assets
    # -------------------------------------------------------------
    def _init_assets_tab(self):
        layout = QVBoxLayout(self.tab_assets)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        add_btn = QPushButton("🖥️ Register Fixed Asset")
        add_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: bold;")
        add_btn.clicked.connect(self._add_asset)

        edit_btn = QPushButton("✏️ Edit Selected Asset")
        edit_btn.clicked.connect(self._edit_asset)

        self.asset_status_filter = QComboBox()
        self.asset_status_filter.addItems(["All"] + ASSET_STATUSES)
        self.asset_status_filter.currentTextChanged.connect(self._filter_assets)

        bar.addWidget(add_btn)
        bar.addWidget(edit_btn)
        bar.addSpacing(12)
        bar.addWidget(QLabel("Status:"))
        bar.addWidget(self.asset_status_filter)
        bar.addStretch()
        layout.addLayout(bar)

        self.assets_table = QTableWidget(0, 11)
        self.assets_table.setHorizontalHeaderLabels([
            "PK", "Asset ID", "Asset Name", "Serial No", "Purchase Date", "Cost",
            "Location", "Department", "Assigned Employee", "Warranty", "Status"
        ])
        self.assets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.assets_table.setAlternatingRowColors(True)
        layout.addWidget(self.assets_table)

    def _add_asset(self):
        if FixedAssetDialog(self, self.db).exec():
            self.refresh_all()

    def _edit_asset(self):
        row = self.assets_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select Asset", "Select a fixed asset row to edit.")
            return
        pk = int(self.assets_table.item(row, 0).text())
        asset = self.db.query(FixedAsset).filter(FixedAsset.id == pk).first()
        if asset and FixedAssetDialog(self, self.db, asset=asset).exec():
            self.refresh_all()

    def _filter_assets(self):
        assets = InventoryRepository.get_assets(self.db, status=self.asset_status_filter.currentText())
        self.assets_table.setRowCount(len(assets))
        for r_idx, a in enumerate(assets):
            dept = a.department.name if a.department else (a.department_name or "-")
            self.assets_table.setItem(r_idx, 0, QTableWidgetItem(str(a.id)))
            self.assets_table.setItem(r_idx, 1, QTableWidgetItem(a.asset_id))
            self.assets_table.setItem(r_idx, 2, QTableWidgetItem(a.name))
            self.assets_table.setItem(r_idx, 3, QTableWidgetItem(a.serial_number or "-"))
            self.assets_table.setItem(r_idx, 4, QTableWidgetItem(str(a.purchase_date)))
            self.assets_table.setItem(r_idx, 5, QTableWidgetItem(f"৳ {float(a.cost or 0):,.2f}"))
            self.assets_table.setItem(r_idx, 6, QTableWidgetItem(a.location))
            self.assets_table.setItem(r_idx, 7, QTableWidgetItem(dept))
            self.assets_table.setItem(r_idx, 8, QTableWidgetItem(a.assigned_employee or "Unassigned"))
            self.assets_table.setItem(r_idx, 9, QTableWidgetItem(a.warranty or "-"))
            self.assets_table.setItem(r_idx, 10, QTableWidgetItem(a.status))

    # -------------------------------------------------------------
    # TAB 7: Low-Stock Alerts & Inventory Reports
    # -------------------------------------------------------------
    def _init_alerts_reports_tab(self):
        layout = QVBoxLayout(self.tab_alerts_reports)
        layout.setContentsMargins(12, 12, 12, 12)

        bar = QHBoxLayout()
        stock_pdf = QPushButton("📄 Stock Valuation & Alerts PDF")
        stock_pdf.setStyleSheet("background-color: #991B1B; color: white; font-weight: bold;")
        stock_pdf.clicked.connect(self._export_stock_pdf)

        proc_pdf = QPushButton("🧾 Procurement & Accounting PDF")
        proc_pdf.clicked.connect(self._export_proc_pdf)

        asset_pdf = QPushButton("🖥️ Fixed Assets Register PDF")
        asset_pdf.clicked.connect(self._export_assets_pdf)

        xlsx_btn = QPushButton("📊 Full Inventory Workbook (.xlsx)")
        xlsx_btn.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        xlsx_btn.clicked.connect(self._export_excel)

        bar.addWidget(stock_pdf)
        bar.addWidget(proc_pdf)
        bar.addWidget(asset_pdf)
        bar.addWidget(xlsx_btn)
        bar.addStretch()
        layout.addLayout(bar)

        self.alerts_table = QTableWidget(0, 8)
        self.alerts_table.setHorizontalHeaderLabels([
            "Code", "Product", "Category", "In Stock", "Reorder Level", "Suggested Reorder", "Preferred Supplier", "Severity"
        ])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alerts_table.setAlternatingRowColors(True)
        layout.addWidget(self.alerts_table)

    def _export_stock_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Stock Report", "Inventory_Stock_Alerts.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            InventoryReportsPDFGenerator.generate_stock_and_low_stock_report(
                InventoryRepository.get_products(self.db),
                InventoryRepository.get_low_stock_alerts(self.db),
                school=school,
                output_path=path,
            )
            QMessageBox.information(self, "PDF Generated", f"Stock & Low-Stock Alerts PDF saved to:\n{path}")

    def _export_proc_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Procurement Report", "Inventory_Procurement_Expenses.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            InventoryReportsPDFGenerator.generate_procurement_and_expense_report(
                InventoryRepository.get_purchase_orders(self.db),
                InventoryRepository.get_purchases(self.db),
                school=school,
                output_path=path,
            )
            QMessageBox.information(self, "PDF Generated", f"Procurement & Expense PDF saved to:\n{path}")

    def _export_assets_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Fixed Assets PDF", "Fixed_Assets_Register.pdf", "PDF Files (*.pdf)")
        if path:
            school = self.db.query(SchoolSetting).first()
            InventoryReportsPDFGenerator.generate_fixed_asset_register_pdf(
                InventoryRepository.get_assets(self.db),
                school=school,
                output_path=path,
            )
            QMessageBox.information(self, "PDF Generated", f"Fixed Assets Register PDF saved to:\n{path}")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Inventory Workbook", "Enterprise_Inventory_Report.xlsx", "Excel Files (*.xlsx)")
        if path:
            InventoryService.export_inventory_comprehensive_excel(self.db, path)
            QMessageBox.information(self, "Export Complete", f"Multi-sheet inventory workbook saved to:\n{path}")

    # -------------------------------------------------------------
    # Global Refresh
    # -------------------------------------------------------------
    def refresh_all(self):
        self._build_kpi_cards()

        # Categories
        cats = InventoryRepository.get_categories(self.db)
        cur_cat = self.cat_filter.currentData()
        self.cat_filter.blockSignals(True)
        self.cat_filter.clear()
        self.cat_filter.addItem("All Categories", None)
        for c in cats:
            self.cat_filter.addItem(f"{c.name} ({c.code})", c.id)
        if cur_cat is not None:
            idx = self.cat_filter.findData(cur_cat)
            if idx >= 0:
                self.cat_filter.setCurrentIndex(idx)
        self.cat_filter.blockSignals(False)

        self.cat_table.setRowCount(len(cats))
        for r_idx, c in enumerate(cats):
            self.cat_table.setItem(r_idx, 0, QTableWidgetItem(c.code))
            self.cat_table.setItem(r_idx, 1, QTableWidgetItem(c.name))
            self.cat_table.setItem(r_idx, 2, QTableWidgetItem(str(len(c.items))))
            self.cat_table.setItem(r_idx, 3, QTableWidgetItem("Active" if c.is_active else "Inactive"))

        # Products
        self._filter_products()

        # Suppliers
        sups = InventoryRepository.get_suppliers(self.db)
        self.sup_table.setRowCount(len(sups))
        for r_idx, s in enumerate(sups):
            self.sup_table.setItem(r_idx, 0, QTableWidgetItem(str(s.id)))
            self.sup_table.setItem(r_idx, 1, QTableWidgetItem(s.supplier_code))
            self.sup_table.setItem(r_idx, 2, QTableWidgetItem(s.name))
            self.sup_table.setItem(r_idx, 3, QTableWidgetItem(s.contact_person or "-"))
            self.sup_table.setItem(r_idx, 4, QTableWidgetItem(s.phone or "-"))
            self.sup_table.setItem(r_idx, 5, QTableWidgetItem(s.email or "-"))
            self.sup_table.setItem(r_idx, 6, QTableWidgetItem(s.payment_terms))
            self.sup_table.setItem(r_idx, 7, QTableWidgetItem(s.status))

        # Purchase Orders
        pos = InventoryRepository.get_purchase_orders(self.db)
        self.po_table.setRowCount(len(pos))
        for r_idx, po in enumerate(pos):
            self.po_table.setItem(r_idx, 0, QTableWidgetItem(str(po.id)))
            self.po_table.setItem(r_idx, 1, QTableWidgetItem(po.po_number))
            self.po_table.setItem(r_idx, 2, QTableWidgetItem(str(po.order_date)))
            self.po_table.setItem(r_idx, 3, QTableWidgetItem(po.supplier.name if po.supplier else "-"))
            self.po_table.setItem(r_idx, 4, QTableWidgetItem(po.location.name if po.location else "-"))
            self.po_table.setItem(r_idx, 5, QTableWidgetItem(f"৳ {float(po.total_amount or 0):,.2f}"))
            self.po_table.setItem(r_idx, 6, QTableWidgetItem(po.status))

        # Purchases
        purs = InventoryRepository.get_purchases(self.db)
        self.pur_table.setRowCount(len(purs))
        for r_idx, p in enumerate(purs):
            vch = p.accounting_tx.voucher_no if p.accounting_tx else "-"
            self.pur_table.setItem(r_idx, 0, QTableWidgetItem(str(p.id)))
            self.pur_table.setItem(r_idx, 1, QTableWidgetItem(p.purchase_no))
            self.pur_table.setItem(r_idx, 2, QTableWidgetItem(str(p.purchase_date)))
            self.pur_table.setItem(r_idx, 3, QTableWidgetItem(p.supplier.name if p.supplier else "-"))
            self.pur_table.setItem(r_idx, 4, QTableWidgetItem(p.invoice_no or "-"))
            self.pur_table.setItem(r_idx, 5, QTableWidgetItem(f"৳ {float(p.total_amount or 0):,.2f}"))
            self.pur_table.setItem(r_idx, 6, QTableWidgetItem(p.payment_method))
            self.pur_table.setItem(r_idx, 7, QTableWidgetItem(vch))
            self.pur_table.setItem(r_idx, 8, QTableWidgetItem(p.status))

        # Location Stock Balances
        stocks = InventoryRepository.get_stock_levels(self.db)
        self.stock_table.setRowCount(len(stocks))
        for r_idx, st in enumerate(stocks):
            self.stock_table.setItem(r_idx, 0, QTableWidgetItem(st.location.code if st.location else "-"))
            self.stock_table.setItem(r_idx, 1, QTableWidgetItem(st.location.name if st.location else "-"))
            self.stock_table.setItem(r_idx, 2, QTableWidgetItem(st.item.item_code if st.item else "-"))
            self.stock_table.setItem(r_idx, 3, QTableWidgetItem(st.item.name if st.item else "-"))
            self.stock_table.setItem(r_idx, 4, QTableWidgetItem(str(st.quantity_on_hand)))
            self.stock_table.setItem(r_idx, 5, QTableWidgetItem(st.bin_shelf or "-"))

        # Adjustments
        adjs = InventoryRepository.get_adjustments(self.db)
        self.adj_table.setRowCount(len(adjs))
        for r_idx, a in enumerate(adjs):
            self.adj_table.setItem(r_idx, 0, QTableWidgetItem(a.adjustment_no))
            self.adj_table.setItem(r_idx, 1, QTableWidgetItem(str(a.adjustment_date)))
            self.adj_table.setItem(r_idx, 2, QTableWidgetItem(a.item.name if a.item else "-"))
            self.adj_table.setItem(r_idx, 3, QTableWidgetItem(a.adjustment_type))
            self.adj_table.setItem(r_idx, 4, QTableWidgetItem(f"{a.quantity_change:+d}"))
            self.adj_table.setItem(r_idx, 5, QTableWidgetItem(a.reason))

        # Transfers
        trfs = InventoryRepository.get_transfers(self.db)
        self.trf_table.setRowCount(len(trfs))
        for r_idx, t in enumerate(trfs):
            self.trf_table.setItem(r_idx, 0, QTableWidgetItem(t.transfer_no))
            self.trf_table.setItem(r_idx, 1, QTableWidgetItem(str(t.transfer_date)))
            self.trf_table.setItem(r_idx, 2, QTableWidgetItem(t.item.name if t.item else "-"))
            self.trf_table.setItem(r_idx, 3, QTableWidgetItem(t.from_location.name if t.from_location else "-"))
            self.trf_table.setItem(r_idx, 4, QTableWidgetItem(t.to_location.name if t.to_location else "-"))
            self.trf_table.setItem(r_idx, 5, QTableWidgetItem(str(t.quantity)))

        # Disposals / Sales
        disposals = InventoryRepository.get_disposals_sales(self.db)
        self.disposal_table.setRowCount(len(disposals))
        for r_idx, d in enumerate(disposals):
            vch = d.accounting_tx.voucher_no if d.accounting_tx else "-"
            self.disposal_table.setItem(r_idx, 0, QTableWidgetItem(d.reference_no))
            self.disposal_table.setItem(r_idx, 1, QTableWidgetItem(str(d.transaction_date)))
            self.disposal_table.setItem(r_idx, 2, QTableWidgetItem(d.record_type))
            self.disposal_table.setItem(r_idx, 3, QTableWidgetItem(d.item.name if d.item else "-"))
            self.disposal_table.setItem(r_idx, 4, QTableWidgetItem(str(d.quantity)))
            self.disposal_table.setItem(r_idx, 5, QTableWidgetItem(f"৳ {float(d.unit_price or 0):,.2f}"))
            self.disposal_table.setItem(r_idx, 6, QTableWidgetItem(f"৳ {float(d.total_amount or 0):,.2f}"))
            self.disposal_table.setItem(r_idx, 7, QTableWidgetItem(d.buyer_or_recipient or "-"))
            self.disposal_table.setItem(r_idx, 8, QTableWidgetItem(vch))

        # Fixed Assets
        self._filter_assets()

        # Low-Stock Alerts
        alerts = InventoryRepository.get_low_stock_alerts(self.db)
        self.alerts_table.setRowCount(len(alerts))
        for r_idx, al in enumerate(alerts):
            self.alerts_table.setItem(r_idx, 0, QTableWidgetItem(al["item_code"]))
            self.alerts_table.setItem(r_idx, 1, QTableWidgetItem(al["name"]))
            self.alerts_table.setItem(r_idx, 2, QTableWidgetItem(al["category"]))
            self.alerts_table.setItem(r_idx, 3, QTableWidgetItem(f"{al['quantity_in_stock']} {al['unit']}"))
            self.alerts_table.setItem(r_idx, 4, QTableWidgetItem(str(al["reorder_level"])))
            self.alerts_table.setItem(r_idx, 5, QTableWidgetItem(str(al["suggested_reorder_qty"])))
            self.alerts_table.setItem(r_idx, 6, QTableWidgetItem(al["supplier"]))
            sev = QTableWidgetItem(al["severity"])
            sev.setForeground(QColor("#DC2626"))
            self.alerts_table.setItem(r_idx, 7, sev)
