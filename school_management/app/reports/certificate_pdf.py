"""
EduManage Pro - Ornamental Certificate & Batch ID Sheet PDF Generator
Phase 15: Landscape A4 Gold/Navy Official Certificates & Portrait A4 8-up CR80 PVC ID Sheets
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter, A4, landscape, portrait
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


class CertificatePDFGenerator:
    """
    Renders high-craft Landscape A4 official certificates with ornamental double borders,
    corner medallions, custom attestation text, verification serial codes, and signature blocks.
    """

    @staticmethod
    def _build_attestation_lines(cert) -> list[str]:
        ctype = cert.certificate_type
        name = cert.recipient_name
        code = cert.recipient_code
        cls_desig = cert.class_or_designation or "Academic Program"
        guardian = cert.father_or_guardian or "Guardian"
        conduct = cert.conduct_grade or "Exemplary"
        purpose = cert.reason_or_purpose or "official purposes"
        issue_str = cert.issue_date.strftime("%B %d, %Y") if cert.issue_date else date.today().strftime("%B %d, %Y")
        leave_str = cert.leaving_date.strftime("%B %d, %Y") if cert.leaving_date else issue_str

        if ctype == "Transfer Certificate":
            return [
                f"This is to certify that {name} (ID: {code}), Son/Daughter of {guardian},",
                f"was a bona fide student of this institution enrolled in {cls_desig}.",
                f"Having cleared all institutional dues and library obligations, he/she is granted",
                f"an honorable Transfer Certificate effective {leave_str} ({purpose}).",
                f"His/Her moral character and academic conduct during tenure were recorded as {conduct}.",
            ]
        elif ctype == "Character Certificate":
            return [
                f"This is to certify that {name} (ID: {code}), Son/Daughter of {guardian},",
                f"is/was a regular student of {cls_desig} at this Academy.",
                f"To the best of our institutional knowledge and disciplinary records, he/she bears",
                f"a {conduct} moral character and has never participated in any activity contrary",
                f"to school discipline or national law. Issued for {purpose}.",
            ]
        elif ctype == "Testimonial":
            return [
                f"We take immense pleasure in certifying that {name} (ID: {code}),",
                f"ward of {guardian}, successfully pursued studies in {cls_desig}.",
                f"He/She demonstrated {conduct} diligence, scholarly discipline, and leadership",
                f"in co-curricular pursuits. This official testimonial is awarded on {issue_str}",
                f"for {purpose}. We wish him/her every success in future endeavors.",
            ]
        elif ctype == "Merit Certificate":
            return [
                f"This Certificate of Academic & Co-Curricular Merit is proudly conferred upon",
                f"{name} (ID: {code}) of {cls_desig} in recognition of",
                f"outstanding achievement and distinction in: {purpose}.",
                f"Awarded on {issue_str} for exemplary dedication, innovation, and {conduct} conduct.",
            ]
        elif ctype == "Staff Experience Letter":
            return [
                f"This is to certify that {name} (Employee ID: {code}) served our institution",
                f"with distinction in the capacity of {cls_desig}.",
                f"Throughout his/her tenure up to {leave_str}, his/her professional integrity,",
                f"pedagogical commitment, and workplace conduct remained {conduct}.",
                f"Issued upon request for {purpose}.",
            ]
        else:  # Bonafide Certificate
            return [
                f"This is to certify that {name} (ID: {code}), Son/Daughter of {guardian},",
                f"is a bona fide full-time student currently enrolled in {cls_desig}",
                f"for the active academic session at our institution.",
                f"His/Her attendance standing and conduct are verified as {conduct}.",
                f"This certificate is issued on {issue_str} specifically for {purpose}.",
            ]

    @classmethod
    def generate_certificate_pdf(cls, cert, school, output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        page_w, page_h = landscape(A4)
        c = canvas.Canvas(output_pdf_path, pagesize=(page_w, page_h))

        # Parchment subtle tint background
        c.setFillColor(colors.HexColor("#FFFDF7"))
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # Outer Royal Navy Border
        margin = 24
        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.setLineWidth(4)
        c.rect(margin, margin, page_w - 2 * margin, page_h - 2 * margin, fill=0, stroke=1)

        # Inner Gold Ornamental Border
        inner = 34
        c.setStrokeColor(colors.HexColor("#B45309"))
        c.setLineWidth(1.5)
        c.rect(inner, inner, page_w - 2 * inner, page_h - 2 * inner, fill=0, stroke=1)

        # Corner Gold Diamonds
        c.setFillColor(colors.HexColor("#D97706"))
        for cx, cy in [
            (inner, inner),
            (page_w - inner, inner),
            (inner, page_h - inner),
            (page_w - inner, page_h - inner),
        ]:
            c.circle(cx, cy, 4, fill=1, stroke=0)

        # Top Serial & Verification Header
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(inner + 16, page_h - inner - 20, f"SERIAL NO: {cert.certificate_number}")
        c.drawRightString(page_w - inner - 16, page_h - inner - 20, f"VERIFY TOKEN: {cert.verification_code}")

        # School Branding
        school_name = getattr(school, "school_name", "Ideal Model High School & College")
        motto = getattr(school, "motto", "Excellence in Education & Character")
        eiin = getattr(school, "eiin_number", "134211")
        address = getattr(school, "address", "Plot 12, Sector 7, Uttara, Dhaka")

        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(page_w / 2.0, page_h - 92, school_name.upper())

        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(page_w / 2.0, page_h - 108, f"{motto}  |  EIIN: {eiin}  |  {address}")

        # Certificate Banner Ribbon
        ribbon_w = 380
        ribbon_h = 34
        ribbon_x = (page_w - ribbon_w) / 2.0
        ribbon_y = page_h - 162
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.roundRect(ribbon_x, ribbon_y, ribbon_w, ribbon_h, 6, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#FDE68A"))
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(page_w / 2.0, ribbon_y + 11, cert.certificate_type.upper())

        # Sub-intro
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(page_w / 2.0, page_h - 196, "TO WHOM IT MAY CONCERN")

        # Highlighted Recipient Nameplate
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Times-BoldItalic", 26)
        c.drawCentredString(page_w / 2.0, page_h - 234, cert.recipient_name)

        c.setStrokeColor(colors.HexColor("#D97706"))
        c.setLineWidth(1)
        c.line(page_w / 2.0 - 170, page_h - 242, page_w / 2.0 + 170, page_h - 242)

        # Attestation Body Lines
        lines = cls._build_attestation_lines(cert)
        y_cursor = page_h - 278
        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Times-Roman", 13)
        for line in lines:
            c.drawCentredString(page_w / 2.0, y_cursor, line)
            y_cursor -= 22

        if cert.remarks:
            c.setFillColor(colors.HexColor("#475569"))
            c.setFont("Helvetica-Oblique", 9.5)
            c.drawCentredString(page_w / 2.0, y_cursor - 6, f"Note: {cert.remarks[:95]}")

        # Official Gold Seal Circle (Bottom Center)
        seal_x = page_w / 2.0
        seal_y = 95
        c.setStrokeColor(colors.HexColor("#B45309"))
        c.setFillColor(colors.HexColor("#FEF3C7"))
        c.setLineWidth(2)
        c.circle(seal_x, seal_y, 30, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#92400E"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(seal_x, seal_y + 4, "OFFICIAL")
        c.drawCentredString(seal_x, seal_y - 6, "INSTITUTE SEAL")

        # Signature Blocks (Left, Right)
        issue_date_str = cert.issue_date.strftime("%d %b %Y") if cert.issue_date else date.today().strftime("%d %b %Y")
        principal_name = getattr(school, "principal_name", "Principal")

        c.setStrokeColor(colors.HexColor("#334155"))
        c.setLineWidth(0.8)
        # Left Block: Date & Registrar
        c.line(85, 88, 255, 88)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9.5)
        c.drawCentredString(170, 74, "Academic Registrar / Office")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(170, 62, f"Issued Date: {issue_date_str}")

        # Right Block: Principal
        c.line(page_w - 255, 88, page_w - 85, 88)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9.5)
        c.drawCentredString(page_w - 170, 74, principal_name)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawCentredString(page_w - 170, 62, "Principal & Head of Institution")

        c.showPage()
        c.save()
        return output_pdf_path

    @classmethod
    def generate_batch_student_id_sheet(cls, students: list, school, output_pdf_path: str) -> str:
        """
        Generates a Portrait A4 sheet containing up to 8 CR80 PVC-size Student ID cards per page (2x4 grid).
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        page_w, page_h = portrait(A4)
        c = canvas.Canvas(output_pdf_path, pagesize=(page_w, page_h))

        card_w = 3.375 * inch
        card_h = 2.125 * inch
        margin_x = (page_w - (2 * card_w + 24)) / 2.0
        top_start_y = page_h - 48 - card_h

        school_title = getattr(school, "school_name", "Ideal Model High School & College")

        for idx, student in enumerate(students):
            pos_in_page = idx % 8
            if idx > 0 and pos_in_page == 0:
                c.showPage()

            col = pos_in_page % 2
            row = pos_in_page // 2

            x0 = margin_x + col * (card_w + 24)
            y0 = top_start_y - row * (card_h + 18)

            # Card Border
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(1)
            c.roundRect(x0, y0, card_w, card_h, 6, fill=1, stroke=1)

            # Header
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.rect(x0, y0 + card_h - 34, card_w, 34, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x0 + card_w / 2.0, y0 + card_h - 14, school_title[:38])
            c.setFont("Helvetica", 6)
            c.drawCentredString(x0 + card_w / 2.0, y0 + card_h - 25, "STUDENT IDENTITY CARD")

            # Photo Box
            px = x0 + 12
            py = y0 + 26
            pw = 50
            ph = 64
            c.setFillColor(colors.HexColor("#F1F5F9"))
            c.setStrokeColor(colors.HexColor("#94A3B8"))
            c.rect(px, py, pw, ph, fill=1, stroke=1)
            c.setFillColor(colors.HexColor("#64748B"))
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(px + pw / 2.0, py + ph / 2.0 - 2, "PHOTO")

            # Info
            ix = px + pw + 10
            iy = y0 + card_h - 48
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(ix, iy, student.full_name[:24])

            c.setFillColor(colors.HexColor("#334155"))
            c.setFont("Helvetica", 7)
            c.drawString(ix, iy - 11, f"ID: {student.student_id}")
            cls_str = student.school_class.name if student.school_class else "N/A"
            sec_str = student.section.name if student.section else "A"
            c.drawString(ix, iy - 22, f"Class: {cls_str} | Sec: {sec_str}")
            c.drawString(ix, iy - 33, f"Roll: {student.roll_number} | Blood: {student.blood_group or 'N/A'}")
            if student.guardian:
                c.drawString(ix, iy - 44, f"Guardian: {student.guardian.guardian_name[:18]}")
                c.drawString(ix, iy - 55, f"Tel: {student.guardian.guardian_phone}")

            # Footer Strip
            c.setFillColor(colors.HexColor("#0F172A"))
            c.rect(x0, y0, card_w, 13, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica", 5.5)
            c.drawString(x0 + 8, y0 + 4, f"Adm: {student.admission_number}")
            c.drawRightString(x0 + card_w - 8, y0 + 4, "Valid 2026 Session")

        c.showPage()
        c.save()
        return output_pdf_path
