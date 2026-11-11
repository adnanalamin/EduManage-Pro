"""
EduManage Pro - Library & Book Circulation Unit Tests
Phase 10: Cataloging, Issue Quotas, Overdue Fines, openpyxl Excel & ReportLab PDF
"""

import os
import tempfile
from datetime import date, timedelta
import pytest
from app.models.library import BookCategory, Book, LibraryMember, BookCirculation
from app.models.student import Student
from app.repositories.library_repository import LibraryRepository
from app.services.library_service import LibraryService
from app.reports.library_card_pdf import LibraryCardGenerator
from app.reports.circulation_report_pdf import CirculationReportPDFGenerator


def test_seed_library_categories_and_catalog(db_session):
    """Verify default book categories and curated book titles seed cleanly."""
    res = LibraryService.seed_default_library_data(db_session)
    assert res["categories_seeded"] >= 5 or db_session.query(BookCategory).count() >= 5
    assert db_session.query(Book).count() >= 10

    # Check category codes
    cs_cat = db_session.query(BookCategory).filter(BookCategory.code == "CS-ICT").first()
    assert cs_cat is not None
    assert len(cs_cat.books) > 0


def test_book_crud_and_copy_tracking(db_session):
    """Verify book creation, stock copy calculations, and editing."""
    cat = db_session.query(BookCategory).first()
    if not cat:
        cat = LibraryRepository.create_category(db_session, "Science & Nature", "SCI-NAT", "Nature studies")

    book = LibraryRepository.create_book(
        session=db_session,
        accession_no="ACC-TEST-9999",
        title="Python Deep Dive",
        author="Guido van Rossum",
        category_id=cat.id,
        rack_number="Rack 09",
        shelf_number="Shelf D",
        total_copies=5,
        price=45.0
    )
    assert book.id is not None
    assert book.available_copies == 5
    assert book.issued_copies == 0
    assert book.status == "Available"

    # Update total copies
    updated = LibraryRepository.update_book(db_session, book.id, total_copies=8)
    assert updated.total_copies == 8
    assert updated.available_copies == 8


def test_issue_book_and_quota_limit(db_session):
    """Verify book checkout, copy decrement, and loan quota rejection."""
    cat = db_session.query(BookCategory).first()
    book = LibraryRepository.create_book(
        session=db_session,
        accession_no="ACC-TEST-8888",
        title="Test Borrowing Rules",
        author="Author Test",
        category_id=cat.id,
        total_copies=1
    )

    member = LibraryRepository.create_member(
        session=db_session,
        member_id="LIB-TEST-001",
        member_type="Student",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=1,
        status="Active"
    )

    today_str = date.today().isoformat()
    due_str = (date.today() + timedelta(days=7)).isoformat()

    # Issue 1: Should succeed
    circ, err = LibraryRepository.issue_book(
        session=db_session,
        book_id=book.id,
        member_id=member.id,
        issue_date=today_str,
        due_date=due_str,
        issued_by="Chief Librarian"
    )
    assert err is None
    assert circ is not None
    assert circ.status == "Issued"

    # Refresh book - copies should be 0 and out of stock
    db_session.refresh(book)
    assert book.available_copies == 0
    assert book.issued_copies == 1
    assert book.status == "Out of Stock"

    # Attempt to issue the same book again - should fail (no copies)
    member_2 = LibraryRepository.create_member(
        session=db_session,
        member_id="LIB-TEST-002",
        member_type="Student",
        card_issue_date=today_str,
        max_allowed_books=3,
        status="Active"
    )
    circ2, err2 = LibraryRepository.issue_book(
        session=db_session,
        book_id=book.id,
        member_id=member_2.id,
        issue_date=today_str,
        due_date=due_str
    )
    assert circ2 is None
    assert "no copies currently available" in err2

    # Attempt to issue another book to member 1 who has max quota 1 - should fail (quota reached)
    book_2 = LibraryRepository.create_book(
        session=db_session,
        accession_no="ACC-TEST-7777",
        title="Second Book",
        author="Author Two",
        category_id=cat.id,
        total_copies=2
    )
    circ3, err3 = LibraryRepository.issue_book(
        session=db_session,
        book_id=book_2.id,
        member_id=member.id,
        issue_date=today_str,
        due_date=due_str
    )
    assert circ3 is None
    assert "maximum quota" in err3


def test_return_book_and_overdue_fines(db_session):
    """Verify check-in restores copy count and calculates overdue fine accurately."""
    cat = db_session.query(BookCategory).first()
    book = LibraryRepository.create_book(
        session=db_session,
        accession_no="ACC-TEST-6666",
        title="Overdue Fine Testing",
        author="Fine Author",
        category_id=cat.id,
        total_copies=2
    )
    member = LibraryRepository.create_member(
        session=db_session,
        member_id="LIB-TEST-003",
        member_type="Teacher",
        card_issue_date=date.today().isoformat(),
        max_allowed_books=5,
        status="Active"
    )

    # Issued 15 days ago, due 5 days ago
    issue_date = (date.today() - timedelta(days=15)).isoformat()
    due_date = (date.today() - timedelta(days=5)).isoformat()
    return_date = date.today().isoformat()

    circ, err = LibraryRepository.issue_book(
        session=db_session,
        book_id=book.id,
        member_id=member.id,
        issue_date=issue_date,
        due_date=due_date,
        issued_by="Chief Librarian"
    )
    assert err is None

    # Return book today (5 days overdue @ $5.00/day = $25.00)
    ret_circ, ret_err = LibraryRepository.return_book(
        session=db_session,
        circulation_id=circ.id,
        return_date=return_date,
        fine_rate_per_day=5.0,
        fine_paid=True,
        remarks="Paid $25 fine"
    )
    assert ret_err is None
    assert ret_circ.status == "Returned"
    assert ret_circ.fine_amount == 25.0
    assert ret_circ.fine_paid is True

    # Book available copies restored
    db_session.refresh(book)
    assert book.available_copies == 2
    assert book.issued_copies == 0


def test_openpyxl_catalog_export(db_session):
    """Verify Excel catalog audit export builds valid spreadsheet."""
    LibraryService.seed_default_library_data(db_session)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        out_path = tf.name

    try:
        saved_path = LibraryService.export_catalog_excel(db_session, out_path)
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_library_reports_pdf_generation(db_session):
    """Verify ReportLab printable CR80 library card and landscape A4 circulation audit PDFs."""
    LibraryService.seed_default_library_data(db_session)
    member = db_session.query(LibraryMember).first()
    assert member is not None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_card:
        card_path = tf_card.name

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_audit:
        audit_path = tf_audit.name

    try:
        # 1. CR80 Library Pass
        c_res = LibraryCardGenerator.generate_single_card(member, None, card_path)
        assert os.path.exists(c_res)
        assert os.path.getsize(c_res) > 500

        # 2. Circulation Audit Statement
        circs = LibraryRepository.get_circulations(db_session)
        stats = LibraryRepository.get_library_stats(db_session)
        a_res = CirculationReportPDFGenerator.generate_report(circs, stats, None, audit_path)
        assert os.path.exists(a_res)
        assert os.path.getsize(a_res) > 1000
    finally:
        if os.path.exists(card_path):
            os.remove(card_path)
        if os.path.exists(audit_path):
            os.remove(audit_path)
