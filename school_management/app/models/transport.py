"""
EduManage Pro - Transport & Fleet Management ORM Models
Phase 11: Vehicles, Routes, Stops & Passenger Route Allocations
"""

from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, Numeric, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin


class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a school bus, van, or fleet vehicle."""
    __tablename__ = "transport_vehicles"

    vehicle_number = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_model = Column(String(100), nullable=False)
    vehicle_type = Column(String(50), default="Bus", nullable=False)  # "Bus", "Minibus", "Van"
    seating_capacity = Column(Integer, nullable=False, default=40)
    driver_name = Column(String(150), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    driver_license = Column(String(50), nullable=True)
    helper_name = Column(String(150), nullable=True)
    helper_phone = Column(String(50), nullable=True)
    insurance_expiry = Column(String(20), nullable=True)  # YYYY-MM-DD
    fitness_expiry = Column(String(20), nullable=True)    # YYYY-MM-DD
    status = Column(String(30), default="Active", nullable=False, index=True)

    # Relationships
    routes = relationship("TransportRoute", back_populates="vehicle")
    passengers = relationship("TransportPassenger", back_populates="vehicle")

    __table_args__ = (
        CheckConstraint("seating_capacity > 0", name="ck_vehicle_capacity_pos"),
    )

    def __repr__(self):
        return f"<Vehicle {self.vehicle_number} ({self.vehicle_model}) Capacity: {self.seating_capacity}>"


class TransportRoute(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a school transit route with origin, destination, and monthly fare."""
    __tablename__ = "transport_routes"

    route_name = Column(String(150), unique=True, nullable=False, index=True)
    route_code = Column(String(30), unique=True, nullable=False)
    start_point = Column(String(150), nullable=False)
    end_point = Column(String(150), nullable=False)
    distance_km = Column(Float, default=15.0, nullable=False)
    monthly_fee = Column(Numeric(12, 2, asdecimal=False), default=2500.0, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    pickup_time = Column(String(20), nullable=True)
    drop_time = Column(String(20), nullable=True)
    status = Column(String(20), default="Active", nullable=False, index=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="routes")
    stops = relationship("TransportStop", back_populates="route", cascade="all, delete-orphan", order_by="TransportStop.stop_order")
    passengers = relationship("TransportPassenger", back_populates="route")

    __table_args__ = (
        CheckConstraint("distance_km >= 0 AND monthly_fee >= 0", name="ck_route_nonneg"),
    )

    def __repr__(self):
        return f"<TransportRoute {self.route_code}: {self.route_name}>"


class TransportStop(Base, TimestampMixin, SoftDeleteMixin):
    """Represents an intermediate boarding/drop-off stage along a route."""
    __tablename__ = "transport_stops"

    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    stop_name = Column(String(150), nullable=False)
    stop_order = Column(Integer, default=1, nullable=False)
    pickup_time = Column(String(20), nullable=True)
    drop_time = Column(String(20), nullable=True)
    fare = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)

    # Relationships
    route = relationship("TransportRoute", back_populates="stops")
    passengers = relationship("TransportPassenger", back_populates="stop")

    __table_args__ = (
        CheckConstraint("stop_order >= 0 AND fare >= 0", name="ck_stop_nonneg"),
    )

    def __repr__(self):
        return f"<TransportStop {self.stop_order}. {self.stop_name} (Route {self.route_id})>"


class TransportPassenger(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a student, teacher, or staff allocated to a bus route and seat."""
    __tablename__ = "transport_passengers"

    passenger_type = Column(String(20), default="Student", nullable=False)  # "Student", "Teacher", "Staff"
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="RESTRICT"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    stop_id = Column(Integer, ForeignKey("transport_stops.id", ondelete="SET NULL"), nullable=True, index=True)
    seat_number = Column(String(20), nullable=True)
    allocation_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    monthly_fare = Column(Numeric(12, 2, asdecimal=False), default=2500.0, nullable=False)
    status = Column(String(20), default="Active", nullable=False, index=True)  # "Active", "Suspended", "Cancelled"
    remarks = Column(Text, nullable=True)

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    route = relationship("TransportRoute", back_populates="passengers")
    vehicle = relationship("Vehicle", back_populates="passengers")
    stop = relationship("TransportStop", back_populates="passengers")

    __table_args__ = (
        CheckConstraint("monthly_fare >= 0", name="ck_passenger_fare_nonneg"),
        Index("idx_transport_pax_route_status", "route_id", "status"),
        Index("idx_transport_pax_vehicle_status", "vehicle_id", "status"),
    )

    def __repr__(self):
        return f"<TransportPassenger {self.passenger_type} -> Route {self.route_id} ({self.status})>"
