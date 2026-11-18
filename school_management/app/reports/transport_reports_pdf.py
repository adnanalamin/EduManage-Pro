"""
EduManage Pro - Transport Fleet & Operations PDF Report Generator
Generates printable A4 reports for Maintenance & Fuel Logs, Transport Fee Collection,
and Vehicle Insurance/Document Compliance Reminders.
"""

from datetime import date
import os
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

from app.models.transport import (
    Vehicle,
    TransportFuelLog,
    TransportMaintenanceLog,
    TransportFeeCharge,
    TransportInsurance,
    TransportDocument,
)
from app.models.school import SchoolSetting


class TransportReportsPDFGenerator:
    """Printable PDF generator for fleet fuel, maintenance, compliance, and transport fees."""

    @staticmethod
    def _build_header(story: list, title: str, subtitle: str, school: Optional[SchoolSetting]):
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle(
            "TrnH1",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=1,
            textColor=colors.HexColor("#0F172A"),
        )
        h2 = ParagraphStyle(
            "TrnH2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#B45309"),
        )
        sub = ParagraphStyle(
            "TrnSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            alignment=1,
            textColor=colors.HexColor("#64748B"),
        )
        school_name = school.school_name if school else "EduManage Pro School & College"
        story.append(Paragraph(school_name.upper(), h1))
        story.append(Paragraph(title, h2))
        story.append(Paragraph(f"{subtitle} • Generated: {date.today().strftime('%B %d, %Y')}", sub))
        story.append(Spacer(1, 12))

    @classmethod
    def generate_maintenance_fuel_report(
        cls,
        vehicles: List[Vehicle],
        fuel_logs: List[TransportFuelLog],
        maintenance_logs: List[TransportMaintenanceLog],
        reminders: List[Dict[str, Any]],
        school: Optional[SchoolSetting] = None,
        output_path: str = "fleet_maintenance_fuel_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=30,
            rightMargin=30,
            topMargin=28,
            bottomMargin=28,
        )
        styles = getSampleStyleSheet()
        sec_style = ParagraphStyle(
            "SecTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#1E293B"),
        )
        story = []
        cls._build_header(
            story,
            "FLEET FUEL, MAINTENANCE & REMINDER AUDIT REPORT",
            f"Vehicles: {len(vehicles)} | Fuel Refills: {len(fuel_logs)} | Service Logs: {len(maintenance_logs)} | Active Alerts: {len(reminders)}",
            school,
        )

        # Summary KPI box
        total_fuel = sum(float(f.total_cost or 0.0) for f in fuel_logs)
        total_liters = sum(float(f.liters or 0.0) for f in fuel_logs)
        total_maint = sum(float(m.cost or 0.0) for m in maintenance_logs)
        overdue_cnt = sum(1 for r in reminders if r.get("severity") == "Overdue")
        kpi_tbl = Table(
            [[
                f"Total Fleet Vehicles: {len(vehicles)}",
                f"Total Fuel Used: {total_liters:.1f} L (${total_fuel:.2f})",
                f"Maintenance Spend: ${total_maint:.2f}",
                f"Overdue Reminders: {overdue_cnt} / {len(reminders)}",
            ]],
            colWidths=[185, 200, 185, 190],
        )
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F59E0B")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        # Section 1: Active Maintenance & Compliance Reminders
        story.append(Paragraph("1. Active Maintenance & Compliance Reminders", sec_style))
        story.append(Spacer(1, 4))
        rem_rows = [["Severity", "Vehicle", "Category", "Reminder", "Due Date", "Details"]]
        for r in reminders[:25]:
            rem_rows.append([
                r.get("severity", "-"),
                r.get("vehicle_number", "-"),
                r.get("category", "-"),
                r.get("title", "-")[:32],
                r.get("due_date", "-"),
                r.get("details", "-")[:45],
            ])
        if len(rem_rows) == 1:
            rem_rows.append(["OK", "-", "-", "No overdue or upcoming reminders", "-", "Fleet compliant"])
        rem_tbl = Table(rem_rows, colWidths=[65, 125, 110, 175, 75, 210], repeatRows=1)
        rem_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FEF2F2")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(rem_tbl)
        story.append(Spacer(1, 12))

        # Section 2: Fuel Logs
        story.append(Paragraph("2. Recent Fuel Refills & Mileage Efficiency", sec_style))
        story.append(Spacer(1, 4))
        f_rows = [["Date", "Vehicle", "Fuel", "Liters", "Total Cost", "Odometer", "Distance", "km/L", "Station"]]
        for fl in fuel_logs[:25]:
            f_rows.append([
                fl.fill_date,
                fl.vehicle.vehicle_number if fl.vehicle else "-",
                fl.fuel_type,
                f"{fl.liters:.1f}",
                f"${float(fl.total_cost or 0.0):.2f}",
                f"{fl.odometer_km:.0f} km",
                f"{fl.distance_covered_km:.0f} km",
                f"{fl.km_per_liter:.2f}",
                (fl.station_name or "-")[:22],
            ])
        if len(f_rows) == 1:
            f_rows.append(["-", "-", "-", "0", "$0.00", "-", "-", "-", "No fuel logs recorded"])
        f_tbl = Table(f_rows, colWidths=[70, 130, 55, 55, 75, 80, 75, 55, 165], repeatRows=1)
        f_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369A1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F9FF")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(f_tbl)
        story.append(Spacer(1, 12))

        # Section 3: Maintenance Logs
        story.append(Paragraph("3. Maintenance & Service History", sec_style))
        story.append(Spacer(1, 4))
        m_rows = [["Date", "Vehicle", "Service Type", "Workshop", "Cost", "Odometer", "Next Due", "Status"]]
        for ml in maintenance_logs[:25]:
            m_rows.append([
                ml.service_date,
                ml.vehicle.vehicle_number if ml.vehicle else "-",
                ml.service_type[:28],
                (ml.workshop_name or "-")[:25],
                f"${float(ml.cost or 0.0):.2f}",
                f"{ml.odometer_km:.0f} km",
                ml.next_service_date or "-",
                ml.status,
            ])
        if len(m_rows) == 1:
            m_rows.append(["-", "-", "No maintenance logs recorded", "-", "$0.00", "-", "-", "-"])
        m_tbl = Table(m_rows, colWidths=[70, 130, 145, 145, 70, 75, 70, 55], repeatRows=1)
        m_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#047857")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECFDF5")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(m_tbl)

        doc.build(story)
        return output_path

    @classmethod
    def generate_fee_collection_report(
        cls,
        charges: List[TransportFeeCharge],
        billing_month: Optional[str] = None,
        school: Optional[SchoolSetting] = None,
        output_path: str = "transport_fee_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=30,
            rightMargin=30,
            topMargin=28,
            bottomMargin=28,
        )
        story = []
        cls._build_header(
            story,
            "TRANSPORT FEE BILLING & COLLECTION REPORT",
            f"Period: {billing_month or 'All Billing Months'} | Total Records: {len(charges)}",
            school,
        )
        rows = [["Month", "Pass Code", "Commuter", "Route", "Amount", "Discount", "Paid", "Due", "Method", "Receipt", "Status"]]
        for c in charges:
            pax = c.passenger
            if pax and pax.student:
                name = pax.student.full_name
            elif pax and pax.teacher:
                name = pax.teacher.full_name
            elif pax and pax.staff:
                name = pax.staff.full_name
            else:
                name = "-"
            rows.append([
                c.billing_month,
                (pax.pass_code if pax else "-") or f"#{c.passenger_id}",
                name[:24],
                c.route.route_code if c.route else "-",
                f"${float(c.amount or 0.0):.2f}",
                f"${float(c.discount or 0.0):.2f}",
                f"${float(c.paid_amount or 0.0):.2f}",
                f"${c.balance_due:.2f}",
                c.payment_method or "-",
                (c.receipt_no or "-")[:18],
                c.status,
            ])
        if len(rows) == 1:
            rows.append(["-", "-", "No transport fee charges recorded", "-", "$0.00", "$0.00", "$0.00", "$0.00", "-", "-", "-"])

        tbl = Table(rows, colWidths=[50, 75, 130, 50, 60, 55, 60, 60, 65, 95, 60], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#047857")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path
