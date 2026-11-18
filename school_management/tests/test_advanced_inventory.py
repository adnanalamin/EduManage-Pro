"""
EduManage Pro - Enterprise Inventory & Fixed Assets Unit Tests
Covers Categories, Products, Suppliers, Multi-Location Stock, Purchase Orders,
Purchases (with Accounting Expense integration & non-destructive cancellation reversal),
Stock Adjustments, Stock Transfers, Sales/Disposals (with Accounting Income on Sale),
Fixed Assets (all custody/warranty fields), Low-Stock Alerts, and PDF/Excel Reports.
"""

from datetime import date, timedelta
import os
import tempfile

import pytest
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  Ensure full metadata & FKs are registered
from app.database.connection import Base, create_database_engine
from app.models.accounting import AccountTransaction
from app.models.inventory import (
    ADJUSTMENT_TYPES,
    ASSET_STATUSES,
    DISPOSAL_SALE_TYPES,
    INVENTORY_ITEM_TYPES,
    PURCHASE_ORDER_STATUSES,
    InventoryCategory,
    InventoryItem,
    InventoryStock,
)
from app.models.school import SchoolSetting
from app.models.staff import Department
from app.reports.inventory_reports_pdf import InventoryReportsPDFGenerator
from app.repositories.inventory_repository import InventoryRepository
from app.services.accounting_service import AccountingService
from app.services.inventory_service import InventoryService


@pytest.fixture(scope="function")
def db_session(tmp_path):
    db_file = tmp_path / "inventory_test.db"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    AccountingService.seed_default_categories(session)
    yield session
    session.close()
    engine.dispose()


def test_catalog_suppliers_locations_and_stock_thresholds(db_session):
    """Verify categories, suppliers, locations, products, and automatic stock status calculation."""
    cat = InventoryRepository.create_category(
        db_session,
        name="Stationery & Exam Supplies",
        code="STAT",
        description="Paper, markers, and OMR sheets",
    )
    sup = InventoryRepository.create_supplier(
        db_session,
        name="Dhaka Academic Stationers Ltd.",
        contact_person="Rafiqul Islam",
        phone="01711002233",
        payment_terms="Net 15",
    )
    loc_main = InventoryRepository.create_location(
        db_session,
        name="Central Campus Store",
        code="STR-MAIN",
        location_type="Central Store",
        manager_name="Karim Mia",
    )
    assert cat.id is not None and sup.supplier_code.startswith("SUP-") and loc_main.id is not None

    # Opening stock > reorder_level -> In Stock
    p1 = InventoryRepository.create_product(
        db_session,
        item_code="PPR-A4",
        name="A4 Printing Paper Ream",
        category_id=cat.id,
        item_type="Consumable",
        unit="Ream",
        quantity_in_stock=25,
        reorder_level=10,
        max_stock_level=60,
        unit_cost=450.0,
        selling_price=500.0,
        preferred_supplier_id=sup.id,
        location_id=loc_main.id,
    )
    assert p1.status == "In Stock"

    # Opening stock <= reorder_level -> Low Stock
    p2 = InventoryRepository.create_product(
        db_session,
        item_code="MRK-BLK",
        name="Whiteboard Marker (Black)",
        category_id=cat.id,
        item_type="Consumable",
        unit="Box",
        quantity_in_stock=4,
        reorder_level=8,
        unit_cost=180.0,
        preferred_supplier_id=sup.id,
        location_id=loc_main.id,
    )
    assert p2.status == "Low Stock"

    alerts = InventoryRepository.get_low_stock_alerts(db_session)
    assert len(alerts) == 1
    assert alerts[0]["item_code"] == "MRK-BLK"
    assert alerts[0]["severity"] == "LOW STOCK"

    # Verify multi-location stock record created
    stocks = InventoryRepository.get_stock_levels(db_session, item_id=p1.id)
    assert len(stocks) == 1 and stocks[0].quantity_on_hand == 25


def test_purchase_order_purchase_accounting_and_reversal(db_session):
    """Verify PO -> Goods Purchase -> Accounting Expense posting & non-destructive cancellation reversal."""
    cat = InventoryRepository.create_category(db_session, "Science Lab Supplies", "LAB-SUP")
    sup = InventoryRepository.create_supplier(db_session, "Bengal Scientific Corp")
    loc = InventoryRepository.create_location(db_session, "Science Store Room", "STR-SCI")
    item = InventoryRepository.create_product(
        db_session,
        item_code="BKR-250",
        name="Borosilicate Beaker 250ml",
        category_id=cat.id,
        quantity_in_stock=2,
        reorder_level=10,
        unit_cost=200.0,
        preferred_supplier_id=sup.id,
        location_id=loc.id,
    )
    assert item.status == "Low Stock"

    po = InventoryRepository.create_purchase_order(
        db_session,
        supplier_id=sup.id,
        location_id=loc.id,
        lines=[{"item_id": item.id, "ordered_qty": 20, "unit_cost": 220.0}],
        status="Approved",
        created_by="store_officer",
    )
    assert po.po_number.startswith("PO-")
    assert po.total_amount == 4400.0

    # Receive Purchase linked to PO with Accounting Expense integration
    pur = InventoryRepository.record_purchase(
        db_session,
        supplier_id=sup.id,
        location_id=loc.id,
        purchase_order_id=po.id,
        invoice_no="INV-BSC-778",
        lines=[{"item_id": item.id, "quantity": 20, "unit_cost": 220.0}],
        payment_method="Bank",
        post_to_accounting=True,
        received_by="accountant",
    )
    assert pur.status == "Received"
    assert pur.accounting_tx_id is not None

    db_session.refresh(item)
    db_session.refresh(po)
    assert item.quantity_in_stock == 22
    assert item.status == "In Stock"
    assert float(item.unit_cost) == 220.0
    assert po.status == "Received"

    # Confirm linked AccountTransaction is an Expense under EXP-INV
    acc_tx = db_session.query(AccountTransaction).filter(AccountTransaction.id == pur.accounting_tx_id).first()
    assert acc_tx is not None
    assert acc_tx.type == "Expense"
    assert float(acc_tx.amount) == 4400.0
    assert acc_tx.is_reversed is False

    # Cancel Purchase -> must reverse stock & non-destructively reverse Accounting Expense
    cancelled = InventoryRepository.cancel_purchase(
        db_session,
        pur.id,
        reason="Damaged glassware batch returned to vendor",
        actor_username="admin",
    )
    assert cancelled.status == "Cancelled"
    db_session.refresh(item)
    db_session.refresh(acc_tx)
    assert item.quantity_in_stock == 2
    assert item.status == "Low Stock"
    assert acc_tx.is_reversed is True


def test_stock_adjustments_transfers_and_disposal_sales(db_session):
    """Verify signed stock adjustments, atomic inter-store transfers, and sales accounting income."""
    cat = InventoryRepository.create_category(db_session, "Uniform & Books", "UNI-BK")
    store_a = InventoryRepository.create_location(db_session, "Main Store", "STR-A")
    store_b = InventoryRepository.create_location(db_session, "Branch Counter", "STR-B")

    item = InventoryRepository.create_product(
        db_session,
        item_code="TIE-01",
        name="School Tie & Badge Set",
        category_id=cat.id,
        quantity_in_stock=50,
        reorder_level=5,
        unit_cost=100.0,
        selling_price=160.0,
        location_id=store_a.id,
    )

    # Transfer 15 units from store_a -> store_b
    trf = InventoryRepository.create_stock_transfer(
        db_session,
        item_id=item.id,
        from_location_id=store_a.id,
        to_location_id=store_b.id,
        quantity=15,
        transferred_by="store_keeper",
        received_by="branch_clerk",
    )
    assert trf.transfer_no.startswith("TRF-")

    # Attempting to transfer more than store_b balance must raise ValueError
    with pytest.raises(ValueError, match="Insufficient stock"):
        InventoryRepository.create_stock_transfer(
            db_session,
            item_id=item.id,
            from_location_id=store_b.id,
            to_location_id=store_a.id,
            quantity=99,
        )

    db_session.refresh(item)
    assert item.quantity_in_stock == 50  # Total preserved across warehouses
    st_a = db_session.query(InventoryStock).filter_by(item_id=item.id, location_id=store_a.id).first()
    st_b = db_session.query(InventoryStock).filter_by(item_id=item.id, location_id=store_b.id).first()
    assert st_a.quantity_on_hand == 35 and st_b.quantity_on_hand == 15

    # Stock adjustment (Damage / Write-Off at store_a)
    adj = InventoryRepository.record_stock_adjustment(
        db_session,
        item_id=item.id,
        adjustment_type="Damage / Write-Off",
        quantity_delta=5,  # repository coerces Damage / Write-Off to negative delta
        reason="Moisture damage in carton #3",
        location_id=store_a.id,
    )
    assert adj.quantity_change == -5
    assert adj.new_qty == 45

    # Sale at store_b -> deducts stock and posts Accounting Income under INC-INV
    sale = InventoryRepository.record_disposal_or_sale(
        db_session,
        item_id=item.id,
        record_type="Sale",
        quantity=10,
        unit_price=160.0,
        location_id=store_b.id,
        buyer_or_recipient="Class 8 Batch",
        payment_method="Cash",
        post_to_accounting=True,
    )
    assert sale.total_amount == 1600.0
    assert sale.accounting_tx_id is not None

    sale_tx = db_session.query(AccountTransaction).filter(AccountTransaction.id == sale.accounting_tx_id).first()
    assert sale_tx.type == "Income"
    assert float(sale_tx.amount) == 1600.0

    # Disposal at store_a -> deducts stock without posting Income
    disp = InventoryRepository.record_disposal_or_sale(
        db_session,
        item_id=item.id,
        record_type="Disposal",
        quantity=2,
        unit_price=0.0,
        location_id=store_a.id,
        reason="Obsolete crest design",
        post_to_accounting=True,
    )
    assert disp.accounting_tx_id is None
    db_session.refresh(item)
    assert item.quantity_in_stock == 33


def test_fixed_assets_custody_warranty_and_reports(db_session):
    """Verify FixedAsset full field coverage, employee assignment, warranty alerts, Excel & PDF reports."""
    dept = Department(name="ICT & Computer Lab", code="ICT")
    db_session.add(dept)
    db_session.flush()

    cat = InventoryRepository.create_category(db_session, "IT & Lab Equipment", "IT-EQ")
    sup = InventoryRepository.create_supplier(db_session, "Star Tech Systems")

    expiring_soon = date.today() + timedelta(days=15)
    asset = InventoryRepository.register_asset(
        db_session,
        asset_id="AST-2026-PC01",
        name="Workstation Core i7",
        category_id=cat.id,
        supplier_id=sup.id,
        serial_number="SN-DELL-998877",
        manufacturer="Dell",
        model_no="OptiPlex 7010",
        purchase_date=date(2026, 2, 10),
        cost=85000.0,
        salvage_value=8000.0,
        location="Computer Lab 2, 3rd Floor",
        department_id=dept.id,
        department_name=dept.name,
        assigned_employee="Tariq Mahmud (Lab Demonstrator)",
        warranty="3 Years On-Site",
        warranty_expiry_date=expiring_soon,
        status="Active",
        post_to_accounting=True,
        payment_method="Bank",
    )
    assert asset.asset_id == "AST-2026-PC01"
    assert asset.serial_number == "SN-DELL-998877"
    assert asset.purchase_date == date(2026, 2, 10)
    assert float(asset.cost) == 85000.0
    assert asset.location == "Computer Lab 2, 3rd Floor"
    assert asset.department_id == dept.id
    assert asset.assigned_employee == "Tariq Mahmud (Lab Demonstrator)"
    assert asset.warranty == "3 Years On-Site"
    assert asset.status == "Active"
    assert asset.accounting_tx_id is not None

    # Reassign employee custody -> promotes status from Active to In Use
    reassigned = InventoryRepository.assign_asset_to_employee(
        db_session,
        asset.id,
        assigned_employee="Farhana Yasmin (ICT Lecturer)",
        location="Smart Classroom 104",
    )
    assert reassigned.assigned_employee == "Farhana Yasmin (ICT Lecturer)"
    assert reassigned.status == "In Use"

    warranty_due = InventoryRepository.get_warranty_alerts(db_session, within_days=30)
    assert len(warranty_due) == 1 and warranty_due[0].asset_id == "AST-2026-PC01"

    # Also test stats, Accounting summary, Excel & PDF reports
    item = InventoryRepository.create_product(
        db_session,
        item_code="CHALK-01",
        name="Dustless Chalk Box",
        category_id=cat.id,
        quantity_in_stock=0,
        reorder_level=5,
        unit_cost=60.0,
    )
    assert item.status == "Out of Stock"

    stats = InventoryRepository.get_inventory_stats(db_session)
    assert stats["total_products"] == 1
    assert stats["low_stock_count"] == 1
    assert stats["out_of_stock_count"] == 1
    assert stats["total_assets"] == 1
    assert stats["asset_valuation"] == 85000.0

    acc_summary = InventoryService.get_accounting_expense_summary(db_session)
    assert acc_summary["total_asset_cost"] == 85000.0
    assert acc_summary["linked_asset_vouchers"] == 1

    school = db_session.query(SchoolSetting).first()
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "enterprise_inventory.xlsx")
        InventoryService.export_inventory_comprehensive_excel(db_session, xlsx_path)
        assert os.path.exists(xlsx_path) and os.path.getsize(xlsx_path) > 2000

        stock_pdf = os.path.join(tmpdir, "stock_alerts.pdf")
        InventoryReportsPDFGenerator.generate_stock_and_low_stock_report(
            InventoryRepository.get_products(db_session),
            InventoryRepository.get_low_stock_alerts(db_session),
            school=school,
            output_path=stock_pdf,
        )
        assert os.path.exists(stock_pdf) and os.path.getsize(stock_pdf) > 1000

        proc_pdf = os.path.join(tmpdir, "procurement.pdf")
        InventoryReportsPDFGenerator.generate_procurement_and_expense_report(
            InventoryRepository.get_purchase_orders(db_session),
            InventoryRepository.get_purchases(db_session),
            school=school,
            output_path=proc_pdf,
        )
        assert os.path.exists(proc_pdf) and os.path.getsize(proc_pdf) > 1000

        asset_pdf = os.path.join(tmpdir, "fixed_assets.pdf")
        InventoryReportsPDFGenerator.generate_fixed_asset_register_pdf(
            InventoryRepository.get_assets(db_session),
            school=school,
            output_path=asset_pdf,
        )
        assert os.path.exists(asset_pdf) and os.path.getsize(asset_pdf) > 1000
