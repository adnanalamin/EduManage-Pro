"""
EduManage Pro - Transport & Fleet Management Unit Tests
Phase 11: Vehicles, Route Network, Passenger Allocations, openpyxl Excel & ReportLab PDF
"""

import os
import tempfile
from datetime import date
import pytest
from app.models.transport import Vehicle, TransportRoute, TransportStop, TransportPassenger
from app.models.student import Student
from app.repositories.transport_repository import TransportRepository
from app.services.transport_service import TransportService
from app.reports.bus_pass_pdf import BusPassGenerator
from app.reports.route_manifest_pdf import RouteManifestPDFGenerator


def test_seed_transport_fleet_and_routes(db_session):
    """Verify fleet vehicles, transit routes, stops, and initial passenger seed cleanly."""
    res = TransportService.seed_default_transport_data(db_session)
    assert res["vehicles_seeded"] >= 3 or db_session.query(Vehicle).count() >= 3
    assert db_session.query(TransportRoute).count() >= 3

    r1 = db_session.query(TransportRoute).filter(TransportRoute.route_code == "RT-01").first()
    assert r1 is not None
    assert len(r1.stops) >= 4
    assert r1.vehicle_id is not None


def test_vehicle_crud_operations(db_session):
    """Verify fleet vehicle registration, capacity tracking, and status modification."""
    v = TransportRepository.create_vehicle(
        session=db_session,
        vehicle_number="DHK-TEST-CHA-99-9999",
        vehicle_model="Isuzu Journey 30-Seater",
        vehicle_type="Minibus",
        seating_capacity=30,
        driver_name="Test Driver",
        driver_phone="+880 1700-000000",
        status="Active"
    )
    assert v.id is not None
    assert v.seating_capacity == 30

    updated = TransportRepository.update_vehicle(db_session, v.id, status="Maintenance", seating_capacity=32)
    assert updated.status == "Maintenance"
    assert updated.seating_capacity == 32


def test_passenger_allocation_and_capacity_limits(db_session):
    """Verify commuter seat allocation, capacity cap enforcement, and duplicate check."""
    # Create small test vehicle with capacity 1
    v = TransportRepository.create_vehicle(
        session=db_session,
        vehicle_number="DHK-MINI-01",
        vehicle_model="Microbus 1-Seater Test",
        vehicle_type="Van",
        seating_capacity=1,
        driver_name="Mini Driver",
        driver_phone="+880 1700-111111",
        status="Active"
    )

    r = TransportRepository.create_route(
        session=db_session,
        route_code="RT-TEST",
        route_name="Test Route Limited",
        start_point="Point A",
        end_point="Point B",
        monthly_fee=1500.0,
        vehicle_id=v.id
    )

    today_str = date.today().isoformat()

    # Passenger 1: Should succeed
    p1, err1 = TransportRepository.allocate_passenger(
        session=db_session,
        passenger_type="Student",
        student_id=101,
        route_id=r.id,
        vehicle_id=v.id,
        seat_number="Seat 01",
        allocation_date=today_str,
        monthly_fare=1500.0
    )
    assert err1 is None
    assert p1 is not None
    assert p1.status == "Active"

    # Passenger 2: Should fail because vehicle is fully booked (1/1 seats)
    p2, err2 = TransportRepository.allocate_passenger(
        session=db_session,
        passenger_type="Student",
        student_id=102,
        route_id=r.id,
        vehicle_id=v.id,
        seat_number="Seat 02",
        allocation_date=today_str,
        monthly_fare=1500.0
    )
    assert p2 is None
    assert "fully booked" in err2

    # Attempt duplicate allocation of student 101 to another route
    r2 = TransportRepository.create_route(
        session=db_session,
        route_code="RT-TEST-2",
        route_name="Second Test Route",
        start_point="Point C",
        end_point="Point D",
        monthly_fee=1800.0
    )
    p3, err3 = TransportRepository.allocate_passenger(
        session=db_session,
        passenger_type="Student",
        student_id=101,
        route_id=r2.id,
        allocation_date=today_str
    )
    assert p3 is None
    assert "already allocated" in err3


def test_openpyxl_manifest_export(db_session):
    """Verify openpyxl passenger manifest export builds valid spreadsheet."""
    TransportService.seed_default_transport_data(db_session)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        out_path = tf.name

    try:
        saved_path = TransportService.export_passengers_excel(db_session, None, out_path)
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 1000
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_transport_reports_pdf_generation(db_session):
    """Verify ReportLab printable CR80 bus pass and landscape A4 route manifest PDFs."""
    TransportService.seed_default_transport_data(db_session)
    passenger = db_session.query(TransportPassenger).first()
    assert passenger is not None

    route = db_session.query(TransportRoute).first()
    assert route is not None

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_pass:
        pass_path = tf_pass.name

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf_manifest:
        manifest_path = tf_manifest.name

    try:
        # 1. CR80 School Bus Pass
        p_res = BusPassGenerator.generate_single_pass(passenger, None, pass_path)
        assert os.path.exists(p_res)
        assert os.path.getsize(p_res) > 500

        # 2. Route Roll Sheet Manifest
        passengers = TransportRepository.get_passengers(db_session, route_id=route.id)
        m_res = RouteManifestPDFGenerator.generate_manifest(route, passengers, None, manifest_path)
        assert os.path.exists(m_res)
        assert os.path.getsize(m_res) > 1000
    finally:
        if os.path.exists(pass_path):
            os.remove(pass_path)
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
