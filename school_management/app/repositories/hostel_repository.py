"""
EduManage Pro - Hostel & Dormitory Repository
Phase 12: Blocks, Rooms, Bed Allocations with Capacity Checks & Gate Passes
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.hostel import HostelBlock, HostelRoom, HostelAllocation, HostelGatePass
from app.models.student import Student


class HostelRepository:
    """Repository handling all database operations for Hostel & Boarding Management."""

    # -------------------------------------------------------------
    # 1. Hostel Blocks
    # -------------------------------------------------------------
    @staticmethod
    def get_all_blocks(session: Session) -> List[HostelBlock]:
        return session.query(HostelBlock).order_by(HostelBlock.block_name.asc()).all()

    @staticmethod
    def get_block_by_id(session: Session, block_id: int) -> Optional[HostelBlock]:
        return session.query(HostelBlock).filter(HostelBlock.id == block_id).first()

    @staticmethod
    def create_block(
        session: Session,
        block_name: str,
        gender_type: str = "Boys",
        warden_name: Optional[str] = None,
        warden_phone: Optional[str] = None,
        address: Optional[str] = None,
        total_floors: int = 3,
        status: str = "Active"
    ) -> HostelBlock:
        block = HostelBlock(
            block_name=block_name.strip(),
            gender_type=gender_type,
            warden_name=warden_name.strip() if warden_name else None,
            warden_phone=warden_phone.strip() if warden_phone else None,
            address=address.strip() if address else None,
            total_floors=total_floors,
            status=status
        )
        session.add(block)
        session.commit()
        session.refresh(block)
        return block

    @staticmethod
    def update_block(session: Session, block_id: int, **kwargs) -> Optional[HostelBlock]:
        block = session.query(HostelBlock).filter(HostelBlock.id == block_id).first()
        if not block:
            return None
        for key, value in kwargs.items():
            if hasattr(block, key):
                setattr(block, key, value)
        session.commit()
        session.refresh(block)
        return block

    @staticmethod
    def delete_block(session: Session, block_id: int) -> bool:
        block = session.query(HostelBlock).filter(HostelBlock.id == block_id).first()
        if not block:
            return False
        session.delete(block)
        session.commit()
        return True

    # -------------------------------------------------------------
    # 2. Hostel Rooms
    # -------------------------------------------------------------
    @staticmethod
    def get_all_rooms(session: Session, block_id: Optional[int] = None) -> List[HostelRoom]:
        query = session.query(HostelRoom).options(
            joinedload(HostelRoom.block),
            joinedload(HostelRoom.allocations)
        )
        if block_id:
            query = query.filter(HostelRoom.block_id == block_id)
        return query.order_by(HostelRoom.room_number.asc()).all()

    @staticmethod
    def get_room_by_id(session: Session, room_id: int) -> Optional[HostelRoom]:
        return session.query(HostelRoom).options(
            joinedload(HostelRoom.block),
            joinedload(HostelRoom.allocations)
        ).filter(HostelRoom.id == room_id).first()

    @staticmethod
    def create_room(
        session: Session,
        block_id: int,
        room_number: str,
        floor_number: int = 1,
        room_type: str = "Double",
        capacity: int = 2,
        monthly_fee: float = 3000.0,
        amenities: str = "Attached Bath, Study Table, Wi-Fi",
        status: str = "Available"
    ) -> HostelRoom:
        room = HostelRoom(
            block_id=block_id,
            room_number=room_number.strip(),
            floor_number=floor_number,
            room_type=room_type,
            capacity=capacity,
            monthly_fee=monthly_fee,
            amenities=amenities.strip() if amenities else "Standard",
            status=status
        )
        session.add(room)
        session.commit()
        session.refresh(room)
        return room

    @staticmethod
    def update_room(session: Session, room_id: int, **kwargs) -> Optional[HostelRoom]:
        room = session.query(HostelRoom).filter(HostelRoom.id == room_id).first()
        if not room:
            return None
        for key, value in kwargs.items():
            if hasattr(room, key):
                setattr(room, key, value)
        session.commit()
        session.refresh(room)
        return room

    @staticmethod
    def delete_room(session: Session, room_id: int) -> bool:
        room = session.query(HostelRoom).filter(HostelRoom.id == room_id).first()
        if not room:
            return False
        session.delete(room)
        session.commit()
        return True

    # -------------------------------------------------------------
    # 3. Bed Allocations with Business Rule Validation
    # -------------------------------------------------------------
    @staticmethod
    def get_active_allocations(session: Session, room_id: Optional[int] = None) -> List[HostelAllocation]:
        query = session.query(HostelAllocation).options(
            joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
            joinedload(HostelAllocation.student)
        ).filter(HostelAllocation.status == "Active")
        if room_id:
            query = query.filter(HostelAllocation.room_id == room_id)
        return query.order_by(HostelAllocation.admission_date.desc()).all()

    @staticmethod
    def get_all_allocations(session: Session) -> List[HostelAllocation]:
        return session.query(HostelAllocation).options(
            joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
            joinedload(HostelAllocation.student)
        ).order_by(HostelAllocation.id.desc()).all()

    @staticmethod
    def allocate_student_to_room(
        session: Session,
        room_id: int,
        student_id: int,
        bed_number: str,
        admission_date: Optional[date] = None,
        guardian_contact: Optional[str] = None,
        emergency_phone: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> HostelAllocation:
        """
        Allocates a student to a hostel bed enforcing:
        1. Room capacity cap
        2. Single active hostel allocation per student
        3. Gender match between student and hostel block
        """
        room = session.query(HostelRoom).options(joinedload(HostelRoom.block)).filter(HostelRoom.id == room_id).first()
        if not room:
            raise ValueError(f"Hostel room with ID {room_id} not found.")

        # 1. Capacity check
        active_in_room = session.query(HostelAllocation).filter(
            HostelAllocation.room_id == room_id,
            HostelAllocation.status == "Active"
        ).count()
        if active_in_room >= room.capacity:
            raise ValueError(f"Room {room.room_number} is full! Capacity: {room.capacity}, Occupied: {active_in_room}.")

        # 2. Check for duplicate active allocation
        existing = session.query(HostelAllocation).filter(
            HostelAllocation.student_id == student_id,
            HostelAllocation.status == "Active"
        ).first()
        if existing:
            raise ValueError(f"Student ID {student_id} already has an active bed in Room {existing.room.room_number}.")

        # 3. Check gender if student info is present
        student = session.query(Student).filter(Student.id == student_id).first()
        if student and student.gender and room.block and room.block.gender_type in ["Boys", "Girls"]:
            student_gender = student.gender.strip().capitalize()
            block_gender = room.block.gender_type.strip().capitalize()
            # Normalize e.g. "Male" vs "Boys", "Female" vs "Girls"
            if block_gender == "Boys" and student_gender in ["Female", "Girl", "Girls"]:
                raise ValueError("Gender mismatch: Female student cannot be assigned to Boys Hostel Block.")
            elif block_gender == "Girls" and student_gender in ["Male", "Boy", "Boys"]:
                raise ValueError("Gender mismatch: Male student cannot be assigned to Girls Hostel Block.")

        alloc = HostelAllocation(
            room_id=room_id,
            student_id=student_id,
            bed_number=bed_number.strip(),
            admission_date=admission_date or date.today(),
            guardian_contact=guardian_contact.strip() if guardian_contact else (student.emergency_contact if student else None),
            emergency_phone=emergency_phone.strip() if emergency_phone else (student.emergency_contact if student else None),
            remarks=remarks.strip() if remarks else None,
            status="Active"
        )
        session.add(alloc)

        # Update room status if full
        if active_in_room + 1 >= room.capacity:
            room.status = "Full"

        session.commit()
        session.refresh(alloc)
        return alloc

    @staticmethod
    def vacate_student(
        session: Session,
        allocation_id: int,
        vacate_date: Optional[date] = None,
        remarks: Optional[str] = None
    ) -> Optional[HostelAllocation]:
        alloc = session.query(HostelAllocation).filter(HostelAllocation.id == allocation_id).first()
        if not alloc:
            return None
        alloc.status = "Vacated"
        alloc.vacate_date = vacate_date or date.today()
        if remarks:
            alloc.remarks = f"{alloc.remarks or ''}\nVacate Notice: {remarks}".strip()

        # Update room status back to Available
        room = session.query(HostelRoom).filter(HostelRoom.id == alloc.room_id).first()
        if room and room.status == "Full":
            room.status = "Available"

        session.commit()
        session.refresh(alloc)
        return alloc

    # -------------------------------------------------------------
    # 4. Gate Passes / Outpasses
    # -------------------------------------------------------------
    @staticmethod
    def get_all_gate_passes(session: Session) -> List[HostelGatePass]:
        return session.query(HostelGatePass).options(
            joinedload(HostelGatePass.allocation).joinedload(HostelAllocation.student),
            joinedload(HostelGatePass.allocation).joinedload(HostelAllocation.room).joinedload(HostelRoom.block)
        ).order_by(HostelGatePass.leave_date.desc(), HostelGatePass.id.desc()).all()

    @staticmethod
    def create_gate_pass(
        session: Session,
        allocation_id: int,
        purpose: str,
        expected_return_date: date,
        leave_date: Optional[date] = None,
        remarks: Optional[str] = None
    ) -> HostelGatePass:
        # Generate pass number: GP-YYYYMMDD-XXXX
        today_str = datetime.now().strftime("%Y%m%d")
        count = session.query(HostelGatePass).count() + 1
        pass_no = f"GP-{today_str}-{count:04d}"

        gp = HostelGatePass(
            pass_number=pass_no,
            allocation_id=allocation_id,
            purpose=purpose.strip(),
            leave_date=leave_date or date.today(),
            expected_return_date=expected_return_date,
            warden_approval="Approved",
            status="Out",
            remarks=remarks.strip() if remarks else None
        )
        session.add(gp)
        session.commit()
        session.refresh(gp)
        return gp

    @staticmethod
    def return_gate_pass(
        session: Session,
        gate_pass_id: int,
        actual_return_date: Optional[date] = None
    ) -> Optional[HostelGatePass]:
        gp = session.query(HostelGatePass).filter(HostelGatePass.id == gate_pass_id).first()
        if not gp:
            return None
        return_dt = actual_return_date or date.today()
        gp.actual_return_date = return_dt
        if return_dt > gp.expected_return_date:
            gp.status = "Overstayed"
        else:
            gp.status = "Returned"
        session.commit()
        session.refresh(gp)
        return gp

    # -------------------------------------------------------------
    # 5. Overall Hostel Stats
    # -------------------------------------------------------------
    @staticmethod
    def get_hostel_stats(session: Session) -> Dict[str, Any]:
        total_blocks = session.query(HostelBlock).count()
        total_rooms = session.query(HostelRoom).count()
        total_capacity = session.query(func.coalesce(func.sum(HostelRoom.capacity), 0)).scalar() or 0
        active_allocations = session.query(HostelAllocation).filter(HostelAllocation.status == "Active").count()
        available_beds = max(0, total_capacity - active_allocations)
        occupancy_rate = round((active_allocations / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        boarders_out = session.query(HostelGatePass).filter(
            HostelGatePass.status.in_(["Out", "Overstayed"])
        ).count()

        return {
            "total_blocks": total_blocks,
            "total_rooms": total_rooms,
            "total_capacity": total_capacity,
            "occupied_beds": active_allocations,
            "available_beds": available_beds,
            "occupancy_rate": occupancy_rate,
            "boarders_out": boarders_out,
            "present_in_hostel": max(0, active_allocations - boarders_out)
        }
