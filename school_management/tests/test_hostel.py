"""
EduManage Pro - Hostel & Dormitory Unit Tests
Phase 12: Blocks, Rooms, Bed Allocations, Capacity Rules, Gate Passes & Reports
"""

import os
import tempfile
from datetime import date, timedelta
import pytest
from app.models.hostel import HostelBlock, HostelRoom, HostelAllocation, HostelGatePass
from app.models.student import Student
from app.repositories.hostel_repository import HostelRepository
from app.services.hostel_service import HostelService
from app.reports.hostel_id_card_pdf import HostelCardGenerator
from app.reports.hostel_roll_call_pdf import HostelRollCallPDFGenerator


def test_seed_hostel_blocks_and_rooms(db_session):
    """Verify default hostel halls, rooms, and sample resident allocations seed correctly."""
    res = HostelService.seed_default_hostel_data(db_session)
    assert res["blocks_seeded"] >= 3 or db_session.query(HostelBlock).count() >= 3
    assert db_session.query(HostelRoom).count() >= 5

    block_a = db_session.query(HostelBlock).filter(HostelBlock.block_name.like("%Iqbal%")).first()
    assert block_a is not None
    assert block_a.gender_type == "Boys"
    assert len(block_a.rooms) >= 3


def test_room_crud_and_capacity(db_session):
    """Verify room creation, capacity updates, and floor configuration."""
    b = HostelRepository.create_block(db_session, "Test Hall", "Boys")
    room = HostelRepository.create_room(
        session=db_session,
        block_id=b.id,
        room_number="T-101",
        floor_number=1,
        room_type="Single",
        capacity=1,
        monthly_fee=4000.0
    )
    assert room.id is not None
    assert room.capacity == 1

    updated = HostelRepository.update_room(db_session, room.id, capacity=2, room_type="Double")
    assert updated.capacity == 2
    assert updated.room_type == "Double"


def test_bed_allocation_capacity_overflow_error(db_session):
    """Verify allocating more students than room capacity raises ValueError."""
    b = HostelRepository.create_block(db_session, "Capacity Block", "Co-ed")
    room = HostelRepository.create_room(db_session, b.id, "CAP-1", capacity=1)

    s1 = db_session.query(Student).first()
    if not s1:
        s1 = Student(student_id="STU-H1", first_name="Ali", last_name="Khan", gender="Male")
        db_session.add(s1)
        db_session.commit()

    # Allocate bed 1 (fills capacity 1/1)
    alloc1 = HostelRepository.allocate_student_to_room(
        db_session,
        room_id=room.id,
        student_id=s1.id,
        bed_number="Bed-1"
    )
    assert alloc1.id is not None

    # Create second student
    s2 = Student(student_id="STU-H2", first_name="Bilal", last_name="Hassan", gender="Male")
    db_session.add(s2)
    db_session.commit()

    # Second allocation must fail due to room capacity cap
    with pytest.raises(ValueError, match="full"):
        HostelRepository.allocate_student_to_room(
            db_session,
            room_id=room.id,
            student_id=s2.id,
            bed_number="Bed-2"
        )


def test_duplicate_active_allocation_error(db_session):
    """Verify a student cannot have more than one active hostel bed allocation."""
    b = HostelRepository.create_block(db_session, "Multi Block", "Co-ed")
    r1 = HostelRepository.create_room(db_session, b.id, "M-101", capacity=3)
    r2 = HostelRepository.create_room(db_session, b.id, "M-102", capacity=3)

    s = Student(student_id="STU-DUP-1", first_name="Karim", last_name="Rahman", gender="Male")
    db_session.add(s)
    db_session.commit()

    HostelRepository.allocate_student_to_room(db_session, r1.id, s.id, "Bed-A")

    # Attempt to allocate same student to second room
    with pytest.raises(ValueError, match="already has an active bed"):
        HostelRepository.allocate_student_to_room(db_session, r2.id, s.id, "Bed-B")


def test_gender_mismatch_rejection(db_session):
    """Verify male student cannot be placed in Girls Hostel and vice versa."""
    girls_block = HostelRepository.create_block(db_session, "Pari Hall", "Girls")
    room = HostelRepository.create_room(db_session, girls_block.id, "P-101", capacity=2)

    male_student = Student(student_id="STU-BOY-1", first_name="Rahim", last_name="Miah", gender="Male")
    db_session.add(male_student)
    db_session.commit()

    with pytest.raises(ValueError, match="Gender mismatch"):
        HostelRepository.allocate_student_to_room(db_session, room.id, male_student.id, "Bed-1")


def test_gate_pass_lifecycle(db_session):
    """Verify gate pass creation, departure tracking, and return status calculation."""
    b = HostelRepository.create_block(db_session, "Pass Hall", "Co-ed")
    r = HostelRepository.create_room(db_session, b.id, "PASS-1", capacity=2)
    s = Student(student_id="STU-PASS-1", first_name="Faisal", last_name="Ahmed", gender="Male")
    db_session.add(s)
    db_session.commit()

    alloc = HostelRepository.allocate_student_to_room(db_session, r.id, s.id, "Bed-1")

    # Issue pass
    gp = HostelRepository.create_gate_pass(
        session=db_session,
        allocation_id=alloc.id,
        purpose="Medical Checkup",
        expected_return_date=date.today() + timedelta(days=1),
        leave_date=date.today()
    )
    assert gp.pass_number.startswith("GP-")
    assert gp.status == "Out"

    # Return on time
    returned_gp = HostelRepository.return_gate_pass(db_session, gp.id, actual_return_date=date.today())
    assert returned_gp.status == "Returned"


def test_openpyxl_export_and_reportlab_card(db_session):
    """Verify Excel manifest export and ReportLab CR80 PVC card generation."""
    HostelService.seed_default_hostel_data(db_session)
    alloc = HostelRepository.get_active_allocations(db_session)[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Excel
        xlsx_path = os.path.join(tmpdir, "hostel_manifest.xlsx")
        HostelService.export_hostel_allocations_excel(db_session, xlsx_path)
        assert os.path.exists(xlsx_path)
        assert os.path.getsize(xlsx_path) > 1000

        # 2. CR80 PVC Card PDF
        from app.models.school import SchoolSetting
        school = db_session.query(SchoolSetting).first()
        card_pdf = os.path.join(tmpdir, "resident_card.pdf")
        HostelCardGenerator.generate_single_card(alloc, school, card_pdf)
        assert os.path.exists(card_pdf)
        assert os.path.getsize(card_pdf) > 1000

        # 3. Night Roll Call PDF
        roll_pdf = os.path.join(tmpdir, "night_roll_call.pdf")
        HostelRollCallPDFGenerator.generate_manifest(alloc.room.block, [alloc], school, roll_pdf)
        assert os.path.exists(roll_pdf)
        assert os.path.getsize(roll_pdf) > 1000
