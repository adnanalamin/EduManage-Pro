"""
EduManage Pro - Enterprise Library Repository
Authors, Publishers, Categories, Shelves, Barcoded/QR Book Copies, Members,
Issue/Return/Renewal Circulation, Reservations, Fines, and Lost/Damaged Incidents.
"""

import hashlib
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session, joinedload

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
from app.models.staff import Staff, Teacher
from app.models.student import Student


ACTIVE_LOAN_STATUSES = ("Issued", "Overdue", "Renewed")


class LibraryRepository:
    """Repository handling complete library catalog, physical copies, circulation, reservations, fines & incidents."""

    # ---------------- Barcode / QR Helpers ----------------
    @staticmethod
    def _clean_code(val: str, max_len: int = 16) -> str:
        cleaned = "".join(ch for ch in (val or "").upper() if ch.isalnum())
        return cleaned[:max_len] or uuid.uuid4().hex[:8].upper()

    @staticmethod
    def generate_book_barcode(accession_no: str) -> str:
        digest = hashlib.sha1((accession_no or "").encode("utf-8")).hexdigest()[:6].upper()
        return f"BK-{LibraryRepository._clean_code(accession_no, 10)}-{digest}"

    @staticmethod
    def generate_copy_barcode(copy_code: str) -> str:
        digest = hashlib.sha1((copy_code or "").encode("utf-8")).hexdigest()[:6].upper()
        return f"CP-{LibraryRepository._clean_code(copy_code, 12)}-{digest}"

    @staticmethod
    def generate_member_barcode(member_id: str) -> str:
        digest = hashlib.sha1((member_id or "").encode("utf-8")).hexdigest()[:6].upper()
        return f"LM-{LibraryRepository._clean_code(member_id, 12)}-{digest}"

    @staticmethod
    def build_book_qr_payload(book: Book) -> str:
        return (
            f"EDUMANAGE|LIB_BOOK|ACC:{book.accession_no}|ISBN:{book.isbn or ''}"
            f"|BC:{book.barcode or ''}"
        )

    @staticmethod
    def build_copy_qr_payload(copy_obj: BookCopy, accession_no: str = "") -> str:
        return (
            f"EDUMANAGE|LIB_COPY|CODE:{copy_obj.copy_code}|ACC:{accession_no}"
            f"|BC:{copy_obj.barcode}"
        )

    @staticmethod
    def build_member_qr_payload(member: LibraryMember) -> str:
        return (
            f"EDUMANAGE|LIB_MEM|ID:{member.member_id}|TYPE:{member.member_type}"
            f"|BC:{member.barcode or ''}"
        )

    @staticmethod
    def lookup_by_barcode_or_qr(session: Session, scan_text: str) -> Optional[Dict[str, Any]]:
        """
        Resolves any scanned barcode, QR payload, copy code, accession number, ISBN, or member ID.
        Returns dict with {'type': 'copy'|'book'|'member', ...} or None.
        """
        raw = (scan_text or "").strip()
        if not raw:
            return None

        # Parse structured QR payload if pasted/scanned
        candidate_codes = [raw]
        if raw.startswith("EDUMANAGE|"):
            for part in raw.split("|"):
                if ":" in part:
                    _, val = part.split(":", 1)
                    if val.strip():
                        candidate_codes.append(val.strip())

        # 1. Physical BookCopy match
        copy_obj = (
            session.query(BookCopy)
            .options(joinedload(BookCopy.book))
            .filter(
                BookCopy.is_deleted == False,
                or_(
                    BookCopy.barcode.in_(candidate_codes),
                    BookCopy.copy_code.in_(candidate_codes),
                    BookCopy.qr_payload == raw,
                ),
            )
            .first()
        )
        if copy_obj:
            return {"type": "copy", "copy": copy_obj, "book": copy_obj.book}

        # 2. Book Title match (Accession / Barcode / ISBN / QR)
        book_obj = (
            session.query(Book)
            .options(joinedload(Book.category), joinedload(Book.copies))
            .filter(
                Book.is_deleted == False,
                or_(
                    Book.barcode.in_(candidate_codes),
                    Book.accession_no.in_(candidate_codes),
                    Book.isbn.in_(candidate_codes),
                    Book.isbn_13.in_(candidate_codes),
                    Book.isbn_10.in_(candidate_codes),
                    Book.qr_payload == raw,
                ),
            )
            .first()
        )
        if book_obj:
            return {"type": "book", "book": book_obj}

        # 3. Member Card match
        member_obj = (
            session.query(LibraryMember)
            .options(
                joinedload(LibraryMember.student),
                joinedload(LibraryMember.teacher),
                joinedload(LibraryMember.staff),
            )
            .filter(
                LibraryMember.is_deleted == False,
                or_(
                    LibraryMember.barcode.in_(candidate_codes),
                    LibraryMember.member_id.in_(candidate_codes),
                    LibraryMember.qr_payload == raw,
                ),
            )
            .first()
        )
        if member_obj:
            return {"type": "member", "member": member_obj}

        return None

    # ---------------- Author Operations ----------------
    @staticmethod
    def get_authors(session: Session, search_query: Optional[str] = None) -> List[LibraryAuthor]:
        query = session.query(LibraryAuthor).filter(LibraryAuthor.is_deleted == False)
        if search_query:
            q = f"%{search_query.strip()}%"
            query = query.filter(or_(LibraryAuthor.name.ilike(q), LibraryAuthor.code.ilike(q)))
        return query.order_by(LibraryAuthor.name.asc()).all()

    @staticmethod
    def get_or_create_author(
        session: Session,
        name: str,
        country: Optional[str] = None,
        biography: Optional[str] = None,
    ) -> LibraryAuthor:
        clean_name = (name or "Unknown Author").strip()
        existing = session.query(LibraryAuthor).filter(LibraryAuthor.name.ilike(clean_name)).first()
        if existing:
            return existing
        base_code = "AUT-" + LibraryRepository._clean_code(clean_name, 8)
        code = base_code
        suffix = 1
        while session.query(LibraryAuthor).filter(LibraryAuthor.code == code).first():
            suffix += 1
            code = f"{base_code}-{suffix}"
        author = LibraryAuthor(name=clean_name, code=code, country=country, biography=biography)
        session.add(author)
        session.flush()
        return author

    @staticmethod
    def create_author(
        session: Session,
        name: str,
        code: Optional[str] = None,
        country: Optional[str] = None,
        website: Optional[str] = None,
        biography: Optional[str] = None,
    ) -> LibraryAuthor:
        clean_name = name.strip()
        if not code:
            base = "AUT-" + LibraryRepository._clean_code(clean_name, 8)
            code = base
            idx = 1
            while session.query(LibraryAuthor).filter(LibraryAuthor.code == code).first():
                idx += 1
                code = f"{base}-{idx}"
        author = LibraryAuthor(
            name=clean_name,
            code=code.strip(),
            country=country,
            website=website,
            biography=biography,
        )
        session.add(author)
        session.commit()
        session.refresh(author)
        return author

    @staticmethod
    def update_author(session: Session, author_id: int, **kwargs) -> Optional[LibraryAuthor]:
        author = session.query(LibraryAuthor).filter(LibraryAuthor.id == author_id).first()
        if not author:
            return None
        for k, v in kwargs.items():
            if hasattr(author, k):
                setattr(author, k, v)
        session.commit()
        session.refresh(author)
        return author

    @staticmethod
    def delete_author(session: Session, author_id: int) -> Tuple[bool, Optional[str]]:
        author = session.query(LibraryAuthor).filter(LibraryAuthor.id == author_id).first()
        if not author:
            return False, "Author not found."
        if session.query(Book).filter(Book.author_id == author_id, Book.is_deleted == False).count() > 0:
            return False, "Cannot delete an author assigned to existing books."
        session.delete(author)
        session.commit()
        return True, None

    # ---------------- Publisher Operations ----------------
    @staticmethod
    def get_publishers(session: Session, search_query: Optional[str] = None) -> List[LibraryPublisher]:
        query = session.query(LibraryPublisher).filter(LibraryPublisher.is_deleted == False)
        if search_query:
            q = f"%{search_query.strip()}%"
            query = query.filter(or_(LibraryPublisher.name.ilike(q), LibraryPublisher.code.ilike(q)))
        return query.order_by(LibraryPublisher.name.asc()).all()

    @staticmethod
    def get_or_create_publisher(
        session: Session,
        name: str,
        country: Optional[str] = None,
    ) -> LibraryPublisher:
        clean_name = (name or "").strip()
        existing = session.query(LibraryPublisher).filter(LibraryPublisher.name.ilike(clean_name)).first()
        if existing:
            return existing
        base_code = "PUB-" + LibraryRepository._clean_code(clean_name, 8)
        code = base_code
        suffix = 1
        while session.query(LibraryPublisher).filter(LibraryPublisher.code == code).first():
            suffix += 1
            code = f"{base_code}-{suffix}"
        pub = LibraryPublisher(name=clean_name, code=code, country=country)
        session.add(pub)
        session.flush()
        return pub

    @staticmethod
    def create_publisher(
        session: Session,
        name: str,
        code: Optional[str] = None,
        contact_email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        country: Optional[str] = None,
        website: Optional[str] = None,
    ) -> LibraryPublisher:
        clean_name = name.strip()
        if not code:
            base = "PUB-" + LibraryRepository._clean_code(clean_name, 8)
            code = base
            idx = 1
            while session.query(LibraryPublisher).filter(LibraryPublisher.code == code).first():
                idx += 1
                code = f"{base}-{idx}"
        pub = LibraryPublisher(
            name=clean_name,
            code=code.strip(),
            contact_email=contact_email,
            phone=phone,
            address=address,
            country=country,
            website=website,
        )
        session.add(pub)
        session.commit()
        session.refresh(pub)
        return pub

    @staticmethod
    def update_publisher(session: Session, publisher_id: int, **kwargs) -> Optional[LibraryPublisher]:
        pub = session.query(LibraryPublisher).filter(LibraryPublisher.id == publisher_id).first()
        if not pub:
            return None
        for k, v in kwargs.items():
            if hasattr(pub, k):
                setattr(pub, k, v)
        session.commit()
        session.refresh(pub)
        return pub

    @staticmethod
    def delete_publisher(session: Session, publisher_id: int) -> Tuple[bool, Optional[str]]:
        pub = session.query(LibraryPublisher).filter(LibraryPublisher.id == publisher_id).first()
        if not pub:
            return False, "Publisher not found."
        if session.query(Book).filter(Book.publisher_id == publisher_id, Book.is_deleted == False).count() > 0:
            return False, "Cannot delete a publisher assigned to existing books."
        session.delete(pub)
        session.commit()
        return True, None

    # ---------------- Category Operations ----------------
    @staticmethod
    def get_categories(session: Session) -> List[BookCategory]:
        return (
            session.query(BookCategory)
            .filter(BookCategory.is_deleted == False)
            .order_by(BookCategory.name.asc())
            .all()
        )

    @staticmethod
    def create_category(
        session: Session,
        name: str,
        code: str,
        description: Optional[str] = None,
        ddc_code: Optional[str] = None,
        default_loan_days: int = 14,
    ) -> BookCategory:
        cat = BookCategory(
            name=name.strip(),
            code=code.strip(),
            description=description,
            ddc_code=ddc_code,
            default_loan_days=default_loan_days,
        )
        session.add(cat)
        session.commit()
        session.refresh(cat)
        return cat

    @staticmethod
    def update_category(session: Session, category_id: int, **kwargs) -> Optional[BookCategory]:
        cat = session.query(BookCategory).filter(BookCategory.id == category_id).first()
        if not cat:
            return None
        for k, v in kwargs.items():
            if hasattr(cat, k):
                setattr(cat, k, v)
        session.commit()
        session.refresh(cat)
        return cat

    # ---------------- Shelf / Rack Operations ----------------
    @staticmethod
    def get_shelves(session: Session, category_id: Optional[int] = None) -> List[LibraryShelf]:
        query = (
            session.query(LibraryShelf)
            .options(joinedload(LibraryShelf.category))
            .filter(LibraryShelf.is_deleted == False)
        )
        if category_id:
            query = query.filter(LibraryShelf.category_id == category_id)
        return query.order_by(LibraryShelf.rack_number.asc(), LibraryShelf.shelf_number.asc()).all()

    @staticmethod
    def get_or_create_shelf(
        session: Session,
        rack_number: str,
        shelf_number: str,
        category_id: Optional[int] = None,
    ) -> LibraryShelf:
        rack = (rack_number or "Rack 01").strip()
        shelf = (shelf_number or "Shelf A").strip()
        existing = (
            session.query(LibraryShelf)
            .filter(
                LibraryShelf.rack_number.ilike(rack),
                LibraryShelf.shelf_number.ilike(shelf),
            )
            .first()
        )
        if existing:
            return existing
        base_code = f"{LibraryRepository._clean_code(rack, 6)}-{LibraryRepository._clean_code(shelf, 6)}"
        code = base_code
        idx = 1
        while session.query(LibraryShelf).filter(LibraryShelf.shelf_code == code).first():
            idx += 1
            code = f"{base_code}-{idx}"
        obj = LibraryShelf(
            shelf_code=code,
            rack_number=rack,
            shelf_number=shelf,
            category_id=category_id,
            capacity=100,
        )
        session.add(obj)
        session.flush()
        return obj

    @staticmethod
    def create_shelf(
        session: Session,
        shelf_code: str,
        rack_number: str,
        shelf_number: str,
        floor: Optional[str] = None,
        section_zone: Optional[str] = None,
        category_id: Optional[int] = None,
        capacity: int = 100,
        description: Optional[str] = None,
    ) -> LibraryShelf:
        shelf = LibraryShelf(
            shelf_code=shelf_code.strip(),
            rack_number=rack_number.strip(),
            shelf_number=shelf_number.strip(),
            floor=floor,
            section_zone=section_zone,
            category_id=category_id,
            capacity=capacity,
            description=description,
        )
        session.add(shelf)
        session.commit()
        session.refresh(shelf)
        return shelf

    @staticmethod
    def update_shelf(session: Session, shelf_id: int, **kwargs) -> Optional[LibraryShelf]:
        shelf = session.query(LibraryShelf).filter(LibraryShelf.id == shelf_id).first()
        if not shelf:
            return None
        for k, v in kwargs.items():
            if hasattr(shelf, k):
                setattr(shelf, k, v)
        session.commit()
        session.refresh(shelf)
        return shelf

    @staticmethod
    def delete_shelf(session: Session, shelf_id: int) -> Tuple[bool, Optional[str]]:
        shelf = session.query(LibraryShelf).filter(LibraryShelf.id == shelf_id).first()
        if not shelf:
            return False, "Shelf not found."
        if session.query(Book).filter(Book.shelf_id == shelf_id, Book.is_deleted == False).count() > 0:
            return False, "Cannot delete a shelf that currently holds catalog books."
        session.delete(shelf)
        session.commit()
        return True, None

    # ---------------- Book & Physical Copy Operations ----------------
    @staticmethod
    def _sync_book_copy_counts(session: Session, book: Book) -> None:
        """Synchronizes aggregate Book copy counters with individual BookCopy records."""
        copies = (
            session.query(BookCopy)
            .filter(BookCopy.book_id == book.id, BookCopy.is_deleted == False)
            .all()
        )
        if not copies:
            book.status = "Available" if (book.available_copies or 0) > 0 else "Out of Stock"
            return

        active_copies = [c for c in copies if c.status != "Retired"]
        book.total_copies = len(active_copies)
        book.available_copies = sum(1 for c in active_copies if c.status == "Available")
        book.issued_copies = sum(1 for c in active_copies if c.status == "Issued")
        book.lost_copies = sum(1 for c in active_copies if c.status == "Lost")
        book.damaged_copies = sum(1 for c in active_copies if c.status == "Damaged")
        reserved_cnt = sum(1 for c in active_copies if c.status == "Reserved")

        if book.available_copies > 0:
            book.status = "Available"
        elif reserved_cnt > 0:
            book.status = "Reserved Hold"
        elif book.issued_copies > 0:
            book.status = "Out of Stock"
        elif book.lost_copies + book.damaged_copies == book.total_copies and book.total_copies > 0:
            book.status = "Unavailable"
        else:
            book.status = "Out of Stock"

    @staticmethod
    def _create_physical_copies(
        session: Session,
        book: Book,
        count: int,
        start_num: int = 1,
    ) -> List[BookCopy]:
        created: List[BookCopy] = []
        today_str = date.today().isoformat()
        existing_nums = {
            c.copy_number
            for c in session.query(BookCopy).filter(BookCopy.book_id == book.id).all()
        }
        next_num = max([start_num - 1] + list(existing_nums)) + 1
        for _ in range(max(0, count)):
            copy_code = f"{book.accession_no}-C{next_num:02d}"
            while session.query(BookCopy).filter(BookCopy.copy_code == copy_code).first():
                next_num += 1
                copy_code = f"{book.accession_no}-C{next_num:02d}"
            bc = LibraryRepository.generate_copy_barcode(copy_code)
            while session.query(BookCopy).filter(BookCopy.barcode == bc).first():
                bc = f"{bc}-{uuid.uuid4().hex[:3].upper()}"
            copy_obj = BookCopy(
                book_id=book.id,
                copy_code=copy_code,
                copy_number=next_num,
                barcode=bc,
                shelf_id=book.shelf_id,
                condition="Good",
                status="Available",
                purchase_date=today_str,
                purchase_price=book.price or 0.0,
            )
            copy_obj.qr_payload = LibraryRepository.build_copy_qr_payload(copy_obj, book.accession_no)
            session.add(copy_obj)
            created.append(copy_obj)
            next_num += 1
        session.flush()
        return created

    @staticmethod
    def get_books(
        session: Session,
        category_id: Optional[int] = None,
        search_query: Optional[str] = None,
        only_available: bool = False,
        author_id: Optional[int] = None,
        publisher_id: Optional[int] = None,
        shelf_id: Optional[int] = None,
    ) -> List[Book]:
        query = (
            session.query(Book)
            .options(
                joinedload(Book.category),
                joinedload(Book.author_ref),
                joinedload(Book.publisher_ref),
                joinedload(Book.shelf_ref),
            )
            .filter(Book.is_deleted == False)
        )
        if category_id:
            query = query.filter(Book.category_id == category_id)
        if author_id:
            query = query.filter(Book.author_id == author_id)
        if publisher_id:
            query = query.filter(Book.publisher_id == publisher_id)
        if shelf_id:
            query = query.filter(Book.shelf_id == shelf_id)
        if only_available:
            query = query.filter(Book.available_copies > 0)
        if search_query:
            q = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Book.title.ilike(q),
                    Book.author.ilike(q),
                    Book.publisher.ilike(q),
                    Book.isbn.ilike(q),
                    Book.isbn_13.ilike(q),
                    Book.accession_no.ilike(q),
                    Book.barcode.ilike(q),
                    Book.call_number.ilike(q),
                )
            )
        return query.order_by(Book.id.desc()).all()

    @staticmethod
    def get_book_by_id(session: Session, book_id: int) -> Optional[Book]:
        return (
            session.query(Book)
            .options(
                joinedload(Book.category),
                joinedload(Book.author_ref),
                joinedload(Book.publisher_ref),
                joinedload(Book.shelf_ref),
                joinedload(Book.copies),
            )
            .filter(Book.id == book_id)
            .first()
        )

    @staticmethod
    def get_book_by_accession(session: Session, accession_no: str) -> Optional[Book]:
        return session.query(Book).filter(Book.accession_no == accession_no.strip()).first()

    @staticmethod
    def create_book(session: Session, generate_copies: bool = True, **kwargs) -> Book:
        total_copies = int(kwargs.get("total_copies", 1) or 1)
        if "available_copies" not in kwargs:
            kwargs["available_copies"] = total_copies

        # Normalize Author
        if not kwargs.get("author_id") and kwargs.get("author"):
            auth_obj = LibraryRepository.get_or_create_author(session, kwargs["author"])
            kwargs["author_id"] = auth_obj.id

        # Normalize Publisher
        if not kwargs.get("publisher_id") and kwargs.get("publisher"):
            pub_obj = LibraryRepository.get_or_create_publisher(session, kwargs["publisher"])
            kwargs["publisher_id"] = pub_obj.id

        # Normalize Shelf
        if kwargs.get("shelf_id"):
            shelf_obj = session.query(LibraryShelf).filter(LibraryShelf.id == kwargs["shelf_id"]).first()
            if shelf_obj:
                kwargs.setdefault("rack_number", shelf_obj.rack_number)
                kwargs.setdefault("shelf_number", shelf_obj.shelf_number)
        elif kwargs.get("rack_number") or kwargs.get("shelf_number"):
            shelf_obj = LibraryRepository.get_or_create_shelf(
                session,
                kwargs.get("rack_number") or "Rack 01",
                kwargs.get("shelf_number") or "Shelf A",
                category_id=kwargs.get("category_id"),
            )
            kwargs["shelf_id"] = shelf_obj.id

        # Normalize ISBN-10 / ISBN-13
        isbn_val = (kwargs.get("isbn") or "").strip()
        if isbn_val:
            digits = "".join(ch for ch in isbn_val if ch.isalnum())
            if len(digits) == 13 and not kwargs.get("isbn_13"):
                kwargs["isbn_13"] = isbn_val
            elif len(digits) == 10 and not kwargs.get("isbn_10"):
                kwargs["isbn_10"] = isbn_val

        # Barcode & QR
        if not kwargs.get("barcode"):
            bc = LibraryRepository.generate_book_barcode(kwargs.get("accession_no", ""))
            while session.query(Book).filter(Book.barcode == bc).first():
                bc = f"{bc}-{uuid.uuid4().hex[:3].upper()}"
            kwargs["barcode"] = bc

        book = Book(**kwargs)
        if not book.qr_payload:
            book.qr_payload = LibraryRepository.build_book_qr_payload(book)

        session.add(book)
        session.flush()

        if generate_copies and total_copies > 0:
            LibraryRepository._create_physical_copies(session, book, total_copies)
            LibraryRepository._sync_book_copy_counts(session, book)

        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def update_book(session: Session, book_id: int, **kwargs) -> Optional[Book]:
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None

        if "author" in kwargs and kwargs["author"] and "author_id" not in kwargs:
            auth_obj = LibraryRepository.get_or_create_author(session, kwargs["author"])
            kwargs["author_id"] = auth_obj.id

        if "publisher" in kwargs and kwargs["publisher"] and "publisher_id" not in kwargs:
            pub_obj = LibraryRepository.get_or_create_publisher(session, kwargs["publisher"])
            kwargs["publisher_id"] = pub_obj.id

        if "shelf_id" in kwargs and kwargs["shelf_id"]:
            shelf_obj = session.query(LibraryShelf).filter(LibraryShelf.id == kwargs["shelf_id"]).first()
            if shelf_obj:
                kwargs["rack_number"] = shelf_obj.rack_number
                kwargs["shelf_number"] = shelf_obj.shelf_number
        elif ("rack_number" in kwargs or "shelf_number" in kwargs) and "shelf_id" not in kwargs:
            rack = kwargs.get("rack_number", book.rack_number)
            shelf_n = kwargs.get("shelf_number", book.shelf_number)
            if rack or shelf_n:
                shelf_obj = LibraryRepository.get_or_create_shelf(
                    session,
                    rack or "Rack 01",
                    shelf_n or "Shelf A",
                    category_id=kwargs.get("category_id", book.category_id),
                )
                kwargs["shelf_id"] = shelf_obj.id

        requested_total = kwargs.pop("total_copies", None)
        for k, v in kwargs.items():
            if hasattr(book, k):
                setattr(book, k, v)

        if not book.barcode:
            book.barcode = LibraryRepository.generate_book_barcode(book.accession_no)
        book.qr_payload = LibraryRepository.build_book_qr_payload(book)

        if requested_total is not None:
            requested_total = int(requested_total)
            existing_copies = (
                session.query(BookCopy)
                .filter(BookCopy.book_id == book.id, BookCopy.is_deleted == False, BookCopy.status != "Retired")
                .order_by(BookCopy.copy_number.desc())
                .all()
            )
            if existing_copies:
                delta = requested_total - len(existing_copies)
                if delta > 0:
                    LibraryRepository._create_physical_copies(session, book, delta)
                elif delta < 0:
                    avail = [c for c in existing_copies if c.status == "Available"]
                    for c in avail[: abs(delta)]:
                        has_circ = session.query(BookCirculation).filter(BookCirculation.copy_id == c.id).count() > 0
                        if has_circ:
                            c.status = "Retired"
                            c.condition = "Retired"
                        else:
                            session.delete(c)
                    session.flush()
                LibraryRepository._sync_book_copy_counts(session, book)
            else:
                book.total_copies = requested_total
                book.available_copies = max(
                    0,
                    book.total_copies - (book.issued_copies or 0) - (book.lost_copies or 0) - (book.damaged_copies or 0),
                )
                book.status = "Available" if book.available_copies > 0 else "Out of Stock"

        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def delete_book(session: Session, book_id: int) -> bool:
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return False
        session.delete(book)
        session.commit()
        return True

    @staticmethod
    def get_book_copies(session: Session, book_id: int) -> List[BookCopy]:
        return (
            session.query(BookCopy)
            .options(joinedload(BookCopy.shelf), joinedload(BookCopy.book))
            .filter(BookCopy.book_id == book_id, BookCopy.is_deleted == False)
            .order_by(BookCopy.copy_number.asc(), BookCopy.id.asc())
            .all()
        )

    @staticmethod
    def add_book_copy(
        session: Session,
        book_id: int,
        condition: str = "Good",
        shelf_id: Optional[int] = None,
        purchase_date: Optional[str] = None,
        purchase_price: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[BookCopy]:
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None
        created = LibraryRepository._create_physical_copies(session, book, 1)
        copy_obj = created[0]
        copy_obj.condition = condition
        if shelf_id is not None:
            copy_obj.shelf_id = shelf_id
        if purchase_date:
            copy_obj.purchase_date = purchase_date
        if purchase_price is not None:
            copy_obj.purchase_price = purchase_price
        if notes:
            copy_obj.notes = notes
        LibraryRepository._sync_book_copy_counts(session, book)
        session.commit()
        session.refresh(copy_obj)
        return copy_obj

    @staticmethod
    def update_book_copy(session: Session, copy_id: int, **kwargs) -> Optional[BookCopy]:
        copy_obj = session.query(BookCopy).filter(BookCopy.id == copy_id).first()
        if not copy_obj:
            return None
        for k, v in kwargs.items():
            if hasattr(copy_obj, k):
                setattr(copy_obj, k, v)
        if copy_obj.book:
            copy_obj.qr_payload = LibraryRepository.build_copy_qr_payload(copy_obj, copy_obj.book.accession_no)
            LibraryRepository._sync_book_copy_counts(session, copy_obj.book)
        session.commit()
        session.refresh(copy_obj)
        return copy_obj

    # ---------------- Library Member Operations ----------------
    @staticmethod
    def get_members(
        session: Session,
        member_type: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[LibraryMember]:
        query = (
            session.query(LibraryMember)
            .options(
                joinedload(LibraryMember.student).joinedload(Student.school_class),
                joinedload(LibraryMember.teacher),
                joinedload(LibraryMember.staff),
            )
            .filter(LibraryMember.is_deleted == False)
        )
        if member_type:
            query = query.filter(LibraryMember.member_type == member_type)
        if status:
            query = query.filter(LibraryMember.status == status)
        members = query.order_by(LibraryMember.id.desc()).all()
        if search_query:
            q = search_query.strip().lower()
            members = [
                m
                for m in members
                if q in (m.member_id or "").lower()
                or q in (m.barcode or "").lower()
                or q in m.display_name.lower()
                or q in (m.member_type or "").lower()
            ]
        return members

    @staticmethod
    def get_member_by_id(session: Session, member_id: int) -> Optional[LibraryMember]:
        return (
            session.query(LibraryMember)
            .options(
                joinedload(LibraryMember.student).joinedload(Student.school_class),
                joinedload(LibraryMember.teacher),
                joinedload(LibraryMember.staff),
            )
            .filter(LibraryMember.id == member_id)
            .first()
        )

    @staticmethod
    def get_member_by_code(session: Session, member_code: str) -> Optional[LibraryMember]:
        code = member_code.strip()
        return (
            session.query(LibraryMember)
            .filter(or_(LibraryMember.member_id == code, LibraryMember.barcode == code))
            .first()
        )

    @staticmethod
    def create_member(session: Session, **kwargs) -> LibraryMember:
        if not kwargs.get("card_issue_date"):
            kwargs["card_issue_date"] = date.today().isoformat()
        if not kwargs.get("card_expiry_date"):
            try:
                iss = datetime.strptime(kwargs["card_issue_date"], "%Y-%m-%d").date()
                kwargs["card_expiry_date"] = (iss + timedelta(days=365)).isoformat()
            except Exception:
                kwargs["card_expiry_date"] = (date.today() + timedelta(days=365)).isoformat()
        if not kwargs.get("barcode"):
            bc = LibraryRepository.generate_member_barcode(kwargs.get("member_id", ""))
            while session.query(LibraryMember).filter(LibraryMember.barcode == bc).first():
                bc = f"{bc}-{uuid.uuid4().hex[:3].upper()}"
            kwargs["barcode"] = bc

        member = LibraryMember(**kwargs)
        if not member.qr_payload:
            member.qr_payload = LibraryRepository.build_member_qr_payload(member)
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

    @staticmethod
    def update_member(session: Session, member_id: int, **kwargs) -> Optional[LibraryMember]:
        member = session.query(LibraryMember).filter(LibraryMember.id == member_id).first()
        if not member:
            return None
        for k, v in kwargs.items():
            if hasattr(member, k):
                setattr(member, k, v)
        if not member.barcode:
            member.barcode = LibraryRepository.generate_member_barcode(member.member_id)
        member.qr_payload = LibraryRepository.build_member_qr_payload(member)
        session.commit()
        session.refresh(member)
        return member

    @staticmethod
    def sync_members_from_school(
        session: Session,
        include_students: bool = True,
        include_teachers: bool = True,
        include_staff: bool = True,
    ) -> Dict[str, int]:
        """Enrolls active real Students, Teachers, and Staff records who do not yet have a LibraryMember card."""
        today_str = date.today().isoformat()
        added = {"students": 0, "teachers": 0, "staff": 0}

        if include_students:
            existing_sids = {
                r[0]
                for r in session.query(LibraryMember.student_id)
                .filter(LibraryMember.student_id.isnot(None))
                .all()
            }
            students = session.query(Student).filter(Student.is_deleted == False).all()
            for std in students:
                if std.id in existing_sids:
                    continue
                code = f"LIB-STD-{std.student_id or std.id:04d}"
                if session.query(LibraryMember).filter(LibraryMember.member_id == code).first():
                    code = f"LIB-STD-{std.id}-{uuid.uuid4().hex[:4].upper()}"
                LibraryRepository.create_member(
                    session,
                    member_id=code,
                    member_type="Student",
                    student_id=std.id,
                    phone=std.phone,
                    email=std.email,
                    card_issue_date=today_str,
                    max_allowed_books=3,
                    max_loan_days=14,
                    status="Active",
                )
                added["students"] += 1

        if include_teachers:
            existing_tids = {
                r[0]
                for r in session.query(LibraryMember.teacher_id)
                .filter(LibraryMember.teacher_id.isnot(None))
                .all()
            }
            teachers = session.query(Teacher).filter(Teacher.is_deleted == False).all()
            for tch in teachers:
                if tch.id in existing_tids:
                    continue
                code = f"LIB-FAC-{tch.teacher_id or tch.id:04d}"
                if session.query(LibraryMember).filter(LibraryMember.member_id == code).first():
                    code = f"LIB-FAC-{tch.id}-{uuid.uuid4().hex[:4].upper()}"
                LibraryRepository.create_member(
                    session,
                    member_id=code,
                    member_type="Teacher",
                    teacher_id=tch.id,
                    phone=tch.phone,
                    email=tch.email,
                    card_issue_date=today_str,
                    max_allowed_books=5,
                    max_loan_days=30,
                    status="Active",
                )
                added["teachers"] += 1

        if include_staff:
            existing_stids = {
                r[0]
                for r in session.query(LibraryMember.staff_id)
                .filter(LibraryMember.staff_id.isnot(None))
                .all()
            }
            staff_rows = session.query(Staff).filter(Staff.is_deleted == False).all()
            for st in staff_rows:
                if st.id in existing_stids:
                    continue
                code = f"LIB-STF-{st.staff_id or st.id:04d}"
                if session.query(LibraryMember).filter(LibraryMember.member_id == code).first():
                    code = f"LIB-STF-{st.id}-{uuid.uuid4().hex[:4].upper()}"
                LibraryRepository.create_member(
                    session,
                    member_id=code,
                    member_type="Staff",
                    staff_id=st.id,
                    phone=st.phone,
                    email=st.email,
                    card_issue_date=today_str,
                    max_allowed_books=3,
                    max_loan_days=14,
                    status="Active",
                )
                added["staff"] += 1

        return added

    # ---------------- Circulation (Issue / Renewal / Return) ----------------
    @staticmethod
    def issue_book(
        session: Session,
        book_id: int,
        member_id: int,
        issue_date: str,
        due_date: str,
        issued_by: Optional[str] = None,
        remarks: Optional[str] = None,
        copy_id: Optional[int] = None,
        max_renewals: int = 2,
    ) -> Tuple[Optional[BookCirculation], Optional[str]]:
        """
        Validates borrower eligibility, quota, reservations & physical copy availability,
        then creates an active loan circulation record.
        """
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None, "Book not found."

        member = session.query(LibraryMember).filter(LibraryMember.id == member_id).first()
        if not member:
            return None, "Library member borrower not found."
        if member.status != "Active":
            return None, f"Member '{member.member_id}' is {member.status} and cannot borrow books."

        # Check borrower's active loans count
        active_loans = (
            session.query(BookCirculation)
            .filter(
                BookCirculation.member_id == member_id,
                BookCirculation.status.in_(ACTIVE_LOAN_STATUSES),
            )
            .count()
        )
        if active_loans >= member.max_allowed_books:
            return None, f"Member has reached their maximum quota of {member.max_allowed_books} borrowed books."

        # Check if this member has a Ready/Pending reservation for this book
        member_reservation = (
            session.query(BookReservation)
            .filter(
                BookReservation.book_id == book_id,
                BookReservation.member_id == member_id,
                BookReservation.status.in_(["Ready", "Pending"]),
            )
            .order_by(BookReservation.id.asc())
            .first()
        )

        # Resolve physical copy if physical copies exist
        copies = (
            session.query(BookCopy)
            .filter(BookCopy.book_id == book_id, BookCopy.is_deleted == False)
            .order_by(BookCopy.copy_number.asc(), BookCopy.id.asc())
            .all()
        )

        selected_copy: Optional[BookCopy] = None
        if copy_id is not None:
            selected_copy = next((c for c in copies if c.id == copy_id), None)
            if not selected_copy:
                return None, "Selected physical book copy was not found for this title."
            if selected_copy.status == "Reserved":
                if not member_reservation or (
                    member_reservation.copy_id is not None and member_reservation.copy_id != selected_copy.id
                ):
                    return None, f"Copy '{selected_copy.copy_code}' is currently on reservation hold for another member."
            elif selected_copy.status != "Available":
                return None, f"Copy '{selected_copy.copy_code}' is currently {selected_copy.status}."
        elif copies:
            if member_reservation and member_reservation.copy_id:
                selected_copy = next(
                    (c for c in copies if c.id == member_reservation.copy_id and c.status in ("Reserved", "Available")),
                    None,
                )
            if not selected_copy:
                selected_copy = next((c for c in copies if c.status == "Available"), None)
            if not selected_copy and member_reservation:
                selected_copy = next((c for c in copies if c.status == "Reserved"), None)

            if not selected_copy:
                return None, f"'{book.title}' has no copies currently available."
        else:
            if book.available_copies <= 0:
                return None, f"'{book.title}' has no copies currently available."

        if selected_copy is not None:
            selected_copy.status = "Issued"
            LibraryRepository._sync_book_copy_counts(session, book)
        else:
            book.available_copies -= 1
            book.issued_copies += 1
            if book.available_copies == 0:
                book.status = "Out of Stock"

        if member_reservation:
            member_reservation.status = "Fulfilled"
            member_reservation.fulfilled_date = issue_date

        circulation = BookCirculation(
            book_id=book_id,
            copy_id=selected_copy.id if selected_copy else None,
            member_id=member_id,
            reservation_id=member_reservation.id if member_reservation else None,
            issue_date=issue_date,
            due_date=due_date,
            status="Issued",
            renewal_count=0,
            max_renewals=max_renewals,
            issued_by=issued_by,
            remarks=remarks,
        )
        session.add(circulation)
        session.commit()
        session.refresh(circulation)
        return circulation, None

    @staticmethod
    def renew_loan(
        session: Session,
        circulation_id: int,
        new_due_date: str,
        renewed_by: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> Tuple[Optional[BookCirculation], Optional[str]]:
        """Extends due date on an active loan if within renewal limits and unreserved."""
        circ = (
            session.query(BookCirculation)
            .options(joinedload(BookCirculation.book), joinedload(BookCirculation.member))
            .filter(BookCirculation.id == circulation_id)
            .first()
        )
        if not circ:
            return None, "Circulation record not found."
        if circ.status not in ACTIVE_LOAN_STATUSES:
            return None, f"Cannot renew a loan with status '{circ.status}'."
        if circ.member and circ.member.status != "Active":
            return None, f"Member '{circ.member.member_id}' is {circ.member.status} and cannot renew loans."
        if (circ.renewal_count or 0) >= (circ.max_renewals or 2):
            return None, f"Maximum renewal limit ({circ.max_renewals}) reached for this loan."

        # Check if another member has an active reservation waiting for this title
        other_res = (
            session.query(BookReservation)
            .filter(
                BookReservation.book_id == circ.book_id,
                BookReservation.member_id != circ.member_id,
                BookReservation.status.in_(["Pending", "Ready"]),
            )
            .first()
        )
        if other_res:
            return None, "Renewal blocked: another member has an active reservation for this book."

        if new_due_date <= circ.due_date:
            return None, f"New due date ({new_due_date}) must be later than current due date ({circ.due_date})."

        circ.due_date = new_due_date
        circ.renewal_count = (circ.renewal_count or 0) + 1
        circ.last_renewed_at = date.today().isoformat()
        circ.status = "Renewed"
        if remarks:
            prefix = f"{circ.remarks} | " if circ.remarks else ""
            circ.remarks = f"{prefix}Renewed ({renewed_by or 'Librarian'}): {remarks}"

        session.commit()
        session.refresh(circ)
        return circ, None

    @staticmethod
    def _create_fine_record(
        session: Session,
        member_id: int,
        fine_type: str,
        amount: float,
        assessed_date: str,
        circulation_id: Optional[int] = None,
        book_id: Optional[int] = None,
        copy_id: Optional[int] = None,
        paid: bool = False,
        payment_method: Optional[str] = None,
        collected_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> LibraryFine:
        fine_code = f"FINE-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        amt = round(float(amount or 0.0), 2)
        fine = LibraryFine(
            fine_code=fine_code,
            circulation_id=circulation_id,
            member_id=member_id,
            book_id=book_id,
            copy_id=copy_id,
            fine_type=fine_type,
            amount=amt,
            paid_amount=amt if paid else 0.0,
            waived_amount=0.0,
            status="Paid" if paid else "Unpaid",
            assessed_date=assessed_date,
            paid_date=assessed_date if paid else None,
            payment_method=(payment_method or "Cash") if paid else None,
            receipt_no=f"RCPT-{uuid.uuid4().hex[:6].upper()}" if paid else None,
            collected_by=collected_by if paid else None,
            notes=notes,
        )
        session.add(fine)
        session.flush()
        return fine

    @staticmethod
    def return_book(
        session: Session,
        circulation_id: int,
        return_date: str,
        fine_rate_per_day: float = 5.0,
        fine_paid: bool = False,
        remarks: Optional[str] = None,
        return_condition: str = "Good",
        damage_fee: float = 0.0,
        returned_to: Optional[str] = None,
        payment_method: str = "Cash",
    ) -> Tuple[Optional[BookCirculation], Optional[str]]:
        """
        Processes book check-in, calculates overdue days & fines, handles Good/Damaged/Lost returns,
        records LibraryFine/BookIncident audit trails, promotes FIFO reservations, and updates inventory.
        """
        circ = (
            session.query(BookCirculation)
            .options(
                joinedload(BookCirculation.book),
                joinedload(BookCirculation.copy),
                joinedload(BookCirculation.member),
            )
            .filter(BookCirculation.id == circulation_id)
            .first()
        )
        if not circ:
            return None, "Circulation record not found."
        if circ.status in ("Returned", "Lost"):
            return None, "This book has already been returned or closed."

        cond = (return_condition or "Good").strip()
        if cond not in ("Good", "Fair", "Damaged", "Lost"):
            cond = "Good"

        # Calculate overdue days
        try:
            d_due = datetime.strptime(circ.due_date, "%Y-%m-%d").date()
            d_ret = datetime.strptime(return_date, "%Y-%m-%d").date()
            overdue_days = max(0, (d_ret - d_due).days)
        except Exception:
            overdue_days = 0

        overdue_fine = round(overdue_days * float(fine_rate_per_day or 0.0), 2)
        extra_fee = round(float(damage_fee or 0.0), 2)
        if cond == "Lost" and extra_fee <= 0 and circ.book:
            extra_fee = round(float(circ.book.price or 0.0), 2)

        total_fine = round(overdue_fine + extra_fee, 2)

        circ.return_date = return_date
        circ.return_condition = cond
        circ.fine_amount = overdue_fine
        circ.damage_or_lost_fee = extra_fee
        circ.fine_paid = fine_paid or (total_fine == 0)
        circ.returned_to = returned_to
        if remarks:
            circ.remarks = remarks

        if cond == "Lost":
            circ.status = "Lost"
        elif cond == "Damaged":
            circ.status = "Damaged"
        else:
            circ.status = "Returned"

        # Record Fine Ledger entries
        incident_fine: Optional[LibraryFine] = None
        if overdue_fine > 0:
            LibraryRepository._create_fine_record(
                session,
                member_id=circ.member_id,
                fine_type="Overdue",
                amount=overdue_fine,
                assessed_date=return_date,
                circulation_id=circ.id,
                book_id=circ.book_id,
                copy_id=circ.copy_id,
                paid=fine_paid,
                payment_method=payment_method,
                collected_by=returned_to,
                notes=f"{overdue_days} days overdue @ {fine_rate_per_day}/day",
            )

        if extra_fee > 0 or cond in ("Damaged", "Lost"):
            if extra_fee > 0:
                incident_fine = LibraryRepository._create_fine_record(
                    session,
                    member_id=circ.member_id,
                    fine_type="Lost" if cond == "Lost" else "Damaged",
                    amount=extra_fee,
                    assessed_date=return_date,
                    circulation_id=circ.id,
                    book_id=circ.book_id,
                    copy_id=circ.copy_id,
                    paid=fine_paid,
                    payment_method=payment_method,
                    collected_by=returned_to,
                    notes=remarks or f"{cond} book fee on return",
                )

        # Update physical copy & book inventory
        if cond in ("Good", "Fair"):
            next_res = (
                session.query(BookReservation)
                .filter(
                    BookReservation.book_id == circ.book_id,
                    BookReservation.status == "Pending",
                )
                .order_by(BookReservation.priority_order.asc(), BookReservation.id.asc())
                .first()
            )
            if circ.copy:
                circ.copy.condition = cond
                if next_res:
                    circ.copy.status = "Reserved"
                    next_res.status = "Ready"
                    next_res.copy_id = circ.copy.id
                    next_res.ready_date = return_date
                    try:
                        rd = datetime.strptime(return_date, "%Y-%m-%d").date()
                        next_res.expiry_date = (rd + timedelta(days=3)).isoformat()
                    except Exception:
                        pass
                else:
                    circ.copy.status = "Available"
                if circ.book:
                    LibraryRepository._sync_book_copy_counts(session, circ.book)
            elif circ.book:
                circ.book.available_copies += 1
                circ.book.issued_copies = max(0, circ.book.issued_copies - 1)
                circ.book.status = "Available"
        else:
            # Damaged or Lost return
            inc_type = "Lost" if cond == "Lost" else "Damaged"
            if circ.copy:
                circ.copy.condition = inc_type
                circ.copy.status = inc_type
                if circ.book:
                    LibraryRepository._sync_book_copy_counts(session, circ.book)
            elif circ.book:
                circ.book.issued_copies = max(0, circ.book.issued_copies - 1)
                if inc_type == "Lost":
                    circ.book.lost_copies = (circ.book.lost_copies or 0) + 1
                else:
                    circ.book.damaged_copies = (circ.book.damaged_copies or 0) + 1

            inc = BookIncident(
                incident_code=f"INC-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                book_id=circ.book_id,
                copy_id=circ.copy_id,
                circulation_id=circ.id,
                member_id=circ.member_id,
                fine_id=incident_fine.id if incident_fine else None,
                incident_type=inc_type,
                severity="Total Loss" if inc_type == "Lost" else "Major",
                incident_date=return_date,
                description=remarks or f"Reported {inc_type} upon loan #{circ.id} check-in.",
                replacement_cost=float(circ.book.price or 0.0) if circ.book else 0.0,
                fine_assessed=extra_fee,
                resolution_status="Billed" if extra_fee > 0 else "Reported",
                resolved_by=returned_to,
            )
            session.add(inc)

        session.commit()
        session.refresh(circ)
        return circ, None

    @staticmethod
    def get_circulations(
        session: Session,
        status: Optional[str] = None,
        member_id: Optional[int] = None,
        book_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[BookCirculation]:
        query = (
            session.query(BookCirculation)
            .options(
                joinedload(BookCirculation.book),
                joinedload(BookCirculation.copy),
                joinedload(BookCirculation.member).joinedload(LibraryMember.student),
                joinedload(BookCirculation.member).joinedload(LibraryMember.teacher),
                joinedload(BookCirculation.member).joinedload(LibraryMember.staff),
            )
            .filter(BookCirculation.is_deleted == False)
        )
        if status:
            if status == "Active":
                query = query.filter(BookCirculation.status.in_(ACTIVE_LOAN_STATUSES))
            else:
                query = query.filter(BookCirculation.status == status)
        if member_id:
            query = query.filter(BookCirculation.member_id == member_id)
        if book_id:
            query = query.filter(BookCirculation.book_id == book_id)
        if date_from:
            query = query.filter(BookCirculation.issue_date >= date_from)
        if date_to:
            query = query.filter(BookCirculation.issue_date <= date_to)

        return query.order_by(BookCirculation.id.desc()).all()

    @staticmethod
    def refresh_overdue_statuses(session: Session, as_of_date: Optional[str] = None) -> int:
        today_str = as_of_date or date.today().isoformat()
        rows = (
            session.query(BookCirculation)
            .filter(
                BookCirculation.status.in_(["Issued", "Renewed"]),
                BookCirculation.due_date < today_str,
            )
            .all()
        )
        for c in rows:
            c.status = "Overdue"
        if rows:
            session.commit()
        return len(rows)

    # ---------------- Reservation Operations ----------------
    @staticmethod
    def create_reservation(
        session: Session,
        book_id: int,
        member_id: int,
        expiry_days: int = 3,
        copy_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
        hold_available_copy: bool = True,
    ) -> Tuple[Optional[BookReservation], Optional[str]]:
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None, "Book not found."
        member = session.query(LibraryMember).filter(LibraryMember.id == member_id).first()
        if not member:
            return None, "Library member not found."
        if member.status != "Active":
            return None, f"Member '{member.member_id}' is {member.status} and cannot reserve books."

        dup = (
            session.query(BookReservation)
            .filter(
                BookReservation.book_id == book_id,
                BookReservation.member_id == member_id,
                BookReservation.status.in_(["Pending", "Ready"]),
            )
            .first()
        )
        if dup:
            return None, "Member already has an active reservation for this book."

        today = date.today()
        today_str = today.isoformat()
        exp_str = (today + timedelta(days=max(1, int(expiry_days)))).isoformat()

        max_prio = (
            session.query(BookReservation)
            .filter(BookReservation.book_id == book_id, BookReservation.status.in_(["Pending", "Ready"]))
            .count()
        ) + 1

        res_status = "Pending"
        assigned_copy: Optional[BookCopy] = None
        if hold_available_copy:
            if copy_id:
                assigned_copy = (
                    session.query(BookCopy)
                    .filter(BookCopy.id == copy_id, BookCopy.book_id == book_id, BookCopy.status == "Available")
                    .first()
                )
            else:
                assigned_copy = (
                    session.query(BookCopy)
                    .filter(BookCopy.book_id == book_id, BookCopy.status == "Available")
                    .order_by(BookCopy.copy_number.asc())
                    .first()
                )
            if assigned_copy:
                assigned_copy.status = "Reserved"
                res_status = "Ready"
                LibraryRepository._sync_book_copy_counts(session, book)

        res = BookReservation(
            reservation_code=f"RES-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            book_id=book_id,
            copy_id=assigned_copy.id if assigned_copy else None,
            member_id=member_id,
            reserved_date=today_str,
            ready_date=today_str if res_status == "Ready" else None,
            expiry_date=exp_str,
            status=res_status,
            priority_order=max_prio,
            created_by=created_by,
            notes=notes,
        )
        session.add(res)
        session.commit()
        session.refresh(res)
        return res, None

    @staticmethod
    def get_reservations(
        session: Session,
        status: Optional[str] = None,
        book_id: Optional[int] = None,
        member_id: Optional[int] = None,
    ) -> List[BookReservation]:
        query = (
            session.query(BookReservation)
            .options(
                joinedload(BookReservation.book),
                joinedload(BookReservation.copy),
                joinedload(BookReservation.member).joinedload(LibraryMember.student),
                joinedload(BookReservation.member).joinedload(LibraryMember.teacher),
                joinedload(BookReservation.member).joinedload(LibraryMember.staff),
            )
            .filter(BookReservation.is_deleted == False)
        )
        if status:
            if status == "Active":
                query = query.filter(BookReservation.status.in_(["Pending", "Ready"]))
            else:
                query = query.filter(BookReservation.status == status)
        if book_id:
            query = query.filter(BookReservation.book_id == book_id)
        if member_id:
            query = query.filter(BookReservation.member_id == member_id)
        return query.order_by(BookReservation.priority_order.asc(), BookReservation.id.desc()).all()

    @staticmethod
    def cancel_reservation(session: Session, reservation_id: int, new_status: str = "Cancelled") -> Tuple[bool, Optional[str]]:
        res = (
            session.query(BookReservation)
            .options(joinedload(BookReservation.book), joinedload(BookReservation.copy))
            .filter(BookReservation.id == reservation_id)
            .first()
        )
        if not res:
            return False, "Reservation not found."
        if res.status in ("Fulfilled", "Cancelled", "Expired"):
            return False, f"Reservation is already {res.status}."

        res.status = new_status
        if res.copy and res.copy.status == "Reserved":
            # Reassign to next pending reservation or release back to Available
            next_res = (
                session.query(BookReservation)
                .filter(
                    BookReservation.book_id == res.book_id,
                    BookReservation.id != res.id,
                    BookReservation.status == "Pending",
                )
                .order_by(BookReservation.priority_order.asc(), BookReservation.id.asc())
                .first()
            )
            if next_res:
                next_res.status = "Ready"
                next_res.copy_id = res.copy.id
                next_res.ready_date = date.today().isoformat()
            else:
                res.copy.status = "Available"
                if res.book:
                    LibraryRepository._sync_book_copy_counts(session, res.book)

        session.commit()
        return True, None

    # ---------------- Fine Ledger Operations ----------------
    @staticmethod
    def get_fines(
        session: Session,
        status: Optional[str] = None,
        member_id: Optional[int] = None,
        fine_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[LibraryFine]:
        query = (
            session.query(LibraryFine)
            .options(
                joinedload(LibraryFine.book),
                joinedload(LibraryFine.circulation),
                joinedload(LibraryFine.member).joinedload(LibraryMember.student),
                joinedload(LibraryFine.member).joinedload(LibraryMember.teacher),
                joinedload(LibraryFine.member).joinedload(LibraryMember.staff),
            )
            .filter(LibraryFine.is_deleted == False)
        )
        if status:
            if status == "Outstanding":
                query = query.filter(LibraryFine.status.in_(["Unpaid", "Partial"]))
            else:
                query = query.filter(LibraryFine.status == status)
        if member_id:
            query = query.filter(LibraryFine.member_id == member_id)
        if fine_type:
            query = query.filter(LibraryFine.fine_type == fine_type)
        if date_from:
            query = query.filter(LibraryFine.assessed_date >= date_from)
        if date_to:
            query = query.filter(LibraryFine.assessed_date <= date_to)
        return query.order_by(LibraryFine.id.desc()).all()

    @staticmethod
    def collect_fine_payment(
        session: Session,
        fine_id: int,
        amount: float,
        payment_method: str = "Cash",
        collected_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[LibraryFine], Optional[str]]:
        fine = session.query(LibraryFine).filter(LibraryFine.id == fine_id).first()
        if not fine:
            return None, "Fine record not found."
        if fine.status in ("Paid", "Waived"):
            return None, f"Fine is already {fine.status}."

        pay_amt = round(float(amount or 0.0), 2)
        if pay_amt <= 0:
            return None, "Payment amount must be greater than zero."

        due = fine.balance_due
        if pay_amt > due + 0.001:
            return None, f"Payment (${pay_amt:.2f}) exceeds remaining balance due (${due:.2f})."

        fine.paid_amount = round(float(fine.paid_amount or 0.0) + pay_amt, 2)
        fine.paid_date = date.today().isoformat()
        fine.payment_method = payment_method
        if not fine.receipt_no:
            fine.receipt_no = f"RCPT-{uuid.uuid4().hex[:6].upper()}"
        fine.collected_by = collected_by
        if notes:
            fine.notes = notes

        if fine.balance_due <= 0.001:
            fine.status = "Paid"
            if fine.circulation_id:
                circ = session.query(BookCirculation).filter(BookCirculation.id == fine.circulation_id).first()
                if circ:
                    circ.fine_paid = True
        else:
            fine.status = "Partial"

        session.commit()
        session.refresh(fine)
        return fine, None

    @staticmethod
    def waive_fine(
        session: Session,
        fine_id: int,
        reason: str,
        waived_by: Optional[str] = None,
    ) -> Tuple[Optional[LibraryFine], Optional[str]]:
        fine = session.query(LibraryFine).filter(LibraryFine.id == fine_id).first()
        if not fine:
            return None, "Fine record not found."
        if fine.status in ("Paid", "Waived"):
            return None, f"Fine is already {fine.status}."

        due = fine.balance_due
        fine.waived_amount = round(float(fine.waived_amount or 0.0) + due, 2)
        fine.status = "Waived"
        fine.waive_reason = reason.strip() or "Administrative Waiver"
        fine.collected_by = waived_by
        if fine.circulation_id:
            circ = session.query(BookCirculation).filter(BookCirculation.id == fine.circulation_id).first()
            if circ:
                circ.fine_paid = True

        session.commit()
        session.refresh(fine)
        return fine, None

    # ---------------- Lost & Damaged Book Incident Operations ----------------
    @staticmethod
    def report_book_incident(
        session: Session,
        book_id: int,
        incident_type: str,
        copy_id: Optional[int] = None,
        circulation_id: Optional[int] = None,
        member_id: Optional[int] = None,
        severity: str = "Major",
        incident_date: Optional[str] = None,
        description: Optional[str] = None,
        replacement_cost: Optional[float] = None,
        fine_assessed: float = 0.0,
        reported_by: Optional[str] = None,
    ) -> Tuple[Optional[BookIncident], Optional[str]]:
        if incident_type not in ("Lost", "Damaged"):
            return None, "Incident type must be 'Lost' or 'Damaged'."

        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None, "Book not found."

        inc_date = incident_date or date.today().isoformat()
        circ: Optional[BookCirculation] = None
        if circulation_id:
            circ = session.query(BookCirculation).filter(BookCirculation.id == circulation_id).first()
            if circ:
                member_id = member_id or circ.member_id
                copy_id = copy_id or circ.copy_id
                circ.status = incident_type
                circ.return_date = inc_date
                circ.return_condition = incident_type
                circ.damage_or_lost_fee = float(fine_assessed or 0.0)
                circ.fine_paid = float(fine_assessed or 0.0) == 0.0

        copy_obj: Optional[BookCopy] = None
        if copy_id:
            copy_obj = session.query(BookCopy).filter(BookCopy.id == copy_id, BookCopy.book_id == book_id).first()
        else:
            copy_obj = (
                session.query(BookCopy)
                .filter(BookCopy.book_id == book_id, BookCopy.status == "Available")
                .order_by(BookCopy.copy_number.asc())
                .first()
            )

        if copy_obj:
            copy_obj.status = incident_type
            copy_obj.condition = incident_type
            LibraryRepository._sync_book_copy_counts(session, book)
        else:
            if circ and book.issued_copies > 0:
                book.issued_copies -= 1
            elif book.available_copies > 0:
                book.available_copies -= 1
            if incident_type == "Lost":
                book.lost_copies = (book.lost_copies or 0) + 1
            else:
                book.damaged_copies = (book.damaged_copies or 0) + 1

        rep_cost = round(float(replacement_cost if replacement_cost is not None else (book.price or 0.0)), 2)
        fine_amt = round(float(fine_assessed or 0.0), 2)

        fine_obj: Optional[LibraryFine] = None
        if fine_amt > 0 and member_id:
            fine_obj = LibraryRepository._create_fine_record(
                session,
                member_id=member_id,
                fine_type=incident_type,
                amount=fine_amt,
                assessed_date=inc_date,
                circulation_id=circulation_id,
                book_id=book_id,
                copy_id=copy_obj.id if copy_obj else None,
                paid=False,
                notes=description or f"{incident_type} book assessment",
            )

        inc = BookIncident(
            incident_code=f"INC-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            book_id=book_id,
            copy_id=copy_obj.id if copy_obj else None,
            circulation_id=circulation_id,
            member_id=member_id,
            fine_id=fine_obj.id if fine_obj else None,
            incident_type=incident_type,
            severity="Total Loss" if incident_type == "Lost" else severity,
            incident_date=inc_date,
            description=description,
            replacement_cost=rep_cost,
            fine_assessed=fine_amt,
            resolution_status="Billed" if fine_amt > 0 else "Reported",
            resolved_by=reported_by,
        )
        session.add(inc)
        session.commit()
        session.refresh(inc)
        return inc, None

    @staticmethod
    def resolve_book_incident(
        session: Session,
        incident_id: int,
        resolution_status: str,
        resolved_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[BookIncident], Optional[str]]:
        inc = (
            session.query(BookIncident)
            .options(joinedload(BookIncident.book), joinedload(BookIncident.copy))
            .filter(BookIncident.id == incident_id)
            .first()
        )
        if not inc:
            return None, "Incident record not found."

        inc.resolution_status = resolution_status
        inc.resolved_date = date.today().isoformat()
        inc.resolved_by = resolved_by
        if notes:
            inc.notes = notes

        # If repaired or replaced, restore copy to Available shelf stock
        if resolution_status in ("Repaired", "Replaced"):
            if inc.copy:
                inc.copy.status = "Available"
                inc.copy.condition = "Good"
                if inc.book:
                    LibraryRepository._sync_book_copy_counts(session, inc.book)
            elif inc.book:
                if inc.incident_type == "Lost" and (inc.book.lost_copies or 0) > 0:
                    inc.book.lost_copies -= 1
                    inc.book.available_copies += 1
                elif inc.incident_type == "Damaged" and (inc.book.damaged_copies or 0) > 0:
                    inc.book.damaged_copies -= 1
                    inc.book.available_copies += 1
                inc.book.status = "Available" if inc.book.available_copies > 0 else inc.book.status
        elif resolution_status == "Written Off" and inc.copy:
            inc.copy.status = "Retired"
            if inc.book:
                LibraryRepository._sync_book_copy_counts(session, inc.book)

        session.commit()
        session.refresh(inc)
        return inc, None

    @staticmethod
    def get_incidents(
        session: Session,
        incident_type: Optional[str] = None,
        resolution_status: Optional[str] = None,
    ) -> List[BookIncident]:
        query = (
            session.query(BookIncident)
            .options(
                joinedload(BookIncident.book),
                joinedload(BookIncident.copy),
                joinedload(BookIncident.member).joinedload(LibraryMember.student),
                joinedload(BookIncident.member).joinedload(LibraryMember.teacher),
                joinedload(BookIncident.member).joinedload(LibraryMember.staff),
                joinedload(BookIncident.fine),
            )
            .filter(BookIncident.is_deleted == False)
        )
        if incident_type:
            query = query.filter(BookIncident.incident_type == incident_type)
        if resolution_status:
            query = query.filter(BookIncident.resolution_status == resolution_status)
        return query.order_by(BookIncident.id.desc()).all()

    # ---------------- Statistics & Analytics ----------------
    @staticmethod
    def get_library_stats(session: Session) -> Dict[str, Any]:
        """Calculates real-time library KPI metrics directly from database records."""
        books = session.query(Book).filter(Book.is_deleted == False).all()
        total_books = len(books)
        total_copies = sum(b.total_copies or 0 for b in books)
        total_available = sum(b.available_copies or 0 for b in books)
        total_lost = sum(b.lost_copies or 0 for b in books)
        total_damaged = sum(b.damaged_copies or 0 for b in books)
        catalog_valuation = round(sum(float(b.price or 0.0) * (b.total_copies or 0) for b in books), 2)

        total_issued = (
            session.query(BookCirculation)
            .filter(BookCirculation.status.in_(ACTIVE_LOAN_STATUSES))
            .count()
        )

        today_str = date.today().isoformat()
        overdue_count = (
            session.query(BookCirculation)
            .filter(
                BookCirculation.status.in_(ACTIVE_LOAN_STATUSES),
                BookCirculation.due_date < today_str,
            )
            .count()
        )

        total_members = session.query(LibraryMember).filter(LibraryMember.status == "Active").count()
        active_reservations = (
            session.query(BookReservation)
            .filter(BookReservation.status.in_(["Pending", "Ready"]))
            .count()
        )

        fines = session.query(LibraryFine).filter(LibraryFine.is_deleted == False).all()
        if fines:
            total_fine_collected = round(sum(float(f.paid_amount or 0.0) for f in fines), 2)
            unpaid_fines_total = round(sum(f.balance_due for f in fines if f.status in ("Unpaid", "Partial")), 2)
        else:
            # Fallback compatibility if BookCirculation fine_paid records exist without LibraryFine rows
            total_fine_collected = round(
                sum(
                    float(c.fine_amount or 0.0)
                    for c in session.query(BookCirculation).filter(BookCirculation.fine_paid == True).all()
                ),
                2,
            )
            unpaid_fines_total = 0.0

        return {
            "total_titles": total_books,
            "total_inventory_copies": total_copies,
            "available_copies": total_available,
            "currently_issued": total_issued,
            "overdue_count": overdue_count,
            "lost_copies": total_lost,
            "damaged_copies": total_damaged,
            "active_members": total_members,
            "active_reservations": active_reservations,
            "total_fine_collected": total_fine_collected,
            "unpaid_fines_total": unpaid_fines_total,
            "catalog_valuation": catalog_valuation,
            "total_authors": session.query(LibraryAuthor).filter(LibraryAuthor.is_deleted == False).count(),
            "total_publishers": session.query(LibraryPublisher).filter(LibraryPublisher.is_deleted == False).count(),
            "total_shelves": session.query(LibraryShelf).filter(LibraryShelf.is_deleted == False).count(),
        }
