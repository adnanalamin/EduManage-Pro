"""
EduManage Pro - Fee Payment Receipt PDF Generator (ReportLab)
Generates high-resolution official payment vouchers with itemized breakdowns,
scholarship discounts, remaining balances, and cashier stamps.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class FeeReceiptPDFGenerator:
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5) # 210mm x 148mm (Landscape A5 is standard for receipt vouchers)

    @classmethod
    def generate_receipt(
        cls,
        payment,
        school,
        output_pdf_path: str
    ) -> str:
        c = canvas.Canvas(output_pdf_path, pagesize=(cls.PAGE_WIDTH, cls.PAGE_HEIGHT))

        # Margin & Dimensions
        m_x = 24
        m_y = cls.PAGE_HEIGHT - 24
        w = cls.PAGE_WIDTH - (m_x * 2)

        # Outer Decorative Border
        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.setLineWidth(1.5)
        c.roundRect(m_x - 8, 16, cls.PAGE_WIDTH - (m_x - 8) * 2, cls.PAGE_HEIGHT - 32, 6, fill=0, stroke=1)

        # Inner Accent Line
        c.setStrokeColor(colors.HexColor("#93C5FD"))
        c.setLineWidth(0.5)
        c.roundRect(m_x - 5, 19, cls.PAGE_WIDTH - (m_x - 5) * 2, cls.PAGE_HEIGHT - 38, 4, fill=0, stroke=1)

        # Top School Header Banner
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(m_x - 8, cls.PAGE_HEIGHT - 65, cls.PAGE_WIDTH - (m_x - 8) * 2, 49, fill=1, stroke=0)

        # School Name & EIIN
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 32, school.school_name.upper())

        c.setFont("Helvetica", 8)
        info_str = f"EIIN: {school.eiin_number or '134211'} | {school.address or 'Uttara, Dhaka'} | Phone: {school.phone or '+880 1712-345678'}"
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 44, info_str)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#FEF08A")) # Gold badge
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 57, "OFFICIAL MONEY RECEIPT / STUDENT FEE VOUCHER")

        # Voucher Metadata Bar
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_x, cls.PAGE_HEIGHT - 80, f"RECEIPT NO: {payment.receipt_no}")
        
        c.setFont("Helvetica", 8.5)
        pay_date = payment.payment_date.strftime("%d-%b-%Y") if hasattr(payment.payment_date, "strftime") else str(payment.payment_date)
        c.drawRightString(cls.PAGE_WIDTH - m_x, cls.PAGE_HEIGHT - 80, f"Payment Date: {pay_date}")

        # Horizontal Rule
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(0.8)
        c.line(m_x, cls.PAGE_HEIGHT - 86, cls.PAGE_WIDTH - m_x, cls.PAGE_HEIGHT - 86)

        # Student Details Box
        stu = payment.student
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x, cls.PAGE_HEIGHT - 98, "Student Name:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 70, cls.PAGE_HEIGHT - 98, stu.full_name)

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x + 240, cls.PAGE_HEIGHT - 98, "Student ID:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 295, cls.PAGE_HEIGHT - 98, stu.student_id)

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x, cls.PAGE_HEIGHT - 110, "Roll Number:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 70, cls.PAGE_HEIGHT - 110, f"#{stu.roll_number}")

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x + 240, cls.PAGE_HEIGHT - 110, "Class & Sec:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 295, cls.PAGE_HEIGHT - 110, f"{stu.school_class.name if hasattr(stu, 'school_class') and stu.school_class else 'Class 10'} ({stu.section.name if hasattr(stu, 'section') and stu.section else 'Sec A'})")

        # Table Header
        tbl_top = cls.PAGE_HEIGHT - 124
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(m_x, tbl_top - 16, w, 16, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(m_x + 8, tbl_top - 12, "DESCRIPTION / FEE HEAD")
        c.drawRightString(m_x + 220, tbl_top - 12, "ORIGINAL")
        c.drawRightString(m_x + 280, tbl_top - 12, "DISCOUNT")
        c.drawRightString(m_x + 350, tbl_top - 12, "NET FEE")
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 12, "PAID NOW (BDT)")

        # Table Data Row
        s_fee = payment.student_fee
        struct_title = s_fee.fee_structure.title if s_fee and s_fee.fee_structure else "Academic Tuition Fee"
        tot_amt = s_fee.total_amount if s_fee else payment.amount_paid
        disc_amt = s_fee.discount_amount if s_fee else 0.0
        net_amt = s_fee.net_amount if s_fee else payment.amount_paid

        c.setFont("Helvetica", 8)
        c.drawString(m_x + 8, tbl_top - 30, struct_title)
        c.drawRightString(m_x + 220, tbl_top - 30, f"৳{tot_amt:,.2f}")
        c.drawRightString(m_x + 280, tbl_top - 30, f"৳{disc_amt:,.2f}")
        c.drawRightString(m_x + 350, tbl_top - 30, f"৳{net_amt:,.2f}")

        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#059669")) # Green
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 30, f"৳{payment.amount_paid:,.2f}")

        # Summary Breakdown Box
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(m_x, tbl_top - 38, cls.PAGE_WIDTH - m_x, tbl_top - 38)

        rem_due = s_fee.due_amount if s_fee else 0.0
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)
        c.drawString(m_x + 8, tbl_top - 50, f"Payment Channel: {payment.payment_method} {'(' + payment.transaction_id + ')' if payment.transaction_id else ''}")
        
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 50, f"Remaining Due Balance: ৳{rem_due:,.2f}")

        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(m_x + 8, tbl_top - 62, "Note: This is an official computer-generated receipt. Please preserve it for future records.")

        # Bottom Signatures
        sig_y = 42
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(0.8)
        c.line(m_x + 10, sig_y + 12, m_x + 130, sig_y + 12)
        c.line(cls.PAGE_WIDTH - m_x - 130, sig_y + 12, cls.PAGE_WIDTH - m_x - 10, sig_y + 12)

        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(m_x + 70, sig_y + 2, "Depositor / Student Signature")
        c.drawCentredString(cls.PAGE_WIDTH - m_x - 70, sig_y + 2, f"Authorized Cashier ({payment.collected_by})")

        c.showPage()
        c.save()
        return output_pdf_path
