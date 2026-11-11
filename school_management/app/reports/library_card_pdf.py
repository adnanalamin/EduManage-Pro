"""
EduManage Pro - Library Card Generator (ReportLab PDF)
Phase 10: CR80 PVC Printable Library Membership ID Card with Barcode & Member Meta
"""

import os
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from app.models.library import LibraryMember
from app.models.school import SchoolSetting


class LibraryCardGenerator:
    """Generates standard CR80 (85.6mm x 54mm) library cards with barcode & borrowing quota."""
    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @classmethod
    def generate_single_card(cls, member: LibraryMember, school: SchoolSetting = None, output_pdf_path: str = "library_card.pdf") -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # 1. Background Card Outline & Fill
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # 2. Header Bar (Dark Emerald / Teal theme for Library)
        c.setFillColor(colors.HexColor("#065F46"))  # Emerald 800
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)

        # School Name & Card Type
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_title[:38])

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#A7F3D0"))  # Emerald 200
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 28, "OFFICIAL LIBRARY BORROWER PASS")

        # 3. Photo / Avatar Placeholder
        photo_x = 12
        photo_y = 30
        photo_w = 52
        photo_h = 64
        c.setStrokeColor(colors.HexColor("#A7F3D0"))
        c.setFillColor(colors.HexColor("#ECFDF5"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        
        # User initials or icon placeholder
        c.setFillColor(colors.HexColor("#047857"))
        c.setFont("Helvetica-Bold", 14)
        member_name = "Library Patron"
        extra_meta = ""
        if member.student:
            member_name = member.student.full_name
            extra_meta = f"Class {member.student.school_class.name if member.student.school_class else ''} | Roll {member.student.roll_number or '-'}"
        elif member.teacher:
            member_name = member.teacher.full_name
            extra_meta = f"Teacher ({member.teacher.designation or 'Faculty'})"
        elif member.staff:
            member_name = member.staff.full_name
            extra_meta = f"Staff ({member.staff.role or 'Staff'})"

        initials = "".join([part[0] for part in member_name.split()[:2]]).upper() or "LIB"
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 4, initials)

        c.setFont("Helvetica", 5.5)
        c.setFillColor(colors.HexColor("#065F46"))
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + 4, member.member_type.upper())

        # 4. Member Details Column
        info_x = photo_x + photo_w + 10
        info_y = cls.CARD_HEIGHT - 50
        line_spacing = 9.5

        # Name
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, member_name[:24])

        # Extra meta (Class/Role)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#475569"))
        if extra_meta:
            info_y -= line_spacing
            c.drawString(info_x, info_y, extra_meta[:28])

        # Card ID
        info_y -= line_spacing
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(colors.HexColor("#065F46"))
        c.drawString(info_x, info_y, f"Card No: {member.member_id}")

        # Limit & Status
        info_y -= line_spacing
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y, f"Max Loan Quota: {member.max_allowed_books} Books")

        info_y -= line_spacing
        c.drawString(info_x, info_y, f"Issued: {member.card_issue_date}  |  {member.status}")

        # 5. Simulated Barcode at Bottom
        barcode_x = 12
        barcode_y = 8
        barcode_w = cls.CARD_WIDTH - 24
        barcode_h = 14

        # Draw barcode bars pattern based on member_id hash
        c.setFillColor(colors.HexColor("#0F172A"))
        curr_x = barcode_x + 10
        code_str = member.member_id
        for i, char in enumerate(code_str * 3):
            val = ord(char) + i
            bar_w = 1.0 if (val % 2 == 0) else 1.8
            if curr_x + bar_w > barcode_x + barcode_w - 10:
                break
            c.rect(curr_x, barcode_y + 4, bar_w, barcode_h - 4, fill=1, stroke=0)
            curr_x += bar_w + (1.2 if (val % 3 == 0) else 0.8)

        # Barcode text caption
        c.setFont("Helvetica", 5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(cls.CARD_WIDTH / 2.0, barcode_y - 1, f"*{member.member_id}*")

        c.showPage()
        c.save()
        return output_pdf_path
