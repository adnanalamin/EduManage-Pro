"""
EduManage Pro - Book Form Dialog
PySide6 Modal for Adding & Editing Catalog Books with Authors, Publishers,
Categories, Shelves, ISBN, Barcodes & Live QR Preview.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.orm import Session

from app.models.library import Book
from app.repositories.library_repository import LibraryRepository
from app.ui.widgets.qr_code_widget import QRCodeWidget


class BookFormDialog(QDialog):
    """Dialog for cataloging new books or editing existing catalog metadata."""

    def __init__(self, db_session: Session, book: Optional[Book] = None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.book = book

        self.setWindowTitle("Edit Book Details" if book else "Add New Book to Catalog")
        self.setMinimumWidth(620)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        header_row = QHBoxLayout()
        title_lbl = QLabel("Book Catalog & Metadata")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: #065F46;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        self.qr_preview = QRCodeWidget(size=64)
        header_row.addWidget(self.qr_preview)
        main_layout.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(8)

        # Accession & Barcode
        acc_row = QHBoxLayout()
        self.accession_input = QLineEdit()
        self.accession_input.setPlaceholderText("e.g. ACC-2026-0015")
        self.accession_input.textChanged.connect(self._update_barcode_qr_preview)
        acc_row.addWidget(self.accession_input, 2)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Auto-generated if blank")
        self.barcode_input.textChanged.connect(self._update_qr_only)
        acc_row.addWidget(QLabel("Barcode:"))
        acc_row.addWidget(self.barcode_input, 2)
        form.addRow("Accession No *:", acc_row)

        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Book Title")
        form.addRow("Book Title *:", self.title_input)

        # Author (Editable Combo from LibraryAuthor table)
        self.author_combo = QComboBox()
        self.author_combo.setEditable(True)
        self.author_combo.setInsertPolicy(QComboBox.NoInsert)
        for aut in LibraryRepository.get_authors(self.db_session):
            self.author_combo.addItem(aut.name, aut.id)
        if not self.book:
            self.author_combo.setCurrentText("")
        form.addRow("Author(s) *:", self.author_combo)

        # Publisher (Editable Combo from LibraryPublisher table)
        pub_row = QHBoxLayout()
        self.publisher_combo = QComboBox()
        self.publisher_combo.setEditable(True)
        self.publisher_combo.setInsertPolicy(QComboBox.NoInsert)
        for pub in LibraryRepository.get_publishers(self.db_session):
            self.publisher_combo.addItem(pub.name, pub.id)
        if not self.book:
            self.publisher_combo.setCurrentText("")
        pub_row.addWidget(self.publisher_combo, 2)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1800, 2035)
        self.year_spin.setValue(2025)
        pub_row.addWidget(QLabel("Year:"))
        pub_row.addWidget(self.year_spin)
        form.addRow("Publisher & Year:", pub_row)

        # Category & Call No
        cat_row = QHBoxLayout()
        self.category_combo = QComboBox()
        for cat in LibraryRepository.get_categories(self.db_session):
            self.category_combo.addItem(f"{cat.name} ({cat.code})", cat.id)
        cat_row.addWidget(self.category_combo, 2)

        self.call_number_input = QLineEdit()
        self.call_number_input.setPlaceholderText("e.g. 005.133 COR")
        cat_row.addWidget(QLabel("Call No:"))
        cat_row.addWidget(self.call_number_input, 1)
        form.addRow("Category *:", cat_row)

        # ISBN & Edition
        isbn_row = QHBoxLayout()
        self.isbn_input = QLineEdit()
        self.isbn_input.setPlaceholderText("ISBN-10 or ISBN-13")
        self.isbn_input.textChanged.connect(self._update_qr_only)
        isbn_row.addWidget(self.isbn_input, 2)

        self.edition_input = QLineEdit()
        self.edition_input.setPlaceholderText("e.g. 4th Edition")
        isbn_row.addWidget(QLabel("Edition:"))
        isbn_row.addWidget(self.edition_input, 1)
        form.addRow("ISBN & Edition:", isbn_row)

        # Language & Pages
        meta_row = QHBoxLayout()
        self.language_input = QLineEdit("English")
        meta_row.addWidget(self.language_input)
        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(0, 10000)
        self.pages_spin.setValue(0)
        meta_row.addWidget(QLabel("Pages:"))
        meta_row.addWidget(self.pages_spin)
        form.addRow("Language & Pages:", meta_row)

        # Shelf Location (Catalog Shelf + Manual Rack/Shelf)
        loc_row = QHBoxLayout()
        self.shelf_combo = QComboBox()
        self.shelf_combo.addItem("-- Custom / Auto-create Rack & Shelf --", None)
        for sh in LibraryRepository.get_shelves(self.db_session):
            self.shelf_combo.addItem(f"{sh.shelf_code} ({sh.rack_number} / {sh.shelf_number})", sh.id)
        self.shelf_combo.currentIndexChanged.connect(self._on_shelf_selected)
        loc_row.addWidget(self.shelf_combo, 2)

        self.rack_input = QLineEdit()
        self.rack_input.setPlaceholderText("Rack 01")
        loc_row.addWidget(self.rack_input, 1)

        self.shelf_input = QLineEdit()
        self.shelf_input.setPlaceholderText("Shelf A")
        loc_row.addWidget(self.shelf_input, 1)
        form.addRow("Shelf Location:", loc_row)

        # Copies & Price
        copies_row = QHBoxLayout()
        self.copies_spin = QSpinBox()
        self.copies_spin.setRange(1, 1000)
        self.copies_spin.setValue(1)
        copies_row.addWidget(self.copies_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.0, 50000.0)
        self.price_spin.setPrefix("$ ")
        self.price_spin.setValue(25.0)
        copies_row.addWidget(QLabel("Unit Price:"))
        copies_row.addWidget(self.price_spin)
        form.addRow("Total Copies & Price:", copies_row)

        # Description
        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(58)
        self.desc_input.setPlaceholderText("Optional synopsis or cataloging remarks...")
        form.addRow("Description:", self.desc_input)

        main_layout.addLayout(form)

        if self.book:
            self.accession_input.setText(self.book.accession_no)
            self.accession_input.setEnabled(False)
            self.barcode_input.setText(self.book.barcode or "")
            self.title_input.setText(self.book.title)
            self.author_combo.setCurrentText(self.book.author or "")
            self.publisher_combo.setCurrentText(self.book.publisher or "")
            self.isbn_input.setText(self.book.isbn or "")
            self.call_number_input.setText(self.book.call_number or "")
            if self.book.publication_year:
                self.year_spin.setValue(self.book.publication_year)
            self.edition_input.setText(self.book.edition or "")
            self.language_input.setText(self.book.language or "English")
            self.pages_spin.setValue(self.book.pages or 0)
            self.rack_input.setText(self.book.rack_number or "")
            self.shelf_input.setText(self.book.shelf_number or "")
            self.copies_spin.setValue(self.book.total_copies or 1)
            self.price_spin.setValue(float(self.book.price or 0.0))
            self.desc_input.setPlainText(self.book.description or "")

            cat_idx = self.category_combo.findData(self.book.category_id)
            if cat_idx >= 0:
                self.category_combo.setCurrentIndex(cat_idx)
            if self.book.shelf_id:
                sh_idx = self.shelf_combo.findData(self.book.shelf_id)
                if sh_idx >= 0:
                    self.shelf_combo.setCurrentIndex(sh_idx)
            self._update_qr_only()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Book")
        save_btn.setStyleSheet("background-color: #065F46; color: white; font-weight: bold; padding: 6px 18px;")
        save_btn.clicked.connect(self._save_book)
        btn_row.addWidget(save_btn)

        main_layout.addLayout(btn_row)

    def _on_shelf_selected(self):
        sh_id = self.shelf_combo.currentData()
        if not sh_id:
            return
        sh = next((s for s in LibraryRepository.get_shelves(self.db_session) if s.id == sh_id), None)
        if sh:
            self.rack_input.setText(sh.rack_number)
            self.shelf_input.setText(sh.shelf_number)

    def _update_barcode_qr_preview(self):
        acc = self.accession_input.text().strip()
        if acc and not self.book and not self.barcode_input.isModified():
            self.barcode_input.setText(LibraryRepository.generate_book_barcode(acc))
        self._update_qr_only()

    def _update_qr_only(self):
        acc = self.accession_input.text().strip() or "ACC-NEW"
        isbn = self.isbn_input.text().strip()
        bc = self.barcode_input.text().strip() or LibraryRepository.generate_book_barcode(acc)
        payload = f"EDUMANAGE|LIB_BOOK|ACC:{acc}|ISBN:{isbn}|BC:{bc}"
        self.qr_preview.set_payload(payload)

    def _save_book(self):
        accession = self.accession_input.text().strip()
        title = self.title_input.text().strip()
        author = self.author_combo.currentText().strip()
        cat_id = self.category_combo.currentData()

        if not accession or not title or not author:
            QMessageBox.warning(self, "Validation Error", "Accession No, Title, and Author are required fields.")
            return
        if not cat_id:
            QMessageBox.warning(self, "Validation Error", "Please select a valid Book Category.")
            return

        pub_text = self.publisher_combo.currentText().strip() or None
        shelf_id = self.shelf_combo.currentData()
        barcode_val = self.barcode_input.text().strip() or LibraryRepository.generate_book_barcode(accession)

        try:
            kwargs = {
                "title": title,
                "author": author,
                "publisher": pub_text,
                "isbn": self.isbn_input.text().strip() or None,
                "barcode": barcode_val,
                "call_number": self.call_number_input.text().strip() or None,
                "edition": self.edition_input.text().strip() or None,
                "publication_year": self.year_spin.value(),
                "language": self.language_input.text().strip() or "English",
                "pages": self.pages_spin.value() or None,
                "category_id": cat_id,
                "rack_number": self.rack_input.text().strip() or None,
                "shelf_number": self.shelf_input.text().strip() or None,
                "total_copies": self.copies_spin.value(),
                "price": self.price_spin.value(),
                "description": self.desc_input.toPlainText().strip() or None,
            }
            if shelf_id:
                kwargs["shelf_id"] = shelf_id

            if self.book:
                LibraryRepository.update_book(self.db_session, self.book.id, **kwargs)
            else:
                existing = LibraryRepository.get_book_by_accession(self.db_session, accession)
                if existing:
                    QMessageBox.warning(
                        self,
                        "Duplicate Accession",
                        f"A book with Accession No '{accession}' already exists.",
                    )
                    return
                LibraryRepository.create_book(self.db_session, accession_no=accession, **kwargs)

            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save book:\n{str(e)}")
