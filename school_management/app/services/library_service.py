"""
EduManage Pro - Enterprise Library Service
Classification Presets, Book Import/Export (Excel & CSV),
Borrowing History, Fine & Inventory Report Exports.
"""

import csv
import os
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.models.library import (
    Book,
    BookCategory,
    BookCirculation,
    LibraryAuthor,
    LibraryFine,
    LibraryMember,
    LibraryPublisher,
    LibraryShelf,
)
from app.models.staff import Teacher
from app.models.student import Student
from app.repositories.library_repository import LibraryRepository


DEFAULT_CATEGORIES = [
    {"name": "Computer Science & ICT", "code": "CS-ICT", "ddc_code": "004", "description": "Programming, Algorithms, AI, Hardware and Networking"},
    {"name": "Mathematics & Physics", "code": "MATH-PHY", "ddc_code": "510", "description": "Calculus, Linear Algebra, Mechanics, Electromagnetism"},
    {"name": "General Science & Biology", "code": "SCI-BIO", "ddc_code": "570", "description": "Chemistry, Genetics, Ecology and General Science"},
    {"name": "English Literature & Grammar", "code": "ENG-LIT", "ddc_code": "820", "description": "Classic Novels, Poetry, English Grammar and Composition"},
    {"name": "Bangla Literature & Language", "code": "BAN-LIT", "ddc_code": "891.44", "description": "Nobel laureate works, prose, poetry and linguistics"},
    {"name": "World History & Social Sciences", "code": "HIST-SOC", "ddc_code": "900", "description": "Ancient civilization, Modern history, Economics & Geography"},
    {"name": "Reference & Encyclopedias", "code": "REF-ENC", "ddc_code": "030", "description": "Dictionaries, Atlases, Yearbooks and Research Handbooks"},
]

DEFAULT_BOOKS = [
    {
        "accession_no": "ACC-2026-0001",
        "title": "Introduction to Algorithms (4th Edition)",
        "author": "Thomas H. Cormen, Charles E. Leiserson",
        "publisher": "MIT Press",
        "isbn": "978-0262046305",
        "edition": "4th Edition",
        "publication_year": 2022,
        "category_code": "CS-ICT",
        "rack_number": "Rack 01",
        "shelf_number": "Shelf A",
        "total_copies": 5,
        "price": 85.00,
    },
    {
        "accession_no": "ACC-2026-0002",
        "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
        "author": "Robert C. Martin",
        "publisher": "Prentice Hall",
        "isbn": "978-0132350884",
        "edition": "1st Edition",
        "publication_year": 2008,
        "category_code": "CS-ICT",
        "rack_number": "Rack 01",
        "shelf_number": "Shelf B",
        "total_copies": 4,
        "price": 42.50,
    },
    {
        "accession_no": "ACC-2026-0003",
        "title": "University Physics with Modern Physics",
        "author": "Hugh D. Young, Roger A. Freedman",
        "publisher": "Pearson",
        "isbn": "978-0135159552",
        "edition": "15th Edition",
        "publication_year": 2019,
        "category_code": "MATH-PHY",
        "rack_number": "Rack 02",
        "shelf_number": "Shelf A",
        "total_copies": 6,
        "price": 95.00,
    },
    {
        "accession_no": "ACC-2026-0004",
        "title": "Calculus: Early Transcendentals",
        "author": "James Stewart",
        "publisher": "Cengage Learning",
        "isbn": "978-1305272378",
        "edition": "8th Edition",
        "publication_year": 2015,
        "category_code": "MATH-PHY",
        "rack_number": "Rack 02",
        "shelf_number": "Shelf C",
        "total_copies": 8,
        "price": 78.00,
    },
    {
        "accession_no": "ACC-2026-0005",
        "title": "Campbell Biology (12th Edition)",
        "author": "Lisa A. Urry, Michael L. Cain",
        "publisher": "Pearson",
        "isbn": "978-0135188743",
        "edition": "12th Edition",
        "publication_year": 2020,
        "category_code": "SCI-BIO",
        "rack_number": "Rack 03",
        "shelf_number": "Shelf A",
        "total_copies": 5,
        "price": 110.00,
    },
    {
        "accession_no": "ACC-2026-0006",
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "publisher": "J. B. Lippincott & Co.",
        "isbn": "978-0060935467",
        "edition": "50th Anniversary Ed.",
        "publication_year": 1960,
        "category_code": "ENG-LIT",
        "rack_number": "Rack 04",
        "shelf_number": "Shelf A",
        "total_copies": 7,
        "price": 18.00,
    },
    {
        "accession_no": "ACC-2026-0007",
        "title": "1984 & Animal Farm Special Collection",
        "author": "George Orwell",
        "publisher": "Secker & Warburg",
        "isbn": "978-0451524935",
        "edition": "Classic Edition",
        "publication_year": 1949,
        "category_code": "ENG-LIT",
        "rack_number": "Rack 04",
        "shelf_number": "Shelf B",
        "total_copies": 6,
        "price": 22.00,
    },
    {
        "accession_no": "ACC-2026-0008",
        "title": "Shesher Kobita (The Last Poem)",
        "author": "Rabindranath Tagore",
        "publisher": "Visva-Bharati",
        "isbn": "978-8172153578",
        "edition": "Centenary Edition",
        "publication_year": 1929,
        "category_code": "BAN-LIT",
        "rack_number": "Rack 05",
        "shelf_number": "Shelf A",
        "total_copies": 10,
        "price": 12.00,
    },
    {
        "accession_no": "ACC-2026-0009",
        "title": "A Brief History of Humankind (Sapiens)",
        "author": "Yuval Noah Harari",
        "publisher": "Harper",
        "isbn": "978-0062316097",
        "edition": "1st Edition",
        "publication_year": 2015,
        "category_code": "HIST-SOC",
        "rack_number": "Rack 06",
        "shelf_number": "Shelf A",
        "total_copies": 6,
        "price": 26.00,
    },
    {
        "accession_no": "ACC-2026-0010",
        "title": "Oxford Advanced Learner's Dictionary (10th Edition)",
        "author": "A. S. Hornby",
        "publisher": "Oxford University Press",
        "isbn": "978-0194798488",
        "edition": "10th Edition",
        "publication_year": 2020,
        "category_code": "REF-ENC",
        "rack_number": "Rack 07",
        "shelf_number": "Shelf A",
        "total_copies": 4,
        "price": 55.00,
    },
]


class LibraryService:
    """High-level business service for Library Catalog, Import/Export, Reports, and Testing Helpers."""

    @staticmethod
    def ensure_default_categories(session: Session) -> int:
        """Creates baseline classification categories ONLY when book_categories is empty."""
        if session.query(BookCategory).count() > 0:
            return 0
        count = 0
        for c_data in DEFAULT_CATEGORIES:
            cat = BookCategory(
                name=c_data["name"],
                code=c_data["code"],
                ddc_code=c_data.get("ddc_code"),
                description=c_data.get("description"),
            )
            session.add(cat)
            count += 1
        session.commit()
        return count

    @staticmethod
    def seed_default_library_data(session: Session) -> Dict[str, int]:
        """
        Seeds categories, sample book titles, members, and sample loans idempotently.
        Preserved for automated tests and explicit CLI/dev seeding only; not invoked automatically by UI.
        """
        cat_count = 0
        book_count = 0
        member_count = 0
        circ_count = 0

        cat_map: Dict[str, int] = {}
        for c_data in DEFAULT_CATEGORIES:
            existing = session.query(BookCategory).filter(BookCategory.code == c_data["code"]).first()
            if not existing:
                cat = BookCategory(
                    name=c_data["name"],
                    code=c_data["code"],
                    ddc_code=c_data.get("ddc_code"),
                    description=c_data.get("description"),
                )
                session.add(cat)
                session.commit()
                session.refresh(cat)
                cat_map[c_data["code"]] = cat.id
                cat_count += 1
            else:
                cat_map[c_data["code"]] = existing.id

        for b_data in DEFAULT_BOOKS:
            existing_book = session.query(Book).filter(Book.accession_no == b_data["accession_no"]).first()
            if not existing_book:
                cat_id = cat_map.get(b_data["category_code"])
                if not cat_id:
                    continue
                LibraryRepository.create_book(
                    session,
                    accession_no=b_data["accession_no"],
                    title=b_data["title"],
                    author=b_data["author"],
                    publisher=b_data.get("publisher"),
                    isbn=b_data.get("isbn"),
                    edition=b_data.get("edition"),
                    publication_year=b_data.get("publication_year"),
                    category_id=cat_id,
                    rack_number=b_data.get("rack_number"),
                    shelf_number=b_data.get("shelf_number"),
                    total_copies=b_data["total_copies"],
                    price=b_data.get("price", 0.0),
                )
                book_count += 1

        students = session.query(Student).order_by(Student.id.asc()).limit(5).all()
        teachers = session.query(Teacher).order_by(Teacher.id.asc()).limit(3).all()
        today_str = date.today().isoformat()

        for idx, std in enumerate(students):
            m_code = f"LIB-STD-{1001 + idx}"
            if not session.query(LibraryMember).filter(LibraryMember.member_id == m_code).first():
                LibraryRepository.create_member(
                    session,
                    member_id=m_code,
                    member_type="Student",
                    student_id=std.id,
                    card_issue_date=today_str,
                    max_allowed_books=3,
                    status="Active",
                )
                member_count += 1

        for idx, tch in enumerate(teachers):
            m_code = f"LIB-FAC-{2001 + idx}"
            if not session.query(LibraryMember).filter(LibraryMember.member_id == m_code).first():
                LibraryRepository.create_member(
                    session,
                    member_id=m_code,
                    member_type="Teacher",
                    teacher_id=tch.id,
                    card_issue_date=today_str,
                    max_allowed_books=5,
                    status="Active",
                )
                member_count += 1

        existing_circs = session.query(BookCirculation).count()
        if existing_circs == 0:
            all_members = session.query(LibraryMember).all()
            all_books = session.query(Book).all()

            if len(all_members) >= 2 and len(all_books) >= 3:
                due_in_7_days = (date.today() + timedelta(days=7)).isoformat()
                LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[0].id,
                    member_id=all_members[0].id,
                    issue_date=today_str,
                    due_date=due_in_7_days,
                    issued_by="Librarian",
                    remarks="Reference loan for mid-term study",
                )
                circ_count += 1

                past_issue = (date.today() - timedelta(days=20)).isoformat()
                past_due = (date.today() - timedelta(days=6)).isoformat()
                c2, _ = LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[1].id,
                    member_id=all_members[1].id,
                    issue_date=past_issue,
                    due_date=past_due,
                    issued_by="Librarian",
                    remarks="Overdue loan check",
                )
                if c2:
                    c2.status = "Overdue"
                    session.commit()
                    circ_count += 1

                past_issue_3 = (date.today() - timedelta(days=14)).isoformat()
                past_due_3 = (date.today() - timedelta(days=4)).isoformat()
                c3, _ = LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[2].id,
                    member_id=all_members[0].id,
                    issue_date=past_issue_3,
                    due_date=past_due_3,
                    issued_by="Librarian",
                    remarks="Returned past deadline",
                )
                if c3:
                    LibraryRepository.return_book(
                        session=session,
                        circulation_id=c3.id,
                        return_date=today_str,
                        fine_rate_per_day=5.0,
                        fine_paid=True,
                        remarks="Fine received in cash.",
                    )
                    circ_count += 1

        return {
            "categories_seeded": cat_count,
            "books_seeded": book_count,
            "members_seeded": member_count,
            "circulations_seeded": circ_count,
        }

    # ---------------- Excel Styling Helper ----------------
    @staticmethod
    def _style_worksheet(ws, title: str, subtitle: str, headers: List[str], header_color: str = "065F46"):
        header_fill = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=15, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        ws["A1"] = title
        ws["A1"].font = title_font
        ws["A2"] = subtitle
        ws["A2"].font = sub_font

        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
        ws.row_dimensions[4].height = 25
        return thin_border

    @staticmethod
    def _autofit_columns(ws):
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    # ---------------- Catalog Import / Export ----------------
    @staticmethod
    def export_catalog_excel(session: Session, output_path: str) -> str:
        """Exports complete book catalog to formatted openpyxl Excel spreadsheet."""
        books = LibraryRepository.get_books(session)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Book Catalog"

        headers = [
            "Accession No",
            "Title",
            "Author",
            "Publisher",
            "Category",
            "ISBN",
            "Barcode",
            "Call No",
            "Edition",
            "Year",
            "Rack",
            "Shelf",
            "Total Copies",
            "Available",
            "Issued",
            "Damaged",
            "Lost",
            "Unit Price",
            "Status",
        ]
        thin_border = LibraryService._style_worksheet(
            ws,
            "EDUMANAGE PRO - LIBRARY CATALOG & INVENTORY AUDIT",
            f"Generated on: {date.today().strftime('%B %d, %Y')} | Real Database Records ({len(books)} Titles)",
            headers,
            header_color="1E3A8A",
        )
        data_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)

        row_num = 4
        for b in books:
            row_num += 1
            vals = [
                b.accession_no,
                b.title,
                b.author,
                b.publisher or "-",
                b.category.name if b.category else "N/A",
                b.isbn or "-",
                b.barcode or "-",
                b.call_number or "-",
                b.edition or "-",
                b.publication_year or "-",
                b.rack_number or "-",
                b.shelf_number or "-",
                b.total_copies or 0,
                b.available_copies or 0,
                b.issued_copies or 0,
                b.damaged_copies or 0,
                b.lost_copies or 0,
                float(b.price or 0.0),
                b.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws.cell(row=row_num, column=c_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                if c_idx == 18:
                    cell.number_format = "#,##0.00"

        row_num += 1
        ws.cell(row=row_num, column=1, value="TOTAL SUMMARY").font = bold_font
        ws.cell(row=row_num, column=13, value=sum(b.total_copies or 0 for b in books)).font = bold_font
        ws.cell(row=row_num, column=14, value=sum(b.available_copies or 0 for b in books)).font = bold_font
        ws.cell(row=row_num, column=15, value=sum(b.issued_copies or 0 for b in books)).font = bold_font
        ws.cell(row=row_num, column=16, value=sum(b.damaged_copies or 0 for b in books)).font = bold_font
        ws.cell(row=row_num, column=17, value=sum(b.lost_copies or 0 for b in books)).font = bold_font
        ws.cell(row=row_num, column=18, value=round(sum(float(b.price or 0.0) * (b.total_copies or 0) for b in books), 2)).font = bold_font

        sum_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = sum_fill
            cell.border = thin_border

        LibraryService._autofit_columns(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_catalog_csv(session: Session, output_path: str) -> str:
        """Exports the book catalog to UTF-8 CSV."""
        books = LibraryRepository.get_books(session)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        headers = [
            "accession_no", "title", "author", "publisher", "category", "isbn",
            "edition", "publication_year", "language", "pages", "call_number",
            "rack_number", "shelf_number", "total_copies", "available_copies",
            "issued_copies", "damaged_copies", "lost_copies", "price", "barcode", "status",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for b in books:
                writer.writerow([
                    b.accession_no,
                    b.title,
                    b.author,
                    b.publisher or "",
                    b.category.name if b.category else "",
                    b.isbn or "",
                    b.edition or "",
                    b.publication_year or "",
                    b.language or "",
                    b.pages or "",
                    b.call_number or "",
                    b.rack_number or "",
                    b.shelf_number or "",
                    b.total_copies or 0,
                    b.available_copies or 0,
                    b.issued_copies or 0,
                    b.damaged_copies or 0,
                    b.lost_copies or 0,
                    float(b.price or 0.0),
                    b.barcode or "",
                    b.status,
                ])
        return output_path

    @staticmethod
    def export_import_template_excel(output_path: str) -> str:
        """Creates a clean Excel template for bulk Book Catalog import."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Book Import Template"
        headers = [
            "accession_no", "title", "author", "publisher", "category",
            "isbn", "edition", "publication_year", "language", "pages",
            "call_number", "rack_number", "shelf_number", "total_copies", "price", "description",
        ]
        header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        for idx, h in enumerate(headers, 1):
            c = ws.cell(row=1, column=idx, value=h)
            c.fill = header_fill
            c.font = header_font
        ws.append([
            "ACC-2026-0101", "Physics Principles", "H. C. Verma", "Bharati Bhawan",
            "Mathematics & Physics", "978-8177091878", "1st Edition", 2023,
            "English", 460, "530.1 VER", "Rack 02", "Shelf A", 3, 28.50, "Core reference textbook",
        ])
        LibraryService._autofit_columns(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def _parse_import_rows(file_path: str) -> List[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        rows: List[Dict[str, Any]] = []
        if ext == ".csv":
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    rows.append({(k or "").strip().lower().replace(" ", "_"): v for k, v in row.items() if k})
        elif ext in (".xlsx", ".xlsm"):
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            # Detect header row (row 1 or row 4 if exported from catalog)
            header_row_idx = 1
            for r_idx in range(1, min(6, ws.max_row + 1)):
                vals = [str(ws.cell(r_idx, c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
                if "title" in vals and any("accession" in v for v in vals):
                    header_row_idx = r_idx
                    break
            raw_headers = [
                str(ws.cell(header_row_idx, c).value or "").strip().lower().replace(" ", "_")
                for c in range(1, ws.max_column + 1)
            ]
            for r_idx in range(header_row_idx + 1, ws.max_row + 1):
                item: Dict[str, Any] = {}
                non_empty = False
                for c_idx, h in enumerate(raw_headers, 1):
                    if not h:
                        continue
                    v = ws.cell(r_idx, c_idx).value
                    if v is not None and str(v).strip() != "":
                        non_empty = True
                    item[h] = v
                if non_empty:
                    first_val = str(item.get(raw_headers[0], "") or "").upper()
                    if first_val.startswith("TOTAL"):
                        continue
                    rows.append(item)
        else:
            raise ValueError(f"Unsupported import format '{ext}'. Please use .xlsx or .csv.")
        return rows

    @staticmethod
    def import_books_from_file(
        session: Session,
        file_path: str,
        update_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Imports book titles from Excel (.xlsx) or CSV (.csv) into the database,
        automatically resolving/creating categories, authors, publishers, shelves, and barcoded copies.
        """
        rows = LibraryService._parse_import_rows(file_path)
        imported = 0
        updated = 0
        skipped = 0
        errors: List[str] = []

        # Ensure at least one fallback category exists
        LibraryService.ensure_default_categories(session)
        default_cat = session.query(BookCategory).first()

        for idx, row in enumerate(rows, start=1):
            try:
                title = str(row.get("title") or row.get("book_title") or "").strip()
                author = str(row.get("author") or row.get("author(s)") or "Unknown Author").strip()
                accession = str(row.get("accession_no") or row.get("accession") or "").strip()
                if not title:
                    skipped += 1
                    errors.append(f"Row {idx}: Missing book title.")
                    continue
                if not accession:
                    accession = f"ACC-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"

                cat_name = str(row.get("category") or row.get("category_name") or "").strip()
                cat_obj = None
                if cat_name:
                    cat_obj = (
                        session.query(BookCategory)
                        .filter((BookCategory.name.ilike(cat_name)) | (BookCategory.code.ilike(cat_name)))
                        .first()
                    )
                    if not cat_obj:
                        code_clean = LibraryRepository._clean_code(cat_name, 10)
                        while session.query(BookCategory).filter(BookCategory.code == code_clean).first():
                            code_clean = f"{code_clean[:6]}-{uuid.uuid4().hex[:3].upper()}"
                        cat_obj = LibraryRepository.create_category(session, name=cat_name, code=code_clean)
                if not cat_obj:
                    cat_obj = default_cat

                pub_val = str(row.get("publisher") or "").strip() or None
                isbn_val = str(row.get("isbn") or "").strip() or None
                edition_val = str(row.get("edition") or "").strip() or None
                call_no = str(row.get("call_no") or row.get("call_number") or "").strip() or None
                language_val = str(row.get("language") or "English").strip()
                rack_val = str(row.get("rack") or row.get("rack_number") or "").strip() or None
                shelf_val = str(row.get("shelf") or row.get("shelf_number") or "").strip() or None
                desc_val = str(row.get("description") or "").strip() or None

                def _to_int(v, default=None):
                    try:
                        if v is None or str(v).strip() in ("", "-"):
                            return default
                        return int(float(v))
                    except Exception:
                        return default

                def _to_float(v, default=0.0):
                    try:
                        if v is None or str(v).strip() in ("", "-"):
                            return default
                        return float(str(v).replace("$", "").replace(",", "").strip())
                    except Exception:
                        return default

                pub_year = _to_int(row.get("publication_year") or row.get("year"))
                pages = _to_int(row.get("pages"))
                total_copies = max(1, _to_int(row.get("total_copies"), 1) or 1)
                price = _to_float(row.get("price") or row.get("unit_price"), 0.0)

                existing = LibraryRepository.get_book_by_accession(session, accession)
                if existing:
                    if update_existing:
                        LibraryRepository.update_book(
                            session,
                            existing.id,
                            title=title,
                            author=author,
                            publisher=pub_val,
                            category_id=cat_obj.id,
                            isbn=isbn_val,
                            edition=edition_val,
                            publication_year=pub_year,
                            language=language_val,
                            pages=pages,
                            call_number=call_no,
                            rack_number=rack_val,
                            shelf_number=shelf_val,
                            total_copies=total_copies,
                            price=price,
                            description=desc_val,
                        )
                        updated += 1
                    else:
                        skipped += 1
                    continue

                LibraryRepository.create_book(
                    session,
                    accession_no=accession,
                    title=title,
                    author=author,
                    publisher=pub_val,
                    category_id=cat_obj.id,
                    isbn=isbn_val,
                    edition=edition_val,
                    publication_year=pub_year,
                    language=language_val,
                    pages=pages,
                    call_number=call_no,
                    rack_number=rack_val,
                    shelf_number=shelf_val,
                    total_copies=total_copies,
                    price=price,
                    description=desc_val,
                )
                imported += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"Row {idx}: {str(exc)}")

        return {"imported": imported, "updated": updated, "skipped": skipped, "errors": errors}

    # ---------------- Specialized Report Excel Exports ----------------
    @staticmethod
    def export_borrowing_history_excel(
        session: Session,
        output_path: str,
        member_id: Optional[int] = None,
        book_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        circs = LibraryRepository.get_circulations(
            session, member_id=member_id, book_id=book_id, date_from=date_from, date_to=date_to
        )
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Borrowing History"
        headers = [
            "Loan ID", "Accession No", "Copy Code", "Book Title",
            "Member ID", "Borrower Name", "Type", "Issue Date",
            "Due Date", "Return Date", "Renewals", "Fine", "Status",
        ]
        border = LibraryService._style_worksheet(
            ws,
            "EDUMANAGE PRO - LIBRARY BORROWING HISTORY REPORT",
            f"Generated on: {date.today().strftime('%B %d, %Y')} | Total Transactions: {len(circs)}",
            headers,
            header_color="065F46",
        )
        for r_idx, c in enumerate(circs, start=5):
            vals = [
                f"#{c.id:04d}",
                c.book.accession_no if c.book else "-",
                c.copy.copy_code if c.copy else "-",
                c.book.title if c.book else "-",
                c.member.member_id if c.member else "-",
                c.member.display_name if c.member else "-",
                c.member.member_type if c.member else "-",
                c.issue_date,
                c.due_date,
                c.return_date or "-",
                c.renewal_count or 0,
                float((c.fine_amount or 0.0) + (c.damage_or_lost_fee or 0.0)),
                c.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=v)
                cell.border = border
        LibraryService._autofit_columns(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_fine_report_excel(
        session: Session,
        output_path: str,
        status: Optional[str] = None,
        fine_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        fines = LibraryRepository.get_fines(
            session, status=status, fine_type=fine_type, date_from=date_from, date_to=date_to
        )
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Fine Report"
        headers = [
            "Fine Code", "Assessed Date", "Member ID", "Borrower Name",
            "Book Title", "Fine Type", "Assessed", "Paid", "Waived",
            "Balance Due", "Paid Date", "Method", "Receipt No", "Status",
        ]
        border = LibraryService._style_worksheet(
            ws,
            "EDUMANAGE PRO - LIBRARY FINE & RECOVERY REPORT",
            f"Generated on: {date.today().strftime('%B %d, %Y')} | Fine Records: {len(fines)}",
            headers,
            header_color="7C3AED",
        )
        for r_idx, f in enumerate(fines, start=5):
            vals = [
                f.fine_code,
                f.assessed_date,
                f.member.member_id if f.member else "-",
                f.member.display_name if f.member else "-",
                f.book.title if f.book else "-",
                f.fine_type,
                float(f.amount or 0.0),
                float(f.paid_amount or 0.0),
                float(f.waived_amount or 0.0),
                f.balance_due,
                f.paid_date or "-",
                f.payment_method or "-",
                f.receipt_no or "-",
                f.status,
            ]
            for c_idx, v in enumerate(vals, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=v)
                cell.border = border
        LibraryService._autofit_columns(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_inventory_report_excel(session: Session, output_path: str) -> str:
        return LibraryService.export_catalog_excel(session, output_path)
