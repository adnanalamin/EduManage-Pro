"""
EduManage Pro - Advanced Library Management Unit Tests
Covers: Authors, Publishers, Categories, Shelves, Barcoded/QR BookCopies,
Members Sync, Issue/Renewal/Return, FIFO Reservations, Fines & Waivers,
Lost/Damaged Incidents, CR80 Cards & Barcode Label PDFs, Borrowing/Fine/Inventory
Reports, and Excel/CSV Book Import & Export using real DB records.
"""

import os
import tempfile
from datetime import date, timedelta

from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.library import (
    Book,
    BookCategory,
    BookCirculation,
    BookCopy,
    BookIncident,
    BookReservation,
    LibraryAuthor,
    LibraryFine,
    LibraryMember,
    LibraryPublisher,
    LibraryShelf,
)
from app.models.staff import Department, Staff, Teacher
from app.models.student import Student
from app.reports.library_card_pdf import LibraryCardGenerator
from app.reports.library_reports_pdf import LibraryReportsPDFGenerator
from app.repositories.library_repository import LibraryRepository
from app.services.library_service import LibraryService


def _setup_category(db_session):
    LibraryService.ensure_default_categories(db_session)
    return db_session.query(BookCategory).first()


def test_ensure_default_categories_no_demo_books(db_session):
    """Verify UI startup helper creates categories ONLY and zero demo books/loans."""
    added = LibraryService.ensure_default_categories(db_session)
    assert added >= 5
    assert db_session.query(Book).count() == 0
    assert db_session.query(BookCirculation).count() == 0


def test_authors_publishers_shelves_copies_and_barcode_qr_lookup(db_session):
    """Verify normalized Author/Publisher/Shelf creation, physical BookCopy barcodes, and QR lookup."""
    cat = _setup_category(db_session)
    shelf = LibraryRepository.create_shelf(
        db_session,
        shelf_code="SH-R10-B",
        rack_number="Rack 10",
        shelf_number="Shelf B",
        floor="2nd Floor",
        section_zone="STEM Wing",
        category_id=cat.id,
        capacity=120,
    )
    book = LibraryRepository.create_book(
        db_session,
        accession_no="ACC-ADV-1001",
        title="Algorithms Illuminated",
        author="Tim Roughgarden",
        publisher="Soundlikeyourself Publishing",
        isbn="978-0999282908",
        category_id=cat.id,
        shelf_id=shelf.id,
        total_copies=3,
        price=39.99,
    )

    assert book.author_id is not None
    assert book.publisher_id is not None
    assert book.shelf_id == shelf.id
    assert book.barcode is not None
    assert book.qr_payload is not None

    copies = LibraryRepository.get_book_copies(db_session, book.id)
    assert len(copies) == 3
    first_copy = copies[0]
    assert first_copy.copy_code == "ACC-ADV-1001-C01"

    # Lookup by physical copy barcode
    hit_copy = LibraryRepository.lookup_by_barcode_or_qr(db_session, first_copy.barcode)
    assert hit_copy is not None
    assert hit_copy["type"] == "copy"
    assert hit_copy["copy"].id == first_copy.id

    # Lookup by Book ISBN or QR payload
    hit_isbn = LibraryRepository.lookup_by_barcode_or_qr(db_session, "978-0999282908")
    assert hit_isbn is not None and hit_isbn["book"].id == book.id

    hit_qr = LibraryRepository.lookup_by_barcode_or_qr(db_session, book.qr_payload)
    assert hit_qr is not None and hit_qr["book"].id == book.id


def test_sync_real_school_members_and_qr_lookup(db_session):
    """Verify real Student/Teacher/Staff enrollment into LibraryMembers with QR/Barcodes."""
    ay = db_session.query(AcademicYear).first()
    if not ay:
        ay = AcademicYear(name="2026-2027", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
        db_session.add(ay)
        db_session.flush()
    cls = db_session.query(SchoolClass).first()
    if not cls:
        cls = SchoolClass(name="Class 9", code="C9-LIB", numeric_order=9, academic_year_id=ay.id)
        db_session.add(cls)
        db_session.flush()
    sec = db_session.query(Section).first()
    if not sec:
        sec = Section(name="Section A", class_id=cls.id)
        db_session.add(sec)
        db_session.flush()

    stu = Student(
        student_id="STU-LIB-01",
        admission_number="ADM-LIB-01",
        roll_number=1,
        first_name="Nadia",
        last_name="Rahman",
        full_name="Nadia Rahman",
        gender="Female",
        date_of_birth=date(2011, 4, 15),
        class_id=cls.id,
        section_id=sec.id,
        academic_year_id=ay.id,
    )
    db_session.add(stu)
    db_session.commit()

    dept = db_session.query(Department).first()
    if not dept:
        dept = Department(name="General", code="GEN-LIB")
        db_session.add(dept)
        db_session.flush()
    stf = Staff(
        staff_id="STF-LIB-01",
        employee_id="EMP-LIB-01",
        full_name="Hasan Mahmud",
        gender="Male",
        date_of_birth=date(1990, 2, 10),
        phone="01810000001",
        position="Librarian Assistant",
        department_id=dept.id,
    )
    db_session.add(stf)
    db_session.commit()

    res = LibraryRepository.sync_members_from_school(db_session)
    assert res["students"] >= 1
    assert res["staff"] >= 1

    mem = db_session.query(LibraryMember).filter(LibraryMember.student_id == stu.id).first()
    assert mem is not None
    assert mem.display_name == "Nadia Rahman"
    hit = LibraryRepository.lookup_by_barcode_or_qr(db_session, mem.qr_payload)
    assert hit is not None and hit["type"] == "member" and hit["member"].id == mem.id


def test_renewal_and_reservation_fifo_workflow(db_session):
    """Verify loan renewal limits, reservation hold queue, auto-promotion on return, and renewal blocking."""
    cat = _setup_category(db_session)
    book = LibraryRepository.create_book(
        db_session,
        accession_no="ACC-ADV-2002",
        title="Clean Architecture",
        author="Robert C. Martin",
        category_id=cat.id,
        total_copies=1,
        price=50.0,
    )
    m1 = LibraryRepository.create_member(
        db_session,
        member_id="LIB-MEM-A",
        member_type="Student",
        full_name_override="Patron One",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=3,
    )
    m2 = LibraryRepository.create_member(
        db_session,
        member_id="LIB-MEM-B",
        member_type="Student",
        full_name_override="Patron Two",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=3,
    )

    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=7)).isoformat()
    circ, err = LibraryRepository.issue_book(db_session, book.id, m1.id, today_str, due_str, max_renewals=2)
    assert err is None and circ is not None

    # Renew once cleanly
    new_due = (date.today() + timedelta(days=14)).isoformat()
    ren_circ, ren_err = LibraryRepository.renew_loan(db_session, circ.id, new_due, renewed_by="Admin")
    assert ren_err is None
    assert ren_circ.renewal_count == 1
    assert ren_circ.status == "Renewed"

    # Patron Two reserves the title while out on loan -> Pending
    res, res_err = LibraryRepository.create_reservation(db_session, book.id, m2.id, expiry_days=3)
    assert res_err is None
    assert res.status == "Pending"

    # Renewing again should now be blocked because another member reserved the book
    blocked, b_err = LibraryRepository.renew_loan(
        db_session, circ.id, (date.today() + timedelta(days=21)).isoformat()
    )
    assert blocked is None and "active reservation" in b_err

    # Returning the book should automatically promote Patron Two's reservation to Ready and hold the copy
    ret_circ, ret_err = LibraryRepository.return_book(db_session, circ.id, today_str)
    assert ret_err is None and ret_circ.status == "Returned"
    db_session.refresh(res)
    assert res.status == "Ready"
    assert res.copy_id == circ.copy_id

    # Patron One cannot steal the reserved copy; Patron Two can issue it and fulfill reservation
    deny, deny_err = LibraryRepository.issue_book(db_session, book.id, m1.id, today_str, due_str)
    assert deny is None and deny_err is not None

    fulfill, f_err = LibraryRepository.issue_book(db_session, book.id, m2.id, today_str, due_str)
    assert f_err is None and fulfill is not None
    db_session.refresh(res)
    assert res.status == "Fulfilled"


def test_fines_partial_payment_waiver_and_lost_damaged_incidents(db_session):
    """Verify Lost/Damaged book handling, Fine Ledger partial payment, waiver, and incident resolution."""
    cat = _setup_category(db_session)
    book = LibraryRepository.create_book(
        db_session,
        accession_no="ACC-ADV-3003",
        title="Discrete Mathematics",
        author="Kenneth Rosen",
        category_id=cat.id,
        total_copies=2,
        price=80.0,
    )
    member = LibraryRepository.create_member(
        db_session,
        member_id="LIB-MEM-FINE",
        member_type="Student",
        full_name_override="Fine Tester",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=3,
    )

    issue_d = (date.today() - timedelta(days=10)).isoformat()
    due_d = (date.today() - timedelta(days=4)).isoformat()
    today_d = date.today().isoformat()

    circ, err = LibraryRepository.issue_book(db_session, book.id, member.id, issue_d, due_d)
    assert err is None

    # Return Damaged with unpaid fine + damage fee
    ret, ret_err = LibraryRepository.return_book(
        db_session,
        circ.id,
        return_date=today_d,
        fine_rate_per_day=5.0,
        fine_paid=False,
        return_condition="Damaged",
        damage_fee=30.0,
        remarks="Torn cover pages",
    )
    assert ret_err is None
    assert ret.status == "Damaged"
    db_session.refresh(book)
    assert book.damaged_copies == 1
    assert book.available_copies == 1

    fines = LibraryRepository.get_fines(db_session, member_id=member.id)
    assert len(fines) == 2  # Overdue ($20) + Damaged ($30)
    dmg_fine = next(f for f in fines if f.fine_type == "Damaged")
    ovd_fine = next(f for f in fines if f.fine_type == "Overdue")

    # Partial then full payment on damage fine
    f_part, p_err = LibraryRepository.collect_fine_payment(db_session, dmg_fine.id, 10.0, payment_method="Cash")
    assert p_err is None and f_part.status == "Partial" and f_part.balance_due == 20.0
    f_full, p_err2 = LibraryRepository.collect_fine_payment(db_session, dmg_fine.id, 20.0, payment_method="Card")
    assert p_err2 is None and f_full.status == "Paid" and f_full.balance_due == 0.0

    # Waive overdue fine
    f_waived, w_err = LibraryRepository.waive_fine(db_session, ovd_fine.id, "First-time courtesy")
    assert w_err is None and f_waived.status == "Waived"

    # Resolve damaged incident as Repaired -> copy returns to Available
    incidents = LibraryRepository.get_incidents(db_session, incident_type="Damaged")
    assert len(incidents) >= 1
    resolved, r_err = LibraryRepository.resolve_book_incident(db_session, incidents[0].id, "Repaired", resolved_by="Binder")
    assert r_err is None and resolved.resolution_status == "Repaired"
    db_session.refresh(book)
    assert book.damaged_copies == 0
    assert book.available_copies == 2

    # Report a Lost book incident directly
    lost_inc, l_err = LibraryRepository.report_book_incident(
        db_session, book.id, "Lost", member_id=member.id, fine_assessed=80.0, description="Misplaced copy"
    )
    assert l_err is None and lost_inc.incident_type == "Lost"
    db_session.refresh(book)
    assert book.lost_copies == 1
    assert book.available_copies == 1


def test_import_export_and_printable_reports_and_cards(db_session):
    """Verify Excel/CSV book import & export, QR/Barcode Library Cards, and Borrowing/Fine/Inventory PDFs."""
    cat = _setup_category(db_session)
    book = LibraryRepository.create_book(
        db_session,
        accession_no="ACC-EXP-4004",
        title="Data Structures & Algorithms",
        author="Michael Goodrich",
        publisher="Wiley",
        category_id=cat.id,
        total_copies=2,
        price=60.0,
    )
    member = LibraryRepository.create_member(
        db_session,
        member_id="LIB-CARD-4004",
        member_type="Teacher",
        full_name_override="Dr. Ayesha Siddiqua",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=5,
    )
    circ, _ = LibraryRepository.issue_book(
        db_session,
        book.id,
        member.id,
        (date.today() - timedelta(days=8)).isoformat(),
        (date.today() - timedelta(days=2)).isoformat(),
    )
    LibraryRepository.return_book(db_session, circ.id, date.today().isoformat(), fine_rate_per_day=5.0, fine_paid=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Template + Import roundtrip
        tpl_path = os.path.join(tmpdir, "template.xlsx")
        LibraryService.export_import_template_excel(tpl_path)
        assert os.path.exists(tpl_path)

        imp_res = LibraryService.import_books_from_file(db_session, tpl_path)
        assert imp_res["imported"] == 1
        assert LibraryRepository.get_book_by_accession(db_session, "ACC-2026-0101") is not None

        # 2. Catalog CSV & Borrowing/Fine Excel
        csv_path = os.path.join(tmpdir, "catalog.csv")
        bh_xl = os.path.join(tmpdir, "history.xlsx")
        fn_xl = os.path.join(tmpdir, "fines.xlsx")
        LibraryService.export_catalog_csv(db_session, csv_path)
        LibraryService.export_borrowing_history_excel(db_session, bh_xl)
        LibraryService.export_fine_report_excel(db_session, fn_xl)
        assert os.path.getsize(csv_path) > 50
        assert os.path.getsize(bh_xl) > 1000
        assert os.path.getsize(fn_xl) > 1000

        # 3. Cards & Barcode Stickers PDFs
        single_card = os.path.join(tmpdir, "card.pdf")
        bulk_cards = os.path.join(tmpdir, "cards_batch.pdf")
        labels_pdf = os.path.join(tmpdir, "book_labels.pdf")
        LibraryCardGenerator.generate_single_card(member, None, single_card)
        LibraryCardGenerator.generate_bulk_cards_pdf([member], None, bulk_cards)
        LibraryCardGenerator.generate_book_barcodes_pdf(LibraryRepository.get_book_copies(db_session, book.id), None, labels_pdf)
        assert os.path.getsize(single_card) > 500
        assert os.path.getsize(bulk_cards) > 500
        assert os.path.getsize(labels_pdf) > 500

        # 4. Borrowing History, Fine, Inventory PDFs
        bh_pdf = os.path.join(tmpdir, "borrowing_history.pdf")
        fn_pdf = os.path.join(tmpdir, "fine_report.pdf")
        inv_pdf = os.path.join(tmpdir, "inventory_report.pdf")
        LibraryReportsPDFGenerator.generate_borrowing_history_pdf(
            LibraryRepository.get_circulations(db_session), "All Members", None, bh_pdf
        )
        LibraryReportsPDFGenerator.generate_fine_report_pdf(
            LibraryRepository.get_fines(db_session), None, fn_pdf
        )
        LibraryReportsPDFGenerator.generate_inventory_report_pdf(
            LibraryRepository.get_books(db_session),
            LibraryRepository.get_library_stats(db_session),
            None,
            inv_pdf,
        )
        assert os.path.getsize(bh_pdf) > 500
        assert os.path.getsize(fn_pdf) > 500
        assert os.path.getsize(inv_pdf) > 500
