"""
EduManage Pro - Transport & Fleet Management ORM Models
Enterprise Fleet Vehicles (Bus, Van, Microbus, Other), Registrations, Crew,
Transit Routes & Pickup Points, Passenger Seat Allocations, Transport Fees,
Fuel Logs, Maintenance Logs & Reminders, Insurance Policies, Documents Vault,
and Hardware-Optional Future GPS Integration Architecture.
"""

from typing import List
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, utc_now


VEHICLE_TYPES: List[str] = ["Bus", "Van", "Microbus", "Other"]

DOCUMENT_TYPES: List[str] = [
    "Registration",
    "Fitness",
    "Route Permit",
    "Tax Token",
    "Insurance",
    "Pollution",
    "Driver License",
    "Other",
]

MAINTENANCE_SERVICE_TYPES: List[str] = [
    "General Inspection",
    "Engine Oil & Filter",
    "Brake Service",
    "Tire Replacement / Alignment",
    "Battery & Electrical",
    "AC & Cooling",
    "Suspension & Steering",
    "Transmission Service",
    "Body & Paint Repair",
    "Annual Overhaul",
    "Other",
]

GPS_PROVIDER_TYPES: List[str] = [
    "Manual",
    "SIM_GPS",
    "OBD_II",
    "Webhook_API",
    "MQTT",
    "Simulated",
]


class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a school bus, van, microbus, or other fleet vehicle."""
    __tablename__ = "transport_vehicles"

    vehicle_number = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_model = Column(String(100), nullable=False)
    vehicle_type = Column(String(50), default="Bus", nullable=False)  # Bus, Van, Microbus, Other (Minibus legacy supported)
    seating_capacity = Column(Integer, nullable=False, default=40)

    # Registration & Mechanical Specs
    registration_no = Column(String(80), nullable=True, index=True)
    registration_expiry = Column(String(20), nullable=True)  # YYYY-MM-DD
    chassis_no = Column(String(80), nullable=True)
    engine_no = Column(String(80), nullable=True)
    manufacture_year = Column(Integer, nullable=True)
    fuel_type = Column(String(30), default="Diesel", nullable=False)  # Diesel, Petrol, CNG, Octane, Electric, Hybrid
    current_odometer_km = Column(Float, default=0.0, nullable=False)

    # Assigned Driver & Helper Crew
    driver_name = Column(String(150), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    driver_license = Column(String(50), nullable=True)
    driver_license_expiry = Column(String(20), nullable=True)  # YYYY-MM-DD
    driver_staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)

    helper_name = Column(String(150), nullable=True)
    helper_phone = Column(String(50), nullable=True)
    helper_staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True, index=True)

    # Compliance & Maintenance Summary Dates
    insurance_expiry = Column(String(20), nullable=True)  # YYYY-MM-DD
    fitness_expiry = Column(String(20), nullable=True)    # YYYY-MM-DD
    last_service_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    next_service_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    next_service_odometer_km = Column(Float, nullable=True)

    status = Column(String(30), default="Active", nullable=False, index=True)  # Active, Maintenance, Out of Service
    notes = Column(Text, nullable=True)

    # Relationships
    driver_staff = relationship("Staff", foreign_keys=[driver_staff_id])
    helper_staff = relationship("Staff", foreign_keys=[helper_staff_id])
    routes = relationship("TransportRoute", back_populates="vehicle")
    passengers = relationship("TransportPassenger", back_populates="vehicle")
    fuel_logs = relationship(
        "TransportFuelLog",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="TransportFuelLog.fill_date.desc(), TransportFuelLog.id.desc()",
    )
    maintenance_logs = relationship(
        "TransportMaintenanceLog",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="TransportMaintenanceLog.service_date.desc(), TransportMaintenanceLog.id.desc()",
    )
    insurances = relationship(
        "TransportInsurance",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="TransportInsurance.expiry_date.desc(), TransportInsurance.id.desc()",
    )
    documents = relationship(
        "TransportDocument",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="TransportDocument.id.desc()",
    )
    gps_devices = relationship("TransportGPSDevice", back_populates="vehicle")
    gps_pings = relationship(
        "TransportGPSPing",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="TransportGPSPing.recorded_at.desc(), TransportGPSPing.id.desc()",
    )

    __table_args__ = (
        CheckConstraint("seating_capacity > 0 AND current_odometer_km >= 0", name="ck_vehicle_capacity_pos"),
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
    notes = Column(Text, nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="routes")
    stops = relationship(
        "TransportStop",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="TransportStop.stop_order",
    )
    passengers = relationship("TransportPassenger", back_populates="route")

    __table_args__ = (
        CheckConstraint("distance_km >= 0 AND monthly_fee >= 0", name="ck_route_nonneg"),
    )

    def __repr__(self):
        return f"<TransportRoute {self.route_code}: {self.route_name}>"


class TransportStop(Base, TimestampMixin, SoftDeleteMixin):
    """Represents a pickup/drop-off point along a route."""
    __tablename__ = "transport_stops"

    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    stop_name = Column(String(150), nullable=False)
    stop_order = Column(Integer, default=1, nullable=False)
    pickup_time = Column(String(20), nullable=True)
    drop_time = Column(String(20), nullable=True)
    fare = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    landmark = Column(String(150), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

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
    pass_code = Column(String(40), unique=True, nullable=True, index=True)
    qr_payload = Column(String(255), nullable=True)
    pickup_address = Column(String(255), nullable=True)
    status = Column(String(20), default="Active", nullable=False, index=True)  # "Active", "Suspended", "Cancelled"
    remarks = Column(Text, nullable=True)

    # Relationships
    student = relationship("Student")
    teacher = relationship("Teacher")
    staff = relationship("Staff")
    route = relationship("TransportRoute", back_populates="passengers")
    vehicle = relationship("Vehicle", back_populates="passengers")
    stop = relationship("TransportStop", back_populates="passengers")
    fee_charges = relationship(
        "TransportFeeCharge",
        back_populates="passenger",
        cascade="all, delete-orphan",
        order_by="TransportFeeCharge.billing_month.desc(), TransportFeeCharge.id.desc()",
    )

    __table_args__ = (
        CheckConstraint("monthly_fare >= 0", name="ck_passenger_fare_nonneg"),
        Index("idx_transport_pax_route_status", "route_id", "status"),
        Index("idx_transport_pax_vehicle_status", "vehicle_id", "status"),
    )

    def __repr__(self):
        return f"<TransportPassenger {self.passenger_type} -> Route {self.route_id} ({self.status})>"


class TransportFeeCharge(Base, TimestampMixin, SoftDeleteMixin):
    """Monthly or periodic transport fee charge & payment collection record per commuter."""
    __tablename__ = "transport_fee_charges"

    passenger_id = Column(Integer, ForeignKey("transport_passengers.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    billing_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    due_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    discount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    paid_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    status = Column(String(20), default="Pending", nullable=False, index=True)  # Pending, Partial, Paid, Waived
    payment_method = Column(String(30), nullable=True)
    receipt_no = Column(String(60), unique=True, nullable=True, index=True)
    paid_date = Column(String(20), nullable=True)
    collected_by = Column(String(80), nullable=True)
    remarks = Column(Text, nullable=True)

    passenger = relationship("TransportPassenger", back_populates="fee_charges")
    student = relationship("Student")
    route = relationship("TransportRoute")

    __table_args__ = (
        UniqueConstraint("passenger_id", "billing_month", name="uq_transport_fee_pax_month"),
        CheckConstraint("amount >= 0 AND discount >= 0 AND paid_amount >= 0", name="ck_transport_fee_nonneg"),
        Index("idx_transport_fee_month_status", "billing_month", "status"),
    )

    @property
    def net_payable(self) -> float:
        return max(0.0, float(self.amount or 0.0) - float(self.discount or 0.0))

    @property
    def balance_due(self) -> float:
        if self.status == "Waived":
            return 0.0
        return max(0.0, self.net_payable - float(self.paid_amount or 0.0))


class TransportFuelLog(Base, TimestampMixin, SoftDeleteMixin):
    """Fuel refill & mileage efficiency log for a fleet vehicle."""
    __tablename__ = "transport_fuel_logs"

    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    fill_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    fuel_type = Column(String(30), default="Diesel", nullable=False)
    liters = Column(Float, nullable=False)
    price_per_liter = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    total_cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    previous_odometer_km = Column(Float, nullable=True)
    odometer_km = Column(Float, nullable=False)
    station_name = Column(String(150), nullable=True)
    receipt_no = Column(String(60), nullable=True)
    filled_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="fuel_logs")

    __table_args__ = (
        CheckConstraint("liters > 0 AND total_cost >= 0 AND odometer_km >= 0", name="ck_transport_fuel_pos"),
        Index("idx_transport_fuel_vehicle_date", "vehicle_id", "fill_date"),
    )

    @property
    def distance_covered_km(self) -> float:
        if self.previous_odometer_km is not None and self.odometer_km > self.previous_odometer_km:
            return round(self.odometer_km - self.previous_odometer_km, 2)
        return 0.0

    @property
    def km_per_liter(self) -> float:
        dist = self.distance_covered_km
        if dist > 0 and self.liters > 0:
            return round(dist / self.liters, 2)
        return 0.0


class TransportMaintenanceLog(Base, TimestampMixin, SoftDeleteMixin):
    """Vehicle service, repair, inspection, and next-due reminder tracking."""
    __tablename__ = "transport_maintenance_logs"

    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    service_type = Column(String(80), nullable=False, index=True)
    service_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    workshop_name = Column(String(150), nullable=True)
    cost = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    odometer_km = Column(Float, default=0.0, nullable=False)
    next_service_date = Column(String(20), nullable=True, index=True)  # YYYY-MM-DD
    next_service_odometer_km = Column(Float, nullable=True)
    invoice_no = Column(String(60), nullable=True)
    status = Column(String(30), default="Completed", nullable=False, index=True)  # Scheduled, In Progress, Completed
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="maintenance_logs")

    __table_args__ = (
        CheckConstraint("cost >= 0 AND odometer_km >= 0", name="ck_transport_maint_nonneg"),
        Index("idx_transport_maint_vehicle_date", "vehicle_id", "service_date"),
    )


class TransportInsurance(Base, TimestampMixin, SoftDeleteMixin):
    """Vehicle insurance policy records with expiry tracking."""
    __tablename__ = "transport_insurances"

    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_number = Column(String(80), nullable=False, index=True)
    provider = Column(String(150), nullable=False)
    coverage_type = Column(String(50), default="Comprehensive", nullable=False)
    start_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    expiry_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    premium_amount = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    insured_value = Column(Numeric(12, 2, asdecimal=False), default=0.0, nullable=False)
    status = Column(String(30), default="Active", nullable=False, index=True)  # Active, Expired, Cancelled
    document_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="insurances")

    __table_args__ = (
        CheckConstraint("premium_amount >= 0 AND insured_value >= 0", name="ck_transport_ins_nonneg"),
    )


class TransportDocument(Base, TimestampMixin, SoftDeleteMixin):
    """Vehicle & driver compliance document vault (Registration, Fitness, Permit, Tax Token, etc.)."""
    __tablename__ = "transport_documents"

    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(60), nullable=False, index=True)
    document_number = Column(String(80), nullable=True)
    issuing_authority = Column(String(120), nullable=True)
    issue_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    expiry_date = Column(String(20), nullable=True, index=True)  # YYYY-MM-DD
    file_path = Column(String(255), nullable=True)
    status = Column(String(30), default="Valid", nullable=False, index=True)  # Valid, Expiring Soon, Expired
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="documents")


class TransportGPSDevice(Base, TimestampMixin, SoftDeleteMixin):
    """
    Optional GPS telematics tracker registry for vehicles.
    Hardware is strictly non-mandatory; transport operations run cleanly without GPS hardware.
    """
    __tablename__ = "transport_gps_devices"

    device_code = Column(String(60), unique=True, nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_type = Column(String(40), default="Manual", nullable=False)  # Manual, SIM_GPS, OBD_II, Webhook_API, MQTT, Simulated
    imei_or_serial = Column(String(80), nullable=True)
    endpoint_url = Column(String(255), nullable=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    status = Column(String(30), default="Standby", nullable=False, index=True)  # Standby, Online, Offline, Disabled
    last_ping_at = Column(DateTime(timezone=True), nullable=True)
    config_json = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="gps_devices")
    pings = relationship("TransportGPSPing", back_populates="device")


class TransportGPSPing(Base, TimestampMixin):
    """Telemetry coordinate history ingested from optional GPS hardware or manual check-ins."""
    __tablename__ = "transport_gps_pings"

    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("transport_gps_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id = Column(Integer, ForeignKey("transport_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0, nullable=False)
    heading_deg = Column(Float, nullable=True)
    ignition_on = Column(Boolean, default=True, nullable=False)
    odometer_km = Column(Float, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    source = Column(String(40), default="Manual", nullable=False)
    location_label = Column(String(150), nullable=True)
    raw_payload = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="gps_pings")
    device = relationship("TransportGPSDevice", back_populates="pings")
    route = relationship("TransportRoute")

    __table_args__ = (
        Index("idx_transport_gps_vehicle_time", "vehicle_id", "recorded_at"),
    )
