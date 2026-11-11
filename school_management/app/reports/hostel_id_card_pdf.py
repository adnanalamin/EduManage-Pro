"""
EduManage Pro - Hostel Resident Card Generator
Phase 12: CR80 PVC Printable Hostel Boarder Card with Barcode
"""

import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor


class HostelCardGenerator:
    """Generates official CR80 PVC (85.6mm x 54mm) Boarding Pass & Resident Identity Cards."""

    # Standard CR80 Dimensions in points (1 inch = 72 points)
    CARD_WIDTH = 3.375 * inch   # ~243 pt (85.6 mm)
    CARD_HEIGHT = 2.125 * inch  # ~153 pt (54 mm)

    @classmethod
    def generate_single_card(cls, allocation, school, output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # Background Fill
        c.setFillColor(HexColor("#0F172A"))  # Slate-900 Dark Card
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=0)

        # Header Accent Strip (Emerald Theme for Boarding/Campus Living)
        c.setFillColor(HexColor("#059669"))  # Emerald 600
        c.roundRect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, 0, fill=1, stroke=0)

        # School Name & Header
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 8.5)
        school_name = school.school_name if hasattr(school, 'school_name') and school.school_name else "EDUMANAGE RESIDENTIAL ACADEMY"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_name.upper()[:36])

        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(HexColor("#D1FAE5"))
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 26, "HOSTEL RESIDENT IDENTITY CARD")

        # Photo Container (Left Column)
        photo_x = 12
        photo_y = 36
        photo_w = 54
        photo_h = 66
        c.setFillColor(HexColor("#1E293B"))  # Slate-800
        c.setStrokeColor(HexColor("#334155"))
        c.setLineWidth(1)
        c.roundRect(photo_x, photo_y, photo_w, photo_h, 4, fill=1, stroke=1)

        c.setFillColor(HexColor("#64748B"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 2, "PHOTO")

        # Boarder Details (Right Column)
        info_x = 76
        start_y = cls.CARD_HEIGHT - 50

        # Resident Name
        student_name = "RESIDENT STUDENT"
        if hasattr(allocation, 'student') and allocation.student:
            student_name = f"{allocation.student.first_name} {allocation.student.last_name}".upper()
        c.setFillColor(HexColor("#34D399"))  # Emerald-400
        c.setFont("Helvetica-Bold", 8)
        c.drawString(info_x, start_y, student_name[:24])

        # Block & Room
        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("Helvetica-Bold", 6)
        c.drawString(info_x, start_y - 11, "BLOCK:")
        c.drawString(info_x, start_y - 20, "ROOM / BED:")
        c.drawString(info_x, start_y - 29, "STUDENT ID:")
        c.drawString(info_x, start_y - 38, "WARDEN / CONT:")

        block_title = allocation.room.block.block_name if (hasattr(allocation, 'room') and allocation.room and allocation.room.block) else "Main Block"
        room_info = f"{allocation.room.room_number if allocation.room else 'N/A'} ({allocation.bed_number})"
        student_id = allocation.student.student_id if (hasattr(allocation, 'student') and allocation.student) else f"STU-{allocation.student_id:04d}"
        contact_no = allocation.emergency_phone or (allocation.room.block.warden_phone if allocation.room and allocation.room.block else "+880 1700-000000")

        c.setFillColor(HexColor("#F8FAFC"))
        c.setFont("Helvetica", 6)
        c.drawString(info_x + 55, start_y - 11, str(block_title)[:22])
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(HexColor("#FCD34D"))  # Amber-300
        c.drawString(info_x + 55, start_y - 20, str(room_info)[:22])

        c.setFont("Helvetica", 6)
        c.setFillColor(HexColor("#F8FAFC"))
        c.drawString(info_x + 55, start_y - 29, str(student_id))
        c.drawString(info_x + 55, start_y - 38, str(contact_no)[:20])

        # Bottom Barcode & Footer Strip
        barcode_y = 12
        c.setFillColor(HexColor("#022C22"))  # Dark Emerald
        c.roundRect(8, barcode_y - 2, cls.CARD_WIDTH - 16, 20, 3, fill=1, stroke=0)

        # Simulated Code 128 Barcode lines
        c.setFillColor(HexColor("#E2E8F0"))
        pattern = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 2, 3, 1, 2, 1, 3, 1, 2, 2, 1, 3, 1, 1, 2, 3, 1]
        bx = 20
        for w in pattern * 3:
            if bx > cls.CARD_WIDTH - 30:
                break
            c.rect(bx, barcode_y + 6, w, 10, fill=1, stroke=0)
            bx += w + 2

        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("Helvetica", 5)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, barcode_y + 1, f"*HST-ALLOC-{allocation.id:04d}*")

        c.showPage()
        c.save()
        return output_pdf_path
