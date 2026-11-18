"""
EduManage Pro - Admission CRM PDF Document Generators (ReportLab)
Generates 4 official admission artifacts:
1. Printable Admission Application Form (Portrait A4)
2. Applicant Fee Payment Money Receipt (Landscape A5)
3. Admission Entrance Test Admit Card (Landscape A5)
4. Official Merit & Waiting List Publication (Portrait A4)
"""

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _school_attr(school: Any, key: str, default: str = "") -> str:
    if isinstance(school, dict):
        return str(school.get(key, default) or default)
    return str(getattr(school, key, default) or default)


class AdmissionPDFGenerator:
    # ------------------------------------------------------------------
    # 1. ADMISSION APPLICATION FORM (A4 PORTRAIT)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_admission_form(
        application: Any,
        school: Any,
        output_path: str,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30,
        )
        styles = getSampleStyleSheet()
        h_title = ParagraphStyle(
            "AdmFormTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1, textColor=colors.HexColor("#1E3A8A")
        )
        h_sub = ParagraphStyle(
            "AdmFormSub", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, alignment=1, textColor=colors.HexColor("#475569")
        )
        sec_hdr = ParagraphStyle(
            "SecHdr", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.white
        )
        cell_p = ParagraphStyle("CellP", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)
        cell_b = ParagraphStyle("CellB", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11)

        school_name = _school_attr(school, "school_name", _school_attr(school, "name", "EduManage Pro Model School"))
        eiin = _school_attr(school, "eiin_number", _school_attr(school, "eiin", "134211"))
        address = _school_attr(school, "address", "Main Campus")

        story = [
            Paragraph(school_name.upper(), h_title),
            Paragraph(f"EIIN: {eiin} | {address}", h_sub),
            Spacer(1, 6),
            Paragraph("OFFICIAL ADMISSION APPLICATION FORM", ParagraphStyle("Banner", parent=h_title, fontSize=12, textColor=colors.HexColor("#0F172A"))),
            Spacer(1, 10),
        ]

        cls_name = application.applying_class.name if getattr(application, "applying_class", None) else f"Class #{application.applying_class_id}"
        ay_name = application.academic_year.name if getattr(application, "academic_year", None) else str(application.academic_year_id)

        meta_table = Table(
            [
                [
                    Paragraph(f"<b>Applicant ID:</b> {application.applicant_id}", cell_p),
                    Paragraph(f"<b>Form No:</b> {application.form_number or '-'}", cell_p),
                    Paragraph(f"<b>Status:</b> {application.status}", cell_p),
                ],
                [
                    Paragraph(f"<b>Target Class:</b> {cls_name}", cell_p),
                    Paragraph(f"<b>Academic Year:</b> {ay_name}", cell_p),
                    Paragraph(f"<b>Applied On:</b> {application.application_date}", cell_p),
                ],
            ],
            colWidths=[175, 175, 173],
        )
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#93C5FD")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        def _section_banner(title: str):
            t = Table([[Paragraph(title, sec_hdr)]], colWidths=[523])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E3A8A")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            return t

        story.append(_section_banner("1. APPLICANT & ACADEMIC DETAILS"))
        stu_rows = [
            [Paragraph("<b>Full Name:</b>", cell_b), Paragraph(application.full_name, cell_p), Paragraph("<b>Gender / Blood:</b>", cell_b), Paragraph(f"{application.gender} / {application.blood_group or 'N/A'}", cell_p)],
            [Paragraph("<b>Date of Birth:</b>", cell_b), Paragraph(str(application.date_of_birth), cell_p), Paragraph("<b>Birth Cert No:</b>", cell_b), Paragraph(application.birth_certificate_no or "-", cell_p)],
            [Paragraph("<b>Group / Shift:</b>", cell_b), Paragraph(f"{application.group_name} / {application.shift_name}", cell_p), Paragraph("<b>Nationality:</b>", cell_b), Paragraph(application.nationality or "Bangladeshi", cell_p)],
            [Paragraph("<b>Phone / Email:</b>", cell_b), Paragraph(f"{application.phone or '-'} | {application.email or '-'}", cell_p), Paragraph("<b>Source Channel:</b>", cell_b), Paragraph(application.source_channel, cell_p)],
            [Paragraph("<b>Address:</b>", cell_b), Paragraph(application.address or "-", cell_p), Paragraph("<b>Previous School:</b>", cell_b), Paragraph(f"{application.previous_school or '-'} (GPA: {application.previous_gpa or '-'})", cell_p)],
        ]
        t_stu = Table(stu_rows, colWidths=[95, 170, 100, 158])
        t_stu.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_stu)
        story.append(Spacer(1, 8))

        story.append(_section_banner("2. GUARDIAN & EMERGENCY CONTACT"))
        g_rows = [
            [Paragraph("<b>Guardian Name:</b>", cell_b), Paragraph(f"{application.guardian_name} ({application.guardian_relation})", cell_p), Paragraph("<b>Guardian Phone:</b>", cell_b), Paragraph(application.guardian_phone, cell_p)],
            [Paragraph("<b>Father / Mother:</b>", cell_b), Paragraph(f"{application.father_name or '-'} / {application.mother_name or '-'}", cell_p), Paragraph("<b>Occupation / Email:</b>", cell_b), Paragraph(f"{application.guardian_occupation or '-'} | {application.guardian_email or '-'}", cell_p)],
        ]
        t_g = Table(g_rows, colWidths=[95, 170, 100, 158])
        t_g.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_g)
        story.append(Spacer(1, 8))

        story.append(_section_banner("3. DOCUMENT CHECKLIST & EVALUATION SUMMARY"))
        chk_rows = [[
            Paragraph("<b>Document Item</b>", cell_b),
            Paragraph("<b>Required</b>", cell_b),
            Paragraph("<b>Submitted</b>", cell_b),
            Paragraph("<b>Verified</b>", cell_b),
        ]]
        for item in getattr(application, "checklist_items", []) or []:
            chk_rows.append([
                Paragraph(item.document_name, cell_p),
                Paragraph("Yes" if item.is_required else "Optional", cell_p),
                Paragraph("Yes" if item.is_submitted else "Pending", cell_p),
                Paragraph("Verified" if item.is_verified else "Pending", cell_p),
            ])
        if len(chk_rows) == 1:
            chk_rows.append([Paragraph("Standard checklist pending", cell_p), Paragraph("-", cell_p), Paragraph("-", cell_p), Paragraph("-", cell_p)])

        t_chk = Table(chk_rows, colWidths=[250, 90, 90, 93])
        t_chk.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_chk)
        story.append(Spacer(1, 18))

        sig_table = Table(
            [[
                Paragraph("___________________________<br/>Applicant / Guardian Signature", cell_p),
                Paragraph("___________________________<br/>Admissions Officer", cell_p),
                Paragraph("___________________________<br/>Principal Approval", cell_p),
            ]],
            colWidths=[174, 174, 175],
        )
        sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(sig_table)

        doc.build(story)
        return output_path

    # ------------------------------------------------------------------
    # 2. APPLICANT FEE RECEIPT (LANDSCAPE A5)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_applicant_receipt(
        payment: Any,
        application: Any,
        school: Any,
        output_path: str,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        page_w, page_h = landscape(A5)
        c = canvas.Canvas(output_path, pagesize=(page_w, page_h))

        m_x = 24
        w = page_w - (m_x * 2)

        c.setStrokeColor(colors.HexColor("#1E3A8A"))
        c.setLineWidth(1.5)
        c.roundRect(m_x - 8, 16, page_w - (m_x - 8) * 2, page_h - 32, 6, fill=0, stroke=1)

        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.rect(m_x - 8, page_h - 65, page_w - (m_x - 8) * 2, 49, fill=1, stroke=0)

        school_name = _school_attr(school, "school_name", _school_attr(school, "name", "EduManage Pro Model School"))
        eiin = _school_attr(school, "eiin_number", _school_attr(school, "eiin", "134211"))
        sym = _school_attr(school, "currency_symbol", "BDT ")

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(page_w / 2.0, page_h - 32, school_name.upper())
        c.setFont("Helvetica", 8)
        c.drawCentredString(page_w / 2.0, page_h - 44, f"EIIN: {eiin} | Admission Office Money Receipt")
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(colors.HexColor("#FEF08A"))
        c.drawCentredString(page_w / 2.0, page_h - 58, "APPLICANT ADMISSION FEE RECEIPT")

        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_x, page_h - 82, f"RECEIPT NO: {payment.receipt_no}")
        c.setFont("Helvetica", 8.5)
        c.drawRightString(page_w - m_x, page_h - 82, f"Payment Date: {payment.payment_date}")

        cls_name = application.applying_class.name if getattr(application, "applying_class", None) else f"Class #{application.applying_class_id}"
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(m_x, page_h - 102, f"Applicant Name: {application.full_name}")
        c.drawString(m_x + 250, page_h - 102, f"Applicant ID: {application.applicant_id}")
        c.setFont("Helvetica", 8.5)
        c.drawString(m_x, page_h - 116, f"Guardian: {application.guardian_name} ({application.guardian_phone})")
        c.drawString(m_x + 250, page_h - 116, f"Target Class: {cls_name}")

        tbl_top = page_h - 134
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(m_x, tbl_top - 16, w, 16, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(m_x + 8, tbl_top - 12, "FEE DESCRIPTION")
        c.drawRightString(m_x + 250, tbl_top - 12, "AMOUNT DUE")
        c.drawRightString(m_x + 330, tbl_top - 12, "DISCOUNT")
        c.drawRightString(page_w - m_x - 8, tbl_top - 12, "AMOUNT PAID")

        c.setFont("Helvetica", 8.5)
        c.drawString(m_x + 8, tbl_top - 32, f"{payment.fee_type} ({payment.payment_method})")
        c.drawRightString(m_x + 250, tbl_top - 32, f"{sym}{float(payment.amount_due or 0):,.2f}")
        c.drawRightString(m_x + 330, tbl_top - 32, f"{sym}{float(payment.discount_amount or 0):,.2f}")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(page_w - m_x - 8, tbl_top - 32, f"{sym}{float(payment.amount_paid or 0):,.2f}")

        balance = max(0.0, float(payment.amount_due or 0) - float(payment.discount_amount or 0) - float(payment.amount_paid or 0))
        c.setFont("Helvetica", 8)
        c.drawString(m_x + 8, tbl_top - 52, f"Status: {payment.payment_status} | Ref: {payment.reference_no or 'N/A'} | Balance Due: {sym}{balance:,.2f}")

        c.setFont("Helvetica-Bold", 8)
        c.drawString(m_x, 42, f"Collected By: {payment.collected_by}")
        c.drawRightString(page_w - m_x, 42, "Authorized Cashier / Admissions Seal")
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(page_w / 2.0, 24, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | EduManage Pro Admission CRM")

        c.save()
        return output_path

    # ------------------------------------------------------------------
    # 3. ADMISSION TEST ADMIT CARD (LANDSCAPE A5)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_admit_card(
        application: Any,
        test_score: Optional[Any],
        school: Any,
        output_path: str,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A5),
            leftMargin=26,
            rightMargin=26,
            topMargin=22,
            bottomMargin=22,
        )
        styles = getSampleStyleSheet()
        title_s = ParagraphStyle("ACTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=17, alignment=1, textColor=colors.HexColor("#1E3A8A"))
        sub_s = ParagraphStyle("ACSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor("#475569"))
        badge_s = ParagraphStyle("ACBadge", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, alignment=1, textColor=colors.HexColor("#0F172A"))
        cell_n = ParagraphStyle("ACCellN", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

        school_name = _school_attr(school, "school_name", _school_attr(school, "name", "EduManage Pro Model School"))
        eiin = _school_attr(school, "eiin_number", _school_attr(school, "eiin", "134211"))
        cls_name = application.applying_class.name if getattr(application, "applying_class", None) else f"Class #{application.applying_class_id}"
        ay_name = application.academic_year.name if getattr(application, "academic_year", None) else str(application.academic_year_id)

        admit_no = (getattr(test_score, "admit_card_no", None) if test_score else None) or application.admit_card_number or application.applicant_id
        seat_no = (getattr(test_score, "seat_number", None) if test_score else None) or "HALL-A-01"
        exam_title = (getattr(test_score, "exam_title", None) if test_score else None) or "Admission Entrance Assessment"
        exam_date = (str(getattr(test_score, "exam_date", None)) if test_score and getattr(test_score, "exam_date", None) else "To Be Announced")
        exam_time = (getattr(test_score, "exam_time", None) if test_score else None) or "10:00 AM - 11:30 AM"
        venue = (getattr(test_score, "venue_room", None) if test_score else None) or "Main Examination Hall"

        story = [
            Paragraph(school_name.upper(), title_s),
            Paragraph(f"EIIN: {eiin} | Office of the Admissions Committee", sub_s),
            Spacer(1, 4),
            Paragraph(f"ADMISSION TEST ADMIT CARD — {ay_name}", badge_s),
            Spacer(1, 8),
        ]

        info_tbl = Table(
            [
                [
                    Paragraph(f"<b>Admit Card No:</b> {admit_no}", cell_n),
                    Paragraph(f"<b>Applicant ID:</b> {application.applicant_id}", cell_n),
                    Paragraph(f"<b>Seat / Roll No:</b> {seat_no}", cell_n),
                ],
                [
                    Paragraph(f"<b>Candidate Name:</b> {application.full_name}", cell_n),
                    Paragraph(f"<b>Applying Class:</b> {cls_name}", cell_n),
                    Paragraph(f"<b>Gender:</b> {application.gender}", cell_n),
                ],
                [
                    Paragraph(f"<b>Guardian:</b> {application.guardian_name}", cell_n),
                    Paragraph(f"<b>Contact:</b> {application.guardian_phone}", cell_n),
                    Paragraph(f"<b>Status:</b> {application.status}", cell_n),
                ],
            ],
            colWidths=[190, 190, 160],
        )
        info_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#1E3A8A")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 8))

        sched_tbl = Table(
            [
                [Paragraph("<b>Examination</b>", cell_n), Paragraph("<b>Date</b>", cell_n), Paragraph("<b>Time Slot</b>", cell_n), Paragraph("<b>Venue / Room</b>", cell_n)],
                [Paragraph(exam_title, cell_n), Paragraph(exam_date, cell_n), Paragraph(exam_time, cell_n), Paragraph(venue, cell_n)],
            ],
            colWidths=[170, 100, 130, 140],
        )
        sched_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(sched_tbl)
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Instructions:</b> Bring this Admit Card and a black ballpoint pen 30 minutes prior to the test.", cell_n))
        story.append(Spacer(1, 18))

        sigs = Table(
            [[Paragraph("_____________________<br/>Candidate Signature", cell_n), Paragraph("_____________________<br/>Invigilator Signature", cell_n), Paragraph("_____________________<br/>Principal / Controller", cell_n)]],
            colWidths=[180, 180, 180],
        )
        sigs.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(sigs)

        doc.build(story)
        return output_path

    # ------------------------------------------------------------------
    # 4. OFFICIAL MERIT & WAITING LIST PUBLICATION (A4 PORTRAIT)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_merit_list(
        entries: List[Dict[str, Any]],
        school: Any,
        academic_year_name: str,
        class_name: str,
        seat_quota: int,
        output_path: str,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=32,
            rightMargin=32,
            topMargin=30,
            bottomMargin=30,
        )
        styles = getSampleStyleSheet()
        title_s = ParagraphStyle("MLTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1, textColor=colors.HexColor("#1E3A8A"))
        sub_s = ParagraphStyle("MLSub", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor("#334155"))
        cell_b = ParagraphStyle("MLCellB", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11)
        cell_n = ParagraphStyle("MLCellN", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

        school_name = _school_attr(school, "school_name", _school_attr(school, "name", "EduManage Pro Model School"))
        eiin = _school_attr(school, "eiin_number", _school_attr(school, "eiin", "134211"))

        story = [
            Paragraph(school_name.upper(), title_s),
            Paragraph(f"EIIN: {eiin} | Official Admission Selection & Waiting List ({academic_year_name})", sub_s),
            Spacer(1, 6),
            Paragraph(
                f"<b>MERIT LIST — {class_name.upper()}</b> (Approved Seat Quota: {seat_quota} | Published: {date.today().isoformat()})",
                ParagraphStyle("MLMeta", parent=sub_s, textColor=colors.HexColor("#0F172A")),
            ),
            Spacer(1, 10),
        ]

        rows = [[
            Paragraph("<b>Rank</b>", cell_b),
            Paragraph("<b>Applicant ID</b>", cell_b),
            Paragraph("<b>Candidate Name</b>", cell_b),
            Paragraph("<b>Guardian</b>", cell_b),
            Paragraph("<b>Test %</b>", cell_b),
            Paragraph("<b>Interview</b>", cell_b),
            Paragraph("<b>Merit Score</b>", cell_b),
            Paragraph("<b>Outcome</b>", cell_b),
        ]]

        for item in entries:
            status_lbl = item.get("status", "-")
            if item.get("waitlist_position"):
                status_lbl = f"Waitlisted (#{item['waitlist_position']})"
            rows.append([
                Paragraph(str(item.get("merit_rank") or "-"), cell_n),
                Paragraph(str(item.get("applicant_id", "-")), cell_n),
                Paragraph(str(item.get("full_name", "-")), cell_n),
                Paragraph(str(item.get("guardian_name", "-")), cell_n),
                Paragraph(f"{item.get('test_pct', 0.0):.1f}%", cell_n),
                Paragraph(f"{item.get('interview_score', 0.0):.1f}", cell_n),
                Paragraph(f"<b>{item.get('combined_score', 0.0):.1f}</b>", cell_n),
                Paragraph(status_lbl, cell_n),
            ])

        if len(rows) == 1:
            rows.append([Paragraph("-", cell_n), Paragraph("No ranked candidates available", cell_n), Paragraph("", cell_n), Paragraph("", cell_n), Paragraph("", cell_n), Paragraph("", cell_n), Paragraph("", cell_n), Paragraph("", cell_n)])

        tbl = Table(rows, colWidths=[34, 80, 110, 90, 48, 52, 55, 62])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 24))

        sigs = Table(
            [[Paragraph("_________________________<br/>Admission Committee Convener", cell_n), Paragraph("_________________________<br/>Principal & Seal", cell_n)]],
            colWidths=[265, 265],
        )
        sigs.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(sigs)

        doc.build(story)
        return output_path
