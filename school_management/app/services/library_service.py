"""
EduManage Pro - Library Service
Phase 10: Library Catalog Seeding, Inventory Excel Export, Circulation Logic
"""

import os
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.library import BookCategory, Book, LibraryMember, BookCirculation
from app.models.student import Student
from app.models.staff import Teacher
from app.repositories.library_repository import LibraryRepository


DEFAULT_CATEGORIES = [
    {"name": "Computer Science & ICT", "code": "CS-ICT", "description": "Programming, Algorithms, AI, Hardware and Networking"},
    {"name": "Mathematics & Physics", "code": "MATH-PHY", "description": "Calculus, Linear Algebra, Mechanics, Electromagnetism"},
    {"name": "General Science & Biology", "code": "SCI-BIO", "description": "Chemistry, Genetics, Ecology and General Science"},
    {"name": "English Literature & Grammar", "code": "ENG-LIT", "description": "Classic Novels, Poetry, English Grammar and Composition"},
    {"name": "Bangla Literature & Language", "code": "BAN-LIT", "description": "Nobel laureate works, prose, poetry and linguistics"},
    {"name": "World History & Social Sciences", "code": "HIST-SOC", "description": "Ancient civilization, Modern history, Economics & Geography"},
    {"name": "Reference & Encyclopedias", "code": "REF-ENC", "description": "Dictionaries, Atlases, Yearbooks and Research Handbooks"},
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
    """High-level business service for Library Catalog, Seeding, and Reports."""

    @staticmethod
    def seed_default_library_data(session: Session) -> Dict[str, int]:
        """Seeds categories, book titles, library members, and initial loans idempotently."""
        cat_count = 0
        book_count = 0
        member_count = 0
        circ_count = 0

        # 1. Categories
        cat_map = {}
        for c_data in DEFAULT_CATEGORIES:
            existing = session.query(BookCategory).filter(BookCategory.code == c_data["code"]).first()
            if not existing:
                cat = BookCategory(
                    name=c_data["name"],
                    code=c_data["code"],
                    description=c_data.get("description")
                )
                session.add(cat)
                session.commit()
                session.refresh(cat)
                cat_map[c_data["code"]] = cat.id
                cat_count += 1
            else:
                cat_map[c_data["code"]] = existing.id

        # 2. Books
        for b_data in DEFAULT_BOOKS:
            existing_book = session.query(Book).filter(Book.accession_no == b_data["accession_no"]).first()
            if not existing_book:
                cat_id = cat_map.get(b_data["category_code"])
                if not cat_id:
                    continue
                book = Book(
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
                    available_copies=b_data["total_copies"],
                    issued_copies=0,
                    lost_copies=0,
                    price=b_data.get("price", 0.0),
                    status="Available"
                )
                session.add(book)
                session.commit()
                book_count += 1

        # 3. Members (Attach to sample students & teachers if available)
        students = session.query(Student).order_by(Student.id.asc()).limit(5).all()
        teachers = session.query(Teacher).order_by(Teacher.id.asc()).limit(3).all()

        today_str = date.today().isoformat()

        # Seed student members
        for idx, std in enumerate(students):
            m_code = f"LIB-STD-{1001 + idx}"
            existing_m = session.query(LibraryMember).filter(LibraryMember.member_id == m_code).first()
            if not existing_m:
                m = LibraryMember(
                    member_id=m_code,
                    member_type="Student",
                    student_id=std.id,
                    card_issue_date=today_str,
                    max_allowed_books=3,
                    status="Active"
                )
                session.add(m)
                session.commit()
                member_count += 1

        # Seed teacher members
        for idx, tch in enumerate(teachers):
            m_code = f"LIB-FAC-{2001 + idx}"
            existing_m = session.query(LibraryMember).filter(LibraryMember.member_id == m_code).first()
            if not existing_m:
                m = LibraryMember(
                    member_id=m_code,
                    member_type="Teacher",
                    teacher_id=tch.id,
                    card_issue_date=today_str,
                    max_allowed_books=5,
                    status="Active"
                )
                session.add(m)
                session.commit()
                member_count += 1

        # 4. Seed sample circulation transactions if none exist
        existing_circs = session.query(BookCirculation).count()
        if existing_circs == 0:
            all_members = session.query(LibraryMember).all()
            all_books = session.query(Book).all()

            if len(all_members) >= 2 and len(all_books) >= 3:
                # Issue 1: Normal active loan
                due_in_7_days = (date.today() + timedelta(days=7)).isoformat()
                LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[0].id,
                    member_id=all_members[0].id,
                    issue_date=today_str,
                    due_date=due_in_7_days,
                    issued_by="Chief Librarian",
                    remarks="Reference loan for mid-term study"
                )
                circ_count += 1

                # Issue 2: Overdue loan (issued 20 days ago, due 6 days ago)
                past_issue = (date.today() - timedelta(days=20)).isoformat()
                past_due = (date.today() - timedelta(days=6)).isoformat()
                c2, _ = LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[1].id,
                    member_id=all_members[1].id,
                    issue_date=past_issue,
                    due_date=past_due,
                    issued_by="Assistant Librarian",
                    remarks="Overdue loan check"
                )
                if c2:
                    c2.status = "Overdue"
                    session.commit()
                    circ_count += 1

                # Issue 3: Returned book with small fine paid
                past_issue_3 = (date.today() - timedelta(days=14)).isoformat()
                past_due_3 = (date.today() - timedelta(days=4)).isoformat()
                c3, _ = LibraryRepository.issue_book(
                    session=session,
                    book_id=all_books[2].id,
                    member_id=all_members[0].id,
                    issue_date=past_issue_3,
                    due_date=past_due_3,
                    issued_by="Chief Librarian",
                    remarks="Returned past deadline"
                )
                if c3:
                    LibraryRepository.return_book(
                        session=session,
                        circulation_id=c3.id,
                        return_date=today_str,
                        fine_rate_per_day=5.0,
                        fine_paid=True,
                        remarks="Fine received in cash."
                    )
                    circ_count += 1

        return {
            "categories_seeded": cat_count,
            "books_seeded": book_count,
            "members_seeded": member_count,
            "circulations_seeded": circ_count,
        }

    @staticmethod
    def export_catalog_excel(session: Session, output_path: str) -> str:
        """Exports complete book catalog to formatted openpyxl Excel spreadsheet."""
        books = LibraryRepository.get_books(session)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Book Catalog"

        # Brand header
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy 900
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        data_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # Title Rows
        ws["A1"] = "EDUMANAGE PRO - LIBRARY CATALOG & INVENTORY AUDIT"
        ws["A1"].font = title_font
        ws["A2"] = f"Generated on: {date.today().strftime('%B %d, %Y')} | Comprehensive Books Inventory & Shelf Allocation"
        ws["A2"].font = sub_font

        headers = [
            "Accession No", "Title", "Author", "Category", "ISBN",
            "Edition", "Year", "Rack", "Shelf", "Total Copies",
            "Available", "Issued", "Price ($)", "Status"
        ]

        row_num = 4
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        ws.row_dimensions[4].height = 26

        # Fill data
        for b in books:
            row_num += 1
            ws.cell(row=row_num, column=1, value=b.accession_no).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=2, value=b.title)
            ws.cell(row=row_num, column=3, value=b.author)
            ws.cell(row=row_num, column=4, value=b.category.name if b.category else "N/A")
            ws.cell(row=row_num, column=5, value=b.isbn or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=6, value=b.edition or "-")
            ws.cell(row=row_num, column=7, value=b.publication_year or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=8, value=b.rack_number or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=9, value=b.shelf_number or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=10, value=b.total_copies).alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=11, value=b.available_copies).alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=12, value=b.issued_copies).alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=13, value=f"${b.price:.2f}").alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=14, value=b.status).alignment = Alignment(horizontal="center")

            # Style each cell
            for c in range(1, 15):
                cell = ws.cell(row=row_num, column=c)
                cell.font = data_font
                cell.border = thin_border

        # Total summary row
        row_num += 1
        ws.cell(row=row_num, column=1, value="TOTAL SUMMARY").font = bold_font
        ws.cell(row=row_num, column=10, value=sum(b.total_copies for b in books)).font = bold_font
        ws.cell(row=row_num, column=11, value=sum(b.available_copies for b in books)).font = bold_font
        ws.cell(row=row_num, column=12, value=sum(b.issued_copies for b in books)).font = bold_font
        ws.cell(row=row_num, column=13, value=f"${sum(b.price * b.total_copies for b in books):.2f}").font = bold_font
        
        sum_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for c in range(1, 15):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = sum_fill
            cell.border = thin_border

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path
