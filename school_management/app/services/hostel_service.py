"""
EduManage Pro - Hostel & Dormitory Service
Phase 12: Seeder, Business Validation & openpyxl Excel Export
"""

import os
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.models.hostel import HostelBlock, HostelRoom, HostelAllocation, HostelGatePass
from app.models.student import Student
from app.repositories.hostel_repository import HostelRepository


class HostelService:
    """Service layer managing business logic, sample data seeding, and spreadsheet generation."""

    @staticmethod
    def seed_default_hostel_data(session: Session) -> Dict[str, Any]:
        """Seeds standard hostel blocks, multi-tier rooms, and sample resident boarders."""
        blocks_seeded = 0
        rooms_seeded = 0
        allocations_seeded = 0

        # Check if already seeded
        if session.query(HostelBlock).count() > 0:
            return {
                "message": "Hostel data already seeded.",
                "blocks_seeded": session.query(HostelBlock).count(),
                "rooms_seeded": session.query(HostelRoom).count(),
                "allocations_seeded": session.query(HostelAllocation).count()
            }

        # 1. Blocks
        b_block_a = HostelRepository.create_block(
            session=session,
            block_name="Iqbal Hall (Boys Block A)",
            gender_type="Boys",
            warden_name="Md. Rafiqul Islam",
            warden_phone="+880 1711-234567",
            address="North Campus, Gate 3",
            total_floors=3,
            status="Active"
        )
        blocks_seeded += 1

        b_block_b = HostelRepository.create_block(
            session=session,
            block_name="Rokeya Hall (Girls Block B)",
            gender_type="Girls",
            warden_name="Dr. Farida Begum",
            warden_phone="+880 1722-345678",
            address="South Campus, Residential Area",
            total_floors=3,
            status="Active"
        )
        blocks_seeded += 1

        b_block_c = HostelRepository.create_block(
            session=session,
            block_name="Pioneer Hall (Junior Dormitory)",
            gender_type="Boys",
            warden_name="Kamal Hossain",
            warden_phone="+880 1733-456789",
            address="East Campus, Building 5",
            total_floors=2,
            status="Active"
        )
        blocks_seeded += 1

        # 2. Rooms in Iqbal Hall (Boys)
        r101 = HostelRepository.create_room(session, b_block_a.id, "A-101", 1, "Double", 2, 3500.0, "Attached Bath, Study Table, Balcony")
        r102 = HostelRepository.create_room(session, b_block_a.id, "A-102", 1, "Triple", 3, 3000.0, "Shared Bath, Study Desk, Ceiling Fan")
        r201 = HostelRepository.create_room(session, b_block_a.id, "A-201", 2, "Single", 1, 5500.0, "Attached Bath, Air Conditioning, Executive Desk")
        r202 = HostelRepository.create_room(session, b_block_a.id, "A-202", 2, "4-Bed Dorm", 4, 2500.0, "Bunk Beds, Common Bath, Wi-Fi")
        rooms_seeded += 4

        # Rooms in Rokeya Hall (Girls)
        r_g101 = HostelRepository.create_room(session, b_block_b.id, "B-101", 1, "Double", 2, 3500.0, "Attached Bath, Built-in Wardrobe, Study Lamps")
        r_g102 = HostelRepository.create_room(session, b_block_b.id, "B-102", 1, "Triple", 3, 3000.0, "Shared Bath, 3 Study Desks, High Security Intercom")
        r_g201 = HostelRepository.create_room(session, b_block_b.id, "B-201", 2, "Single", 1, 5500.0, "Attached Bath, AC, Individual Balcony")
        rooms_seeded += 3

        # Rooms in Junior Dorm
        r_j101 = HostelRepository.create_room(session, b_block_c.id, "J-101", 1, "4-Bed Dorm", 4, 2400.0, "Bunk Beds, Matron Supervision, Study Hall Access")
        rooms_seeded += 1

        # 3. Sample Allocations
        students = session.query(Student).order_by(Student.id.asc()).limit(8).all()
        if students:
            # Male student to A-101 Bed 1
            if len(students) >= 1:
                HostelRepository.allocate_student_to_room(
                    session=session,
                    room_id=r101.id,
                    student_id=students[0].id,
                    bed_number="Bed-1",
                    admission_date=date.today() - timedelta(days=60),
                    guardian_contact=students[0].emergency_contact or "+880 1819-000001",
                    emergency_phone=students[0].emergency_contact or "+880 1819-000001",
                    remarks="Prefers quiet evening study."
                )
                allocations_seeded += 1

            # Male student to A-101 Bed 2
            if len(students) >= 2:
                HostelRepository.allocate_student_to_room(
                    session=session,
                    room_id=r101.id,
                    student_id=students[1].id,
                    bed_number="Bed-2",
                    admission_date=date.today() - timedelta(days=45),
                    guardian_contact=students[1].emergency_contact or "+880 1819-000002",
                    emergency_phone=students[1].emergency_contact or "+880 1819-000002",
                    remarks="School football team captain."
                )
                allocations_seeded += 1

            # Female student to B-101 Bed 1 (if female, or students[2])
            if len(students) >= 3:
                try:
                    HostelRepository.allocate_student_to_room(
                        session=session,
                        room_id=r_g101.id,
                        student_id=students[2].id,
                        bed_number="Bed-A",
                        admission_date=date.today() - timedelta(days=30),
                        guardian_contact="+880 1819-000003",
                        emergency_phone="+880 1819-000003",
                        remarks="Science Olympiad team member."
                    )
                    allocations_seeded += 1
                except ValueError:
                    # If gender validation failed due to student gender, allocate to A-102
                    HostelRepository.allocate_student_to_room(
                        session=session,
                        room_id=r102.id,
                        student_id=students[2].id,
                        bed_number="Bed-1",
                        admission_date=date.today() - timedelta(days=30)
                    )
                    allocations_seeded += 1

        # 4. Sample Gate Pass
        first_alloc = session.query(HostelAllocation).first()
        if first_alloc:
            HostelRepository.create_gate_pass(
                session=session,
                allocation_id=first_alloc.id,
                purpose="Home Visit (Weekend Leave)",
                expected_return_date=date.today() + timedelta(days=2),
                leave_date=date.today(),
                remarks="Guardian approved via phone verification."
            )

        return {
            "message": "Hostel data seeded successfully.",
            "blocks_seeded": blocks_seeded,
            "rooms_seeded": rooms_seeded,
            "allocations_seeded": allocations_seeded
        }

    @staticmethod
    def export_hostel_allocations_excel(session: Session, file_path: str) -> str:
        """Exports full hostel occupancy and resident roster to an openpyxl Excel spreadsheet."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Hostel Boarders Manifest"

        # Styles
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        data_font = Font(name="Calibri", size=10)
        border_thin = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # Title Block
        ws.merge_cells("A1:H1")
        ws["A1"] = "EduManage Pro - Hostel & Dormitory Residents Manifest"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

        ws.merge_cells("A2:H2")
        ws["A2"] = f"Report Generated on: {date.today().strftime('%B %d, %Y')} | Official School Boarding Registry"
        ws["A2"].font = sub_font
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")

        ws.append([])  # Row 3 blank

        # Table Headers
        headers = [
            "SL",
            "Hostel Block",
            "Room No",
            "Room Type",
            "Bed No",
            "Student ID",
            "Student Name",
            "Admission Date",
            "Emergency Phone",
            "Status"
        ]
        ws.append(headers)
        row_num = 4
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        allocations = HostelRepository.get_all_allocations(session)
        for idx, a in enumerate(allocations, 1):
            row_num += 1
            block_name = a.room.block.block_name if a.room and a.room.block else "N/A"
            room_no = a.room.room_number if a.room else "N/A"
            room_type = a.room.room_type if a.room else "N/A"
            student_id_str = a.student.student_id if a.student else str(a.student_id)
            student_name = f"{a.student.first_name} {a.student.last_name}" if a.student else "Unknown Student"
            adm_date = a.admission_date.strftime("%Y-%m-%d") if a.admission_date else ""
            phone = a.emergency_phone or (a.student.emergency_contact if a.student else "") or "N/A"

            row_data = [
                idx,
                block_name,
                room_no,
                room_type,
                a.bed_number,
                student_id_str,
                student_name,
                adm_date,
                phone,
                a.status
            ]
            ws.append(row_data)

            # Apply cell styles
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.font = data_font
                cell.border = border_thin
                if col_idx in [1, 3, 5, 6, 8, 10]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val = str(cell.value or "")
                if len(val) > max_len and cell.row > 2:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        wb.save(file_path)
        return file_path
