"""
EduManage Pro - Teacher & Staff ID Card Generator (ReportLab PDF)
Renders standard CR80 printable PVC / Paper Faculty & Staff Badges.
"""

from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from app.models.staff import Teacher, Staff
from app.models.school import SchoolSetting


class StaffIDCardGenerator:
    CARD_WIDTH = 3.375 * inch   # ~85.6 mm
    CARD_HEIGHT = 2.125 * inch  # ~54 mm

    @classmethod
    def generate_teacher_card(cls, teacher: Teacher, school: SchoolSetting, output_pdf_path: str):
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # Background Outline
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # Header Bar (Dark Emerald for Faculty)
        c.setFillColor(colors.HexColor("#065F46"))
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)

        # School Name in White
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_title[:38])

        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 27, "FACULTY IDENTITY CARD")

        # Photo Frame
        photo_x = 14
        photo_y = 28
        photo_w = 54
        photo_h = 68
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#065F46"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 2, "TEACHER")

        # Details Column
        info_x = photo_x + photo_w + 12
        info_y = cls.CARD_HEIGHT - 52
        line_spacing = 11

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(info_x, info_y, teacher.full_name[:24])

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y - line_spacing, f"ID: {teacher.teacher_id} ({teacher.employee_id})")
        c.drawString(info_x, info_y - (line_spacing * 2), f"Dept: {teacher.department.name if teacher.department else '-'}")
        c.drawString(info_x, info_y - (line_spacing * 3), f"Subject: {teacher.primary_subject}")
        c.drawString(info_x, info_y - (line_spacing * 4), f"Designation: {teacher.designation[:18]}")
        c.drawString(info_x, info_y - (line_spacing * 5), f"Phone: {teacher.phone}")

        # Bottom Bar
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, 0, cls.CARD_WIDTH, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 6)
        c.drawString(10, 4, "Official Faculty Credential")
        c.drawRightString(cls.CARD_WIDTH - 10, 4, "Principal Signature")

        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def generate_staff_card(cls, staff: Staff, school: SchoolSetting, output_pdf_path: str):
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.CARD_WIDTH, cls.CARD_HEIGHT))

        # Background Outline
        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.roundRect(0, 0, cls.CARD_WIDTH, cls.CARD_HEIGHT, 8, fill=1, stroke=1)

        # Header Bar (Indigo for Staff)
        c.setFillColor(colors.HexColor("#3730A3"))
        c.rect(0, cls.CARD_HEIGHT - 38, cls.CARD_WIDTH, 38, fill=1, stroke=0)

        # School Name in White
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        school_title = school.school_name if school else "Ideal Model High School & College"
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 16, school_title[:38])

        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cls.CARD_WIDTH / 2.0, cls.CARD_HEIGHT - 27, "STAFF IDENTITY CARD")

        # Photo Frame
        photo_x = 14
        photo_y = 28
        photo_w = 54
        photo_h = 68
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#3730A3"))
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + (photo_w / 2.0), photo_y + (photo_h / 2.0) - 2, "STAFF")

        # Details Column
        info_x = photo_x + photo_w + 12
        info_y = cls.CARD_HEIGHT - 52
        line_spacing = 11

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(info_x, info_y, staff.full_name[:24])

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(info_x, info_y - line_spacing, f"ID: {staff.staff_id} ({staff.employee_id})")
        c.drawString(info_x, info_y - (line_spacing * 2), f"Position: {staff.position}")
        c.drawString(info_x, info_y - (line_spacing * 3), f"Dept: {staff.department.name if staff.department else '-'}")
        c.drawString(info_x, info_y - (line_spacing * 4), f"Shift: {staff.shift}")
        c.drawString(info_x, info_y - (line_spacing * 5), f"Phone: {staff.phone}")

        # Bottom Bar
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, 0, cls.CARD_WIDTH, 14, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 6)
        c.drawString(10, 4, "Official Institutional Staff")
        c.drawRightString(cls.CARD_WIDTH - 10, 4, "Authority Signature")

        c.showPage()
        c.save()
        return output_pdf_path
