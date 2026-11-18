"""
EduManage Pro - Library Card & Barcode/QR Label Generator (ReportLab PDF)
Generates CR80 PVC Library Membership ID Cards with embedded QR + Barcode,
Batch Member Card Sheets, and Book/Copy Barcode & QR Sticker Sheets.
"""

import os
from typing import List, Optional, Union
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.library import Book, BookCopy, LibraryMember
from app.models.school import SchoolSetting
from app.repositories.library_repository import LibraryRepository
from app.utils.qr_generator import generate_qr_matrix


class LibraryCardGenerator:
    """Generates CR80 (85.6mm x 54mm) library cards and printable book/copy barcode+QR sticker sheets."""

    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @staticmethod
    def _draw_qr_matrix(c: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
        matrix = generate_qr_matrix(payload or "EDUMANAGE")
        if not matrix:
            return
        dim = len(matrix)
        cell = size / float(dim)
        c.saveState()
        c.setFillColor(colors.white)
        c.rect(x - 1.5, y - 1.5, size + 3, size + 3, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0F172A"))
        for r_idx, row in enumerate(matrix):
            for c_idx, val in enumerate(row):
                if val:
                    rx = x + c_idx * cell
                    ry = y + size - (r_idx + 1) * cell
                    c.rect(rx, ry, cell, cell, fill=1, stroke=0)
        c.restoreState()

    @staticmethod
    def _draw_barcode_strip(c: canvas.Canvas, code_str: str, x: float, y: float, w: float, h: float) -> None:
        c.saveState()
        c.setFillColor(colors.HexColor("#0F172A"))
        curr_x = x + 6
        text_val = code_str or "LIB-000"
        for i, char in enumerate(text_val * 3):
            val = ord(char) + i
            bar_w = 0.9 if (val % 2 == 0) else 1.7
            if curr_x + bar_w > x + w - 6:
                break
            c.rect(curr_x, y + 5, bar_w, h - 5, fill=1, stroke=0)
            curr_x += bar_w + (1.1 if (val % 3 == 0) else 0.7)
        c.setFont("Helvetica", 4.8)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(x + (w / 2.0), y, f"*{text_val}*")
        c.restoreState()

    @classmethod
    def _draw_card_at(
        cls,
        c: canvas.Canvas,
        member: LibraryMember,
        school: Optional[SchoolSetting],
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> None:
        c.saveState()
        c.translate(origin_x, origin_y)

        # 1. Card Outline & Fill
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # 2. Header Bar
        c.setFillColor(colors.HexColor("#065F46"))
        c.rect(0, cls.CARD_HEIGHT - 36, cls.CARD_WIDTH, 36, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 15, school_title[:38])

        c.setFont("Helvetica-Bold", 6.2)
        c.setFillColor(colors.HexColor("#A7F3D0"))
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 27, "OFFICIAL LIBRARY BORROWER PASS")

        # 3. Avatar Badge
        photo_x = 10
        photo_y = 32
        photo_w = 46
        photo_h = 58
        c.setStrokeColor(colors.HexColor("#A7F3D0"))
        c.setFillColor(colors.HexColor("#ECFDF5"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)

        member_name = member.display_name
        extra_meta = member.affiliation_label

        c.setFillColor(colors.HexColor("#047857"))
        c.setFont("Helvetica-Bold", 13)
        initials = "".join([part[0] for part in member_name.split()[:2]]).upper() or "LIB"
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 3, initials)

        c.setFont("Helvetica-Bold", 5.2)
        c.setFillColor(colors.HexColor("#065F46"))
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + 4, (member.member_type or "PATRON").upper())

        # 4. Member Details Column
        info_x = photo_x + photo_w + 8
        info_y = cls.CARD_HEIGHT - 48
        line_spacing = 9.2

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 8.2)
        c.drawString(info_x, info_y, member_name[:22])

        c.setFont("Helvetica", 6.2)
        c.setFillColor(colors.HexColor("#475569"))
        if extra_meta:
            info_y -= line_spacing
            c.drawString(info_x, info_y, extra_meta[:26])

        info_y -= line_spacing
        c.setFont("Helvetica-Bold", 6.4)
        c.setFillColor(colors.HexColor("#065F46"))
        c.drawString(info_x, info_y, f"Card ID: {member.member_id}")

        info_y -= line_spacing
        c.setFont("Helvetica", 5.8)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y, f"Quota: {member.max_allowed_books} Books | {getattr(member, 'max_loan_days', 14)} Days")

        info_y -= line_spacing
        exp_txt = getattr(member, "card_expiry_date", None) or "-"
        c.drawString(info_x, info_y, f"Valid Thru: {exp_txt} | {member.status}")

        # 5. Embedded QR Matrix (Right side)
        qr_payload = getattr(member, "qr_payload", None) or LibraryRepository.build_member_qr_payload(member)
        cls._draw_qr_matrix(c, qr_payload, x=cls.CARD_WIDTH - 48, y=32, size=38)

        # 6. Barcode Strip at Bottom
        bc_val = getattr(member, "barcode", None) or member.member_id
        cls._draw_barcode_strip(c, bc_val, 10, 6, cls.CARD_WIDTH - 20, 17)

        c.restoreState()

    @classmethod
    def generate_single_card(
        cls,
        member: LibraryMember,
        school: Optional[SchoolSetting] = None,
        output_pdf_path: str = "library_card.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))
        cls._draw_card_at(c, member, school, 0.0, 0.0)
        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def generate_bulk_cards_pdf(
        cls,
        members: List[LibraryMember],
        school: Optional[SchoolSetting] = None,
        output_pdf_path: str = "library_cards_batch.pdf",
    ) -> str:
        """Generates printable A4 sheet (2x4 CR80 cards per page) for bulk member card printing."""
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=A4)
        page_w, page_h = A4
        margin_x = (page_w - 2 * cls.CARD_WIDTH - 18) / 2.0
        top_y = page_h - 42 - cls.CARD_HEIGHT

        for idx, member in enumerate(members):
            slot = idx % 8
            if idx > 0 and slot == 0:
                c.showPage()
            col = slot % 2
            row = slot // 2
            x = margin_x + col * (cls.CARD_WIDTH + 18)
            y = top_y - row * (cls.CARD_HEIGHT + 16)
            cls._draw_card_at(c, member, school, x, y)

        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def generate_book_barcodes_pdf(
        cls,
        items: List[Union[Book, BookCopy]],
        school: Optional[SchoolSetting] = None,
        output_pdf_path: str = "book_barcode_labels.pdf",
    ) -> str:
        """Generates printable A4 sheet (3 columns x 6 rows) of Barcode + QR spine/cover labels for books or physical copies."""
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=A4)
        page_w, page_h = A4

        lbl_w = 175
        lbl_h = 108
        gap_x = 12
        gap_y = 14
        start_x = (page_w - (3 * lbl_w + 2 * gap_x)) / 2.0
        start_y = page_h - 40 - lbl_h
        school_short = (school.school_name if school else "EduManage Library")[:28]

        for idx, obj in enumerate(items):
            slot = idx % 18
            if idx > 0 and slot == 0:
                c.showPage()
            col = slot % 3
            row = slot // 3
            x = start_x + col * (lbl_w + gap_x)
            y = start_y - row * (lbl_h + gap_y)

            c.saveState()
            c.translate(x, y)
            c.setStrokeColor(colors.HexColor("#94A3B8"))
            c.setFillColor(colors.white)
            c.roundRect(0, 0, lbl_w, lbl_h, 4, fill=1, stroke=1)

            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.rect(0, lbl_h - 16, lbl_w, 16, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawString(6, lbl_h - 11, school_short)

            if isinstance(obj, BookCopy):
                title_txt = obj.book.title[:26] if obj.book else obj.copy_code
                sub_txt = f"Copy: {obj.copy_code}"
                call_txt = (obj.book.call_number or obj.book.accession_no) if obj.book else obj.copy_code
                bc_txt = obj.barcode
                qr_txt = obj.qr_payload or LibraryRepository.build_copy_qr_payload(
                    obj, obj.book.accession_no if obj.book else ""
                )
            else:
                title_txt = obj.title[:26]
                sub_txt = f"Acc: {obj.accession_no}"
                call_txt = obj.call_number or (f"{obj.rack_number or '-'} / {obj.shelf_number or '-'}")
                bc_txt = obj.barcode or LibraryRepository.generate_book_barcode(obj.accession_no)
                qr_txt = obj.qr_payload or LibraryRepository.build_book_qr_payload(obj)

            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(6, lbl_h - 29, title_txt)

            c.setFont("Helvetica", 6.2)
            c.setFillColor(colors.HexColor("#475569"))
            c.drawString(6, lbl_h - 40, sub_txt)
            c.drawString(6, lbl_h - 50, f"Loc/Call: {call_txt[:22]}")

            cls._draw_qr_matrix(c, qr_txt, x=lbl_w - 42, y=lbl_h - 60, size=34)
            cls._draw_barcode_strip(c, bc_txt, 4, 6, lbl_w - 8, 22)
            c.restoreState()

        c.showPage()
        c.save()
        return output_pdf_path
