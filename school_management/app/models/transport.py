"""
EduManage Pro - Transport & Fleet Management ORM Models
Phase 11: Vehicles, Routes, Stops & Passenger Route Allocations
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Vehicle(Base):
    """Represents a school bus, van, or fleet vehicle."""
    __tablename__ = "transport_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "DHAKA-METRO-CHA-11-2045"
    vehicle_model = Column(String(100), nullable=False)                          # e.g., "Tata Marcopolo 42-Seater"
    vehicle_type = Column(String(50), default="Bus")                             # "Bus", "Minibus", "Van"
    seating_capacity = Column(Integer, nullable=False, default=40)
    driver_name = Column(String(150), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    driver_license = Column(String(50), nullable=True)
    helper_name = Column(String(150), nullable=True)
    helper_phone = Column(String(50), nullable=True)
    insurance_expiry = Column(String(20), nullable=True)                         # YYYY-MM-DD
    fitness_expiry = Column(String(20), nullable=True)                           # YYYY-MM-DD
    status = Column(String(30), default="Active")                                # "Active", "Maintenance", "Out of Service"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    routes = relationship("TransportRoute", back_populates="vehicle")
    passengers = relationship("TransportPassenger", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.vehicle_number} ({self.vehicle_model}) Capacity: {self.seating_capacity}>"


class TransportRoute(Base):
    """Represents a school transit route with origin, destination, and monthly fare."""
    __tablename__ = "transport_routes"

    id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String(150), unique=True, nullable=False, index=True)   # e.g., "Route 01: Uttara - Mirpur - Dhanmondi"
    route_code = Column(String(30), unique=True, nullable=False)                # e.g., "RT-01"
    start_point = Column(String(150), nullable=False)                            # e.g., "Uttara Sector 14"
    end_point = Column(String(150), nullable=False)                              # e.g., "School Main Campus"
    distance_km = Column(Float, default=15.0)
    monthly_fee = Column(Float, default=2500.0)                                  # Monthly transport charge
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id"), nullable=True)
    pickup_time = Column(String(20), nullable=True)                              # e.g., "06:45 AM"
    drop_time = Column(String(20), nullable=True)                                # e.g., "02:30 PM"
    status = Column(String(20), default="Active")                                # "Active", "Inactive"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="routes")
    stops = relationship("TransportStop", back_populates="route", cascade="all, delete-orphan", order_by="TransportStop.stop_order")
    passengers = relationship("TransportPassenger", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TransportRoute {self.route_code}: {self.route_name}>"


class TransportStop(Base):
    """Represents an intermediate boarding/drop-off stage along a route."""
    __tablename__ = "transport_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id"), nullable=False)
    stop_name = Column(String(150), nullable=False)                              # e.g., "House Building / Azampur"
    stop_order = Column(Integer, default=1)                                      # Sequential 1, 2, 3...
    pickup_time = Column(String(20), nullable=True)                              # e.g., "07:05 AM"
    drop_time = Column(String(20), nullable=True)                                # e.g., "02:50 PM"
    fare = Column(Float, default=0.0)                                            # Stage specific fare override

    # Relationships
    route = relationship("TransportRoute", back_populates="stops")
    passengers = relationship("TransportPassenger", back_populates="stop")

    def __repr__(self):
        return f"<TransportStop {self.stop_order}. {self.stop_name} (Route {self.route_id})>"


class TransportPassenger(Base):
    """Represents a student or teacher allocated to a bus route and seat."""
    __tablename__ = "transport_passengers"

    id = Column(Integer, primary_key=True, index=True)
    passenger_type = Column(String(20), default="Student")                       # "Student", "Teacher", "Staff"
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id"), nullable=True)
    stop_id = Column(Integer, ForeignKey("transport_stops.id"), nullable=True)
    seat_number = Column(String(20), nullable=True)                              # e.g., "Seat 14A"
    allocation_date = Column(String(20), nullable=False)                         # YYYY-MM-DD
    monthly_fare = Column(Float, default=2500.0)
    status = Column(String(20), default="Active")                                # "Active", "Suspended", "Cancelled"
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    route = relationship("TransportRoute", back_populates="passengers")
    vehicle = relationship("Vehicle", back_populates="passengers")
    stop = relationship("TransportStop", back_populates="passengers")

    def __repr__(self):
        return f"<TransportPassenger {self.passenger_type} -> Route {self.route_id} ({self.status})>"
