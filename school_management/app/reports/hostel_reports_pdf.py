"""
EduManage Pro - Hostel Comprehensive PDF Report Generator
Generates printable A4 PDF reports for:
1. Hostel Building, Floor, Room & Bed Occupancy Inventory
2. Hostel & Mess Fee Collection Statement
3. Visitor, Complaints & Maintenance Audit Report
"""

from datetime import date
import os
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

from app.models.hostel import (
    HostelBlock,
    HostelRoom,
    HostelAllocation,
    HostelFeeCharge,
    HostelVisitorLog,
    HostelComplaint,
    HostelMaintenanceRequest,
)
from app.models.school import SchoolSetting


class HostelReportsPDFGenerator:
    """Generates formatted printable PDF reports for hostel operations."""

    @staticmethod
    def _add_header(story: list, title: str, subtitle: str, school: Optional[SchoolSetting]):
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("HstH1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, alignment=1, textColor=colors.HexColor("#0F172A"))
        h2 = ParagraphStyle("HstH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, alignment=1, textColor=colors.HexColor("#065F46"))
        sub = ParagraphStyle("HstSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, alignment=1, textColor=colors.HexColor("#64748B"))
        school_name = school.school_name if school and getattr(school, "school_name", None) else "EduManage Residential Academy"
        story.append(Paragraph(school_name.upper(), h1))
        story.append(Paragraph(title, h2))
        story.append(Paragraph(f"{subtitle} • Generated: {date.today().strftime('%B %d, %Y')}", sub))
        story.append(Spacer(1, 10))

    @classmethod
    def generate_occupancy_report(
        cls,
        blocks: List[HostelBlock],
        rooms: List[HostelRoom],
        allocations: List[HostelAllocation],
        school: Optional[SchoolSetting] = None,
        output_path: str = "hostel_occupancy_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        story = []
        total_cap = sum(int(r.capacity or 0) for r in rooms)
        active_allocs = [a for a in allocations if a.status == "Active"]
        cls._add_header(
            story,
            "HOSTEL BUILDINGS, FLOORS, ROOMS & BED OCCUPANCY REPORT",
            f"Buildings: {len(blocks)} | Rooms: {len(rooms)} | Active Boarders: {len(active_allocs)} / {total_cap} Beds",
            school,
        )

        rows = [["Building", "Gender", "Floor", "Room No", "Type", "Capacity", "Occupied", "Vacant", "Monthly Rent", "Status"]]
        for r in rooms:
            occ = len([a for a in (r.allocations or []) if a.status == "Active"])
            vac = max(0, int(r.capacity or 0) - occ)
            rows.append([
                (r.block.block_name if r.block else "-")[:28],
                r.block.gender_type if r.block else "-",
                r.floor.floor_name if r.floor else f"Floor {r.floor_number}",
                r.room_number,
                r.room_type,
                str(r.capacity),
                str(occ),
                str(vac),
                f"{float(r.monthly_fee or 0.0):.2f}",
                r.status,
            ])
        if len(rows) == 1:
            rows.append(["No rooms configured", "-", "-", "-", "-", "0", "0", "0", "0.00", "-"])

        tbl = Table(rows, colWidths=[150, 55, 70, 65, 75, 55, 55, 55, 75, 65], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ECFDF5")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        doc.build(story)
        return output_path

    @classmethod
    def generate_fee_report(
        cls,
        charges: List[HostelFeeCharge],
        billing_month: Optional[str] = None,
        school: Optional[SchoolSetting] = None,
        output_path: str = "hostel_fee_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        story = []
        cls._add_header(
            story,
            "HOSTEL & MESS FEE COLLECTION REPORT",
            f"Billing Month: {billing_month or 'All Months'} | Total Bills: {len(charges)}",
            school,
        )
        rows = [["Month", "Student", "Room / Bed", "Rent", "Mess", "Other", "Discount", "Paid", "Due", "Receipt", "Status"]]
        for ch in charges:
            s_name = f"{ch.student.first_name} {ch.student.last_name}" if ch.student else f"Student #{ch.student_id}"
            rb = f"{ch.allocation.room.room_number if ch.allocation and ch.allocation.room else '-'} / {ch.allocation.bed_number if ch.allocation else '-'}"
            rows.append([
                ch.billing_month,
                s_name[:24],
                rb[:16],
                f"{float(ch.room_rent or 0.0):.2f}",
                f"{float(ch.mess_fee or 0.0):.2f}",
                f"{float(ch.other_charges or 0.0):.2f}",
                f"{float(ch.discount or 0.0):.2f}",
                f"{float(ch.paid_amount or 0.0):.2f}",
                f"{ch.balance_due:.2f}",
                (ch.receipt_no or "-")[:18],
                ch.status,
            ])
        if len(rows) == 1:
            rows.append(["-", "No hostel fee records", "-", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "-", "-"])

        tbl = Table(rows, colWidths=[50, 130, 80, 55, 55, 50, 55, 55, 55, 100, 55], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
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

    @classmethod
    def generate_operations_report(
        cls,
        visitors: List[HostelVisitorLog],
        complaints: List[HostelComplaint],
        maintenance_requests: List[HostelMaintenanceRequest],
        school: Optional[SchoolSetting] = None,
        output_path: str = "hostel_operations_report.pdf",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), leftMargin=28, rightMargin=28, topMargin=26, bottomMargin=26)
        styles = getSampleStyleSheet()
        sec = ParagraphStyle("Sec", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#1E293B"))
        story = []
        cls._add_header(
            story,
            "HOSTEL VISITORS, COMPLAINTS & MAINTENANCE AUDIT REPORT",
            f"Visitors: {len(visitors)} | Complaints: {len(complaints)} | Maintenance Tickets: {len(maintenance_requests)}",
            school,
        )

        # Visitors
        story.append(Paragraph("1. Recent Visitor Records", sec))
        story.append(Spacer(1, 4))
        v_rows = [["Date", "Visitor Name", "Phone", "Relation", "Student", "Purpose", "Check-In", "Check-Out", "Status"]]
        for v in visitors[:20]:
            s_name = f"{v.student.first_name} {v.student.last_name}" if v.student else "-"
            v_rows.append([str(v.visit_date), v.visitor_name[:22], v.visitor_phone, v.relationship_to_student, s_name[:20], v.purpose[:28], v.check_in_time, v.check_out_time or "-", v.status])
        if len(v_rows) == 1:
            v_rows.append(["-", "No visitor records", "-", "-", "-", "-", "-", "-", "-"])
        vt = Table(v_rows, colWidths=[65, 110, 80, 60, 100, 145, 65, 65, 60], repeatRows=1)
        vt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369A1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(vt)
        story.append(Spacer(1, 10))

        # Complaints & Maintenance
        story.append(Paragraph("2. Complaints & Facility Maintenance Tickets", sec))
        story.append(Spacer(1, 4))
        m_rows = [["Kind", "Ref No", "Block / Room", "Issue Title", "Category", "Priority", "Technician / Assignee", "Cost", "Status"]]
        for c in complaints[:20]:
            loc = f"{c.block.block_name if c.block else '-'} / {c.room.room_number if c.room else '-'}"
            m_rows.append(["Complaint", c.complaint_no, loc[:24], c.title[:28], c.category, c.priority, (c.assigned_to or "-")[:18], "0.00", c.status])
        for m in maintenance_requests[:20]:
            loc = f"{m.block.block_name if m.block else '-'} / {m.room.room_number if m.room else '-'}"
            m_rows.append(["Maintenance", m.ticket_no, loc[:24], m.issue_title[:28], m.maintenance_type, m.priority, (m.vendor_or_technician or "-")[:18], f"{float(m.actual_cost or m.estimated_cost or 0.0):.2f}", m.status])
        if len(m_rows) == 1:
            m_rows.append(["-", "-", "-", "No complaints or maintenance tickets", "-", "-", "-", "0.00", "-"])
        mt = Table(m_rows, colWidths=[60, 95, 115, 140, 80, 55, 100, 55, 60], repeatRows=1)
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        story.append(mt)

        doc.build(story)
        return output_path
