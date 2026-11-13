"""
EduManage Pro - Student ID Card Generator (ReportLab PDF)
Renders standard CR80 printable PVC / Paper ID cards with student photo, Digital ID,
vector QR code matrix, class metadata, and emergency contacts.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.school import SchoolSetting
from app.models.student import Student
from app.utils.qr_generator import build_qr_payload, generate_digital_id, generate_qr_matrix


class StudentIDCardGenerator:
    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @staticmethod
    def _draw_qr_matrix(c: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
        matrix = generate_qr_matrix(payload)
        dim = len(matrix)
        if dim == 0:
            return
        cell = size / float(dim)
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.rect(x, y, size, size, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#0F172A"))
        for r_idx, row in enumerate(matrix):
            for c_idx, val in enumerate(row):
                if val:
                    rx = x + c_idx * cell
                    ry = y + size - (r_idx + 1) * cell
                    c.rect(rx, ry, cell, cell, fill=1, stroke=0)
        c.restoreState()

    @classmethod
    def generate_single_card(cls, student: Student, school: SchoolSetting, output_pdf_path: str):
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # Background Card Outline
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # Header Bar (Navy Blue)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(0, cls.CARD_HEIGHT - 36, cls.CARD_WIDTH, 36, fill=1, stroke=0)

        # School Name in White
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 15, school_title[:38])

        c.setFont("Helvetica", 6.2)
        did = student.digital_id_code or generate_digital_id(student.student_id, student.admission_date)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 26, f"STUDENT DIGITAL ID  |  {did}")

        # Photo Frame
        photo_x = 12
        photo_y = 26
        photo_w = 50
        photo_h = 64
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)

        photo_drawn = False
        if student.photo_path and Path(student.photo_path).exists():
            try:
                c.drawImage(
                    student.photo_path,
                    photo_x + 1,
                    photo_y + 1,
                    width=photo_w - 2,
                    height=photo_h - 2,
                    preserveAspectRatio=True,
                    anchor="c",
                )
                photo_drawn = True
            except Exception:
                photo_drawn = False

        if not photo_drawn:
            c.setFillColor(colors.HexColor("#64748B"))
            c.setFont("Helvetica", 7)
            c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 2, "PHOTO")

        # Student Details Column
        info_x = photo_x + photo_w + 10
        info_y = cls.CARD_HEIGHT - 49
        line_spacing = 10.5

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(info_x, info_y, student.full_name[:22])

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y - line_spacing, f"ID: {student.student_id}  |  Adm: {student.admission_number}")

        class_str = student.school_class.name if student.school_class else "-"
        sec_str = student.section.name if student.section else "-"
        c.drawString(info_x, info_y - (line_spacing * 2), f"Class: {class_str} ({sec_str})  |  Roll: {student.roll_number}")
        c.drawString(info_x, info_y - (line_spacing * 3), f"Blood: {student.blood_group or 'N/A'}  |  Status: {student.status.upper()}")

        if student.guardian:
            c.drawString(info_x, info_y - (line_spacing * 4), f"Guardian: {student.guardian.guardian_name[:16]}")
            c.drawString(info_x, info_y - (line_spacing * 5), f"Phone: {student.guardian.guardian_phone}")
        elif student.emergency_contact:
            c.drawString(info_x, info_y - (line_spacing * 4), f"Emergency: {student.emergency_contact}")

        # QR Code Bottom-Right
        qr_payload = student.qr_payload or build_qr_payload(
            student.student_id, student.admission_number, did, getattr(student, "public_id", None)
        )
        cls._draw_qr_matrix(c, qr_payload, x=cls.CARD_WIDTH - 48, y=20, size=38)

        # Bottom Bar & Signature
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, 0, cls.CARD_WIDTH, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 5.8)
        c.drawString(10, 4, "Verified Institute Digital ID")
        c.drawRightString(cls.CARD_WIDTH - 10, 4, "Principal Signature")

        c.showPage()
        c.save()
        return output_pdf_path
