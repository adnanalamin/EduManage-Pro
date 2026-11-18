"""
EduManage Pro - Enterprise Library Management ORM Models
Books, Authors, Publishers, Categories, Shelves, Physical Copies, Members,
Circulations, Renewals, Reservations, Fines, and Lost/Damaged Book Incidents.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Text,
    Numeric,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class LibraryAuthor(Base, TimestampMixin, SoftDeleteMixin):
    """Normalized catalog author directory."""
    __tablename__ = "library_authors"

    name = Column(String(150), unique=True, nullable=False, index=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    country = Column(String(80), nullable=True)
    website = Column(String(200), nullable=True)
    biography = Column(Text, nullable=True)

    books = relationship("Book", back_populates="author_ref")

    def __repr__(self):
        return f"<LibraryAuthor {self.code}: {self.name}>"


class LibraryPublisher(Base, TimestampMixin, SoftDeleteMixin):
    """Normalized publisher directory."""
    __tablename__ = "library_publishers"

    name = Column(String(150), unique=True, nullable=False, index=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    contact_email = Column(String(120), nullable=True)
    phone = Column(String(40), nullable=True)
    address = Column(Text, nullable=True)
    country = Column(String(80), nullable=True)
    website = Column(String(200), nullable=True)

    books = relationship("Book", back_populates="publisher_ref")

    def __repr__(self):
        return f"<LibraryPublisher {self.code}: {self.name}>"


class BookCategory(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a classification category for books (e.g., Science, Literature, ICT)."""
    __tablename__ = "book_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(20), unique=True, nullable=False)
    ddc_code = Column(String(30), nullable=True)
    default_loan_days = Column(Integer, default=14, nullable=False)
    description = Column(String(255), nullable=True)

    books = relationship("Book", back_populates="category")
    shelves = relationship("LibraryShelf", back_populates="category")

    def __repr__(self):
        return f"<BookCategory {self.code}: {self.name}>"


class LibraryShelf(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a physical rack/shelf location in the library."""
    __tablename__ = "library_shelves"

    shelf_code = Column(String(50), unique=True, nullable=False, index=True)
    rack_number = Column(String(50), nullable=False, index=True)
    shelf_number = Column(String(50), nullable=False)
    floor = Column(String(40), nullable=True)
    section_zone = Column(String(80), nullable=True)
    category_id = Column(
        Integer,
        ForeignKey("book_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    capacity = Column(Integer, default=100, nullable=False)
    description = Column(String(255), nullable=True)

    category = relationship("BookCategory", back_populates="shelves")
    books = relationship("Book", back_populates="shelf_ref")
    copies = relationship("BookCopy", back_populates="shelf")

    __table_args__ = (
        CheckConstraint("capacity >= 0", name="ck_library_shelf_capacity_nonneg"),
    )

    def __repr__(self):
        return f"<LibraryShelf {self.shelf_code} ({self.rack_number}/{self.shelf_number})>"


class Book(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a book title in the library catalog."""
    __tablename__ = "library_books"

    accession_no = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False, index=True)
    author = Column(String(150), nullable=False, index=True)
    author_id = Column(
        Integer,
        ForeignKey("library_authors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    publisher = Column(String(150), nullable=True)
    publisher_id = Column(
        Integer,
        ForeignKey("library_publishers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    isbn = Column(String(30), nullable=True, index=True)
    isbn_10 = Column(String(20), nullable=True, index=True)
    isbn_13 = Column(String(25), nullable=True, index=True)
    barcode = Column(String(64), unique=True, nullable=True, index=True)
    qr_payload = Column(String(255), nullable=True)
    call_number = Column(String(60), nullable=True, index=True)
    edition = Column(String(50), nullable=True)
    publication_year = Column(Integer, nullable=True)
    language = Column(String(50), default="English", nullable=True)
    pages = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    category_id = Column(
        Integer,
        ForeignKey("book_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    shelf_id = Column(
        Integer,
        ForeignKey("library_shelves.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rack_number = Column(String(50), nullable=True)   # e.g., "Rack 04"
    shelf_number = Column(String(50), nullable=True)  # e.g., "Shelf B"

    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    issued_copies = Column(Integer, default=0, nullable=False)
    lost_copies = Column(Integer, default=0, nullable=False)
    damaged_copies = Column(Integer, default=0, nullable=False)
    price = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    status = Column(String(30), default="Available", nullable=False, index=True)

    # Relationships
    category = relationship("BookCategory", back_populates="books")
    author_ref = relationship("LibraryAuthor", back_populates="books")
    publisher_ref = relationship("LibraryPublisher", back_populates="books")
    shelf_ref = relationship("LibraryShelf", back_populates="books")
    copies = relationship(
        "BookCopy",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="BookCopy.copy_number.asc(), BookCopy.id.asc()",
    )
    circulations = relationship("BookCirculation", back_populates="book")
    reservations = relationship("BookReservation", back_populates="book")
    incidents = relationship("BookIncident", back_populates="book")

    __table_args__ = (
        CheckConstraint(
            "total_copies >= 0 AND available_copies >= 0 AND issued_copies >= 0 "
            "AND lost_copies >= 0 AND damaged_copies >= 0",
            name="ck_library_book_copies_nonneg",
        ),
        Index("idx_library_book_status", "status", "is_deleted"),
    )

    def __repr__(self):
        return f"<Book {self.accession_no}: '{self.title}' ({self.available_copies}/{self.total_copies})>"


class BookCopy(Base, TimestampMixin, SoftDeleteMixin):
    """Represents an individual barcoded physical copy of a cataloged book."""
    __tablename__ = "library_book_copies"

    book_id = Column(
        Integer,
        ForeignKey("library_books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    copy_code = Column(String(64), unique=True, nullable=False, index=True)
    copy_number = Column(Integer, default=1, nullable=False)
    barcode = Column(String(64), unique=True, nullable=False, index=True)
    qr_payload = Column(String(255), nullable=True)
    shelf_id = Column(
        Integer,
        ForeignKey("library_shelves.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    condition = Column(String(30), default="Good", nullable=False)  # Good, Fair, Damaged, Lost, Retired
    status = Column(String(30), default="Available", nullable=False, index=True)  # Available, Issued, Reserved, Lost, Damaged, Retired
    purchase_date = Column(String(20), nullable=True)
    purchase_price = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    notes = Column(Text, nullable=True)

    book = relationship("Book", back_populates="copies")
    shelf = relationship("LibraryShelf", back_populates="copies")
    circulations = relationship("BookCirculation", back_populates="copy")
    incidents = relationship("BookIncident", back_populates="copy")

    __table_args__ = (
        CheckConstraint("copy_number >= 1", name="ck_library_copy_number_pos"),
        Index("idx_book_copy_status", "book_id", "status"),
    )

    def __repr__(self):
        return f"<BookCopy {self.copy_code} ({self.status}/{self.condition})>"


class LibraryMember(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a registered library borrower (student, teacher, or staff)."""
    __tablename__ = "library_members"

    member_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "LIB-STD-001"
    member_type = Column(String(20), nullable=False, index=True)  # "Student", "Teacher", "Staff"
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)

    full_name_override = Column(String(120), nullable=True)
    phone = Column(String(40), nullable=True)
    email = Column(String(120), nullable=True)
    barcode = Column(String(64), unique=True, nullable=True, index=True)
    qr_payload = Column(String(255), nullable=True)

    card_issue_date = Column(String(20), nullable=False)
    card_expiry_date = Column(String(20), nullable=True)
    max_allowed_books = Column(Integer, default=3, nullable=False)
    max_loan_days = Column(Integer, default=14, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Suspended, Expired
    notes = Column(Text, nullable=True)

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    circulations = relationship("BookCirculation", back_populates="member")
    reservations = relationship("BookReservation", back_populates="member")
    fines = relationship("LibraryFine", back_populates="member")
    incidents = relationship("BookIncident", back_populates="member")

    __table_args__ = (
        CheckConstraint("max_allowed_books > 0", name="ck_library_member_max_books"),
    )

    @property
    def display_name(self) -> str:
        if self.student:
            return self.student.full_name
        if self.teacher:
            return self.teacher.full_name
        if self.staff:
            return self.staff.full_name
        return self.full_name_override or self.member_id

    @property
    def affiliation_label(self) -> str:
        if self.student:
            cls_name = self.student.school_class.name if self.student.school_class else "-"
            return f"Class {cls_name} | Roll {self.student.roll_number}"
        if self.teacher:
            return f"{self.teacher.designation or 'Faculty'}"
        if self.staff:
            pos = getattr(self.staff, "position", None) or "Staff"
            return f"{pos}"
        return self.member_type

    def __repr__(self):
        return f"<LibraryMember {self.member_id} ({self.member_type})>"


class BookReservation(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a member's hold/reservation request for a book title."""
    __tablename__ = "library_reservations"

    reservation_code = Column(String(50), unique=True, nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("library_book_copies.id", ondelete="SET NULL"), nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("library_members.id", ondelete="CASCADE"), nullable=False, index=True)
    reserved_date = Column(String(20), nullable=False)
    expiry_date = Column(String(20), nullable=True, index=True)
    ready_date = Column(String(20), nullable=True)
    fulfilled_date = Column(String(20), nullable=True)
    status = Column(String(20), default="Pending", nullable=False, index=True)  # Pending, Ready, Fulfilled, Cancelled, Expired
    priority_order = Column(Integer, default=1, nullable=False)
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    book = relationship("Book", back_populates="reservations")
    copy = relationship("BookCopy")
    member = relationship("LibraryMember", back_populates="reservations")

    __table_args__ = (
        Index("idx_library_res_book_status", "book_id", "status"),
    )

    def __repr__(self):
        return f"<BookReservation {self.reservation_code}: Book {self.book_id} -> Member {self.member_id} ({self.status})>"


class BookCirculation(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a book borrowing transaction (issue, renewal, return, due date, fine)."""
    __tablename__ = "book_circulations"

    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="RESTRICT"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("library_book_copies.id", ondelete="SET NULL"), nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("library_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    reservation_id = Column(Integer, ForeignKey("library_reservations.id", ondelete="SET NULL"), nullable=True)

    issue_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    due_date = Column(String(20), nullable=False, index=True)    # YYYY-MM-DD
    return_date = Column(String(20), nullable=True)  # YYYY-MM-DD when returned
    status = Column(String(30), default="Issued", nullable=False, index=True)   # Issued, Renewed, Overdue, Returned, Lost, Damaged

    renewal_count = Column(Integer, default=0, nullable=False)
    max_renewals = Column(Integer, default=2, nullable=False)
    last_renewed_at = Column(String(20), nullable=True)
    return_condition = Column(String(30), nullable=True)  # Good, Damaged, Lost

    fine_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    damage_or_lost_fee = Column(Numeric(12, 2, asdecimal=False), default=0.0)
    fine_paid = Column(Boolean, default=False, nullable=False)
    remarks = Column(Text, nullable=True)
    issued_by = Column(String(100), nullable=True)
    returned_to = Column(String(100), nullable=True)

    # Relationships
    book = relationship("Book", back_populates="circulations")
    copy = relationship("BookCopy", back_populates="circulations")
    member = relationship("LibraryMember", back_populates="circulations")
    reservation = relationship("BookReservation")
    fines = relationship("LibraryFine", back_populates="circulation")

    __table_args__ = (
        CheckConstraint("fine_amount >= 0 AND damage_or_lost_fee >= 0", name="ck_book_circulation_fine_nonneg"),
        CheckConstraint("renewal_count >= 0", name="ck_book_circulation_renewal_nonneg"),
        Index("idx_book_circ_status_due", "status", "due_date"),
    )

    def __repr__(self):
        return f"<BookCirculation Book {self.book_id} -> Member {self.member_id} ({self.status})>"


class LibraryFine(Base, TimestampMixin, SoftDeleteMixin):
    """Auditable ledger of overdue, damaged, lost, and manual library fines."""
    __tablename__ = "library_fines"

    fine_code = Column(String(50), unique=True, nullable=False, index=True)
    circulation_id = Column(Integer, ForeignKey("book_circulations.id", ondelete="SET NULL"), nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("library_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="SET NULL"), nullable=True, index=True)
    copy_id = Column(Integer, ForeignKey("library_book_copies.id", ondelete="SET NULL"), nullable=True)

    fine_type = Column(String(30), default="Overdue", nullable=False, index=True)  # Overdue, Damaged, Lost, Manual
    amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    waived_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    status = Column(String(20), default="Unpaid", nullable=False, index=True)  # Unpaid, Partial, Paid, Waived

    assessed_date = Column(String(20), nullable=False, index=True)
    paid_date = Column(String(20), nullable=True)
    payment_method = Column(String(30), nullable=True)
    receipt_no = Column(String(60), nullable=True, index=True)
    collected_by = Column(String(100), nullable=True)
    waive_reason = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    circulation = relationship("BookCirculation", back_populates="fines")
    member = relationship("LibraryMember", back_populates="fines")
    book = relationship("Book")
    copy = relationship("BookCopy")

    __table_args__ = (
        CheckConstraint(
            "amount >= 0 AND paid_amount >= 0 AND waived_amount >= 0",
            name="ck_library_fine_amounts_nonneg",
        ),
    )

    @property
    def balance_due(self) -> float:
        return round(max(0.0, float(self.amount or 0.0) - float(self.paid_amount or 0.0) - float(self.waived_amount or 0.0)), 2)

    def __repr__(self):
        return f"<LibraryFine {self.fine_code} ({self.fine_type}: {self.amount} - {self.status})>"


class BookIncident(Base, TimestampMixin, SoftDeleteMixin):
    """Tracks Lost and Damaged book copy incidents, replacement costs, and resolutions."""
    __tablename__ = "library_book_incidents"

    incident_code = Column(String(50), unique=True, nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="RESTRICT"), nullable=False, index=True)
    copy_id = Column(Integer, ForeignKey("library_book_copies.id", ondelete="SET NULL"), nullable=True, index=True)
    circulation_id = Column(Integer, ForeignKey("book_circulations.id", ondelete="SET NULL"), nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("library_members.id", ondelete="SET NULL"), nullable=True, index=True)
    fine_id = Column(Integer, ForeignKey("library_fines.id", ondelete="SET NULL"), nullable=True)

    incident_type = Column(String(20), nullable=False, index=True)  # Lost, Damaged
    severity = Column(String(30), default="Major", nullable=False)  # Minor, Major, Unusable, Total Loss
    incident_date = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    replacement_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    fine_assessed = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    resolution_status = Column(String(30), default="Reported", nullable=False, index=True)  # Reported, Billed, Repaired, Replaced, Written Off
    resolved_date = Column(String(20), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    book = relationship("Book", back_populates="incidents")
    copy = relationship("BookCopy", back_populates="incidents")
    circulation = relationship("BookCirculation")
    member = relationship("LibraryMember", back_populates="incidents")
    fine = relationship("LibraryFine")

    __table_args__ = (
        CheckConstraint(
            "replacement_cost >= 0 AND fine_assessed >= 0",
            name="ck_library_incident_amounts_nonneg",
        ),
    )

    def __repr__(self):
        return f"<BookIncident {self.incident_code} ({self.incident_type} - {self.resolution_status})>"
