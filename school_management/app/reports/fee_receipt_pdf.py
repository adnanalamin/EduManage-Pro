"""
EduManage Pro - Fee Payment Receipt PDF Generator (ReportLab)
Generates high-resolution official payment vouchers with itemized breakdowns,
scholarship/waiver concessions, channel details, remaining balances, and cashier stamps.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5, landscape
from reportlab.pdfgen import canvas


def _school_attr(school, key: str, default: str = "") -> str:
    if school is None:
        return default
    if isinstance(school, dict):
        val = school.get(key) or school.get("name" if key == "school_name" else key)
        return str(val) if val else default
    return str(getattr(school, key, None) or default)


class FeeReceiptPDFGenerator:
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A5)

    @classmethod
    def generate_receipt(
        cls,
        payment,
        school=None,
        output_pdf_path: str = None,
        school_info=None,
        output_path: str = None,
    ) -> bool:
        target_path = output_pdf_path or output_path
        if not target_path:
            raise ValueError("Output PDF path is required.")
        school_obj = school if school is not None else school_info

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        c = canvas.Canvas(target_path, pagesize=(cls.PAGE_WIDTH, cls.PAGE_HEIGHT))

        m_x = 24
        w = cls.PAGE_WIDTH - (m_x * 2)

        # Borders
        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.setLineWidth(1.5)
        c.roundRect(m_x - 8, 16, cls.PAGE_WIDTH - (m_x - 8) * 2, cls.PAGE_HEIGHT - 32, 6, fill=0, stroke=1)
        c.setStrokeColor(colors.HexColor("#93C5FD"))
        c.setLineWidth(0.5)
        c.roundRect(m_x - 5, 19, cls.PAGE_WIDTH - (m_x - 5) * 2, cls.PAGE_HEIGHT - 38, 4, fill=0, stroke=1)

        # Header Banner
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(m_x - 8, cls.PAGE_HEIGHT - 65, cls.PAGE_WIDTH - (m_x - 8) * 2, 49, fill=1, stroke=0)

        school_name = _school_attr(school_obj, "school_name", "EduManage Pro Model High School")
        eiin = _school_attr(school_obj, "eiin_number", _school_attr(school_obj, "eiin", "134211"))
        address = _school_attr(school_obj, "address", "Uttara, Dhaka")
        phone = _school_attr(school_obj, "phone", "+880 1712-345678")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 32, school_name.upper())

        c.setFont("Helvetica", 8)
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 44, f"EIIN: {eiin} | {address} | Phone: {phone}")

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#FEF08A"))
        c.drawCentredString(cls.PAGE_WIDTH / 2.0, cls.PAGE_HEIGHT - 57, "OFFICIAL MONEY RECEIPT / STUDENT FEE VOUCHER")

        # Voucher Metadata Bar
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        receipt_no = getattr(payment, "receipt_no", None) or getattr(payment, "receipt_number", "REC-0000")
        c.drawString(m_x, cls.PAGE_HEIGHT - 80, f"RECEIPT NO: {receipt_no}  [{getattr(payment, 'status', 'Completed')}]")

        c.setFont("Helvetica", 8.5)
        pay_date = payment.payment_date.strftime("%d-%b-%Y") if hasattr(payment.payment_date, "strftime") else str(payment.payment_date)
        c.drawRightString(cls.PAGE_WIDTH - m_x, cls.PAGE_HEIGHT - 80, f"Payment Date: {pay_date}")

        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.setLineWidth(0.8)
        c.line(m_x, cls.PAGE_HEIGHT - 86, cls.PAGE_WIDTH - m_x, cls.PAGE_HEIGHT - 86)

        stu = payment.student
        s_fee = payment.student_fee
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x, cls.PAGE_HEIGHT - 98, "Student Name:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 70, cls.PAGE_HEIGHT - 98, stu.full_name if stu else "Student")

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x + 240, cls.PAGE_HEIGHT - 98, "Student ID:")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 295, cls.PAGE_HEIGHT - 98, stu.student_id if stu else "-")

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x, cls.PAGE_HEIGHT - 110, "Invoice No:")
        c.setFont("Helvetica", 8.5)
        inv_no = s_fee.invoice_number if s_fee else "-"
        roll_txt = f"#{stu.roll_number}" if stu else "-"
        c.drawString(m_x + 70, cls.PAGE_HEIGHT - 110, f"{inv_no} (Roll {roll_txt})")

        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x + 240, cls.PAGE_HEIGHT - 110, "Class & Sec:")
        c.setFont("Helvetica", 8.5)
        cls_name = stu.school_class.name if stu and getattr(stu, "school_class", None) else "Class"
        sec_name = stu.section.name if stu and getattr(stu, "section", None) else "-"
        c.drawString(m_x + 295, cls.PAGE_HEIGHT - 110, f"{cls_name} ({sec_name})")

        # Table Header
        tbl_top = cls.PAGE_HEIGHT - 124
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(m_x, tbl_top - 16, w, 16, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(m_x + 8, tbl_top - 12, "DESCRIPTION / FEE HEAD")
        c.drawRightString(m_x + 220, tbl_top - 12, "ORIGINAL")
        c.drawRightString(m_x + 285, tbl_top - 12, "CONCESSION")
        c.drawRightString(m_x + 350, tbl_top - 12, "NET FEE")
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 12, "PAID NOW (BDT)")

        struct_title = s_fee.display_title if s_fee else "Academic Tuition Fee"
        tot_amt = float(s_fee.total_amount) if s_fee else float(payment.amount_paid)
        disc_amt = float(s_fee.discount_amount) if s_fee else 0.0
        net_amt = float(s_fee.net_amount) if s_fee else float(payment.amount_paid)

        c.setFont("Helvetica", 8)
        c.drawString(m_x + 8, tbl_top - 30, struct_title[:42])
        c.drawRightString(m_x + 220, tbl_top - 30, f"BDT {tot_amt:,.2f}")
        c.drawRightString(m_x + 285, tbl_top - 30, f"BDT {disc_amt:,.2f}")
        c.drawRightString(m_x + 350, tbl_top - 30, f"BDT {net_amt:,.2f}")

        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(colors.HexColor("#059669"))
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 30, f"BDT {float(payment.amount_paid):,.2f}")

        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(m_x, tbl_top - 38, cls.PAGE_WIDTH - m_x, tbl_top - 38)

        rem_due = float(s_fee.due_amount) if s_fee else 0.0
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)
        detail = getattr(payment, "channel_detail", None)
        ch_str = f"{payment.payment_method}" + (f" / {detail}" if detail else "") + (f" ({payment.transaction_id})" if payment.transaction_id else "")
        c.drawString(m_x + 8, tbl_top - 50, f"Payment Channel: {ch_str}")

        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(cls.PAGE_WIDTH - m_x - 8, tbl_top - 50, f"Remaining Due Balance: BDT {rem_due:,.2f}")

        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(m_x + 8, tbl_top - 62, "Note: Official computer-generated financial receipt. Retain for institution audit records.")

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
        return True
