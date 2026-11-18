"""
EduManage Pro - Hostel & Dormitory Repository
Complete Buildings, Floors, Rooms, Beds, Double-Bed Allocation Prevention,
Check-In / Check-Out Clearance, Hostel Fees, Mess Management, Visitor Records,
Boarder Complaints, Maintenance Work Orders, and Gate Passes.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
import uuid
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.hostel import (
    HostelBlock,
    HostelFloor,
    HostelRoom,
    HostelBed,
    HostelMessPlan,
    HostelMessMenu,
    HostelMessLog,
    HostelAllocation,
    HostelFeeCharge,
    HostelGatePass,
    HostelVisitorLog,
    HostelComplaint,
    HostelMaintenanceRequest,
)
from app.models.student import Student


class HostelRepository:
    """Repository handling all database operations for Hostel & Boarding Management."""

    # -------------------------------------------------------------
    # 1. Hostel Buildings / Blocks & Floors
    # -------------------------------------------------------------
    @staticmethod
    def get_all_blocks(session: Session) -> List[HostelBlock]:
        return session.query(HostelBlock).options(
            joinedload(HostelBlock.floors),
            joinedload(HostelBlock.rooms),
        ).order_by(HostelBlock.block_name.asc()).all()

    @staticmethod
    def get_block_by_id(session: Session, block_id: int) -> Optional[HostelBlock]:
        return session.query(HostelBlock).options(
            joinedload(HostelBlock.floors),
            joinedload(HostelBlock.rooms),
        ).filter(HostelBlock.id == block_id).first()

    @staticmethod
    def create_block(
        session: Session,
        block_name: str,
        gender_type: str = "Boys",
        warden_name: Optional[str] = None,
        warden_phone: Optional[str] = None,
        address: Optional[str] = None,
        total_floors: int = 3,
        status: str = "Active",
        block_code: Optional[str] = None,
        warden_staff_id: Optional[int] = None,
        notes: Optional[str] = None,
        auto_create_floors: bool = True,
    ) -> HostelBlock:
        block = HostelBlock(
            block_code=block_code.strip() if block_code else None,
            block_name=block_name.strip(),
            gender_type=gender_type,
            warden_staff_id=warden_staff_id,
            warden_name=warden_name.strip() if warden_name else None,
            warden_phone=warden_phone.strip() if warden_phone else None,
            address=address.strip() if address else None,
            total_floors=total_floors,
            status=status,
            notes=notes,
        )
        session.add(block)
        session.flush()
        if auto_create_floors and total_floors > 0:
            for fl in range(1, total_floors + 1):
                session.add(
                    HostelFloor(
                        block_id=block.id,
                        floor_number=fl,
                        floor_name=f"Floor {fl}",
                        status="Active",
                    )
                )
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

    @staticmethod
    def get_floors(session: Session, block_id: Optional[int] = None) -> List[HostelFloor]:
        query = session.query(HostelFloor).options(
            joinedload(HostelFloor.block),
            joinedload(HostelFloor.rooms),
        )
        if block_id:
            query = query.filter(HostelFloor.block_id == block_id)
        return query.order_by(HostelFloor.block_id.asc(), HostelFloor.floor_number.asc()).all()

    @staticmethod
    def create_floor(
        session: Session,
        block_id: int,
        floor_number: int,
        floor_name: Optional[str] = None,
        supervisor_name: Optional[str] = None,
        supervisor_phone: Optional[str] = None,
        target_capacity: int = 0,
        status: str = "Active",
    ) -> HostelFloor:
        existing = session.query(HostelFloor).filter(
            HostelFloor.block_id == block_id,
            HostelFloor.floor_number == floor_number,
        ).first()
        if existing:
            return existing
        floor = HostelFloor(
            block_id=block_id,
            floor_number=floor_number,
            floor_name=floor_name.strip() if floor_name else (
                "Ground Floor" if floor_number == 0 else f"Floor {floor_number}"
            ),
            supervisor_name=supervisor_name,
            supervisor_phone=supervisor_phone,
            target_capacity=target_capacity,
            status=status,
        )
        session.add(floor)
        session.commit()
        session.refresh(floor)
        return floor

    # -------------------------------------------------------------
    # 2. Hostel Rooms & Beds
    # -------------------------------------------------------------
    @staticmethod
    def get_all_rooms(session: Session, block_id: Optional[int] = None, floor_id: Optional[int] = None) -> List[HostelRoom]:
        query = session.query(HostelRoom).options(
            joinedload(HostelRoom.block),
            joinedload(HostelRoom.floor),
            joinedload(HostelRoom.beds),
            joinedload(HostelRoom.allocations),
        )
        if block_id:
            query = query.filter(HostelRoom.block_id == block_id)
        if floor_id:
            query = query.filter(HostelRoom.floor_id == floor_id)
        return query.order_by(HostelRoom.room_number.asc()).all()

    @staticmethod
    def get_room_by_id(session: Session, room_id: int) -> Optional[HostelRoom]:
        return session.query(HostelRoom).options(
            joinedload(HostelRoom.block),
            joinedload(HostelRoom.floor),
            joinedload(HostelRoom.beds),
            joinedload(HostelRoom.allocations),
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
        status: str = "Available",
        floor_id: Optional[int] = None,
        has_attached_bath: bool = True,
        has_ac: bool = False,
        notes: Optional[str] = None,
        auto_create_beds: bool = True,
    ) -> HostelRoom:
        resolved_floor_id = floor_id
        if resolved_floor_id is None:
            fl = session.query(HostelFloor).filter(
                HostelFloor.block_id == block_id,
                HostelFloor.floor_number == floor_number,
            ).first()
            if not fl:
                fl = HostelFloor(
                    block_id=block_id,
                    floor_number=floor_number,
                    floor_name="Ground Floor" if floor_number == 0 else f"Floor {floor_number}",
                    status="Active",
                )
                session.add(fl)
                session.flush()
            resolved_floor_id = fl.id

        room = HostelRoom(
            block_id=block_id,
            floor_id=resolved_floor_id,
            room_number=room_number.strip(),
            floor_number=floor_number,
            room_type=room_type,
            capacity=capacity,
            monthly_fee=monthly_fee,
            amenities=amenities.strip() if amenities else "Standard",
            has_attached_bath=has_attached_bath,
            has_ac=has_ac,
            status=status,
            notes=notes,
        )
        session.add(room)
        session.flush()

        if auto_create_beds and capacity > 0:
            for b_idx in range(1, capacity + 1):
                session.add(
                    HostelBed(
                        room_id=room.id,
                        bed_number=f"Bed-{b_idx}",
                        bed_type="Single",
                        status="Available",
                    )
                )

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

    @staticmethod
    def get_beds(
        session: Session,
        room_id: Optional[int] = None,
        block_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[HostelBed]:
        query = session.query(HostelBed).options(
            joinedload(HostelBed.room).joinedload(HostelRoom.block),
        )
        if room_id:
            query = query.filter(HostelBed.room_id == room_id)
        if block_id:
            query = query.join(HostelRoom).filter(HostelRoom.block_id == block_id)
        if status:
            query = query.filter(HostelBed.status == status)
        return query.order_by(HostelBed.room_id.asc(), HostelBed.bed_number.asc()).all()

    @staticmethod
    def create_bed(
        session: Session,
        room_id: int,
        bed_number: str,
        bed_type: str = "Single",
        status: str = "Available",
        notes: Optional[str] = None,
    ) -> HostelBed:
        bed = HostelBed(
            room_id=room_id,
            bed_number=bed_number.strip(),
            bed_type=bed_type,
            status=status,
            notes=notes,
        )
        session.add(bed)
        session.commit()
        session.refresh(bed)
        return bed

    @staticmethod
    def update_bed(session: Session, bed_id: int, **kwargs) -> Optional[HostelBed]:
        bed = session.query(HostelBed).filter(HostelBed.id == bed_id).first()
        if not bed:
            return None
        for key, value in kwargs.items():
            if hasattr(bed, key):
                setattr(bed, key, value)
        session.commit()
        session.refresh(bed)
        return bed

    # -------------------------------------------------------------
    # 3. Bed Allocations, Double-Bed Prevention, Check-In & Check-Out
    # -------------------------------------------------------------
    @staticmethod
    def get_active_allocations(session: Session, room_id: Optional[int] = None) -> List[HostelAllocation]:
        query = session.query(HostelAllocation).options(
            joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
            joinedload(HostelAllocation.bed),
            joinedload(HostelAllocation.student),
            joinedload(HostelAllocation.mess_plan),
        ).filter(HostelAllocation.status == "Active")
        if room_id:
            query = query.filter(HostelAllocation.room_id == room_id)
        return query.order_by(HostelAllocation.admission_date.desc()).all()

    @staticmethod
    def get_all_allocations(session: Session) -> List[HostelAllocation]:
        return session.query(HostelAllocation).options(
            joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
            joinedload(HostelAllocation.bed),
            joinedload(HostelAllocation.student),
            joinedload(HostelAllocation.mess_plan),
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
        remarks: Optional[str] = None,
        mess_plan_id: Optional[int] = None,
        mess_opted: bool = True,
        check_in_date: Optional[date] = None,
        check_in_time: Optional[str] = None,
        check_in_notes: Optional[str] = None,
    ) -> HostelAllocation:
        """
        Allocates a student to a hostel bed enforcing:
        1. Room capacity cap
        2. Single active hostel allocation per student
        3. Strict Double Bed Allocation Prevention (no two active residents on same room_id + bed_number)
        4. Gender match between student and hostel block
        """
        bed_clean = bed_number.strip()
        if not bed_clean:
            raise ValueError("Bed number cannot be empty.")

        room = session.query(HostelRoom).options(joinedload(HostelRoom.block)).filter(HostelRoom.id == room_id).first()
        if not room:
            raise ValueError(f"Hostel room with ID {room_id} not found.")
        if room.status == "Maintenance":
            raise ValueError(f"Room {room.room_number} is currently under maintenance.")

        # 1. Capacity check
        active_in_room = session.query(HostelAllocation).filter(
            HostelAllocation.room_id == room_id,
            HostelAllocation.status == "Active",
        ).count()
        if active_in_room >= room.capacity:
            raise ValueError(f"Room {room.room_number} is full! Capacity: {room.capacity}, Occupied: {active_in_room}.")

        # 2. Check for duplicate active allocation for this student
        existing = session.query(HostelAllocation).filter(
            HostelAllocation.student_id == student_id,
            HostelAllocation.status == "Active",
        ).first()
        if existing:
            raise ValueError(f"Student ID {student_id} already has an active bed in Room {existing.room.room_number}.")

        # 3. STRICT DOUBLE BED ALLOCATION CHECK
        bed_occupied = session.query(HostelAllocation).filter(
            HostelAllocation.room_id == room_id,
            func.lower(HostelAllocation.bed_number) == bed_clean.lower(),
            HostelAllocation.status == "Active",
        ).first()
        if bed_occupied:
            raise ValueError(
                f"Bed '{bed_clean}' in Room {room.room_number} is already occupied! Double bed allocation is not allowed."
            )

        bed_obj = session.query(HostelBed).filter(
            HostelBed.room_id == room_id,
            func.lower(HostelBed.bed_number) == bed_clean.lower(),
        ).first()
        if bed_obj and bed_obj.status == "Maintenance":
            raise ValueError(f"Bed '{bed_clean}' in Room {room.room_number} is under maintenance.")
        if bed_obj and bed_obj.status == "Occupied":
            raise ValueError(
                f"Bed '{bed_clean}' in Room {room.room_number} is already occupied! Double bed allocation is not allowed."
            )

        # 4. Gender check
        student = session.query(Student).filter(Student.id == student_id).first()
        if student and student.gender and room.block and room.block.gender_type in ["Boys", "Girls"]:
            student_gender = student.gender.strip().capitalize()
            block_gender = room.block.gender_type.strip().capitalize()
            if block_gender == "Boys" and student_gender in ["Female", "Girl", "Girls"]:
                raise ValueError("Gender mismatch: Female student cannot be assigned to Boys Hostel Block.")
            elif block_gender == "Girls" and student_gender in ["Male", "Boy", "Boys"]:
                raise ValueError("Gender mismatch: Male student cannot be assigned to Girls Hostel Block.")

        if not bed_obj:
            bed_obj = HostelBed(
                room_id=room_id,
                bed_number=bed_clean,
                bed_type="Single",
                status="Occupied",
            )
            session.add(bed_obj)
            session.flush()
        else:
            bed_obj.status = "Occupied"

        eff_date = admission_date or date.today()
        alloc = HostelAllocation(
            room_id=room_id,
            bed_id=bed_obj.id,
            student_id=student_id,
            mess_plan_id=mess_plan_id,
            bed_number=bed_obj.bed_number,
            admission_date=eff_date,
            check_in_date=check_in_date or eff_date,
            check_in_time=check_in_time or datetime.now().strftime("%I:%M %p"),
            check_in_notes=check_in_notes,
            monthly_fee=float(room.monthly_fee or 0.0),
            mess_opted=bool(mess_opted),
            guardian_contact=guardian_contact.strip() if guardian_contact else (student.emergency_contact if student else None),
            emergency_phone=emergency_phone.strip() if emergency_phone else (student.emergency_contact if student else None),
            remarks=remarks.strip() if remarks else None,
            status="Active",
        )
        session.add(alloc)

        if active_in_room + 1 >= room.capacity:
            room.status = "Full"

        session.commit()
        session.refresh(alloc)
        return alloc

    @staticmethod
    def check_in_boarder(
        session: Session,
        allocation_id: int,
        check_in_date: Optional[date] = None,
        check_in_time: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[HostelAllocation]:
        alloc = session.query(HostelAllocation).filter(HostelAllocation.id == allocation_id).first()
        if not alloc:
            return None
        alloc.check_in_date = check_in_date or date.today()
        alloc.check_in_time = check_in_time or datetime.now().strftime("%I:%M %p")
        if notes:
            alloc.check_in_notes = notes
        session.commit()
        session.refresh(alloc)
        return alloc

    @staticmethod
    def check_out_boarder(
        session: Session,
        allocation_id: int,
        check_out_date: Optional[date] = None,
        check_out_time: Optional[str] = None,
        clearance_status: str = "Cleared",
        damage_charges: float = 0.0,
        notes: Optional[str] = None,
    ) -> Optional[HostelAllocation]:
        alloc = session.query(HostelAllocation).filter(HostelAllocation.id == allocation_id).first()
        if not alloc:
            return None
        out_dt = check_out_date or date.today()
        alloc.status = "Vacated"
        alloc.vacate_date = out_dt
        alloc.check_out_date = out_dt
        alloc.check_out_time = check_out_time or datetime.now().strftime("%I:%M %p")
        alloc.clearance_status = clearance_status
        alloc.damage_charges = float(damage_charges or 0.0)
        if notes:
            alloc.check_out_notes = notes
            alloc.remarks = f"{alloc.remarks or ''}\nCheck-Out ({clearance_status}): {notes}".strip()

        if alloc.bed_id:
            bed = session.query(HostelBed).filter(HostelBed.id == alloc.bed_id).first()
            if bed and bed.status == "Occupied":
                bed.status = "Available"
        else:
            bed = session.query(HostelBed).filter(
                HostelBed.room_id == alloc.room_id,
                func.lower(HostelBed.bed_number) == alloc.bed_number.lower(),
            ).first()
            if bed and bed.status == "Occupied":
                bed.status = "Available"

        room = session.query(HostelRoom).filter(HostelRoom.id == alloc.room_id).first()
        if room and room.status == "Full":
            room.status = "Available"

        session.commit()
        session.refresh(alloc)
        return alloc

    @staticmethod
    def vacate_student(
        session: Session,
        allocation_id: int,
        vacate_date: Optional[date] = None,
        remarks: Optional[str] = None,
    ) -> Optional[HostelAllocation]:
        return HostelRepository.check_out_boarder(
            session=session,
            allocation_id=allocation_id,
            check_out_date=vacate_date,
            clearance_status="Cleared",
            notes=remarks,
        )

    # -------------------------------------------------------------
    # 4. Hostel Fees Billing & Collection
    # -------------------------------------------------------------
    @staticmethod
    def get_fee_charges(
        session: Session,
        billing_month: Optional[str] = None,
        status: Optional[str] = None,
        allocation_id: Optional[int] = None,
    ) -> List[HostelFeeCharge]:
        query = session.query(HostelFeeCharge).options(
            joinedload(HostelFeeCharge.allocation).joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
            joinedload(HostelFeeCharge.student),
        )
        if billing_month:
            query = query.filter(HostelFeeCharge.billing_month == billing_month)
        if status:
            query = query.filter(HostelFeeCharge.status == status)
        if allocation_id:
            query = query.filter(HostelFeeCharge.allocation_id == allocation_id)
        return query.order_by(HostelFeeCharge.billing_month.desc(), HostelFeeCharge.id.desc()).all()

    @staticmethod
    def generate_monthly_fees(
        session: Session,
        billing_month: str,
        due_date: Optional[str] = None,
        default_mess_fee: float = 2500.0,
        other_charges: float = 0.0,
    ) -> Dict[str, int]:
        active_allocs = session.query(HostelAllocation).options(
            joinedload(HostelAllocation.room),
            joinedload(HostelAllocation.mess_plan),
        ).filter(HostelAllocation.status == "Active").all()

        created = 0
        skipped = 0
        due_str = due_date or f"{billing_month}-10"

        for a in active_allocs:
            existing = session.query(HostelFeeCharge).filter(
                HostelFeeCharge.allocation_id == a.id,
                HostelFeeCharge.billing_month == billing_month,
            ).first()
            if existing:
                skipped += 1
                continue
            rent = float(a.monthly_fee if a.monthly_fee is not None else (a.room.monthly_fee if a.room else 0.0))
            if a.mess_opted:
                mess_amt = float(a.mess_plan.monthly_fee) if a.mess_plan else float(default_mess_fee)
            else:
                mess_amt = 0.0
            charge = HostelFeeCharge(
                allocation_id=a.id,
                student_id=a.student_id,
                billing_month=billing_month,
                due_date=due_str,
                room_rent=rent,
                mess_fee=mess_amt,
                other_charges=float(other_charges or 0.0),
                discount=0.0,
                paid_amount=0.0,
                status="Pending",
            )
            session.add(charge)
            created += 1

        session.commit()
        return {"created": created, "skipped": skipped}

    @staticmethod
    def record_fee_payment(
        session: Session,
        charge_id: int,
        amount: float,
        payment_method: str = "Cash",
        discount: Optional[float] = None,
        paid_date: Optional[str] = None,
        collected_by: str = "admin",
        remarks: Optional[str] = None,
    ) -> Tuple[Optional[HostelFeeCharge], Optional[str]]:
        charge = session.query(HostelFeeCharge).filter(HostelFeeCharge.id == charge_id).first()
        if not charge:
            return None, "Hostel fee charge not found."
        if charge.status == "Waived":
            return None, "Charge has already been waived."
        if amount < 0:
            return None, "Payment amount cannot be negative."
        if discount is not None:
            if discount < 0:
                return None, "Discount cannot be negative."
            charge.discount = float(discount)

        net = charge.net_payable
        charge.paid_amount = round(min(net, float(charge.paid_amount or 0.0) + float(amount)), 2)
        charge.payment_method = payment_method
        charge.paid_date = paid_date or date.today().isoformat()
        charge.collected_by = collected_by
        if not charge.receipt_no and amount > 0:
            charge.receipt_no = f"HST-RCP-{date.today().strftime('%Y%m')}-{charge.id:04d}-{uuid.uuid4().hex[:4].upper()}"
        if remarks:
            charge.remarks = f"{charge.remarks + ' | ' if charge.remarks else ''}{remarks}"

        if charge.paid_amount >= net:
            charge.status = "Paid"
        elif charge.paid_amount > 0:
            charge.status = "Partial"
        else:
            charge.status = "Pending"

        session.commit()
        session.refresh(charge)
        return charge, None

    @staticmethod
    def waive_fee_charge(session: Session, charge_id: int, remarks: Optional[str] = None) -> Optional[HostelFeeCharge]:
        charge = session.query(HostelFeeCharge).filter(HostelFeeCharge.id == charge_id).first()
        if not charge:
            return None
        charge.status = "Waived"
        charge.discount = charge.total_billed
        if remarks:
            charge.remarks = f"{charge.remarks + ' | ' if charge.remarks else ''}Waived: {remarks}"
        session.commit()
        session.refresh(charge)
        return charge

    # -------------------------------------------------------------
    # 5. Mess Plans, Weekly Menus & Dining Logs
    # -------------------------------------------------------------
    @staticmethod
    def get_mess_plans(session: Session) -> List[HostelMessPlan]:
        return session.query(HostelMessPlan).order_by(HostelMessPlan.plan_name.asc()).all()

    @staticmethod
    def create_mess_plan(
        session: Session,
        plan_name: str,
        monthly_fee: float,
        includes_breakfast: bool = True,
        includes_lunch: bool = True,
        includes_snacks: bool = True,
        includes_dinner: bool = True,
        description: Optional[str] = None,
    ) -> HostelMessPlan:
        plan = HostelMessPlan(
            plan_name=plan_name.strip(),
            monthly_fee=float(monthly_fee or 0.0),
            includes_breakfast=includes_breakfast,
            includes_lunch=includes_lunch,
            includes_snacks=includes_snacks,
            includes_dinner=includes_dinner,
            description=description,
            status="Active",
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)
        return plan

    @staticmethod
    def get_mess_menus(session: Session, block_id: Optional[int] = None) -> List[HostelMessMenu]:
        query = session.query(HostelMessMenu).options(joinedload(HostelMessMenu.block))
        if block_id:
            query = query.filter(HostelMessMenu.block_id == block_id)
        return query.order_by(HostelMessMenu.id.asc()).all()

    @staticmethod
    def add_mess_menu_item(
        session: Session,
        day_of_week: str,
        meal_type: str,
        menu_items: str,
        serving_time: Optional[str] = None,
        block_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> HostelMessMenu:
        item = HostelMessMenu(
            block_id=block_id,
            day_of_week=day_of_week,
            meal_type=meal_type,
            menu_items=menu_items.strip(),
            serving_time=serving_time,
            notes=notes,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item

    @staticmethod
    def get_mess_logs(session: Session, block_id: Optional[int] = None) -> List[HostelMessLog]:
        query = session.query(HostelMessLog).options(joinedload(HostelMessLog.block))
        if block_id:
            query = query.filter(HostelMessLog.block_id == block_id)
        return query.order_by(HostelMessLog.log_date.desc(), HostelMessLog.id.desc()).all()

    @staticmethod
    def add_mess_log(
        session: Session,
        meal_type: str,
        plates_served: int,
        meal_cost: float = 0.0,
        block_id: Optional[int] = None,
        allocation_id: Optional[int] = None,
        log_date: Optional[date] = None,
        remarks: Optional[str] = None,
    ) -> HostelMessLog:
        entry = HostelMessLog(
            log_date=log_date or date.today(),
            block_id=block_id,
            allocation_id=allocation_id,
            meal_type=meal_type,
            plates_served=int(plates_served or 0),
            meal_cost=float(meal_cost or 0.0),
            remarks=remarks,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

    # -------------------------------------------------------------
    # 6. Visitor Records
    # -------------------------------------------------------------
    @staticmethod
    def get_visitors(session: Session, block_id: Optional[int] = None, status: Optional[str] = None) -> List[HostelVisitorLog]:
        query = session.query(HostelVisitorLog).options(
            joinedload(HostelVisitorLog.block),
            joinedload(HostelVisitorLog.student),
            joinedload(HostelVisitorLog.allocation).joinedload(HostelAllocation.room),
        )
        if block_id:
            query = query.filter(HostelVisitorLog.block_id == block_id)
        if status:
            query = query.filter(HostelVisitorLog.status == status)
        return query.order_by(HostelVisitorLog.visit_date.desc(), HostelVisitorLog.id.desc()).all()

    @staticmethod
    def check_in_visitor(
        session: Session,
        visitor_name: str,
        visitor_phone: str,
        purpose: str,
        block_id: Optional[int] = None,
        student_id: Optional[int] = None,
        allocation_id: Optional[int] = None,
        relationship_to_student: str = "Parent",
        id_proof_type: Optional[str] = None,
        id_proof_no: Optional[str] = None,
        visit_date: Optional[date] = None,
        check_in_time: Optional[str] = None,
        approved_by: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> HostelVisitorLog:
        if allocation_id and (not student_id or not block_id):
            alloc = session.query(HostelAllocation).options(joinedload(HostelAllocation.room)).filter(
                HostelAllocation.id == allocation_id
            ).first()
            if alloc:
                student_id = student_id or alloc.student_id
                if alloc.room:
                    block_id = block_id or alloc.room.block_id

        v = HostelVisitorLog(
            block_id=block_id,
            student_id=student_id,
            allocation_id=allocation_id,
            visitor_name=visitor_name.strip(),
            visitor_phone=visitor_phone.strip(),
            relationship_to_student=relationship_to_student,
            id_proof_type=id_proof_type,
            id_proof_no=id_proof_no,
            purpose=purpose.strip(),
            visit_date=visit_date or date.today(),
            check_in_time=check_in_time or datetime.now().strftime("%I:%M %p"),
            approved_by=approved_by,
            status="Checked In",
            remarks=remarks,
        )
        session.add(v)
        session.commit()
        session.refresh(v)
        return v

    @staticmethod
    def check_out_visitor(
        session: Session,
        visitor_id: int,
        check_out_time: Optional[str] = None,
    ) -> Optional[HostelVisitorLog]:
        v = session.query(HostelVisitorLog).filter(HostelVisitorLog.id == visitor_id).first()
        if not v:
            return None
        v.check_out_time = check_out_time or datetime.now().strftime("%I:%M %p")
        v.status = "Checked Out"
        session.commit()
        session.refresh(v)
        return v

    # -------------------------------------------------------------
    # 7. Complaints & Maintenance Work Orders
    # -------------------------------------------------------------
    @staticmethod
    def get_complaints(session: Session, status: Optional[str] = None, block_id: Optional[int] = None) -> List[HostelComplaint]:
        query = session.query(HostelComplaint).options(
            joinedload(HostelComplaint.block),
            joinedload(HostelComplaint.room),
            joinedload(HostelComplaint.student),
        )
        if status:
            query = query.filter(HostelComplaint.status == status)
        if block_id:
            query = query.filter(HostelComplaint.block_id == block_id)
        return query.order_by(HostelComplaint.reported_date.desc(), HostelComplaint.id.desc()).all()

    @staticmethod
    def create_complaint(
        session: Session,
        title: str,
        description: str,
        category: str = "Other",
        priority: str = "Medium",
        block_id: Optional[int] = None,
        room_id: Optional[int] = None,
        student_id: Optional[int] = None,
        allocation_id: Optional[int] = None,
        assigned_to: Optional[str] = None,
        reported_date: Optional[date] = None,
    ) -> HostelComplaint:
        if allocation_id and (not student_id or not room_id or not block_id):
            alloc = session.query(HostelAllocation).options(joinedload(HostelAllocation.room)).filter(
                HostelAllocation.id == allocation_id
            ).first()
            if alloc:
                student_id = student_id or alloc.student_id
                room_id = room_id or alloc.room_id
                if alloc.room:
                    block_id = block_id or alloc.room.block_id

        c_no = f"CMP-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        comp = HostelComplaint(
            complaint_no=c_no,
            block_id=block_id,
            room_id=room_id,
            student_id=student_id,
            allocation_id=allocation_id,
            category=category,
            priority=priority,
            title=title.strip(),
            description=description.strip(),
            reported_date=reported_date or date.today(),
            assigned_to=assigned_to,
            status="Open",
        )
        session.add(comp)
        session.commit()
        session.refresh(comp)
        return comp

    @staticmethod
    def update_complaint(session: Session, complaint_id: int, **kwargs) -> Optional[HostelComplaint]:
        comp = session.query(HostelComplaint).filter(HostelComplaint.id == complaint_id).first()
        if not comp:
            return None
        for key, value in kwargs.items():
            if hasattr(comp, key):
                setattr(comp, key, value)
        if kwargs.get("status") in ("Resolved", "Closed") and not comp.resolved_date:
            comp.resolved_date = date.today()
        session.commit()
        session.refresh(comp)
        return comp

    @staticmethod
    def get_maintenance_requests(
        session: Session,
        status: Optional[str] = None,
        block_id: Optional[int] = None,
    ) -> List[HostelMaintenanceRequest]:
        query = session.query(HostelMaintenanceRequest).options(
            joinedload(HostelMaintenanceRequest.block),
            joinedload(HostelMaintenanceRequest.room),
            joinedload(HostelMaintenanceRequest.bed),
            joinedload(HostelMaintenanceRequest.complaint),
        )
        if status:
            query = query.filter(HostelMaintenanceRequest.status == status)
        if block_id:
            query = query.filter(HostelMaintenanceRequest.block_id == block_id)
        return query.order_by(HostelMaintenanceRequest.reported_date.desc(), HostelMaintenanceRequest.id.desc()).all()

    @staticmethod
    def create_maintenance_request(
        session: Session,
        block_id: int,
        issue_title: str,
        maintenance_type: str = "General Repair",
        priority: str = "Medium",
        room_id: Optional[int] = None,
        bed_id: Optional[int] = None,
        complaint_id: Optional[int] = None,
        vendor_or_technician: Optional[str] = None,
        estimated_cost: float = 0.0,
        actual_cost: float = 0.0,
        scheduled_date: Optional[date] = None,
        blocks_occupancy: bool = False,
        status: str = "Pending",
        notes: Optional[str] = None,
    ) -> HostelMaintenanceRequest:
        t_no = f"HMNT-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        req = HostelMaintenanceRequest(
            ticket_no=t_no,
            block_id=block_id,
            room_id=room_id,
            bed_id=bed_id,
            complaint_id=complaint_id,
            issue_title=issue_title.strip(),
            maintenance_type=maintenance_type,
            priority=priority,
            reported_date=date.today(),
            scheduled_date=scheduled_date,
            vendor_or_technician=vendor_or_technician,
            estimated_cost=float(estimated_cost or 0.0),
            actual_cost=float(actual_cost or 0.0),
            blocks_occupancy=bool(blocks_occupancy),
            status=status,
            notes=notes,
        )
        session.add(req)

        if blocks_occupancy and status in ("Pending", "In Progress"):
            if bed_id:
                bed = session.query(HostelBed).filter(HostelBed.id == bed_id).first()
                if bed:
                    bed.status = "Maintenance"
            elif room_id:
                room = session.query(HostelRoom).filter(HostelRoom.id == room_id).first()
                if room:
                    room.status = "Maintenance"

        if complaint_id:
            comp = session.query(HostelComplaint).filter(HostelComplaint.id == complaint_id).first()
            if comp and comp.status == "Open":
                comp.status = "In Progress"

        session.commit()
        session.refresh(req)
        return req

    @staticmethod
    def update_maintenance_request(session: Session, request_id: int, **kwargs) -> Optional[HostelMaintenanceRequest]:
        req = session.query(HostelMaintenanceRequest).filter(HostelMaintenanceRequest.id == request_id).first()
        if not req:
            return None
        for key, value in kwargs.items():
            if hasattr(req, key):
                setattr(req, key, value)

        if req.status == "Completed":
            if not req.completed_date:
                req.completed_date = date.today()
            if req.blocks_occupancy:
                if req.bed_id:
                    bed = session.query(HostelBed).filter(HostelBed.id == req.bed_id).first()
                    if bed and bed.status == "Maintenance":
                        bed.status = "Available"
                if req.room_id:
                    room = session.query(HostelRoom).filter(HostelRoom.id == req.room_id).first()
                    if room and room.status == "Maintenance":
                        room.status = "Available"
            if req.complaint_id:
                comp = session.query(HostelComplaint).filter(HostelComplaint.id == req.complaint_id).first()
                if comp and comp.status != "Resolved":
                    comp.status = "Resolved"
                    comp.resolved_date = date.today()
                    comp.resolution_notes = req.notes or f"Resolved via Maintenance Ticket {req.ticket_no}"

        session.commit()
        session.refresh(req)
        return req

    # -------------------------------------------------------------
    # 8. Gate Passes / Outpasses
    # -------------------------------------------------------------
    @staticmethod
    def get_all_gate_passes(session: Session) -> List[HostelGatePass]:
        return session.query(HostelGatePass).options(
            joinedload(HostelGatePass.allocation).joinedload(HostelAllocation.student),
            joinedload(HostelGatePass.allocation).joinedload(HostelAllocation.room).joinedload(HostelRoom.block),
        ).order_by(HostelGatePass.leave_date.desc(), HostelGatePass.id.desc()).all()

    @staticmethod
    def create_gate_pass(
        session: Session,
        allocation_id: int,
        purpose: str,
        expected_return_date: date,
        leave_date: Optional[date] = None,
        remarks: Optional[str] = None,
    ) -> HostelGatePass:
        today_str = datetime.now().strftime("%Y%m%d")
        count = session.query(HostelGatePass).count() + 1
        pass_no = f"GP-{today_str}-{count:04d}-{uuid.uuid4().hex[:3].upper()}"

        gp = HostelGatePass(
            pass_number=pass_no,
            allocation_id=allocation_id,
            purpose=purpose.strip(),
            leave_date=leave_date or date.today(),
            expected_return_date=expected_return_date,
            warden_approval="Approved",
            status="Out",
            remarks=remarks.strip() if remarks else None,
        )
        session.add(gp)
        session.commit()
        session.refresh(gp)
        return gp

    @staticmethod
    def return_gate_pass(
        session: Session,
        gate_pass_id: int,
        actual_return_date: Optional[date] = None,
    ) -> Optional[HostelGatePass]:
        gp = session.query(HostelGatePass).filter(HostelGatePass.id == gate_pass_id).first()
        if not gp:
            return None
        return_dt = actual_return_date or date.today()
        gp.actual_return_date = return_dt
        gp.status = "Overstayed" if return_dt > gp.expected_return_date else "Returned"
        session.commit()
        session.refresh(gp)
        return gp

    # -------------------------------------------------------------
    # 9. Overall Hostel Stats
    # -------------------------------------------------------------
    @staticmethod
    def get_hostel_stats(session: Session) -> Dict[str, Any]:
        total_blocks = session.query(HostelBlock).count()
        total_floors = session.query(HostelFloor).count()
        total_rooms = session.query(HostelRoom).count()
        total_beds = session.query(HostelBed).count()
        total_capacity = session.query(func.coalesce(func.sum(HostelRoom.capacity), 0)).scalar() or 0
        active_allocations = session.query(HostelAllocation).filter(HostelAllocation.status == "Active").count()
        available_beds = max(0, total_capacity - active_allocations)
        occupancy_rate = round((active_allocations / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        boarders_out = session.query(HostelGatePass).filter(
            HostelGatePass.status.in_(["Out", "Overstayed"])
        ).count()
        visitors_inside = session.query(HostelVisitorLog).filter(HostelVisitorLog.status == "Checked In").count()
        open_complaints = session.query(HostelComplaint).filter(
            HostelComplaint.status.in_(["Open", "In Progress"])
        ).count()
        pending_maintenance = session.query(HostelMaintenanceRequest).filter(
            HostelMaintenanceRequest.status.in_(["Pending", "In Progress"])
        ).count()

        fee_charges = session.query(HostelFeeCharge).all()
        fee_billed = sum(c.net_payable for c in fee_charges if c.status != "Waived")
        fee_collected = sum(float(c.paid_amount or 0.0) for c in fee_charges)
        fee_due = sum(c.balance_due for c in fee_charges)

        return {
            "total_blocks": total_blocks,
            "total_floors": total_floors,
            "total_rooms": total_rooms,
            "total_beds": total_beds or total_capacity,
            "total_capacity": total_capacity,
            "occupied_beds": active_allocations,
            "available_beds": available_beds,
            "occupancy_rate": occupancy_rate,
            "boarders_out": boarders_out,
            "present_in_hostel": max(0, active_allocations - boarders_out),
            "visitors_inside": visitors_inside,
            "open_complaints": open_complaints,
            "pending_maintenance": pending_maintenance,
            "fee_billed": round(fee_billed, 2),
            "fee_collected": round(fee_collected, 2),
            "fee_due": round(fee_due, 2),
        }
