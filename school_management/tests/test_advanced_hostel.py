"""
EduManage Pro - Advanced Hostel & Dormitory Management Unit Tests
Covers Buildings, Floors, Rooms, Beds, Double-Bed Allocation Prevention,
Check-In / Check-Out Clearance, Hostel Fees, Mess Plans/Menus/Logs,
Visitor Records, Complaints, Maintenance & Occupancy Locks, and Excel/PDF Reports.
"""

from datetime import date, timedelta
import os
import tempfile
import pytest

from app.models.hostel import (
    HOSTEL_ROOM_TYPES,
    COMPLAINT_CATEGORIES,
    MAINTENANCE_TYPES,
    HostelBlock,
    HostelFloor,
    HostelRoom,
    HostelBed,
    HostelMessPlan,
    HostelMessMenu,
    HostelMessLog,
    HostelAllocation,
    HostelFeeCharge,
    HostelVisitorLog,
    HostelComplaint,
    HostelMaintenanceRequest,
)
from app.models.student import Student
from app.models.school import SchoolSetting
from app.repositories.hostel_repository import HostelRepository
from app.services.hostel_service import HostelService
from app.reports.hostel_reports_pdf import HostelReportsPDFGenerator


def _make_student(db_session, code: str, first: str, last: str, gender: str = "Male") -> Student:
    s = Student(
        student_id=code,
        first_name=first,
        last_name=last,
        gender=gender,
        emergency_contact="+880 1700-112233",
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def test_buildings_floors_rooms_and_auto_beds(db_session):
    """Verify buildings auto-create floors and rooms auto-create bed inventory."""
    block = HostelRepository.create_block(
        db_session,
        block_code="HST-N1",
        block_name="North Residence Hall",
        gender_type="Boys",
        total_floors=3,
        warden_name="Kamrul Hasan",
    )
    assert block.id is not None
    floors = HostelRepository.get_floors(db_session, block_id=block.id)
    assert len(floors) == 3

    ground = HostelRepository.create_floor(
        db_session,
        block_id=block.id,
        floor_number=0,
        floor_name="Ground Floor",
        supervisor_name="Prefect Rahim",
        target_capacity=12,
    )
    assert ground.floor_number == 0

    room = HostelRepository.create_room(
        db_session,
        block_id=block.id,
        room_number="N-101",
        floor_number=1,
        room_type="Triple",
        capacity=3,
        monthly_fee=3200.0,
        has_attached_bath=True,
        has_ac=False,
    )
    assert room.floor_id is not None
    beds = HostelRepository.get_beds(db_session, room_id=room.id)
    assert len(beds) == 3
    assert [b.bed_number for b in beds] == ["Bed-1", "Bed-2", "Bed-3"]
    assert all(b.status == "Available" for b in beds)


def test_strict_double_bed_allocation_prevention(db_session):
    """Verify two different students CANNOT be assigned the same bed even when room has free capacity."""
    block = HostelRepository.create_block(db_session, "Double Bed Guard Block", "Boys", total_floors=2)
    room = HostelRepository.create_room(db_session, block.id, "DBG-201", floor_number=2, room_type="Double", capacity=2)

    s1 = _make_student(db_session, "HST-DBL-01", "Tariq", "Aziz", "Male")
    s2 = _make_student(db_session, "HST-DBL-02", "Nabil", "Islam", "Male")

    alloc1 = HostelRepository.allocate_student_to_room(db_session, room.id, s1.id, "Bed-1")
    assert alloc1.bed_id is not None
    bed1 = db_session.query(HostelBed).filter(HostelBed.id == alloc1.bed_id).first()
    assert bed1.status == "Occupied"

    # Attempt allocating s2 onto Bed-1 (or case-variant 'bed-1') when capacity still has 1 free slot
    with pytest.raises(ValueError, match="Double bed allocation is not allowed"):
        HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "bed-1")

    # Allocating s2 onto Bed-2 succeeds and marks room Full
    alloc2 = HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "Bed-2")
    assert alloc2.id is not None
    db_session.refresh(room)
    assert room.status == "Full"


def test_check_in_check_out_clearance_and_reallocation(db_session):
    """Verify check-in logging, check-out clearance freeing the bed, and clean reuse by a new boarder."""
    block = HostelRepository.create_block(db_session, "Clearance Block", "Girls", total_floors=2)
    room = HostelRepository.create_room(db_session, block.id, "CLR-101", floor_number=1, room_type="Single", capacity=1)

    s1 = _make_student(db_session, "HST-CLR-01", "Samira", "Karim", "Female")
    s2 = _make_student(db_session, "HST-CLR-02", "Nusrat", "Jahan", "Female")

    alloc1 = HostelRepository.allocate_student_to_room(
        db_session,
        room_id=room.id,
        student_id=s1.id,
        bed_number="Bed-1",
        check_in_time="09:30 AM",
        check_in_notes="Key #101A handed over",
    )
    assert alloc1.check_in_date == date.today()

    updated_cin = HostelRepository.check_in_boarder(
        db_session, alloc1.id, check_in_time="10:00 AM", notes="Verified luggage"
    )
    assert updated_cin.check_in_notes == "Verified luggage"

    checked_out = HostelRepository.check_out_boarder(
        db_session,
        allocation_id=alloc1.id,
        check_out_date=date.today(),
        check_out_time="04:15 PM",
        clearance_status="Damage Charge",
        damage_charges=350.0,
        notes="Broken study lamp shade",
    )
    assert checked_out.status == "Vacated"
    assert checked_out.clearance_status == "Damage Charge"
    assert float(checked_out.damage_charges) == 350.0

    db_session.refresh(room)
    assert room.status == "Available"
    bed1 = db_session.query(HostelBed).filter(HostelBed.id == alloc1.bed_id).first()
    assert bed1.status == "Available"

    # Now s2 can cleanly occupy Bed-1
    alloc2 = HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "Bed-1")
    assert alloc2.status == "Active"


def test_hostel_fees_mess_and_billing_cycle(db_session):
    """Verify mess plan, menu, logs, monthly fee generation, partial/full payments, and waivers."""
    block = HostelRepository.create_block(db_session, "Mess Fee Hall", "Co-ed", total_floors=2)
    room = HostelRepository.create_room(db_session, block.id, "MF-101", capacity=2, monthly_fee=3500.0)
    plan = HostelRepository.create_mess_plan(db_session, "Standard 4-Meal Plan", monthly_fee=2800.0)

    menu_item = HostelRepository.add_mess_menu_item(
        db_session,
        day_of_week="Monday",
        meal_type="Lunch",
        menu_items="Steamed Rice, Chicken Curry, Dal, Salad",
        serving_time="01:00 PM - 02:15 PM",
        block_id=block.id,
    )
    assert menu_item.id is not None

    mess_log = HostelRepository.add_mess_log(
        db_session, meal_type="Lunch", plates_served=85, meal_cost=6800.0, block_id=block.id
    )
    assert mess_log.plates_served == 85

    s1 = _make_student(db_session, "HST-FEE-01", "Rashed", "Uddin", "Male")
    s2 = _make_student(db_session, "HST-FEE-02", "Farhan", "Sadiq", "Male")

    a1 = HostelRepository.allocate_student_to_room(db_session, room.id, s1.id, "Bed-1", mess_plan_id=plan.id, mess_opted=True)
    a2 = HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "Bed-2", mess_opted=False)

    res = HostelRepository.generate_monthly_fees(db_session, billing_month="2026-05", default_mess_fee=2500.0)
    assert res["created"] == 2

    # Idempotent regeneration skips existing month bills
    res_dup = HostelRepository.generate_monthly_fees(db_session, billing_month="2026-05")
    assert res_dup["created"] == 0 and res_dup["skipped"] == 2

    c1 = HostelRepository.get_fee_charges(db_session, allocation_id=a1.id)[0]
    c2 = HostelRepository.get_fee_charges(db_session, allocation_id=a2.id)[0]
    assert c1.total_billed == 6300.0  # 3500 + 2800
    assert c2.total_billed == 3500.0  # mess_opted=False

    # Partial payment with 300 discount
    c1, err = HostelRepository.record_fee_payment(db_session, c1.id, amount=3000.0, discount=300.0, payment_method="Bank Transfer")
    assert err is None
    assert c1.status == "Partial"
    assert c1.balance_due == 3000.0
    assert c1.receipt_no.startswith("HST-RCP-")

    # Remaining payment
    c1, err = HostelRepository.record_fee_payment(db_session, c1.id, amount=3000.0, payment_method="Cash")
    assert err is None
    assert c1.status == "Paid"
    assert c1.balance_due == 0.0

    # Waive second student's charge
    c2_waived = HostelRepository.waive_fee_charge(db_session, c2.id, remarks="Merit scholarship boarder")
    assert c2_waived.status == "Waived"
    assert c2_waived.balance_due == 0.0


def test_visitors_complaints_maintenance_and_occupancy_lock(db_session):
    """Verify visitor check-in/out, complaint escalation, and maintenance bed-block lifecycle."""
    block = HostelRepository.create_block(db_session, "Ops Maintenance Hall", "Boys", total_floors=2)
    room = HostelRepository.create_room(db_session, block.id, "OPS-101", capacity=2)
    s1 = _make_student(db_session, "HST-OPS-01", "Imran", "Kabir", "Male")
    s2 = _make_student(db_session, "HST-OPS-02", "Mahmud", "Hasan", "Male")

    alloc = HostelRepository.allocate_student_to_room(db_session, room.id, s1.id, "Bed-1")

    # Visitor lifecycle
    vis = HostelRepository.check_in_visitor(
        db_session,
        visitor_name="Abdul Kabir",
        visitor_phone="+880 1711-998877",
        purpose="Deliver winter clothing",
        allocation_id=alloc.id,
        relationship_to_student="Father",
        id_proof_type="NID",
        id_proof_no="1975123456",
    )
    assert vis.status == "Checked In"
    assert vis.student_id == s1.id
    vis_out = HostelRepository.check_out_visitor(db_session, vis.id)
    assert vis_out.status == "Checked Out"
    assert vis_out.check_out_time is not None

    # Complaint & Maintenance with Bed Occupancy Lock on Bed-2
    bed2 = db_session.query(HostelBed).filter(HostelBed.room_id == room.id, HostelBed.bed_number == "Bed-2").first()
    comp = HostelRepository.create_complaint(
        db_session,
        title="Broken bed frame bolt",
        description="Upper rail bolt loose on Bed-2",
        category="Furniture",
        priority="High",
        allocation_id=alloc.id,
    )
    assert comp.complaint_no.startswith("CMP-")

    maint = HostelRepository.create_maintenance_request(
        db_session,
        block_id=block.id,
        room_id=room.id,
        bed_id=bed2.id,
        complaint_id=comp.id,
        issue_title="Weld and reinforce Bed-2 frame",
        maintenance_type="Carpentry",
        priority="High",
        vendor_or_technician="Campus Workshop",
        estimated_cost=600.0,
        blocks_occupancy=True,
    )
    assert maint.ticket_no.startswith("HMNT-")
    db_session.refresh(bed2)
    assert bed2.status == "Maintenance"

    # Bed-2 must reject allocation while under Maintenance
    with pytest.raises(ValueError, match="maintenance"):
        HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "Bed-2")

    # Complete maintenance -> frees Bed-2 & resolves linked complaint
    completed = HostelRepository.update_maintenance_request(
        db_session, maint.id, status="Completed", actual_cost=550.0, notes="Frame welded and tested"
    )
    assert completed.status == "Completed"
    db_session.refresh(bed2)
    db_session.refresh(comp)
    assert bed2.status == "Available"
    assert comp.status == "Resolved"

    # Now Bed-2 accepts s2
    alloc2 = HostelRepository.allocate_student_to_room(db_session, room.id, s2.id, "Bed-2")
    assert alloc2.id is not None


def test_hostel_comprehensive_reports_and_stats(db_session):
    """Verify multi-sheet Excel workbook and Occupancy/Fee/Operations PDF reports."""
    HostelService.seed_default_hostel_data(db_session)
    HostelRepository.generate_monthly_fees(db_session, billing_month="2026-06")

    stats = HostelRepository.get_hostel_stats(db_session)
    assert stats["total_blocks"] >= 3
    assert stats["total_rooms"] >= 5
    assert stats["total_capacity"] > 0

    school = db_session.query(SchoolSetting).first()
    with tempfile.TemporaryDirectory() as tmpdir:
        xlsx_path = os.path.join(tmpdir, "hostel_full.xlsx")
        HostelService.export_hostel_comprehensive_excel(db_session, xlsx_path)
        assert os.path.exists(xlsx_path) and os.path.getsize(xlsx_path) > 2000

        occ_pdf = os.path.join(tmpdir, "occupancy.pdf")
        HostelReportsPDFGenerator.generate_occupancy_report(
            HostelRepository.get_all_blocks(db_session),
            HostelRepository.get_all_rooms(db_session),
            HostelRepository.get_all_allocations(db_session),
            school=school,
            output_path=occ_pdf,
        )
        assert os.path.exists(occ_pdf) and os.path.getsize(occ_pdf) > 1000

        fee_pdf = os.path.join(tmpdir, "fees.pdf")
        HostelReportsPDFGenerator.generate_fee_report(
            HostelRepository.get_fee_charges(db_session),
            billing_month="2026-06",
            school=school,
            output_path=fee_pdf,
        )
        assert os.path.exists(fee_pdf) and os.path.getsize(fee_pdf) > 1000

        ops_pdf = os.path.join(tmpdir, "operations.pdf")
        HostelReportsPDFGenerator.generate_operations_report(
            HostelRepository.get_visitors(db_session),
            HostelRepository.get_complaints(db_session),
            HostelRepository.get_maintenance_requests(db_session),
            school=school,
            output_path=ops_pdf,
        )
        assert os.path.exists(ops_pdf) and os.path.getsize(ops_pdf) > 1000
