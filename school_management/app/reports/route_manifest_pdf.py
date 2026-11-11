"""
EduManage Pro - Route Manifest Report PDF Generator
Phase 11: Landscape A4 ReportLab Route Passenger Roll Sheet & Fleet Conductor Audit
"""

import os
from datetime import date
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.models.transport import TransportRoute, TransportPassenger
from app.models.school import SchoolSetting


class RouteManifestPDFGenerator:
    """Generates official landscape A4 passenger roll sheets for school bus routes."""

    @classmethod
    def generate_manifest(
        cls,
        route: TransportRoute,
        passengers: List[TransportPassenger],
        school: Optional[SchoolSetting] = None,
        output_path: str = "route_manifest_report.pdf"
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'SchoolTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            alignment=1,
            textColor=colors.HexColor('#0F172A')
        )

        sub_style = ParagraphStyle(
            'SchoolSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            alignment=1,
            textColor=colors.HexColor('#64748B')
        )

        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            alignment=1,
            textColor=colors.HexColor('#B45309')
        )

        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )

        cell_bold = ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0F172A')
        )

        story = []

        # 1. School Header
        school_name = school.school_name if school else "Ideal Model High School & College"
        school_address = school.address if (school and school.address) else "Road 12, Dhanmondi, Dhaka-1209 • Contact: transport@edumanage.edu"

        story.append(Paragraph(school_name.upper(), title_style))
        story.append(Paragraph(school_address, sub_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"PASSENGER MANIFEST & BUS CONDUCTOR ROLL SHEET — {route.route_name.upper()}", meta_style))
        story.append(Paragraph(f"Route Code: {route.route_code} • Timing: Pickup {route.pickup_time or '06:45 AM'} / Drop {route.drop_time or '02:30 PM'} • Date: {date.today().strftime('%B %d, %Y')}", sub_style))
        story.append(Spacer(1, 10))

        # 2. Vehicle & Crew Summary Table
        v = route.vehicle
        v_no = v.vehicle_number if v else "Not Assigned"
        v_model = v.vehicle_model if v else "-"
        d_name = f"{v.driver_name} ({v.driver_phone})" if v else "-"
        h_name = f"{v.helper_name or '-'} ({v.helper_phone or '-'})" if v else "-"
        cap = f"{len(passengers)} / {v.seating_capacity if v else 0} Seats Booked"

        crew_data = [
            [
                f"Vehicle: {v_no} ({v_model})",
                f"Driver: {d_name}",
                f"Conductor: {h_name}",
                f"Capacity: {cap}"
            ]
        ]
        crew_table = Table(crew_data, colWidths=[200, 200, 200, 160])
        crew_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFBEB')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F59E0B')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FDE68A')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#92400E')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(crew_table)
        story.append(Spacer(1, 10))

        # 3. Passenger Table
        headers = [
            "Pass No", "Passenger Name", "Type", "Class / Designation",
            "Emergency Contact", "Boarding Stop", "Seat No", "Morning", "Evening"
        ]
        col_widths = [50, 160, 55, 120, 115, 130, 50, 40, 40]

        table_data = [[Paragraph(f"<b>{h}</b>", cell_bold) for h in headers]]

        for p in passengers:
            name = "Passenger"
            affil = "-"
            emg = "-"

            if p.student:
                name = p.student.full_name
                affil = f"Class {p.student.school_class.name if p.student.school_class else '-'} (Roll {p.student.roll_number})"
                emg = p.student.emergency_contact or p.student.phone or "-"
            elif p.teacher:
                name = p.teacher.full_name
                affil = p.teacher.designation or "Faculty"
                emg = p.teacher.phone or "-"

            stop_name = p.stop.stop_name if p.stop else "Campus Gate"
            seat_no = p.seat_number or "-"

            row = [
                Paragraph(f"#{p.id:04d}", cell_style),
                Paragraph(name, cell_bold),
                Paragraph(p.passenger_type, cell_style),
                Paragraph(affil, cell_style),
                Paragraph(emg, cell_style),
                Paragraph(stop_name, cell_style),
                Paragraph(seat_no, cell_style),
                Paragraph("[  ]", cell_style),
                Paragraph("[  ]", cell_style),
            ]
            table_data.append(row)

        if len(passengers) == 0:
            table_data.append([Paragraph("No passengers currently allocated to this route.", cell_style)] + [Paragraph("", cell_style)] * 8)

        passenger_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        passenger_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#92400E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (6, 0), (8, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(passenger_table)
        story.append(Spacer(1, 24))

        # 4. Signatures Block
        sig_data = [
            ["_______________________________", "_______________________________"],
            ["Transport In-Charge / Supervisor", "Principal / Head of Institution"]
        ]
        sig_table = Table(sig_data, colWidths=[380, 380])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#475569')),
        ]))
        story.append(sig_table)

        doc.build(story)
        return output_path
