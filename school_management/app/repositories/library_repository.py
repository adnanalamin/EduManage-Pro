"""
EduManage Pro - Library Repository
Phase 10: Book Inventory, Member Register, Loan Circulation & Fine Aggregations
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from app.models.library import BookCategory, Book, LibraryMember, BookCirculation
from app.models.student import Student
from app.models.staff import Teacher, Staff


class LibraryRepository:
    """Repository handling book inventory, member cards, issue/returns, and fines."""

    # ---------------- Category Operations ----------------
    @staticmethod
    def get_categories(session: Session) -> List[BookCategory]:
        return session.query(BookCategory).order_by(BookCategory.name.asc()).all()

    @staticmethod
    def create_category(session: Session, name: str, code: str, description: Optional[str] = None) -> BookCategory:
        cat = BookCategory(name=name, code=code, description=description)
        session.add(cat)
        session.commit()
        session.refresh(cat)
        return cat

    # ---------------- Book Inventory Operations ----------------
    @staticmethod
    def get_books(
        session: Session,
        category_id: Optional[int] = None,
        search_query: Optional[str] = None,
        only_available: bool = False
    ) -> List[Book]:
        query = session.query(Book).options(joinedload(Book.category))
        if category_id:
            query = query.filter(Book.category_id == category_id)
        if only_available:
            query = query.filter(Book.available_copies > 0)
        if search_query:
            q = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Book.title.ilike(q),
                    Book.author.ilike(q),
                    Book.isbn.ilike(q),
                    Book.accession_no.ilike(q)
                )
            )
        return query.order_by(Book.id.desc()).all()

    @staticmethod
    def get_book_by_id(session: Session, book_id: int) -> Optional[Book]:
        return session.query(Book).options(joinedload(Book.category)).filter(Book.id == book_id).first()

    @staticmethod
    def get_book_by_accession(session: Session, accession_no: str) -> Optional[Book]:
        return session.query(Book).filter(Book.accession_no == accession_no.strip()).first()

    @staticmethod
    def create_book(session: Session, **kwargs) -> Book:
        if "available_copies" not in kwargs:
            kwargs["available_copies"] = kwargs.get("total_copies", 1)
        book = Book(**kwargs)
        session.add(book)
        session.commit()
        session.refresh(book)
        return book

    @staticmethod
    def update_book(session: Session, book_id: int, **kwargs) -> Optional[Book]:
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None
        for k, v in kwargs.items():
            if hasattr(book, k):
                setattr(book, k, v)
        # Recalculate available copies if total changed
        if "total_copies" in kwargs:
            book.available_copies = max(0, book.total_copies - book.issued_copies - book.lost_copies)
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

    # ---------------- Library Member Operations ----------------
    @staticmethod
    def get_members(session: Session, member_type: Optional[str] = None) -> List[LibraryMember]:
        query = session.query(LibraryMember).options(
            joinedload(LibraryMember.student),
            joinedload(LibraryMember.teacher),
            joinedload(LibraryMember.staff)
        )
        if member_type:
            query = query.filter(LibraryMember.member_type == member_type)
        return query.order_by(LibraryMember.id.desc()).all()

    @staticmethod
    def get_member_by_id(session: Session, member_id: int) -> Optional[LibraryMember]:
        return session.query(LibraryMember).options(
            joinedload(LibraryMember.student),
            joinedload(LibraryMember.teacher),
            joinedload(LibraryMember.staff)
        ).filter(LibraryMember.id == member_id).first()

    @staticmethod
    def get_member_by_code(session: Session, member_code: str) -> Optional[LibraryMember]:
        return session.query(LibraryMember).filter(LibraryMember.member_id == member_code.strip()).first()

    @staticmethod
    def create_member(session: Session, **kwargs) -> LibraryMember:
        member = LibraryMember(**kwargs)
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

    # ---------------- Circulation (Issue / Return / Fines) ----------------
    @staticmethod
    def issue_book(
        session: Session,
        book_id: int,
        member_id: int,
        issue_date: str,
        due_date: str,
        issued_by: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> Tuple[Optional[BookCirculation], Optional[str]]:
        """
        Validates borrower eligibility and book availability, then creates loan record.
        """
        book = session.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None, "Book not found."
        if book.available_copies <= 0:
            return None, f"'{book.title}' has no copies currently available."

        member = session.query(LibraryMember).filter(LibraryMember.id == member_id).first()
        if not member:
            return None, "Library member borrower not found."
        if member.status != "Active":
            return None, f"Member '{member.member_id}' is {member.status} and cannot borrow books."

        # Check borrower's active loans count
        active_loans = session.query(BookCirculation).filter(
            BookCirculation.member_id == member_id,
            BookCirculation.status.in_(["Issued", "Overdue"])
        ).count()
        if active_loans >= member.max_allowed_books:
            return None, f"Member has reached their maximum quota of {member.max_allowed_books} borrowed books."

        # Decrement book copies
        book.available_copies -= 1
        book.issued_copies += 1
        if book.available_copies == 0:
            book.status = "Out of Stock"

        circulation = BookCirculation(
            book_id=book_id,
            member_id=member_id,
            issue_date=issue_date,
            due_date=due_date,
            status="Issued",
            issued_by=issued_by,
            remarks=remarks
        )
        session.add(circulation)
        session.commit()
        session.refresh(circulation)
        return circulation, None

    @staticmethod
    def return_book(
        session: Session,
        circulation_id: int,
        return_date: str,
        fine_rate_per_day: float = 5.0,
        fine_paid: bool = False,
        remarks: Optional[str] = None
    ) -> Tuple[Optional[BookCirculation], Optional[str]]:
        """
        Processes book check-in, calculates overdue days & fines, and replenishes copy inventory.
        """
        circ = session.query(BookCirculation).options(
            joinedload(BookCirculation.book),
            joinedload(BookCirculation.member)
        ).filter(BookCirculation.id == circulation_id).first()
        if not circ:
            return None, "Circulation record not found."
        if circ.status == "Returned":
            return None, "This book has already been returned."

        # Calculate overdue days
        try:
            d_due = datetime.strptime(circ.due_date, "%Y-%m-%d").date()
            d_ret = datetime.strptime(return_date, "%Y-%m-%d").date()
            overdue_days = max(0, (d_ret - d_due).days)
        except Exception:
            overdue_days = 0

        fine_amt = overdue_days * fine_rate_per_day

        circ.return_date = return_date
        circ.status = "Returned"
        circ.fine_amount = fine_amt
        circ.fine_paid = fine_paid or (fine_amt == 0)
        if remarks:
            circ.remarks = remarks

        # Restore book inventory copies
        if circ.book:
            circ.book.available_copies += 1
            circ.book.issued_copies = max(0, circ.book.issued_copies - 1)
            circ.book.status = "Available"

        session.commit()
        session.refresh(circ)
        return circ, None

    @staticmethod
    def get_circulations(
        session: Session,
        status: Optional[str] = None,
        member_id: Optional[int] = None,
        book_id: Optional[int] = None
    ) -> List[BookCirculation]:
        query = session.query(BookCirculation).options(
            joinedload(BookCirculation.book),
            joinedload(BookCirculation.member).joinedload(LibraryMember.student),
            joinedload(BookCirculation.member).joinedload(LibraryMember.teacher)
        )
        if status:
            if status == "Active":
                query = query.filter(BookCirculation.status.in_(["Issued", "Overdue"]))
            else:
                query = query.filter(BookCirculation.status == status)
        if member_id:
            query = query.filter(BookCirculation.member_id == member_id)
        if book_id:
            query = query.filter(BookCirculation.book_id == book_id)

        return query.order_by(BookCirculation.id.desc()).all()

    @staticmethod
    def get_library_stats(session: Session) -> Dict[str, Any]:
        """Calculates library KPI metrics for dashboard cards."""
        total_books = session.query(Book).count()
        total_copies = sum(b.total_copies for b in session.query(Book).all())
        total_available = sum(b.available_copies for b in session.query(Book).all())
        total_issued = session.query(BookCirculation).filter(BookCirculation.status.in_(["Issued", "Overdue"])).count()
        
        # Check overdue count
        today_str = date.today().isoformat()
        overdue_count = session.query(BookCirculation).filter(
            BookCirculation.status.in_(["Issued", "Overdue"]),
            BookCirculation.due_date < today_str
        ).count()

        total_members = session.query(LibraryMember).filter(LibraryMember.status == "Active").count()
        total_fine_collected = sum(c.fine_amount for c in session.query(BookCirculation).filter(BookCirculation.fine_paid == True).all())

        return {
            "total_titles": total_books,
            "total_inventory_copies": total_copies,
            "available_copies": total_available,
            "currently_issued": total_issued,
            "overdue_count": overdue_count,
            "active_members": total_members,
            "total_fine_collected": total_fine_collected,
        }
