"""
EduManage Pro - Library Analytical Reports PDF Generator
Landscape A4 ReportLab PDFs for Borrowing History, Fine Collection & Recovery,
and Book Inventory & Lost/Damaged Valuation Reports.
"""

import os
from datetime import date
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.library import Book, BookCirculation, LibraryFine
from app.models.school import SchoolSetting


class LibraryReportsPDFGenerator:
    """Generates official Borrowing History, Fine Report, and Inventory Report PDFs."""

    @staticmethod
    def _styles():
        styles = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "LibRepTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=19,
                alignment=1,
                textColor=colors.HexColor("#0F172A"),
            ),
            "sub": ParagraphStyle(
                "LibRepSub",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=12,
                alignment=1,
                textColor=colors.HexColor("#64748B"),
            ),
            "meta": ParagraphStyle(
                "LibRepMeta",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10.5,
                leading=14,
                alignment=1,
                textColor=colors.HexColor("#065F46"),
            ),
            "cell": ParagraphStyle(
                "LibRepCell",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.8,
                leading=10,
                textColor=colors.HexColor("#1E293B"),
            ),
            "cell_bold": ParagraphStyle(
                "LibRepCellBold",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.white,
            ),
        }

    @staticmethod
    def _build_header(story, st, school: Optional[SchoolSetting], report_title: str, subtitle: str):
        school_name = school.school_name if school else "Ideal Model High School & College"
        school_addr = school.address if (school and school.address) else "Academic Library & Information Resource Center"
        story.append(Paragraph(school_name.upper(), st["title"]))
        story.append(Paragraph(school_addr, st["sub"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(report_title, st["meta"]))
        story.append(Paragraph(subtitle, st["sub"]))
        story.append(Spacer(1, 10))

    @classmethod
    def generate_borrowing_history_pdf(
        cls,
        circulations: List[BookCirculation],
        scope_label: str = "All Library Members & Titles",
        school: Optional[SchoolSetting] = None,
        output_path: str = "borrowing_history_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=32, rightMargin=32, topMargin=28, bottomMargin=28)
        st = cls._styles()
        story = []

        cls._build_header(
            story,
            st,
            school,
            "LIBRARY BORROWING HISTORY REPORT",
            f"Scope: {scope_label} • Generated: {date.today().strftime('%B %d, %Y')} • Records: {len(circulations)}",
        )

        headers = ["Loan #", "Accession / Copy", "Book Title", "Member ID", "Borrower Name", "Issue Date", "Due Date", "Return Date", "Renewals", "Fine", "Status"]
        col_widths = [40, 82, 160, 70, 115, 58, 58, 58, 44, 42, 52]
        rows = [[Paragraph(h, st["cell_bold"]) for h in headers]]

        for c in circulations:
            copy_lbl = c.copy.copy_code if c.copy else (c.book.accession_no if c.book else "-")
            fine_tot = float((c.fine_amount or 0.0) + (c.damage_or_lost_fee or 0.0))
            rows.append([
                Paragraph(f"#{c.id:04d}", st["cell"]),
                Paragraph(copy_lbl, st["cell"]),
                Paragraph((c.book.title if c.book else "Unknown")[:34], st["cell"]),
                Paragraph(c.member.member_id if c.member else "-", st["cell"]),
                Paragraph((c.member.display_name if c.member else "Patron")[:24], st["cell"]),
                Paragraph(c.issue_date, st["cell"]),
                Paragraph(c.due_date, st["cell"]),
                Paragraph(c.return_date or "—", st["cell"]),
                Paragraph(str(c.renewal_count or 0), st["cell"]),
                Paragraph(f"${fine_tot:.2f}", st["cell"]),
                Paragraph(f"<b>{c.status}</b>", st["cell"]),
            ])

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path

    @classmethod
    def generate_fine_report_pdf(
        cls,
        fines: List[LibraryFine],
        school: Optional[SchoolSetting] = None,
        output_path: str = "library_fine_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=32, rightMargin=32, topMargin=28, bottomMargin=28)
        st = cls._styles()
        story = []

        total_assessed = sum(float(f.amount or 0.0) for f in fines)
        total_paid = sum(float(f.paid_amount or 0.0) for f in fines)
        total_waived = sum(float(f.waived_amount or 0.0) for f in fines)
        total_due = sum(f.balance_due for f in fines)

        cls._build_header(
            story,
            st,
            school,
            "LIBRARY FINE COLLECTION & OUTSTANDING DUES REPORT",
            f"Generated: {date.today().strftime('%B %d, %Y')} • Total Assessed: ${total_assessed:.2f} | Collected: ${total_paid:.2f} | Waived: ${total_waived:.2f} | Balance Due: ${total_due:.2f}",
        )

        headers = ["Fine Code", "Date", "Member ID", "Borrower", "Book Title", "Type", "Assessed", "Paid", "Waived", "Balance", "Receipt #", "Status"]
        col_widths = [76, 56, 68, 108, 130, 52, 48, 46, 46, 48, 60, 44]
        rows = [[Paragraph(h, st["cell_bold"]) for h in headers]]

        for f in fines:
            rows.append([
                Paragraph(f.fine_code, st["cell"]),
                Paragraph(f.assessed_date, st["cell"]),
                Paragraph(f.member.member_id if f.member else "-", st["cell"]),
                Paragraph((f.member.display_name if f.member else "-")[:22], st["cell"]),
                Paragraph((f.book.title if f.book else "-")[:26], st["cell"]),
                Paragraph(f.fine_type, st["cell"]),
                Paragraph(f"${float(f.amount or 0.0):.2f}", st["cell"]),
                Paragraph(f"${float(f.paid_amount or 0.0):.2f}", st["cell"]),
                Paragraph(f"${float(f.waived_amount or 0.0):.2f}", st["cell"]),
                Paragraph(f"${f.balance_due:.2f}", st["cell"]),
                Paragraph(f.receipt_no or "-", st["cell"]),
                Paragraph(f"<b>{f.status}</b>", st["cell"]),
            ])

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5B21B6")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path

    @classmethod
    def generate_inventory_report_pdf(
        cls,
        books: List[Book],
        stats: Dict[str, Any],
        school: Optional[SchoolSetting] = None,
        output_path: str = "library_inventory_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=32, rightMargin=32, topMargin=28, bottomMargin=28)
        st = cls._styles()
        story = []

        cls._build_header(
            story,
            st,
            school,
            "LIBRARY BOOK INVENTORY & VALUATION REPORT",
            (
                f"Generated: {date.today().strftime('%B %d, %Y')} • Titles: {stats.get('total_titles', len(books))} | "
                f"Total Copies: {stats.get('total_inventory_copies', 0)} | Available: {stats.get('available_copies', 0)} | "
                f"Damaged: {stats.get('damaged_copies', 0)} | Lost: {stats.get('lost_copies', 0)} | "
                f"Valuation: ${stats.get('catalog_valuation', 0.0):.2f}"
            ),
        )

        headers = ["Accession No", "Title", "Author", "Publisher", "ISBN", "Shelf Loc", "Total", "Avail", "Issued", "Damaged", "Lost", "Unit $", "Total $"]
        col_widths = [68, 145, 95, 80, 72, 68, 34, 34, 36, 44, 32, 42, 48]
        rows = [[Paragraph(h, st["cell_bold"]) for h in headers]]

        for b in books:
            loc = f"{b.rack_number or '-'} / {b.shelf_number or '-'}"
            val_tot = float(b.price or 0.0) * (b.total_copies or 0)
            rows.append([
                Paragraph(b.accession_no, st["cell"]),
                Paragraph(b.title[:30], st["cell"]),
                Paragraph(b.author[:20], st["cell"]),
                Paragraph((b.publisher or "-")[:18], st["cell"]),
                Paragraph(b.isbn or "-", st["cell"]),
                Paragraph(loc[:18], st["cell"]),
                Paragraph(str(b.total_copies or 0), st["cell"]),
                Paragraph(str(b.available_copies or 0), st["cell"]),
                Paragraph(str(b.issued_copies or 0), st["cell"]),
                Paragraph(str(b.damaged_copies or 0), st["cell"]),
                Paragraph(str(b.lost_copies or 0), st["cell"]),
                Paragraph(f"${float(b.price or 0.0):.2f}", st["cell"]),
                Paragraph(f"${val_tot:.2f}", st["cell"]),
            ])

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path
