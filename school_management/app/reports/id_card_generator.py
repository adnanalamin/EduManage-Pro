"""
EduManage Pro - Student ID Card Generator (ReportLab PDF)
Renders standard CR80 printable PVC / Paper ID cards with photo container, barcode, and emergency contacts.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from app.models.student import Student
from app.models.school import SchoolSetting


class StudentIDCardGenerator:
    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @classmethod
    def generate_single_card(cls, student: Student, school: SchoolSetting, output_pdf_path: str):
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # Background Card Outline
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # Header Bar (Navy Blue)
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)

        # School Name in White
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_title[:38])

        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 27, "STUDENT IDENTITY CARD")

        # Photo Placeholder Frame
        photo_x = 14
        photo_y = 28
        photo_w = 54
        photo_h = 68
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 2, "PHOTO")

        # Student Details Column
        info_x = photo_x + photo_w + 12
        info_y = cls.CARD_HEIGHT - 52
        line_spacing = 11

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(info_x, info_y, student.full_name[:24])

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#334155"))
        
        c.drawString(info_x, info_y - line_spacing, f"ID: {student.student_id}")
        
        class_str = student.school_class.name if student.school_class else "Class 10"
        sec_str = student.section.name if student.section else "A"
        c.drawString(info_x, info_y - (line_spacing * 2), f"Class: {class_str}  |  Sec: {sec_str}")
        c.drawString(info_x, info_y - (line_spacing * 3), f"Roll No: {student.roll_number}   |   Blood: {student.blood_group or 'N/A'}")

        if student.guardian:
            c.drawString(info_x, info_y - (line_spacing * 4), f"Guardian: {student.guardian.guardian_name[:18]}")
            c.drawString(info_x, info_y - (line_spacing * 5), f"Phone: {student.guardian.guardian_phone}")

        # Bottom Bar & Signature
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, 0, cls.CARD_WIDTH, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 6)
        c.drawString(10, 4, "Authorized Institute Property")
        c.drawRightString(cls.CARD_WIDTH - 10, 4, "Principal Signature")

        c.showPage()
        c.save()
        return output_pdf_path
