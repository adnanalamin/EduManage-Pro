"""
EduManage Pro - Advanced Transport & Fleet Management Unit Tests
Covers Bus/Van/Microbus/Other vehicles, registration/driver/helper tracking,
routes & pickup points, commuter fees, fuel efficiency, maintenance & reminders,
insurance & documents vault, hardware-optional GPS integration, and Excel/PDF reports.
"""

from datetime import date, timedelta
import os
import tempfile
import pytest

from app.models.transport import (
    VEHICLE_TYPES,
    Vehicle,
    TransportRoute,
    TransportStop,
    TransportPassenger,
    TransportFeeCharge,
    TransportFuelLog,
    TransportMaintenanceLog,
    TransportInsurance,
    TransportDocument,
    TransportGPSDevice,
    TransportGPSPing,
)
from app.repositories.transport_repository import TransportRepository
from app.services.transport_service import TransportService, GPSIntegrationManager
from app.reports.transport_reports_pdf import TransportReportsPDFGenerator


def test_vehicle_types_and_registration_tracking(db_session):
    """Verify Bus, Van, Microbus, and Other vehicle registration, crew, and odometer fields."""
    assert set(VEHICLE_TYPES) == {"Bus", "Van", "Microbus", "Other"}

    created = []
    for idx, v_type in enumerate(VEHICLE_TYPES, start=1):
        v = TransportRepository.create_vehicle(
            session=db_session,
            vehicle_number=f"REG-TEST-{idx:02d}",
            vehicle_model=f"Model {v_type}",
            vehicle_type=v_type,
            seating_capacity=12 * idx,
            registration_no=f"BRTA-2026-{idx:03d}",
            registration_expiry="2027-12-31",
            chassis_no=f"CHS-{idx:05d}",
            engine_no=f"ENG-{idx:05d}",
            fuel_type="Diesel" if v_type == "Bus" else "Petrol",
            current_odometer_km=10000.0 + idx * 500.0,
            driver_name=f"Driver {idx}",
            driver_phone=f"0170000000{idx}",
            driver_license=f"DL-00{idx}",
            helper_name=f"Helper {idx}",
            helper_phone=f"0180000000{idx}",
        )
        created.append(v)

    assert len(created) == 4
    buses = TransportRepository.get_vehicles(db_session, vehicle_type="Bus")
    assert any(b.vehicle_number == "REG-TEST-01" for b in buses)
    microbuses = TransportRepository.get_vehicles(db_session, vehicle_type="Microbus")
    assert any(m.vehicle_number == "REG-TEST-03" for m in microbuses)


def test_route_pickup_points_and_fee_billing_cycle(db_session):
    """Verify route pickup points, student allocation, monthly billing, partial/full payment & waiver."""
    v = TransportRepository.create_vehicle(
        session=db_session,
        vehicle_number="VAN-FEE-01",
        vehicle_model="HiAce Commuter",
        vehicle_type="Van",
        seating_capacity=14,
        driver_name="Karim",
        driver_phone="01711112222",
    )
    route = TransportRepository.create_route(
        session=db_session,
        route_code="RT-FEE-01",
        route_name="Gulshan - Campus Shuttle",
        start_point="Gulshan 2",
        end_point="School Campus",
        distance_km=11.0,
        monthly_fee=3000.0,
        vehicle_id=v.id,
        stops=[
            {"stop_name": "Gulshan 2 Circle", "stop_order": 1, "pickup_time": "07:00 AM", "fare": 3000.0},
            {"stop_name": "Banani Bridge", "stop_order": 2, "pickup_time": "07:15 AM", "fare": 2600.0},
        ],
    )
    assert len(route.stops) == 2

    pax1, err1 = TransportRepository.allocate_passenger(
        session=db_session,
        passenger_type="Student",
        student_id=5001,
        route_id=route.id,
        stop_id=route.stops[1].id,
        allocation_date=date.today().isoformat(),
    )
    assert err1 is None
    assert pax1.pass_code is not None
    assert float(pax1.monthly_fare) == 2600.0

    pax2, err2 = TransportRepository.allocate_passenger(
        session=db_session,
        passenger_type="Staff",
        staff_id=6001,
        route_id=route.id,
        allocation_date=date.today().isoformat(),
        monthly_fare=1000.0,
    )
    assert err2 is None

    # Generate monthly bills idempotently
    bill_res = TransportRepository.generate_monthly_fees(db_session, billing_month="2026-11", route_id=route.id)
    assert bill_res["created"] == 2
    bill_res_dup = TransportRepository.generate_monthly_fees(db_session, billing_month="2026-11", route_id=route.id)
    assert bill_res_dup["created"] == 0

    charges = TransportRepository.get_fee_charges(db_session, billing_month="2026-11", route_id=route.id)
    assert len(charges) == 2

    c_student = next(c for c in charges if c.passenger_id == pax1.id)
    updated, p_err = TransportRepository.record_fee_payment(
        db_session, c_student.id, amount=1000.0, payment_method="Mobile Banking", discount=200.0
    )
    assert p_err is None
    assert updated.status == "Partial"
    assert updated.balance_due == 1400.0

    updated, p_err2 = TransportRepository.record_fee_payment(
        db_session, c_student.id, amount=1400.0, payment_method="Cash"
    )
    assert p_err2 is None
    assert updated.status == "Paid"
    assert updated.receipt_no is not None

    c_staff = next(c for c in charges if c.passenger_id == pax2.id)
    waived = TransportRepository.waive_fee_charge(db_session, c_staff.id, remarks="Staff welfare benefit")
    assert waived.status == "Waived"
    assert waived.balance_due == 0.0


def test_fuel_maintenance_insurance_docs_and_reminders(db_session):
    """Verify fuel efficiency calculation, maintenance logs, insurance, documents & automated reminders."""
    today = date.today()
    v = TransportRepository.create_vehicle(
        session=db_session,
        vehicle_number="BUS-MNT-01",
        vehicle_model="Tata CityBus",
        vehicle_type="Bus",
        seating_capacity=40,
        current_odometer_km=50000.0,
        driver_name="Salim",
        driver_phone="01755556666",
        fitness_expiry=(today + timedelta(days=10)).isoformat(),
    )

    # Fuel log advances odometer and computes km/L
    fuel, f_err = TransportRepository.add_fuel_log(
        session=db_session,
        vehicle_id=v.id,
        fill_date=today.isoformat(),
        liters=50.0,
        price_per_liter=110.0,
        odometer_km=50400.0,
        station_name="Padma Filling Station",
    )
    assert f_err is None
    assert fuel.distance_covered_km == 400.0
    assert fuel.km_per_liter == 8.0
    assert float(fuel.total_cost) == 5500.0

    # Maintenance log sets next service odometer 50700 (within 500km buffer -> Due Soon)
    maint, m_err = TransportRepository.add_maintenance_log(
        session=db_session,
        vehicle_id=v.id,
        service_type="Engine Oil & Filter",
        service_date=today.isoformat(),
        workshop_name="City Motors",
        cost=8500.0,
        odometer_km=50400.0,
        next_service_date=(today - timedelta(days=2)).isoformat(),  # Overdue date for reminder verification
        next_service_odometer_km=50700.0,
        status="Completed",
    )
    assert m_err is None

    # Expiring Insurance & Document
    ins, i_err = TransportRepository.add_insurance(
        session=db_session,
        vehicle_id=v.id,
        policy_number="POL-TEST-99",
        provider="Green Delta Insurance",
        start_date=(today - timedelta(days=340)).isoformat(),
        expiry_date=(today + timedelta(days=15)).isoformat(),
        premium_amount=18000.0,
    )
    assert i_err is None

    doc, d_err = TransportRepository.add_document(
        session=db_session,
        vehicle_id=v.id,
        document_type="Route Permit",
        document_number="RP-2026-11",
        expiry_date=(today - timedelta(days=5)).isoformat(),
    )
    assert d_err is None
    assert doc.status == "Expired"

    reminders = TransportRepository.get_maintenance_reminders(db_session, horizon_days=30, vehicle_id=v.id, reference_date=today)
    categories = {r["category"] for r in reminders}
    severities = {r["severity"] for r in reminders}
    assert "Overdue" in severities
    assert "Due Soon" in severities
    assert "Insurance" in categories
    assert "Fitness" in categories
    assert "Route Permit" in categories


def test_hardware_optional_gps_architecture(db_session):
    """Verify transport operates cleanly without GPS hardware and ingests optional manual/webhook telemetry."""
    v = TransportRepository.create_vehicle(
        session=db_session,
        vehicle_number="MICRO-GPS-01",
        vehicle_model="Toyota Coaster",
        vehicle_type="Microbus",
        seating_capacity=24,
        driver_name="Hasan",
        driver_phone="01788889999",
    )

    # Zero GPS hardware registered -> snapshot still works cleanly in hardware-free mode
    snaps = TransportRepository.get_latest_vehicle_positions(db_session)
    target = next(s for s in snaps if s["vehicle_id"] == v.id)
    assert "Hardware-Free" in target["gps_mode"]
    assert target["latitude"] is None

    # Manual check-in works without registering any hardware tracker
    p_manual, m_err = GPSIntegrationManager.record_manual_checkin(
        session=db_session,
        vehicle_id=v.id,
        latitude=23.8103,
        longitude=90.4125,
        location_label="Departed Uttara Gate",
        speed_kmh=25.0,
        odometer_km=12345.0,
    )
    assert m_err is None
    assert p_manual.source == "Manual"

    # Optional hardware adapter registration & webhook payload ingestion
    dev = TransportRepository.register_gps_device(
        session=db_session,
        device_code="GPS-OBD-101",
        vehicle_id=v.id,
        provider_type="Webhook_API",
        imei_or_serial="861234567890123",
        is_enabled=True,
    )
    assert dev.is_mandatory is False

    ping, w_err = GPSIntegrationManager.ingest_device_payload(
        db_session,
        device_code="GPS-OBD-101",
        payload={"lat": 23.7925, "lng": 90.4078, "speed": 42.0, "odometer_km": 12360.0},
    )
    assert w_err is None
    assert ping.source == "Webhook_API"
    assert db_session.query(Vehicle).filter(Vehicle.id == v.id).first().current_odometer_km == 12360.0


def test_fleet_excel_and_pdf_exports(db_session):
    """Verify multi-sheet fleet Excel workbook, fees Excel, and PDF fleet/fee reports."""
    TransportService.seed_default_transport_data(db_session)
    with tempfile.TemporaryDirectory() as tmpdir:
        fleet_xlsx = os.path.join(tmpdir, "fleet.xlsx")
        fees_xlsx = os.path.join(tmpdir, "fees.xlsx")
        fleet_pdf = os.path.join(tmpdir, "fleet.pdf")
        fees_pdf = os.path.join(tmpdir, "fees.pdf")

        TransportService.export_fleet_operations_excel(db_session, fleet_xlsx)
        TransportService.export_transport_fees_excel(db_session, None, fees_xlsx)
        TransportReportsPDFGenerator.generate_maintenance_fuel_report(
            TransportRepository.get_vehicles(db_session),
            TransportRepository.get_fuel_logs(db_session),
            TransportRepository.get_maintenance_logs(db_session),
            TransportRepository.get_maintenance_reminders(db_session),
            None,
            fleet_pdf,
        )
        TransportReportsPDFGenerator.generate_fee_collection_report(
            TransportRepository.get_fee_charges(db_session),
            None,
            None,
            fees_pdf,
        )

        for path in (fleet_xlsx, fees_xlsx, fleet_pdf, fees_pdf):
            assert os.path.exists(path)
            assert os.path.getsize(path) > 500
