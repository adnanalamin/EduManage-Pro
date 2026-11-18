"""
EduManage Pro - Hostel & Dormitory Management ORM Models
Enterprise Hostel Buildings, Floors, Rooms, Beds, Double-Allocation Prevention,
Student Check-In/Check-Out, Hostel Fees, Mess Plans & Menus, Visitor Records,
Complaints, Maintenance Work Orders, and Gate Passes.
"""

from datetime import date, datetime
from typing import List
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


HOSTEL_ROOM_TYPES: List[str] = ["Single", "Double", "Triple", "4-Bed Dorm", "6-Bed Dorm", "Suite"]
COMPLAINT_CATEGORIES: List[str] = [
    "Electrical",
    "Plumbing",
    "Furniture",
    "Cleanliness",
    "Mess / Food",
    "Internet / Wi-Fi",
    "Discipline / Security",
    "Other",
]
MAINTENANCE_TYPES: List[str] = [
    "Plumbing",
    "Electrical",
    "Carpentry",
    "HVAC / AC",
    "Painting",
    "Pest Control",
    "Appliance Repair",
    "General Repair",
]
DAYS_OF_WEEK: List[str] = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class HostelBlock(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel building / residential block."""
    __tablename__ = "hostel_blocks"

    block_code = Column(String(30), unique=True, nullable=True, index=True)
    block_name = Column(String(100), unique=True, nullable=False, index=True)
    gender_type = Column(String(20), nullable=False, default="Boys")  # Boys, Girls, Co-ed
    warden_staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)
    warden_name = Column(String(100), nullable=True)
    warden_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    total_floors = Column(Integer, default=3, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Maintenance, Closed
    notes = Column(Text, nullable=True)

    # Relationships
    warden_staff = relationship("Staff", foreign_keys=[warden_staff_id])
    floors = relationship(
        "HostelFloor",
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="HostelFloor.floor_number",
    )
    rooms = relationship("HostelRoom", back_populates="block")
    visitors = relationship("HostelVisitorLog", back_populates="block")
    complaints = relationship("HostelComplaint", back_populates="block")
    maintenance_requests = relationship("HostelMaintenanceRequest", back_populates="block")

    __table_args__ = (
        CheckConstraint("total_floors > 0", name="ck_hostel_block_floors_pos"),
    )

    def __repr__(self):
        return f"<HostelBlock(id={self.id}, name='{self.block_name}', gender='{self.gender_type}')>"


class HostelFloor(Base, TimestampMixin, SoftDeleteMixin):
    """Explicit floor definition inside a hostel building."""
    __tablename__ = "hostel_floors"

    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    floor_number = Column(Integer, nullable=False)
    floor_name = Column(String(80), nullable=False)  # e.g. Ground Floor, 1st Floor, Senior Wing
    supervisor_name = Column(String(100), nullable=True)
    supervisor_phone = Column(String(30), nullable=True)
    target_capacity = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="Active", nullable=False)  # Active, Maintenance
    notes = Column(Text, nullable=True)

    block = relationship("HostelBlock", back_populates="floors")
    rooms = relationship("HostelRoom", back_populates="floor")

    __table_args__ = (
        UniqueConstraint("block_id", "floor_number", name="uq_hostel_block_floor_num"),
        CheckConstraint("target_capacity >= 0", name="ck_hostel_floor_cap_nonneg"),
    )

    def __repr__(self):
        return f"<HostelFloor(block_id={self.block_id}, floor={self.floor_number}, name='{self.floor_name}')>"


class HostelRoom(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel room or dorm suite within a block and floor."""
    __tablename__ = "hostel_rooms"

    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    floor_id = Column(Integer, ForeignKey("hostel_floors.id", ondelete="SET NULL"), nullable=True, index=True)
    room_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=1, nullable=False)
    room_type = Column(String(30), default="Double", nullable=False)  # Single, Double, Triple, 4-Bed Dorm, 6-Bed Dorm
    capacity = Column(Integer, nullable=False, default=2)
    monthly_fee = Column(Numeric(12, 2, asdecimal=False), default=3000.0, nullable=False)
    amenities = Column(String(255), default="Attached Bath, Study Table, Wi-Fi")
    has_attached_bath = Column(Boolean, default=True, nullable=False)
    has_ac = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="Available", nullable=False, index=True)  # Available, Full, Maintenance
    notes = Column(Text, nullable=True)

    # Relationships
    block = relationship("HostelBlock", back_populates="rooms")
    floor = relationship("HostelFloor", back_populates="rooms")
    beds = relationship(
        "HostelBed",
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="HostelBed.bed_number",
    )
    allocations = relationship("HostelAllocation", back_populates="room")

    __table_args__ = (
        UniqueConstraint("block_id", "room_number", name="uq_hostel_block_room"),
        CheckConstraint("capacity > 0 AND monthly_fee >= 0", name="ck_hostel_room_valid"),
    )

    def __repr__(self):
        return f"<HostelRoom(id={self.id}, room_number='{self.room_number}', capacity={self.capacity})>"


class HostelBed(Base, TimestampMixin, SoftDeleteMixin):
    """Individual bed inventory unit inside a hostel room to prevent double bed allocation."""
    __tablename__ = "hostel_beds"

    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    bed_number = Column(String(30), nullable=False)  # Bed-1, Bed-2, A, B
    bed_type = Column(String(30), default="Single", nullable=False)  # Single, Bunk-Lower, Bunk-Upper
    status = Column(String(20), default="Available", nullable=False, index=True)  # Available, Occupied, Reserved, Maintenance
    notes = Column(String(255), nullable=True)

    room = relationship("HostelRoom", back_populates="beds")
    allocations = relationship("HostelAllocation", back_populates="bed")

    __table_args__ = (
        UniqueConstraint("room_id", "bed_number", name="uq_hostel_room_bed"),
        Index("idx_hostel_bed_room_status", "room_id", "status"),
    )

    def __repr__(self):
        return f"<HostelBed(room_id={self.room_id}, bed='{self.bed_number}', status='{self.status}')>"


class HostelMessPlan(Base, TimestampMixin, SoftDeleteMixin):
    """Configurable hostel dining / mess meal subscription plans."""
    __tablename__ = "hostel_mess_plans"

    plan_name = Column(String(80), unique=True, nullable=False)  # Full Board, Vegetarian, Two-Meal, Self-Catered
    monthly_fee = Column(Numeric(12, 2, asdecimal=False), default=2500.0, nullable=False)
    includes_breakfast = Column(Boolean, default=True, nullable=False)
    includes_lunch = Column(Boolean, default=True, nullable=False)
    includes_snacks = Column(Boolean, default=True, nullable=False)
    includes_dinner = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(String(20), default="Active", nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("monthly_fee >= 0", name="ck_hostel_mess_plan_fee_nonneg"),
    )


class HostelMessMenu(Base, TimestampMixin, SoftDeleteMixin):
    """Weekly mess dining schedule by day and meal slot."""
    __tablename__ = "hostel_mess_menus"

    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    day_of_week = Column(String(20), nullable=False, index=True)  # Monday..Sunday
    meal_type = Column(String(30), nullable=False)  # Breakfast, Lunch, Snacks, Dinner
    menu_items = Column(Text, nullable=False)
    serving_time = Column(String(40), nullable=True)
    notes = Column(String(255), nullable=True)

    block = relationship("HostelBlock")


class HostelMessLog(Base, TimestampMixin):
    """Daily mess service / plate count or meal consumption log."""
    __tablename__ = "hostel_mess_logs"

    log_date = Column(Date, default=date.today, nullable=False, index=True)
    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="SET NULL"), nullable=True, index=True)
    meal_type = Column(String(30), nullable=False)  # Breakfast, Lunch, Snacks, Dinner
    plates_served = Column(Integer, default=1, nullable=False)
    meal_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    remarks = Column(String(255), nullable=True)

    block = relationship("HostelBlock")

    __table_args__ = (
        CheckConstraint("plates_served >= 0 AND meal_cost >= 0", name="ck_hostel_mess_log_nonneg"),
    )


class HostelAllocation(Base, TimestampMixin, SoftDeleteMixin):
    """Bed allocation, Check-In, and Check-Out lifecycle for boarding students."""
    __tablename__ = "hostel_allocations"

    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    bed_id = Column(Integer, ForeignKey("hostel_beds.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    mess_plan_id = Column(Integer, ForeignKey("hostel_mess_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    bed_number = Column(String(30), nullable=False)  # Bed-1, Bed-2, A, B
    admission_date = Column(Date, default=date.today, nullable=False)
    check_in_date = Column(Date, nullable=True)
    check_in_time = Column(String(20), nullable=True)
    check_in_notes = Column(Text, nullable=True)
    vacate_date = Column(Date, nullable=True)
    check_out_date = Column(Date, nullable=True)
    check_out_time = Column(String(20), nullable=True)
    check_out_notes = Column(Text, nullable=True)
    clearance_status = Column(String(30), default="Pending", nullable=False)  # Pending, Cleared, Damage Charge
    damage_charges = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    monthly_fee = Column(Numeric(12, 2, asdecimal=False), nullable=True)
    mess_opted = Column(Boolean, default=True, nullable=False)
    guardian_contact = Column(String(30), nullable=True)
    emergency_phone = Column(String(30), nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Vacated, Suspended

    # Relationships
    room = relationship("HostelRoom", back_populates="allocations")
    bed = relationship("HostelBed", back_populates="allocations")
    student = relationship("Student")
    mess_plan = relationship("HostelMessPlan")
    gate_passes = relationship("HostelGatePass", back_populates="allocation")
    fee_charges = relationship(
        "HostelFeeCharge",
        back_populates="allocation",
        cascade="all, delete-orphan",
        order_by="HostelFeeCharge.billing_month.desc(), HostelFeeCharge.id.desc()",
    )

    __table_args__ = (
        CheckConstraint("damage_charges >= 0", name="ck_hostel_alloc_damage_nonneg"),
        Index("idx_hostel_alloc_room_status", "room_id", "status"),
        Index("idx_hostel_alloc_room_bed_status", "room_id", "bed_number", "status"),
    )

    def __repr__(self):
        return f"<HostelAllocation(id={self.id}, student_id={self.student_id}, bed='{self.bed_number}', status='{self.status}')>"


class HostelFeeCharge(Base, TimestampMixin, SoftDeleteMixin):
    """Monthly hostel accommodation, mess, utility, and damage fee charge & payment record."""
    __tablename__ = "hostel_fee_charges"

    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    billing_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    due_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    room_rent = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    mess_fee = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    other_charges = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    status = Column(String(20), default="Pending", nullable=False, index=True)  # Pending, Partial, Paid, Waived
    payment_method = Column(String(30), nullable=True)
    receipt_no = Column(String(60), unique=True, nullable=True, index=True)
    paid_date = Column(String(20), nullable=True)
    collected_by = Column(String(80), nullable=True)
    remarks = Column(Text, nullable=True)

    allocation = relationship("HostelAllocation", back_populates="fee_charges")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint("allocation_id", "billing_month", name="uq_hostel_fee_alloc_month"),
        CheckConstraint(
            "room_rent >= 0 AND mess_fee >= 0 AND other_charges >= 0 AND discount >= 0 AND paid_amount >= 0",
            name="ck_hostel_fee_nonneg",
        ),
        Index("idx_hostel_fee_month_status", "billing_month", "status"),
    )

    @property
    def total_billed(self) -> float:
        return round(
            float(self.room_rent or 0.0) + float(self.mess_fee or 0.0) + float(self.other_charges or 0.0),
            2,
        )

    @property
    def net_payable(self) -> float:
        return round(max(0.0, self.total_billed - float(self.discount or 0.0)), 2)

    @property
    def balance_due(self) -> float:
        if self.status == "Waived":
            return 0.0
        return round(max(0.0, self.net_payable - float(self.paid_amount or 0.0)), 2)


class HostelGatePass(Base, TimestampMixin, SoftDeleteMixin):
    """Outpass / Gate pass permit for hostel boarders."""
    __tablename__ = "hostel_gate_passes"

    pass_number = Column(String(30), unique=True, nullable=False, index=True)
    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="RESTRICT"), nullable=False, index=True)
    purpose = Column(String(100), nullable=False)
    leave_date = Column(Date, nullable=False, default=date.today)
    expected_return_date = Column(Date, nullable=False)
    actual_return_date = Column(Date, nullable=True)
    warden_approval = Column(String(20), default="Approved", nullable=False)
    status = Column(String(20), default="Out", nullable=False, index=True)  # Out, Returned, Overstayed, Cancelled
    remarks = Column(Text, nullable=True)

    # Relationships
    allocation = relationship("HostelAllocation", back_populates="gate_passes")

    __table_args__ = (
        Index("idx_hostel_pass_status_dates", "status", "leave_date", "expected_return_date"),
    )

    def __repr__(self):
        return f"<HostelGatePass(pass_no='{self.pass_number}', status='{self.status}')>"


class HostelVisitorLog(Base, TimestampMixin, SoftDeleteMixin):
    """Visitor check-in / check-out log with guardian verification."""
    __tablename__ = "hostel_visitors"

    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="SET NULL"), nullable=True, index=True)
    visitor_name = Column(String(120), nullable=False)
    visitor_phone = Column(String(30), nullable=False)
    relationship_to_student = Column(String(50), default="Parent", nullable=False)
    id_proof_type = Column(String(40), nullable=True)  # NID, Passport, Driving License
    id_proof_no = Column(String(60), nullable=True)
    purpose = Column(String(150), nullable=False)
    visit_date = Column(Date, default=date.today, nullable=False, index=True)
    check_in_time = Column(String(20), nullable=False)
    check_out_time = Column(String(20), nullable=True)
    approved_by = Column(String(80), nullable=True)
    status = Column(String(20), default="Checked In", nullable=False, index=True)  # Checked In, Checked Out, Denied
    remarks = Column(Text, nullable=True)

    block = relationship("HostelBlock", back_populates="visitors")
    student = relationship("Student")
    allocation = relationship("HostelAllocation")


class HostelComplaint(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel boarder complaints and resolution tracking."""
    __tablename__ = "hostel_complaints"

    complaint_no = Column(String(40), unique=True, nullable=False, index=True)
    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(50), default="Other", nullable=False, index=True)
    priority = Column(String(20), default="Medium", nullable=False, index=True)  # Low, Medium, High, Urgent
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    reported_date = Column(Date, default=date.today, nullable=False, index=True)
    assigned_to = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_date = Column(Date, nullable=True)
    status = Column(String(25), default="Open", nullable=False, index=True)  # Open, In Progress, Resolved, Closed

    block = relationship("HostelBlock", back_populates="complaints")
    room = relationship("HostelRoom")
    student = relationship("Student")
    allocation = relationship("HostelAllocation")


class HostelMaintenanceRequest(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel facility, room, and bed maintenance work orders & expenses."""
    __tablename__ = "hostel_maintenance"

    ticket_no = Column(String(40), unique=True, nullable=False, index=True)
    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    bed_id = Column(Integer, ForeignKey("hostel_beds.id", ondelete="SET NULL"), nullable=True, index=True)
    complaint_id = Column(Integer, ForeignKey("hostel_complaints.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_title = Column(String(150), nullable=False)
    maintenance_type = Column(String(50), default="General Repair", nullable=False, index=True)
    priority = Column(String(20), default="Medium", nullable=False, index=True)  # Low, Medium, High, Urgent
    reported_date = Column(Date, default=date.today, nullable=False, index=True)
    scheduled_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    vendor_or_technician = Column(String(120), nullable=True)
    estimated_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    actual_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    blocks_occupancy = Column(Boolean, default=False, nullable=False)
    status = Column(String(25), default="Pending", nullable=False, index=True)  # Pending, In Progress, Completed, Cancelled
    notes = Column(Text, nullable=True)

    block = relationship("HostelBlock", back_populates="maintenance_requests")
    room = relationship("HostelRoom")
    bed = relationship("HostelBed")
    complaint = relationship("HostelComplaint")

    __table_args__ = (
        CheckConstraint("estimated_cost >= 0 AND actual_cost >= 0", name="ck_hostel_maint_cost_nonneg"),
    )
