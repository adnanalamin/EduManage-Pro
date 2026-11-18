"""
EduManage Pro - Hostel & Dormitory Service
Seeding, Business Validation & openpyxl Multi-Sheet Hostel Reports Export
"""

import os
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.hostel import (
    HostelBlock,
    HostelRoom,
    HostelAllocation,
)
from app.models.student import Student
from app.repositories.hostel_repository import HostelRepository


class HostelService:
    """Service layer managing hostel seeding, validation, and Excel exports."""

    @staticmethod
    def seed_default_hostel_data(session: Session) -> Dict[str, Any]:
        """Seeds standard hostel blocks, floors, rooms, beds, mess plan, and sample boarders (used by tests/CLI)."""
        blocks_seeded = 0
        rooms_seeded = 0
        allocations_seeded = 0

        if session.query(HostelBlock).count() > 0:
            return {
                "message": "Hostel data already seeded.",
                "blocks_seeded": session.query(HostelBlock).count(),
                "rooms_seeded": session.query(HostelRoom).count(),
                "allocations_seeded": session.query(HostelAllocation).count(),
            }

        b_block_a = HostelRepository.create_block(
            session=session,
            block_code="HST-B1",
            block_name="Iqbal Hall (Boys Block A)",
            gender_type="Boys",
            warden_name="Md. Rafiqul Islam",
            warden_phone="+880 1711-234567",
            address="North Campus, Gate 3",
            total_floors=3,
            status="Active",
        )
        blocks_seeded += 1

        b_block_b = HostelRepository.create_block(
            session=session,
            block_code="HST-G1",
            block_name="Rokeya Hall (Girls Block B)",
            gender_type="Girls",
            warden_name="Dr. Farida Begum",
            warden_phone="+880 1722-345678",
            address="South Campus, Residential Area",
            total_floors=3,
            status="Active",
        )
        blocks_seeded += 1

        b_block_c = HostelRepository.create_block(
            session=session,
            block_code="HST-J1",
            block_name="Pioneer Hall (Junior Dormitory)",
            gender_type="Boys",
            warden_name="Kamal Hossain",
            warden_phone="+880 1733-456789",
            address="East Campus, Building 5",
            total_floors=2,
            status="Active",
        )
        blocks_seeded += 1

        r101 = HostelRepository.create_room(session, b_block_a.id, "A-101", 1, "Double", 2, 3500.0, "Attached Bath, Study Table, Balcony")
        r102 = HostelRepository.create_room(session, b_block_a.id, "A-102", 1, "Triple", 3, 3000.0, "Shared Bath, Study Desk, Ceiling Fan")
        HostelRepository.create_room(session, b_block_a.id, "A-201", 2, "Single", 1, 5500.0, "Attached Bath, Air Conditioning, Executive Desk")
        HostelRepository.create_room(session, b_block_a.id, "A-202", 2, "4-Bed Dorm", 4, 2500.0, "Bunk Beds, Common Bath, Wi-Fi")
        rooms_seeded += 4

        r_g101 = HostelRepository.create_room(session, b_block_b.id, "B-101", 1, "Double", 2, 3500.0, "Attached Bath, Built-in Wardrobe, Study Lamps")
        HostelRepository.create_room(session, b_block_b.id, "B-102", 1, "Triple", 3, 3000.0, "Shared Bath, 3 Study Desks, High Security Intercom")
        HostelRepository.create_room(session, b_block_b.id, "B-201", 2, "Single", 1, 5500.0, "Attached Bath, AC, Individual Balcony")
        rooms_seeded += 3

        HostelRepository.create_room(session, b_block_c.id, "J-101", 1, "4-Bed Dorm", 4, 2400.0, "Bunk Beds, Matron Supervision, Study Hall Access")
        rooms_seeded += 1

        mess_plan = HostelRepository.create_mess_plan(
            session=session,
            plan_name="Full Board Dining (3 Meals + Snacks)",
            monthly_fee=2500.0,
            description="Daily breakfast, lunch, evening snacks, and dinner.",
        )

        students = session.query(Student).order_by(Student.id.asc()).limit(8).all()
        if students:
            if len(students) >= 1:
                HostelRepository.allocate_student_to_room(
                    session=session,
                    room_id=r101.id,
                    student_id=students[0].id,
                    bed_number="Bed-1",
                    admission_date=date.today() - timedelta(days=60),
                    mess_plan_id=mess_plan.id,
                    guardian_contact=students[0].emergency_contact or "+880 1819-000001",
                    emergency_phone=students[0].emergency_contact or "+880 1819-000001",
                    remarks="Prefers quiet evening study.",
                )
                allocations_seeded += 1

            if len(students) >= 2:
                HostelRepository.allocate_student_to_room(
                    session=session,
                    room_id=r101.id,
                    student_id=students[1].id,
                    bed_number="Bed-2",
                    admission_date=date.today() - timedelta(days=45),
                    mess_plan_id=mess_plan.id,
                    guardian_contact=students[1].emergency_contact or "+880 1819-000002",
                    emergency_phone=students[1].emergency_contact or "+880 1819-000002",
                    remarks="School football team captain.",
                )
                allocations_seeded += 1

            if len(students) >= 3:
                try:
                    HostelRepository.allocate_student_to_room(
                        session=session,
                        room_id=r_g101.id,
                        student_id=students[2].id,
                        bed_number="Bed-1",
                        admission_date=date.today() - timedelta(days=30),
                        mess_plan_id=mess_plan.id,
                        guardian_contact="+880 1819-000003",
                        emergency_phone="+880 1819-000003",
                        remarks="Science Olympiad team member.",
                    )
                    allocations_seeded += 1
                except ValueError:
                    HostelRepository.allocate_student_to_room(
                        session=session,
                        room_id=r102.id,
                        student_id=students[2].id,
                        bed_number="Bed-1",
                        admission_date=date.today() - timedelta(days=30),
                        mess_plan_id=mess_plan.id,
                    )
                    allocations_seeded += 1

        first_alloc = session.query(HostelAllocation).first()
        if first_alloc:
            HostelRepository.create_gate_pass(
                session=session,
                allocation_id=first_alloc.id,
                purpose="Home Visit (Weekend Leave)",
                expected_return_date=date.today() + timedelta(days=2),
                leave_date=date.today(),
                remarks="Guardian approved via phone verification.",
            )

        return {
            "message": "Hostel data seeded successfully.",
            "blocks_seeded": blocks_seeded,
            "rooms_seeded": rooms_seeded,
            "allocations_seeded": allocations_seeded,
        }

    @staticmethod
    def _style_headers(ws, headers: List[str], row_idx: int = 4, fill_hex: str = "1E3A8A") -> Border:
        header_fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border_thin = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        for col_idx, title in enumerate(headers, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=title)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_thin
        ws.row_dimensions[row_idx].height = 24
        return border_thin

    @staticmethod
    def _autofit(ws):
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 12), 45)

    @staticmethod
    def export_hostel_allocations_excel(session: Session, file_path: str) -> str:
        """Exports full hostel occupancy and resident roster to an openpyxl Excel spreadsheet."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Hostel Boarders Manifest"

        ws["A1"] = "EduManage Pro - Hostel & Dormitory Residents Manifest"
        ws["A1"].font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        ws["A2"] = f"Report Generated on: {date.today().strftime('%B %d, %Y')} | Official School Boarding Registry"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="475569")

        headers = [
            "SL", "Hostel Block", "Room No", "Room Type", "Bed No", "Student ID",
            "Student Name", "Admission Date", "Check-In", "Check-Out", "Emergency Phone", "Status",
        ]
        border_thin = HostelService._style_headers(ws, headers, row_idx=4, fill_hex="1E3A8A")
        data_font = Font(name="Calibri", size=10)

        allocations = HostelRepository.get_all_allocations(session)
        row_num = 4
        for idx, a in enumerate(allocations, 1):
            row_num += 1
            block_name = a.room.block.block_name if a.room and a.room.block else "N/A"
            room_no = a.room.room_number if a.room else "N/A"
            room_type = a.room.room_type if a.room else "N/A"
            student_id_str = a.student.student_id if a.student else str(a.student_id)
            student_name = f"{a.student.first_name} {a.student.last_name}" if a.student else "Unknown Student"
            adm_date = a.admission_date.strftime("%Y-%m-%d") if a.admission_date else ""
            cin_date = a.check_in_date.strftime("%Y-%m-%d") if a.check_in_date else adm_date
            cout_date = a.check_out_date.strftime("%Y-%m-%d") if a.check_out_date else "-"
            phone = a.emergency_phone or (a.student.emergency_contact if a.student else "") or "N/A"

            vals = [idx, block_name, room_no, room_type, a.bed_number, student_id_str, student_name, adm_date, cin_date, cout_date, phone, a.status]
            for c_idx, val in enumerate(vals, 1):
                cell = ws.cell(row=row_num, column=c_idx, value=val)
                cell.font = data_font
                cell.border = border_thin
                if c_idx in (1, 3, 5, 6, 8, 9, 10, 12):
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        HostelService._autofit(ws)
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path

    @staticmethod
    def export_hostel_comprehensive_excel(session: Session, file_path: str) -> str:
        """Exports complete multi-sheet hostel operations workbook."""
        blocks = HostelRepository.get_all_blocks(session)
        rooms = HostelRepository.get_all_rooms(session)
        beds = HostelRepository.get_beds(session)
        allocs = HostelRepository.get_all_allocations(session)
        fees = HostelRepository.get_fee_charges(session)
        menus = HostelRepository.get_mess_menus(session)
        visitors = HostelRepository.get_visitors(session)
        complaints = HostelRepository.get_complaints(session)
        maint = HostelRepository.get_maintenance_requests(session)

        wb = Workbook()

        # Sheet 1: Buildings & Rooms
        ws1 = wb.active
        ws1.title = "Buildings & Rooms"
        ws1["A1"] = "EDUMANAGE PRO - HOSTEL BUILDINGS, FLOORS & ROOMS"
        ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="065F46")
        b1 = HostelService._style_headers(ws1, ["Building", "Gender", "Warden", "Floor", "Room No", "Type", "Capacity", "Occupied", "Monthly Fee", "Status"], row_idx=3, fill_hex="065F46")
        r_idx = 4
        for r in rooms:
            occ = len([a for a in (r.allocations or []) if a.status == "Active"])
            vals = [
                r.block.block_name if r.block else "-",
                r.block.gender_type if r.block else "-",
                r.block.warden_name if r.block else "-",
                r.floor.floor_name if r.floor else f"Floor {r.floor_number}",
                r.room_number,
                r.room_type,
                r.capacity,
                occ,
                float(r.monthly_fee or 0.0),
                r.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                c = ws1.cell(row=r_idx, column=c_idx, value=val)
                c.border = b1
            r_idx += 1
        HostelService._autofit(ws1)

        # Sheet 2: Beds & Allocations
        ws2 = wb.create_sheet("Beds & Allocations")
        ws2["A1"] = "BED INVENTORY & CHECK-IN / CHECK-OUT ALLOCATIONS"
        ws2["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        b2 = HostelService._style_headers(ws2, ["Student", "Room", "Bed", "Check-In Date", "Check-Out Date", "Clearance", "Damage Fee", "Status"], row_idx=3, fill_hex="1E3A8A")
        for idx, a in enumerate(allocs, start=4):
            s_name = f"{a.student.first_name} {a.student.last_name}" if a.student else f"Student #{a.student_id}"
            vals = [
                s_name,
                a.room.room_number if a.room else "-",
                a.bed_number,
                str(a.check_in_date or a.admission_date or "-"),
                str(a.check_out_date or a.vacate_date or "-"),
                a.clearance_status,
                float(a.damage_charges or 0.0),
                a.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                ws2.cell(row=idx, column=c_idx, value=val).border = b2
        HostelService._autofit(ws2)

        # Sheet 3: Hostel Fees
        ws3 = wb.create_sheet("Hostel Fees")
        ws3["A1"] = "HOSTEL & MESS FEE BILLING LEDGER"
        ws3["A1"].font = Font(name="Calibri", size=14, bold=True, color="047857")
        b3 = HostelService._style_headers(ws3, ["Month", "Student", "Room", "Room Rent", "Mess Fee", "Other", "Discount", "Paid", "Due", "Receipt", "Status"], row_idx=3, fill_hex="047857")
        for idx, ch in enumerate(fees, start=4):
            s_name = f"{ch.student.first_name} {ch.student.last_name}" if ch.student else f"Student #{ch.student_id}"
            r_no = ch.allocation.room.room_number if ch.allocation and ch.allocation.room else "-"
            vals = [
                ch.billing_month, s_name, r_no, float(ch.room_rent or 0.0), float(ch.mess_fee or 0.0),
                float(ch.other_charges or 0.0), float(ch.discount or 0.0), float(ch.paid_amount or 0.0),
                ch.balance_due, ch.receipt_no or "-", ch.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                ws3.cell(row=idx, column=c_idx, value=val).border = b3
        HostelService._autofit(ws3)

        # Sheet 4: Mess Menu
        ws4 = wb.create_sheet("Mess Weekly Menu")
        ws4["A1"] = "HOSTEL MESS WEEKLY DINING MENU"
        b4 = HostelService._style_headers(ws4, ["Day", "Meal", "Menu Items", "Serving Time", "Block"], row_idx=3, fill_hex="B45309")
        for idx, m in enumerate(menus, start=4):
            vals = [m.day_of_week, m.meal_type, m.menu_items, m.serving_time or "-", m.block.block_name if m.block else "All Blocks"]
            for c_idx, val in enumerate(vals, 1):
                ws4.cell(row=idx, column=c_idx, value=val).border = b4
        HostelService._autofit(ws4)

        # Sheet 5: Visitors
        ws5 = wb.create_sheet("Visitors Log")
        ws5["A1"] = "HOSTEL VISITOR REGISTER"
        b5 = HostelService._style_headers(ws5, ["Date", "Visitor", "Phone", "Relation", "Student", "Purpose", "In", "Out", "Status"], row_idx=3, fill_hex="0369A1")
        for idx, v in enumerate(visitors, start=4):
            s_name = f"{v.student.first_name} {v.student.last_name}" if v.student else "-"
            vals = [str(v.visit_date), v.visitor_name, v.visitor_phone, v.relationship_to_student, s_name, v.purpose, v.check_in_time, v.check_out_time or "-", v.status]
            for c_idx, val in enumerate(vals, 1):
                ws5.cell(row=idx, column=c_idx, value=val).border = b5
        HostelService._autofit(ws5)

        # Sheet 6: Complaints & Maintenance
        ws6 = wb.create_sheet("Complaints & Maintenance")
        ws6["A1"] = "HOSTEL COMPLAINTS & MAINTENANCE WORK ORDERS"
        b6 = HostelService._style_headers(ws6, ["Kind", "Ticket/Ref", "Block / Room", "Title", "Category/Type", "Priority", "Technician/Assignee", "Cost", "Status"], row_idx=3, fill_hex="991B1B")
        row_c = 4
        for cmp_row in complaints:
            loc = f"{cmp_row.block.block_name if cmp_row.block else '-'} / {cmp_row.room.room_number if cmp_row.room else '-'}"
            vals = ["Complaint", cmp_row.complaint_no, loc, cmp_row.title, cmp_row.category, cmp_row.priority, cmp_row.assigned_to or "-", 0.0, cmp_row.status]
            for c_idx, val in enumerate(vals, 1):
                ws6.cell(row=row_c, column=c_idx, value=val).border = b6
            row_c += 1
        for m_row in maint:
            loc = f"{m_row.block.block_name if m_row.block else '-'} / {m_row.room.room_number if m_row.room else '-'}"
            vals = ["Maintenance", m_row.ticket_no, loc, m_row.issue_title, m_row.maintenance_type, m_row.priority, m_row.vendor_or_technician or "-", float(m_row.actual_cost or m_row.estimated_cost or 0.0), m_row.status]
            for c_idx, val in enumerate(vals, 1):
                ws6.cell(row=row_c, column=c_idx, value=val).border = b6
            row_c += 1
        HostelService._autofit(ws6)

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path
