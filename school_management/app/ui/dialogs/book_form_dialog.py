"""
EduManage Pro - Book Form Dialog
Phase 10: PySide6 Modal for Adding & Editing Catalog Books
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton, QLabel, QMessageBox
)
from sqlalchemy.orm import Session
from app.models.library import Book, BookCategory
from app.repositories.library_repository import LibraryRepository


class BookFormDialog(QDialog):
    """Dialog for cataloging new books or editing existing catalog metadata."""

    def __init__(self, db_session: Session, book: Optional[Book] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.book = book

        self.setWindowTitle("Edit Book Details" if book else "Add New Book to Catalog")
        self.setMinimumWidth(480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title_lbl = QLabel("Book Catalog Information")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #065F46;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        # Accession Number
        self.accession_input = QLineEdit()
        self.accession_input.setPlaceholderText("e.g. ACC-2026-0015")
        form.addRow("Accession No *:", self.accession_input)

        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Book Title")
        form.addRow("Book Title *:", self.title_input)

        # Author
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Author(s)")
        form.addRow("Author(s) *:", self.author_input)

        # Category
        self.category_combo = QComboBox()
        categories = LibraryRepository.get_categories(self.db_session)
        for cat in categories:
            self.category_combo.addItem(f"{cat.name} ({cat.code})", cat.id)
        form.addRow("Category *:", self.category_combo)

        # ISBN
        self.isbn_input = QLineEdit()
        self.isbn_input.setPlaceholderText("ISBN-10 or ISBN-13")
        form.addRow("ISBN:", self.isbn_input)

        # Publisher & Year
        pub_layout = QHBoxLayout()
        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Publisher")
        pub_layout.addWidget(self.publisher_input)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1800, 2030)
        self.year_spin.setValue(2024)
        pub_layout.addWidget(QLabel("Year:"))
        pub_layout.addWidget(self.year_spin)
        form.addRow("Publisher & Year:", pub_layout)

        # Edition
        self.edition_input = QLineEdit()
        self.edition_input.setPlaceholderText("e.g., 2nd Edition / Revised")
        form.addRow("Edition:", self.edition_input)

        # Shelf Location
        loc_layout = QHBoxLayout()
        self.rack_input = QLineEdit()
        self.rack_input.setPlaceholderText("e.g., Rack 03")
        loc_layout.addWidget(self.rack_input)

        self.shelf_input = QLineEdit()
        self.shelf_input.setPlaceholderText("e.g., Shelf B")
        loc_layout.addWidget(QLabel("Shelf:"))
        loc_layout.addWidget(self.shelf_input)
        form.addRow("Rack & Shelf:", loc_layout)

        # Copies & Price
        copies_layout = QHBoxLayout()
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 1000)
        self.copies_spin.setValue(1)
        copies_layout.addWidget(self.copies_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 10000.0)
        self.price_spin.setPrefix("$ ")
        self.price_spin.setValue(25.0)
        copies_layout.addWidget(QLabel("Unit Price:"))
        copies_layout.addWidget(self.price_spin)
        form.addRow("Total Copies & Price:", copies_layout)

        layout.addLayout(form)

        # Populate if editing
        if self.book:
            self.accession_input.setText(self.book.accession_no)
            self.accession_input.setEnabled(False)  # accession number is fixed
            self.title_input.setText(self.book.title)
            self.author_input.setText(self.book.author)
            self.isbn_input.setText(self.book.isbn or "")
            self.publisher_input.setText(self.book.publisher or "")
            if self.book.publication_year:
                self.year_spin.setValue(self.book.publication_year)
            self.edition_input.setText(self.book.edition or "")
            self.rack_input.setText(self.book.rack_number or "")
            self.shelf_input.setText(self.book.shelf_number or "")
            self.copies_spin.setValue(self.book.total_copies)
            self.price_spin.setValue(self.book.price)

            idx = self.category_combo.findData(self.book.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Book")
        save_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 16px;")
        save_btn.clicked.connect(self._save_book)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save_book(self):
        accession = self.accession_input.text().strip()
        title = self.title_input.text().strip()
        author = self.author_input.text().strip()
        cat_id = self.category_combo.currentData()

        if not accession or not title or not author:
            QMessageBox.warning(self, "Validation Error", "Accession No, Title, and Author are required fields.")
            return

        if not cat_id:
            QMessageBox.warning(self, "Validation Error", "Please select a valid Book Category.")
            return

        try:
            if self.book:
                LibraryRepository.update_book(
                    self.db_session,
                    self.book.id,
                    title=title,
                    author=author,
                    publisher=self.publisher_input.text().strip() or None,
                    isbn=self.isbn_input.text().strip() or None,
                    edition=self.edition_input.text().strip() or None,
                    publication_year=self.year_spin.value(),
                    category_id=cat_id,
                    rack_number=self.rack_input.text().strip() or None,
                    shelf_number=self.shelf_input.text().strip() or None,
                    total_copies=self.copies_spin.value(),
                    price=self.price_spin.value()
                )
            else:
                existing = LibraryRepository.get_book_by_accession(self.db_session, accession)
                if existing:
                    QMessageBox.warning(self, "Duplicate Accession", f"A book with Accession No '{accession}' already exists.")
                    return

                LibraryRepository.create_book(
                    self.db_session,
                    accession_no=accession,
                    title=title,
                    author=author,
                    publisher=self.publisher_input.text().strip() or None,
                    isbn=self.isbn_input.text().strip() or None,
                    edition=self.edition_input.text().strip() or None,
                    publication_year=self.year_spin.value(),
                    category_id=cat_id,
                    rack_number=self.rack_input.text().strip() or None,
                    shelf_number=self.shelf_input.text().strip() or None,
                    total_copies=self.copies_spin.value(),
                    price=self.price_spin.value()
                )

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save book:\n{str(e)}")
