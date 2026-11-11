"""
EduManage Pro - Library Management ORM Models
Phase 10: Books, Categories, Library Members & Book Circulation
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class BookCategory(Base):
    """Represents a classification category for books (e.g., Science, Literature, ICT)."""
    __tablename__ = "book_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)

    books = relationship("Book", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BookCategory {self.code}: {self.name}>"


class Book(Base):
    """Represents a book title in the library catalog."""
    __tablename__ = "library_books"

    id = Column(Integer, primary_key=True, index=True)
    accession_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False, index=True)
    author = Column(String(150), nullable=False, index=True)
    publisher = Column(String(150), nullable=True)
    isbn = Column(String(30), nullable=True, index=True)
    edition = Column(String(50), nullable=True)
    publication_year = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey("book_categories.id"), nullable=False)
    rack_number = Column(String(50), nullable=True)  # e.g., "Rack 04"
    shelf_number = Column(String(50), nullable=True)  # e.g., "Shelf B"
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    issued_copies = Column(Integer, default=0, nullable=False)
    lost_copies = Column(Integer, default=0, nullable=False)
    price = Column(Float, default=0.0)
    status = Column(String(30), default="Available")  # Available, Out of Stock, Discontinued
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    category = relationship("BookCategory", back_populates="books")
    circulations = relationship("BookCirculation", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Book {self.accession_no}: '{self.title}' ({self.available_copies}/{self.total_copies})>"


class LibraryMember(Base):
    """Represents a registered library borrower (student, teacher, or staff)."""
    __tablename__ = "library_members"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "LIB-STD-001"
    member_type = Column(String(20), nullable=False)  # "Student", "Teacher", "Staff"
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    card_issue_date = Column(String(20), nullable=False)
    max_allowed_books = Column(Integer, default=3)
    status = Column(String(20), default="Active")  # Active, Suspended, Expired
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    circulations = relationship("BookCirculation", back_populates="member", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LibraryMember {self.member_id} ({self.member_type})>"


class BookCirculation(Base):
    """Represents a book borrowing transaction (issue, return, due date, fine)."""
    __tablename__ = "book_circulations"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("library_books.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("library_members.id"), nullable=False)
    issue_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    due_date = Column(String(20), nullable=False)    # YYYY-MM-DD
    return_date = Column(String(20), nullable=True)  # YYYY-MM-DD when returned
    status = Column(String(30), default="Issued")   # Issued, Returned, Overdue, Lost
    fine_amount = Column(Float, default=0.0)
    fine_paid = Column(Boolean, default=False)
    remarks = Column(Text, nullable=True)
    issued_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    book = relationship("Book", back_populates="circulations")
    member = relationship("LibraryMember", back_populates="circulations")

    def __repr__(self):
        return f"<BookCirculation Book {self.book_id} -> Member {self.member_id} ({self.status})>"
