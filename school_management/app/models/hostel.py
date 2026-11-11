"""
EduManage Pro - Hostel & Dormitory ORM Models
Phase 12: Hostel Blocks, Dorm Rooms, Bed Allocations & Gate Passes
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.models.base import Base, TimestampMixin


class HostelBlock(Base, TimestampMixin):
    """Hostel building / residential block."""
    __tablename__ = "hostel_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_name = Column(String(100), unique=True, nullable=False, index=True)
    gender_type = Column(String(20), nullable=False, default="Boys")  # Boys, Girls, Co-ed
    warden_name = Column(String(100), nullable=True)
    warden_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    total_floors = Column(Integer, default=3)
    status = Column(String(20), default="Active")  # Active, Maintenance

    # Relationships
    rooms = relationship("HostelRoom", back_populates="block", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HostelBlock(id={self.id}, name='{self.block_name}', gender='{self.gender_type}')>"


class HostelRoom(Base, TimestampMixin):
    """Hostel room or dorm suite within a block."""
    __tablename__ = "hostel_rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(Integer, ForeignKey("hostel_blocks.id", ondelete="CASCADE"), nullable=False)
    room_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=1)
    room_type = Column(String(30), default="Double")  # Single, Double, Triple, 4-Bed Dorm, 6-Bed Dorm
    capacity = Column(Integer, nullable=False, default=2)  # Total bed capacity
    monthly_fee = Column(Float, default=3000.0)
    amenities = Column(String(255), default="Attached Bath, Study Table, Wi-Fi")
    status = Column(String(20), default="Available")  # Available, Full, Maintenance

    # Relationships
    block = relationship("HostelBlock", back_populates="rooms")
    allocations = relationship("HostelAllocation", back_populates="room", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HostelRoom(id={self.id}, room_number='{self.room_number}', capacity={self.capacity})>"


class HostelAllocation(Base, TimestampMixin):
    """Bed allocation for boarding students."""
    __tablename__ = "hostel_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    bed_number = Column(String(20), nullable=False)  # Bed-1, Bed-2, A, B
    admission_date = Column(Date, default=date.today)
    vacate_date = Column(Date, nullable=True)
    guardian_contact = Column(String(30), nullable=True)
    emergency_phone = Column(String(30), nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(String(20), default="Active")  # Active, Vacated, Suspended

    # Relationships
    room = relationship("HostelRoom", back_populates="allocations")
    student = relationship("Student")
    gate_passes = relationship("HostelGatePass", back_populates="allocation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HostelAllocation(id={self.id}, student_id={self.student_id}, bed='{self.bed_number}', status='{self.status}')>"


class HostelGatePass(Base, TimestampMixin):
    """Outpass / Gate pass permit for hostel boarders."""
    __tablename__ = "hostel_gate_passes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pass_number = Column(String(30), unique=True, nullable=False, index=True)
    allocation_id = Column(Integer, ForeignKey("hostel_allocations.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String(100), nullable=False)  # Home Visit, Medical, Market, Sports, Emergency
    leave_date = Column(Date, nullable=False, default=date.today)
    expected_return_date = Column(Date, nullable=False)
    actual_return_date = Column(Date, nullable=True)
    warden_approval = Column(String(20), default="Approved")  # Approved, Rejected, Pending
    status = Column(String(20), default="Out")  # Out, Returned, Overstayed, Cancelled
    remarks = Column(Text, nullable=True)

    # Relationships
    allocation = relationship("HostelAllocation", back_populates="gate_passes")

    def __repr__(self):
        return f"<HostelGatePass(pass_no='{self.pass_number}', status='{self.status}')>"
