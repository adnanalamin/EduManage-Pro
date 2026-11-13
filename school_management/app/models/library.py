"""
EduManage Pro - Library Management ORM Models
Phase 10: Books, Categories, Library Members & Book Circulation
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Text, Numeric, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class BookCategory(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a classification category for books (e.g., Science, Literature, ICT)."""
    __tablename__ = "book_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    books = relationship("Book", back_populates="category")

    def __repr__(self):
        return f"<BookCategory {self.code}: {self.name}>"


class Book(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a book title in the library catalog."""
    __tablename__ = "library_books"

    accession_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False, index=True)
    author = Column(String(150), nullable=False, index=True)
    publisher = Column(String(150), nullable=True)
    isbn = Column(String(30), nullable=True, index=True)
    edition = Column(String(50), nullable=True)
    publication_year = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey("book_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    rack_number = Column(String(50), nullable=True)  # e.g., "Rack 04"
    shelf_number = Column(String(50), nullable=True)  # e.g., "Shelf B"
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    issued_copies = Column(Integer, default=0, nullable=False)
    lost_copies = Column(Integer, default=0, nullable=False)
    price = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    status = Column(String(30), default="Available", nullable=False, index=True)

    # Relationships
    category = relationship("BookCategory", back_populates="books")
    circulations = relationship("BookCirculation", back_populates="book")

    __table_args__ = (
        CheckConstraint(
            "total_copies >= 0 AND available_copies >= 0 AND issued_copies >= 0 AND lost_copies >= 0",
            name="ck_library_book_copies_nonneg",
        ),
        Index("idx_library_book_status", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Book {self.accession_no}: '{self.title}' ({self.available_copies}/{self.total_copies})>"


class LibraryMember(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a registered library borrower (student, teacher, or staff)."""
    __tablename__ = "library_members"

    member_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "LIB-STD-001"
    member_type = Column(String(20), nullable=False, index=True)  # "Student", "Teacher", "Staff"
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)
    card_issue_date = Column(String(20), nullable=False)
    max_allowed_books = Column(Integer, default=3, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Suspended, Expired

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    circulations = relationship("BookCirculation", back_populates="member")

    __table_args__ = (
        CheckConstraint("max_allowed_books > 0", name="ck_library_member_max_books"),
    )

    def __repr__(self):
        return f"<LibraryMember {self.member_id} ({self.member_type})>"


class BookCirculation(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a book borrowing transaction (issue, return, due date, fine)."""
    __tablename__ = "book_circulations"

    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("library_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    issue_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    due_date = Column(String(20), nullable=False, index=True)    # YYYY-MM-DD
    return_date = Column(String(20), nullable=True)  # YYYY-MM-DD when returned
    status = Column(String(30), default="Issued", nullable=False, index=True)   # Issued, Returned, Overdue, Lost
    fine_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    fine_paid = Column(Boolean, default=False, nullable=False)
    remarks = Column(Text, nullable=True)
    issued_by = Column(String(100), nullable=True)

    # Relationships
    book = relationship("Book", back_populates="circulations")
    member = relationship("LibraryMember", back_populates="circulations")

    __table_args__ = (
        CheckConstraint("fine_amount >= 0", name="ck_book_circulation_fine_nonneg"),
        Index("idx_book_circ_status_due", "status", "due_date"),
    )

    def __repr__(self):
        return f"<BookCirculation Book {self.book_id} -> Member {self.member_id} ({self.status})>"
