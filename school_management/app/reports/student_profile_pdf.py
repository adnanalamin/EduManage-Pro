"""
EduManage Pro - Student Profile Printable Dossier (ReportLab PDF)
Renders complete official student admission record and guardian dossier on standard A4.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.student import Student
from app.models.school import SchoolSetting


class StudentProfilePDFGenerator:
    @classmethod
    def generate(cls, student: Student, school: SchoolSetting, output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        elements = []

        # 1. School Header
        title_style = ParagraphStyle(
            "SchoolTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica-Bold"
        )
        sub_style = ParagraphStyle(
            "SchoolSub",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#64748B")
        )

        elements.append(Paragraph(school.school_name, title_style))
        if school.school_name_bn:
            elements.append(Paragraph(school.school_name_bn, sub_style))
        elements.append(Paragraph(f"EIIN: {school.eiin_number} | Phone: {school.phone} | Email: {school.email}", sub_style))
        elements.append(Paragraph(school.address, sub_style))
        elements.append(Spacer(1, 14))

        # Title: Student Admission Dossier
        dossier_style = ParagraphStyle(
            "DossierHeader",
            fontSize=12,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold"
        )
        elements.append(Paragraph("OFFICIAL STUDENT ADMISSION DOSSIER", dossier_style))
        elements.append(Spacer(1, 10))

        # 2. Key Academic & Personal Table
        personal_data = [
            ["Student ID:", student.student_id, "Admission Date:", str(student.admission_date)],
            ["Admission No:", student.admission_number, "Academic Year:", student.academic_year.name if student.academic_year else "-"],
            ["Full Name:", student.full_name, "Roll Number:", str(student.roll_number)],
            ["Class & Section:", f"{student.school_class.name if student.school_class else '-'} ({student.section.name if student.section else '-'})", "Group & Shift:", f"{student.group} / {student.shift}"],
            ["Gender:", student.gender, "Date of Birth:", str(student.date_of_birth)],
            ["Blood Group:", student.blood_group or "N/A", "Religion & Nation:", f"{student.religion} / {student.nationality}"],
            ["Student Phone:", student.phone or "N/A", "Student Email:", student.email or "N/A"],
            ["Birth Certificate:", student.birth_certificate_no or "N/A", "Status:", student.status.upper()],
        ]

        t_personal = Table(personal_data, colWidths=[110, 150, 110, 150])
        t_personal.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#1E293B")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_personal)
        elements.append(Spacer(1, 14))

        # 3. Guardian & Contact Info
        elements.append(Paragraph("<b>GUARDIAN & EMERGENCY INFORMATION</b>", styles["Normal"]))
        elements.append(Spacer(1, 6))

        guardian = student.guardian
        guardian_data = [
            ["Father's Name:", guardian.father_name if guardian else "N/A", "Mother's Name:", guardian.mother_name if guardian else "N/A"],
            ["Primary Guardian:", guardian.guardian_name if guardian else "N/A", "Relationship:", guardian.relation if guardian else "Father"],
            ["Guardian Phone:", guardian.guardian_phone if guardian else "N/A", "Guardian Email:", guardian.guardian_email if guardian else "N/A"],
            ["Occupation:", guardian.guardian_occupation if guardian else "N/A", "Emergency Phone:", student.emergency_contact or "N/A"],
            ["Permanent Address:", student.address or "N/A", "Guardian Address:", guardian.guardian_address if guardian else "Same as student"],
        ]

        t_guardian = Table(guardian_data, colWidths=[110, 150, 110, 150])
        t_guardian.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_guardian)
        elements.append(Spacer(1, 30))

        # 4. Signatures
        sig_data = [
            ["____________________________", "____________________________", "____________________________"],
            ["Student / Guardian Signature", "Admissions Officer", "Principal & Official Seal"]
        ]
        t_sig = Table(sig_data, colWidths=[170, 170, 170])
        t_sig.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#475569")),
        ]))
        elements.append(t_sig)

        doc.build(elements)
        return output_path
