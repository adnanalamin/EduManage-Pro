"""
EduManage Pro - Hostel & Dormitory ORM Models
Phase 12: Hostel Blocks, Dorm Rooms, Bed Allocations & Gate Passes
"""

from datetime import date
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date, Text, Numeric,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class HostelBlock(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel building / residential block."""
    __tablename__ = "hostel_blocks"

    block_name = Column(String(100), unique=True, nullable=False, index=True)
    gender_type = Column(String(20), nullable=False, default="Boys")  # Boys, Girls, Co-ed
    warden_name = Column(String(100), nullable=True)
    warden_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    total_floors = Column(Integer, default=3, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Maintenance

    # Relationships
    rooms = relationship("HostelRoom", back_populates="block")

    __table_args__ = (
        CheckConstraint("total_floors > 0", name="ck_hostel_block_floors_pos"),
    )

    def __repr__(self):
        return f"<HostelBlock(id={self.id}, name='{self.block_name}', gender='{self.gender_type}')>"


class HostelRoom(Base, TimestampMixin, SoftDeleteMixin):
    """Hostel room or dorm suite within a block."""
    __tablename__ = "hostel_rooms"

    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=1, nullable=False)
    room_type = Column(String(30), default="Double", nullable=False)  # Single, Double, Triple, 4-Bed Dorm, 6-Bed Dorm
    capacity = Column(Integer, nullable=False, default=2)
    monthly_fee = Column(Numeric(12, 2, asdecimal=False), default=3000.0, nullable=False)
    amenities = Column(String(255), default="Attached Bath, Study Table, Wi-Fi")
    status = Column(String(20), default="Available", nullable=False, index=True)

    # Relationships
    block = relationship("HostelBlock", back_populates="rooms")
    allocations = relationship("HostelAllocation", back_populates="room")

    __table_args__ = (
        UniqueConstraint("block_id", "room_number", name="uq_hostel_block_room"),
        CheckConstraint("capacity > 0 AND monthly_fee >= 0", name="ck_hostel_room_valid"),
    )

    def __repr__(self):
        return f"<HostelRoom(id={self.id}, room_number='{self.room_number}', capacity={self.capacity})>"


class HostelAllocation(Base, TimestampMixin, SoftDeleteMixin):
    """Bed allocation for boarding students."""
    __tablename__ = "hostel_allocations"

    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    bed_number = Column(String(20), nullable=False)  # Bed-1, Bed-2, A, B
    admission_date = Column(Date, default=date.today, nullable=False)
    vacate_date = Column(Date, nullable=True)
    guardian_contact = Column(String(30), nullable=True)
    emergency_phone = Column(String(30), nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(String(20), default="Active", nullable=False, index=True)  # Active, Vacated, Suspended

    # Relationships
    room = relationship("HostelRoom", back_populates="allocations")
    student = relationship("Student")
    gate_passes = relationship("HostelGatePass", back_populates="allocation")

    __table_args__ = (
        Index("idx_hostel_alloc_room_status", "room_id", "status"),
    )

    def __repr__(self):
        return f"<HostelAllocation(id={self.id}, student_id={self.student_id}, bed='{self.bed_number}', status='{self.status}')>"


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
