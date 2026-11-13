"""
EduManage Pro - Student Profile Printable Dossier (ReportLab PDF)
Renders complete official student CRM dossier on standard A4 including Digital ID,
QR code, academic/personal summary, multiple guardians, medical notes, and signatures.
"""

from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.school import SchoolSetting
from app.models.student import Student
from app.utils.qr_generator import build_qr_payload, generate_digital_id, generate_qr_matrix


class StudentProfilePDFGenerator:
    @staticmethod
    def _build_qr_drawing(payload: str, size: float = 64) -> Drawing:
        matrix = generate_qr_matrix(payload)
        d = Drawing(size, size)
        dim = len(matrix)
        if dim == 0:
            return d
        cell = size / float(dim)
        d.add(Rect(0, 0, size, size, fillColor=colors.white, strokeColor=colors.HexColor("#CBD5E1")))
        for r_idx, row in enumerate(matrix):
            for c_idx, val in enumerate(row):
                if val:
                    rx = c_idx * cell
                    ry = size - (r_idx + 1) * cell
                    d.add(Rect(rx, ry, cell, cell, fillColor=colors.HexColor("#0F172A"), strokeWidth=0))
        return d

    @classmethod
    def generate(cls, student: Student, school: SchoolSetting, output_path: str):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            "SchoolTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica-Bold",
        )
        sub_style = ParagraphStyle(
            "SchoolSub",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#64748B"),
        )

        if school:
            elements.append(Paragraph(school.school_name, title_style))
            if school.school_name_bn:
                elements.append(Paragraph(school.school_name_bn, sub_style))
            elements.append(
                Paragraph(f"EIIN: {school.eiin_number} | Phone: {school.phone} | Email: {school.email}", sub_style)
            )
            elements.append(Paragraph(school.address, sub_style))
            elements.append(Spacer(1, 14))

        did = student.digital_id_code or generate_digital_id(student.student_id, student.admission_date)
        qr_payload = student.qr_payload or build_qr_payload(
            student.student_id, student.admission_number, did, getattr(student, "public_id", None)
        )

        dossier_style = ParagraphStyle(
            "DossierHeader",
            fontSize=12,
            leading=14,
            alignment=0,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold",
        )
        header_tbl = Table(
            [
                [
                    Paragraph(
                        f"OFFICIAL STUDENT CRM DOSSIER<br/><font size='9' color='#475569'>Digital ID: {did}</font>",
                        dossier_style,
                    ),
                    cls._build_qr_drawing(qr_payload, size=58),
                ]
            ],
            colWidths=[440, 72],
        )
        header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        elements.append(header_tbl)
        elements.append(Spacer(1, 10))

        tags_str = ", ".join(student.get_tag_names()) or "-"
        personal_data = [
            ["Student ID:", student.student_id, "Admission Date:", str(student.admission_date)],
            ["Admission No:", student.admission_number, "Academic Year:", student.academic_year.name if student.academic_year else "-"],
            ["Full Name:", student.full_name, "Roll Number:", str(student.roll_number)],
            ["Class & Section:", f"{student.school_class.name if student.school_class else '-'} ({student.section.name if student.section else '-'})", "Group & Shift:", f"{student.group} / {student.shift}"],
            ["Gender:", student.gender, "Date of Birth:", str(student.date_of_birth)],
            ["Blood Group:", student.blood_group or "N/A", "Religion & Nation:", f"{student.religion} / {student.nationality}"],
            ["Student Phone:", student.phone or "N/A", "Student Email:", student.email or "N/A"],
            ["Birth Certificate:", student.birth_certificate_no or "N/A", "Status:", student.status.upper()],
            ["Digital ID:", did, "Tags:", tags_str],
        ]

        t_personal = Table(personal_data, colWidths=[110, 150, 110, 150])
        t_personal.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E293B")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(t_personal)
        elements.append(Spacer(1, 14))

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
        t_guardian.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(t_guardian)

        if student.medical_profile or student.medical_notes:
            elements.append(Spacer(1, 14))
            elements.append(Paragraph("<b>MEDICAL & HEALTH PROFILE</b>", styles["Normal"]))
            elements.append(Spacer(1, 6))
            mp = student.medical_profile
            med_data = [
                ["Allergies:", (mp.allergies if mp and mp.allergies else student.medical_notes) or "None", "Conditions:", (mp.chronic_conditions if mp else None) or "None"],
                ["Medications:", (mp.medications if mp else None) or "None", "Physician:", f"{mp.physician_name or '-'} ({mp.physician_phone or '-'})" if mp else "N/A"],
            ]
            t_med = Table(med_data, colWidths=[110, 150, 110, 150])
            t_med.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(t_med)

        elements.append(Spacer(1, 30))

        sig_data = [
            ["____________________________", "____________________________", "____________________________"],
            ["Student / Guardian Signature", "Admissions Officer", "Principal & Official Seal"],
        ]
        t_sig = Table(sig_data, colWidths=[170, 170, 170])
        t_sig.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#475569")),
            ])
        )
        elements.append(t_sig)

        doc.build(elements)
        return output_path
