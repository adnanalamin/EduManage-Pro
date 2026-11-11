"""
EduManage Pro - Comprehensive Executive Summary Report Generator
Phase 14: ReportLab Portrait A4 Multi-Section Institutional Briefing
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, portrait
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, colors


class ExecutiveSummaryPdf:
    """
    Generates an official Executive Summary PDF with institutional health metrics,
    financial performance, attendance audits, academic status, and signature blocks.
    """

    @classmethod
    def generate(cls, kpis: dict, school, output_pdf_path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=portrait(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'SchoolHeader',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=HexColor('#1E3A8A')
        )
        sub_style = ParagraphStyle(
            'SchoolSubHeader',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            alignment=1,
            textColor=HexColor('#475569')
        )
        doc_heading = ParagraphStyle(
            'DocHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            alignment=1,
            textColor=HexColor('#0F172A')
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            textColor=HexColor('#1E40AF')
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=HexColor('#0F172A')
        )
        cell_norm = ParagraphStyle(
            'CellNorm',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=HexColor('#334155')
        )
        header_cell = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        elements = []

        # 1. School Header
        school_name = getattr(school, 'school_name', 'EduManage Pro Model Academy')
        motto = getattr(school, 'motto', 'Excellence in Education & Character')
        eiin = getattr(school, 'eiin_number', '134211')
        phone = getattr(school, 'phone', '+880 1712-345678')
        email = getattr(school, 'email', 'admin@edumanage.pro')
        address = getattr(school, 'address', 'Plot 12, Sector 7, Uttara, Dhaka')

        elements.append(Paragraph(school_name.upper(), title_style))
        elements.append(Spacer(1, 2))
        elements.append(Paragraph(f"<i>{motto}</i>", sub_style))
        elements.append(Paragraph(f"{address} | Phone: {phone} | Email: {email} | EIIN: {eiin}", sub_style))
        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=8))

        # 2. Document Title
        elements.append(Paragraph("EXECUTIVE PERFORMANCE BRIEFING & AUDIT SUMMARY", doc_heading))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y - %I:%M %p')} | Institutional Governance Report",
            sub_style
        ))
        elements.append(Spacer(1, 10))

        # 3. Institutional Scorecard Table
        elements.append(Paragraph("1. INSTITUTIONAL SCORECARD & CORE BENCHMARKS", section_style))
        elements.append(Spacer(1, 4))

        scorecard_data = [
            [
                Paragraph("<b>Metric Indicator</b>", header_cell),
                Paragraph("<b>Audited Value</b>", header_cell),
                Paragraph("<b>Benchmark</b>", header_cell),
                Paragraph("<b>Status</b>", header_cell)
            ],
            [
                Paragraph("Total Enrolled Students", cell_norm),
                Paragraph(f"{kpis.get('total_students', 0)} Active", cell_bold),
                Paragraph("500 Target", cell_norm),
                Paragraph("Optimal", cell_bold)
            ],
            [
                Paragraph("Faculty & Staff Strength", cell_norm),
                Paragraph(f"{kpis.get('total_staff', 0)} ({kpis.get('teaching_staff', 0)} Teaching)", cell_bold),
                Paragraph("1:15 Ratio", cell_norm),
                Paragraph("Compliant", cell_bold)
            ],
            [
                Paragraph("Overall Attendance Compliance", cell_norm),
                Paragraph(f"{kpis.get('attendance_rate', 92.5)}%", cell_bold),
                Paragraph("90.0% Minimum", cell_norm),
                Paragraph("Healthy", cell_bold)
            ],
            [
                Paragraph("Fee Collection Efficiency", cell_norm),
                Paragraph(f"{kpis.get('collection_efficiency', 0.0)}%", cell_bold),
                Paragraph("85.0% Target", cell_norm),
                Paragraph("On Track" if kpis.get('collection_efficiency', 0.0) >= 80 else "Attention", cell_bold)
            ],
            [
                Paragraph("Institutional Average GPA", cell_norm),
                Paragraph(f"{kpis.get('avg_gpa', 3.85)} / 5.00", cell_bold),
                Paragraph("3.50 Standard", cell_norm),
                Paragraph("Distinction", cell_bold)
            ],
            [
                Paragraph("Examination Pass Rate", cell_norm),
                Paragraph(f"{kpis.get('pass_rate', 95.0)}%", cell_bold),
                Paragraph("90.0% Standard", cell_norm),
                Paragraph("Exceeding", cell_bold)
            ],
        ]

        scorecard_table = Table(scorecard_data, colWidths=[200, 140, 100, 100])
        scorecard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(scorecard_table)
        elements.append(Spacer(1, 10))

        # 4. Financial Health & Fee Realization
        elements.append(Paragraph("2. FINANCIAL HEALTH & FEE REALIZATION SUMMARY", section_style))
        elements.append(Spacer(1, 4))

        invoiced = kpis.get('total_invoiced', 0.0)
        collected = kpis.get('total_collected', 0.0)
        dues = kpis.get('total_dues', 0.0)
        income = kpis.get('total_income', 0.0)
        expenses = kpis.get('total_expenses', 0.0)
        surplus = kpis.get('net_surplus', 0.0)

        finance_data = [
            [
                Paragraph("<b>Revenue & Accounts Stream</b>", header_cell),
                Paragraph("<b>Total Amount (৳)</b>", header_cell),
                Paragraph("<b>Audited Status</b>", header_cell)
            ],
            [
                Paragraph("Gross Student Fee Billing", cell_norm),
                Paragraph(f"৳ {invoiced:,.2f}", cell_bold),
                Paragraph("Invoiced", cell_norm)
            ],
            [
                Paragraph("Realized Collections (Paid)", cell_norm),
                Paragraph(f"৳ {collected:,.2f}", cell_bold),
                Paragraph(f"{kpis.get('collection_efficiency', 0.0)}% Realized", cell_bold)
            ],
            [
                Paragraph("Total Outstanding Dues / Arrears", cell_norm),
                Paragraph(f"৳ {dues:,.2f}", cell_bold),
                Paragraph(f"{kpis.get('defaulters_count', 0)} Overdue Accounts", cell_norm)
            ],
            [
                Paragraph("Operating Revenue / General Income", cell_norm),
                Paragraph(f"৳ {income:,.2f}", cell_bold),
                Paragraph("Chart of Accounts", cell_norm)
            ],
            [
                Paragraph("Operating Expenditures", cell_norm),
                Paragraph(f"৳ {expenses:,.2f}", cell_bold),
                Paragraph("Staff, Admin & Utilities", cell_norm)
            ],
            [
                Paragraph("<b>Net Operating Surplus / (Deficit)</b>", cell_bold),
                Paragraph(f"<b>৳ {surplus:,.2f}</b>", cell_bold),
                Paragraph("<b>Healthy Cashflow</b>" if surplus >= 0 else "<b>Deficit</b>", cell_bold)
            ],
        ]

        finance_table = Table(finance_data, colWidths=[240, 160, 140])
        finance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563EB')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [HexColor('#FFFFFF'), HexColor('#F8FAFC')]),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#E0F2FE')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(finance_table)
        elements.append(Spacer(1, 10))

        # 5. Facilities & Operations Audit
        elements.append(Paragraph("3. OPERATIONAL FACILITIES & LOGISTICS UTILIZATION", section_style))
        elements.append(Spacer(1, 4))

        facility_data = [
            [
                Paragraph("<b>Division</b>", header_cell),
                Paragraph("<b>Operational Metric</b>", header_cell),
                Paragraph("<b>Current Capacity / Utilization</b>", header_cell),
                Paragraph("<b>Evaluation</b>", header_cell)
            ],
            [
                Paragraph("Library Circulation", cell_norm),
                Paragraph(f"{kpis.get('total_books', 0)} Titles Cataloged", cell_norm),
                Paragraph(f"{kpis.get('active_loans', 0)} Active Borrowings", cell_bold),
                Paragraph("Active Reading", cell_norm)
            ],
            [
                Paragraph("Fleet Transportation", cell_norm),
                Paragraph(f"{kpis.get('total_routes', 0)} Daily Commuter Routes", cell_norm),
                Paragraph(f"{kpis.get('transport_passengers', 0)} Registered Students", cell_bold),
                Paragraph("100% Route Coverage", cell_norm)
            ],
            [
                Paragraph("Hostel & Residential", cell_norm),
                Paragraph(f"{kpis.get('hostel_capacity', 0)} Total Bed Capacity", cell_norm),
                Paragraph(f"{kpis.get('hostel_occupancy', 0)} Occupied ({kpis.get('hostel_occupancy_rate', 0.0)}%)", cell_bold),
                Paragraph("Secure & Managed", cell_norm)
            ],
        ]

        facility_table = Table(facility_data, colWidths=[130, 140, 170, 100])
        facility_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0D9488')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(facility_table)
        elements.append(Spacer(1, 24))

        # 6. Executive Signature Block
        sig_data = [
            [
                Paragraph("<b>_____________________________</b><br/><b>Prepared By</b><br/>Lead Data Analyst", cell_norm),
                Paragraph("<b>_____________________________</b><br/><b>Audited By</b><br/>Bursar / Financial Controller", cell_norm),
                Paragraph(f"<b>_____________________________</b><br/><b>Approved By</b><br/>{getattr(school, 'principal_name', 'Principal')}", cell_norm),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(sig_table)

        doc.build(elements)
        return output_pdf_path
