"""
EduManage Pro - Transport Service
Fleet Seeding, Route Network, Hardware-Optional GPS Integration Architecture,
and openpyxl Excel Exports (Passenger Manifest, Fleet Fuel & Maintenance, Transport Fees).
"""

from abc import ABC, abstractmethod
import json
import os
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.transport import (
    Vehicle,
    TransportRoute,
    TransportStop,
    TransportPassenger,
    TransportGPSDevice,
    TransportGPSPing,
)
from app.models.student import Student
from app.models.staff import Teacher
from app.repositories.transport_repository import TransportRepository


DEFAULT_VEHICLES = [
    {
        "vehicle_number": "DHK-METRO-CHA-11-2041",
        "vehicle_model": "Tata Marcopolo CityBus 42-S",
        "vehicle_type": "Bus",
        "seating_capacity": 42,
        "registration_no": "BRTA-DHK-2041",
        "registration_expiry": "2027-06-30",
        "fuel_type": "Diesel",
        "current_odometer_km": 48250.0,
        "driver_name": "Rafiqul Islam (Driver)",
        "driver_phone": "+880 1711-234567",
        "driver_license": "DL-DHK-88412",
        "helper_name": "Billal Hossain",
        "helper_phone": "+880 1812-334455",
        "insurance_expiry": "2026-12-31",
        "fitness_expiry": "2026-10-15",
        "status": "Active",
    },
    {
        "vehicle_number": "DHK-METRO-CHA-11-2042",
        "vehicle_model": "Ashok Leyland Falcon 38-S",
        "vehicle_type": "Bus",
        "seating_capacity": 38,
        "registration_no": "BRTA-DHK-2042",
        "registration_expiry": "2027-05-15",
        "fuel_type": "Diesel",
        "current_odometer_km": 51900.0,
        "driver_name": "Abdul Malek (Driver)",
        "driver_phone": "+880 1722-345678",
        "driver_license": "DL-DHK-99231",
        "helper_name": "Solaiman Miah",
        "helper_phone": "+880 1913-445566",
        "insurance_expiry": "2026-11-30",
        "fitness_expiry": "2026-09-20",
        "status": "Active",
    },
    {
        "vehicle_number": "DHK-METRO-GA-14-3015",
        "vehicle_model": "Toyota Coaster Microbus 28-S",
        "vehicle_type": "Microbus",
        "seating_capacity": 28,
        "registration_no": "BRTA-DHK-3015",
        "registration_expiry": "2027-08-20",
        "fuel_type": "CNG",
        "current_odometer_km": 32400.0,
        "driver_name": "Mizanur Rahman",
        "driver_phone": "+880 1733-456789",
        "driver_license": "DL-DHK-77124",
        "helper_name": "Jahangir Alam",
        "helper_phone": "+880 1814-556677",
        "insurance_expiry": "2027-01-15",
        "fitness_expiry": "2026-11-10",
        "status": "Active",
    },
    {
        "vehicle_number": "DHK-METRO-CHA-11-2044",
        "vehicle_model": "Toyota HiAce Commuter Van 14-S",
        "vehicle_type": "Van",
        "seating_capacity": 14,
        "registration_no": "BRTA-DHK-2044",
        "registration_expiry": "2026-12-01",
        "fuel_type": "Petrol",
        "current_odometer_km": 61200.0,
        "driver_name": "Kabir Hossain",
        "driver_phone": "+880 1744-567890",
        "driver_license": "DL-DHK-66541",
        "helper_name": "Rokonuzzaman",
        "helper_phone": "+880 1915-667788",
        "insurance_expiry": "2026-08-30",
        "fitness_expiry": "2026-06-25",
        "status": "Maintenance",
    },
]

DEFAULT_ROUTES = [
    {
        "route_code": "RT-01",
        "route_name": "Route 01: Uttara - Airport - Campus",
        "start_point": "Uttara Sector 14",
        "end_point": "School Main Campus",
        "distance_km": 14.5,
        "monthly_fee": 2500.0,
        "pickup_time": "06:45 AM",
        "drop_time": "02:30 PM",
        "vehicle_index": 0,
        "stops": [
            {"stop_name": "Uttara Sector 14 (Origin)", "stop_order": 1, "pickup_time": "06:45 AM", "drop_time": "02:30 PM", "fare": 2500.0},
            {"stop_name": "House Building / Azampur", "stop_order": 2, "pickup_time": "07:00 AM", "drop_time": "02:45 PM", "fare": 2400.0},
            {"stop_name": "Airport Intersection", "stop_order": 3, "pickup_time": "07:15 AM", "drop_time": "03:00 PM", "fare": 2200.0},
            {"stop_name": "Khilkhet Overbridge", "stop_order": 4, "pickup_time": "07:30 AM", "drop_time": "03:15 PM", "fare": 2000.0},
            {"stop_name": "School Campus Gate 1", "stop_order": 5, "pickup_time": "07:45 AM", "drop_time": "03:30 PM", "fare": 0.0},
        ],
    },
    {
        "route_code": "RT-02",
        "route_name": "Route 02: Mirpur - Agargaon - Campus",
        "start_point": "Mirpur 10 Circle",
        "end_point": "School Main Campus",
        "distance_km": 18.0,
        "monthly_fee": 2800.0,
        "pickup_time": "06:30 AM",
        "drop_time": "02:30 PM",
        "vehicle_index": 1,
        "stops": [
            {"stop_name": "Mirpur 10 Circle (Origin)", "stop_order": 1, "pickup_time": "06:30 AM", "drop_time": "02:30 PM", "fare": 2800.0},
            {"stop_name": "Mirpur 1 Bus Stand", "stop_order": 2, "pickup_time": "06:45 AM", "drop_time": "02:45 PM", "fare": 2600.0},
            {"stop_name": "Agargaon Metro Station", "stop_order": 3, "pickup_time": "07:05 AM", "drop_time": "03:05 PM", "fare": 2400.0},
            {"stop_name": "Bijoy Sarani Intersection", "stop_order": 4, "pickup_time": "07:25 AM", "drop_time": "03:25 PM", "fare": 2200.0},
            {"stop_name": "School Campus Gate 2", "stop_order": 5, "pickup_time": "07:50 AM", "drop_time": "03:45 PM", "fare": 0.0},
        ],
    },
    {
        "route_code": "RT-03",
        "route_name": "Route 03: Dhanmondi - Mohakhali - Campus",
        "start_point": "Dhanmondi Road 27",
        "end_point": "School Main Campus",
        "distance_km": 16.5,
        "monthly_fee": 3000.0,
        "pickup_time": "06:40 AM",
        "drop_time": "02:30 PM",
        "vehicle_index": 2,
        "stops": [
            {"stop_name": "Dhanmondi 27 (Origin)", "stop_order": 1, "pickup_time": "06:40 AM", "drop_time": "02:30 PM", "fare": 3000.0},
            {"stop_name": "Kalabagan Bus Stop", "stop_order": 2, "pickup_time": "06:55 AM", "drop_time": "02:45 PM", "fare": 2800.0},
            {"stop_name": "Farmgate Ananda Cinema", "stop_order": 3, "pickup_time": "07:15 AM", "drop_time": "03:05 PM", "fare": 2500.0},
            {"stop_name": "Mohakhali Flyover End", "stop_order": 4, "pickup_time": "07:35 AM", "drop_time": "03:25 PM", "fare": 2200.0},
            {"stop_name": "School Campus Gate 1", "stop_order": 5, "pickup_time": "07:50 AM", "drop_time": "03:40 PM", "fare": 0.0},
        ],
    },
]


# ==============================================================================
# HARDWARE-OPTIONAL GPS INTEGRATION ARCHITECTURE
# ==============================================================================

class GPSProviderAdapter(ABC):
    """
    Abstract integration adapter for future live GPS/telematics providers.
    Implementations never block manual fleet operations if hardware is absent.
    """

    provider_name: str = "Generic"
    requires_hardware: bool = False

    @abstractmethod
    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert vendor-specific telemetry payload into canonical GPS ping fields."""


class ManualCheckinGPSAdapter(GPSProviderAdapter):
    """Hardware-free adapter accepting dispatcher / driver check-in coordinates."""

    provider_name = "Manual"
    requires_hardware = False

    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "latitude": float(payload.get("latitude", payload.get("lat", 23.8103))),
            "longitude": float(payload.get("longitude", payload.get("lng", payload.get("lon", 90.4125)))),
            "speed_kmh": float(payload.get("speed_kmh", payload.get("speed", 0.0)) or 0.0),
            "heading_deg": float(payload["heading_deg"]) if payload.get("heading_deg") is not None else None,
            "ignition_on": bool(payload.get("ignition_on", True)),
            "odometer_km": float(payload["odometer_km"]) if payload.get("odometer_km") is not None else None,
            "location_label": payload.get("location_label") or "Manual Dispatch Check-In",
            "source": "Manual",
        }


class WebhookGPSAdapter(GPSProviderAdapter):
    """Adapter normalizing REST Webhook / SIM_GPS / OBD_II / MQTT JSON telemetry feeds."""

    provider_name = "Webhook_API"
    requires_hardware = True

    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        lat = payload.get("latitude", payload.get("lat"))
        lon = payload.get("longitude", payload.get("lng", payload.get("lon")))
        if lat is None or lon is None:
            raise ValueError("GPS payload missing latitude/longitude coordinates.")
        return {
            "latitude": float(lat),
            "longitude": float(lon),
            "speed_kmh": float(payload.get("speed_kmh", payload.get("speed", 0.0)) or 0.0),
            "heading_deg": float(payload.get("heading_deg", payload.get("heading"))) if payload.get("heading_deg", payload.get("heading")) is not None else None,
            "ignition_on": bool(payload.get("ignition_on", payload.get("ignition", True))),
            "odometer_km": float(payload["odometer_km"]) if payload.get("odometer_km") is not None else None,
            "location_label": payload.get("location_label") or payload.get("address") or "Live GPS Ping",
            "source": str(payload.get("source") or self.provider_name),
        }


class SimulatedGPSAdapter(GPSProviderAdapter):
    """Hardware-free simulated GPS adapter for integration testing and dry runs."""

    provider_name = "Simulated"
    requires_hardware = False

    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "latitude": float(payload.get("latitude", 23.7806)),
            "longitude": float(payload.get("longitude", 90.4070)),
            "speed_kmh": float(payload.get("speed_kmh", 34.5)),
            "heading_deg": float(payload.get("heading_deg", 180.0)),
            "ignition_on": bool(payload.get("ignition_on", True)),
            "odometer_km": float(payload["odometer_km"]) if payload.get("odometer_km") is not None else None,
            "location_label": payload.get("location_label") or "Simulated Campus Corridor",
            "source": "Simulated",
        }


class GPSIntegrationManager:
    """Routes incoming or manual telemetry through registered GPS adapters."""

    _ADAPTERS: Dict[str, GPSProviderAdapter] = {
        "Manual": ManualCheckinGPSAdapter(),
        "Webhook_API": WebhookGPSAdapter(),
        "SIM_GPS": WebhookGPSAdapter(),
        "OBD_II": WebhookGPSAdapter(),
        "MQTT": WebhookGPSAdapter(),
        "Simulated": SimulatedGPSAdapter(),
    }

    @classmethod
    def get_adapter(cls, provider_type: str) -> GPSProviderAdapter:
        return cls._ADAPTERS.get(provider_type, cls._ADAPTERS["Manual"])

    @classmethod
    def ingest_device_payload(
        cls,
        session: Session,
        device_code: str,
        payload: Dict[str, Any],
    ) -> Tuple[Optional[TransportGPSPing], Optional[str]]:
        device = (
            session.query(TransportGPSDevice)
            .filter(TransportGPSDevice.device_code == device_code)
            .first()
        )
        if not device:
            return None, f"GPS device '{device_code}' is not registered."
        if not device.is_enabled:
            return None, f"GPS device '{device_code}' is currently disabled (hardware optional)."
        if not device.vehicle_id:
            return None, f"GPS device '{device_code}' is not bound to any vehicle."

        adapter = cls.get_adapter(device.provider_type)
        normalized = adapter.normalize_payload(payload)
        return TransportRepository.ingest_gps_ping(
            session=session,
            vehicle_id=device.vehicle_id,
            device_id=device.id,
            route_id=payload.get("route_id"),
            latitude=normalized["latitude"],
            longitude=normalized["longitude"],
            speed_kmh=normalized["speed_kmh"],
            heading_deg=normalized["heading_deg"],
            ignition_on=normalized["ignition_on"],
            odometer_km=normalized["odometer_km"],
            source=normalized["source"],
            location_label=normalized["location_label"],
            raw_payload=json.dumps(payload, default=str),
        )

    @classmethod
    def record_manual_checkin(
        cls,
        session: Session,
        vehicle_id: int,
        latitude: float,
        longitude: float,
        location_label: str,
        speed_kmh: float = 0.0,
        route_id: Optional[int] = None,
        odometer_km: Optional[float] = None,
    ) -> Tuple[Optional[TransportGPSPing], Optional[str]]:
        """Allows dispatch staff to log a checkpoint without any GPS hardware device."""
        return TransportRepository.ingest_gps_ping(
            session=session,
            vehicle_id=vehicle_id,
            route_id=route_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            odometer_km=odometer_km,
            source="Manual",
            location_label=location_label,
        )


# ==============================================================================
# TRANSPORT BUSINESS SERVICE
# ==============================================================================

class TransportService:
    """High-level business service for transport seeding, seat allocations, GPS & Excel exports."""

    @staticmethod
    def seed_default_transport_data(session: Session) -> Dict[str, int]:
        """Seeds fleet vehicles, route stops, and sample passenger allocations idempotently (used by tests/CLI)."""
        vehicle_count = 0
        route_count = 0
        stop_count = 0
        passenger_count = 0

        v_map = []
        for v_data in DEFAULT_VEHICLES:
            existing = session.query(Vehicle).filter(Vehicle.vehicle_number == v_data["vehicle_number"]).first()
            if not existing:
                v = Vehicle(**v_data)
                session.add(v)
                session.commit()
                session.refresh(v)
                v_map.append(v)
                vehicle_count += 1
            else:
                v_map.append(existing)

        for r_data in DEFAULT_ROUTES:
            existing_r = session.query(TransportRoute).filter(TransportRoute.route_code == r_data["route_code"]).first()
            target_vehicle = v_map[r_data["vehicle_index"]] if r_data["vehicle_index"] < len(v_map) else None
            if not existing_r:
                r = TransportRoute(
                    route_code=r_data["route_code"],
                    route_name=r_data["route_name"],
                    start_point=r_data["start_point"],
                    end_point=r_data["end_point"],
                    distance_km=r_data["distance_km"],
                    monthly_fee=r_data["monthly_fee"],
                    pickup_time=r_data["pickup_time"],
                    drop_time=r_data["drop_time"],
                    vehicle_id=target_vehicle.id if target_vehicle else None,
                    status="Active",
                )
                session.add(r)
                session.commit()
                session.refresh(r)
                route_count += 1

                for s_data in r_data.get("stops", []):
                    stop = TransportStop(
                        route_id=r.id,
                        stop_name=s_data["stop_name"],
                        stop_order=s_data["stop_order"],
                        pickup_time=s_data.get("pickup_time"),
                        drop_time=s_data.get("drop_time"),
                        fare=s_data.get("fare", 0.0),
                    )
                    session.add(stop)
                    stop_count += 1
                session.commit()

        existing_passengers = session.query(TransportPassenger).count()
        if existing_passengers == 0:
            routes = session.query(TransportRoute).all()
            students = session.query(Student).order_by(Student.id.asc()).limit(6).all()
            teachers = session.query(Teacher).order_by(Teacher.id.asc()).limit(2).all()
            today_str = date.today().isoformat()

            if routes and students:
                r1 = routes[0]
                s1_stop = r1.stops[1] if len(r1.stops) > 1 else None
                TransportRepository.allocate_passenger(
                    session=session,
                    passenger_type="Student",
                    student_id=students[0].id,
                    route_id=r1.id,
                    vehicle_id=r1.vehicle_id,
                    stop_id=s1_stop.id if s1_stop else None,
                    seat_number="Seat 01A",
                    allocation_date=today_str,
                    monthly_fare=r1.monthly_fee,
                    remarks="Regular school commute",
                )
                passenger_count += 1

                if len(students) > 1:
                    TransportRepository.allocate_passenger(
                        session=session,
                        passenger_type="Student",
                        student_id=students[1].id,
                        route_id=r1.id,
                        vehicle_id=r1.vehicle_id,
                        stop_id=s1_stop.id if s1_stop else None,
                        seat_number="Seat 01B",
                        allocation_date=today_str,
                        monthly_fare=r1.monthly_fee,
                        remarks="Sibling discount requested",
                    )
                    passenger_count += 1

                if len(routes) > 1 and len(students) > 2:
                    r2 = routes[1]
                    s2_stop = r2.stops[2] if len(r2.stops) > 2 else None
                    TransportRepository.allocate_passenger(
                        session=session,
                        passenger_type="Student",
                        student_id=students[2].id,
                        route_id=r2.id,
                        vehicle_id=r2.vehicle_id,
                        stop_id=s2_stop.id if s2_stop else None,
                        seat_number="Seat 04A",
                        allocation_date=today_str,
                        monthly_fare=r2.monthly_fee,
                        remarks="Agargaon boarding",
                    )
                    passenger_count += 1

                if len(routes) > 2 and teachers:
                    r3 = routes[2]
                    TransportRepository.allocate_passenger(
                        session=session,
                        passenger_type="Teacher",
                        teacher_id=teachers[0].id,
                        route_id=r3.id,
                        vehicle_id=r3.vehicle_id,
                        seat_number="Seat 01F",
                        allocation_date=today_str,
                        monthly_fare=0.0,
                        remarks="Faculty staff transport benefit",
                    )
                    passenger_count += 1

        return {
            "vehicles_seeded": vehicle_count,
            "routes_seeded": route_count,
            "stops_seeded": stop_count,
            "passengers_seeded": passenger_count,
        }

    @staticmethod
    def _passenger_display_info(p: TransportPassenger) -> Tuple[str, str, str, str]:
        name = "Unknown"
        affil = "-"
        phone = "-"
        emg = "-"
        if p.student:
            name = p.student.full_name
            affil = f"Class {p.student.school_class.name if p.student.school_class else '-'} (Roll {p.student.roll_number})"
            phone = p.student.phone or "-"
            emg = p.student.emergency_contact or phone
        elif p.teacher:
            name = p.teacher.full_name
            affil = p.teacher.designation or "Faculty"
            phone = p.teacher.phone or "-"
            emg = p.teacher.emergency_contact_phone or phone
        elif p.staff:
            name = p.staff.full_name
            affil = p.staff.position or "Staff"
            phone = p.staff.phone or "-"
            emg = p.staff.emergency_contact_phone or phone
        return name, affil, phone, emg

    @staticmethod
    def _style_sheet_headers(ws, headers: List[str], header_row: int = 4, fill_hex: str = "1E3A8A"):
        header_fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
        ws.row_dimensions[header_row].height = 24
        return thin_border

    @staticmethod
    def _autofit_sheet(ws):
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    @staticmethod
    def export_passengers_excel(session: Session, route_id: Optional[int], output_path: str) -> str:
        """Exports route passenger list to formatted openpyxl Excel spreadsheet."""
        passengers = TransportRepository.get_passengers(session, route_id=route_id, status="Active")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Passenger Manifest"

        ws["A1"] = "EDUMANAGE PRO - TRANSPORT PASSENGER MANIFEST & SEAT ALLOCATION"
        ws["A1"].font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        ws["A2"] = f"Generated on: {date.today().strftime('%B %d, %Y')} | Active Route Commuter Audit Sheet"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="475569")

        headers = [
            "Pass Code", "Passenger Name", "Type", "Class / Designation", "Contact Phone",
            "Emergency Phone", "Route Code", "Boarding Stop", "Vehicle No", "Seat No",
            "Monthly Fee", "Status",
        ]
        thin_border = TransportService._style_sheet_headers(ws, headers, header_row=4)
        data_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)

        row_num = 4
        for p in passengers:
            row_num += 1
            name, affil, phone, emg = TransportService._passenger_display_info(p)
            route_code = p.route.route_code if p.route else "-"
            stop_name = p.stop.stop_name if p.stop else "Campus Origin"
            v_no = p.vehicle.vehicle_number if p.vehicle else "-"

            ws.cell(row=row_num, column=1, value=p.pass_code or f"#{p.id:04d}").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=2, value=name)
            ws.cell(row=row_num, column=3, value=p.passenger_type).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=4, value=affil)
            ws.cell(row=row_num, column=5, value=phone).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=6, value=emg).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=7, value=route_code).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=8, value=stop_name)
            ws.cell(row=row_num, column=9, value=v_no).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=10, value=p.seat_number or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=11, value=round(float(p.monthly_fare or 0.0), 2)).alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=12, value=p.status).alignment = Alignment(horizontal="center")

            for c in range(1, 13):
                cell = ws.cell(row=row_num, column=c)
                cell.font = data_font
                cell.border = thin_border

        row_num += 1
        ws.cell(row=row_num, column=1, value="TOTAL ALLOCATED").font = bold_font
        ws.cell(row=row_num, column=2, value=f"{len(passengers)} Passengers").font = bold_font
        ws.cell(row=row_num, column=11, value=round(sum(float(p.monthly_fare or 0.0) for p in passengers), 2)).font = bold_font

        sum_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for c in range(1, 13):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = sum_fill
            cell.border = thin_border

        TransportService._autofit_sheet(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_fleet_operations_excel(session: Session, output_path: str) -> str:
        """Exports multi-sheet workbook covering Vehicles, Fuel Logs, Maintenance, Insurance/Docs, and Reminders."""
        vehicles = TransportRepository.get_vehicles(session)
        fuel_logs = TransportRepository.get_fuel_logs(session)
        maint_logs = TransportRepository.get_maintenance_logs(session)
        insurances = TransportRepository.get_insurances(session)
        documents = TransportRepository.get_documents(session)
        reminders = TransportRepository.get_maintenance_reminders(session)

        wb = openpyxl.Workbook()

        # Sheet 1: Fleet Vehicles
        ws_v = wb.active
        ws_v.title = "Fleet Vehicles"
        ws_v["A1"] = "EDUMANAGE PRO - FLEET VEHICLE REGISTRY"
        ws_v["A1"].font = Font(name="Calibri", size=14, bold=True, color="B45309")
        v_headers = [
            "Plate No", "Registration No", "Model", "Type", "Capacity", "Fuel Type",
            "Odometer (km)", "Driver", "Driver Phone", "Helper", "Insurance Expiry",
            "Fitness Expiry", "Next Service Date", "Status",
        ]
        border = TransportService._style_sheet_headers(ws_v, v_headers, header_row=3, fill_hex="92400E")
        for idx, v in enumerate(vehicles, start=4):
            vals = [
                v.vehicle_number, v.registration_no or "-", v.vehicle_model, v.vehicle_type,
                v.seating_capacity, v.fuel_type, float(v.current_odometer_km or 0.0),
                v.driver_name, v.driver_phone, v.helper_name or "-",
                v.insurance_expiry or "-", v.fitness_expiry or "-", v.next_service_date or "-", v.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_v.cell(row=idx, column=c_idx, value=val)
                cell.border = border
        TransportService._autofit_sheet(ws_v)

        # Sheet 2: Fuel Logs
        ws_f = wb.create_sheet("Fuel Logs")
        ws_f["A1"] = "FLEET FUEL & EFFICIENCY LOGS"
        ws_f["A1"].font = Font(name="Calibri", size=14, bold=True, color="0284C7")
        f_headers = ["Date", "Vehicle No", "Fuel Type", "Liters", "Price/L", "Total Cost", "Prev Odo", "Current Odo", "Distance (km)", "km/L", "Station", "Receipt"]
        border = TransportService._style_sheet_headers(ws_f, f_headers, header_row=3, fill_hex="0369A1")
        for idx, fl in enumerate(fuel_logs, start=4):
            vals = [
                fl.fill_date, fl.vehicle.vehicle_number if fl.vehicle else "-", fl.fuel_type,
                fl.liters, float(fl.price_per_liter or 0.0), float(fl.total_cost or 0.0),
                fl.previous_odometer_km or 0.0, fl.odometer_km, fl.distance_covered_km,
                fl.km_per_liter, fl.station_name or "-", fl.receipt_no or "-",
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_f.cell(row=idx, column=c_idx, value=val)
                cell.border = border
        TransportService._autofit_sheet(ws_f)

        # Sheet 3: Maintenance Logs
        ws_m = wb.create_sheet("Maintenance Logs")
        ws_m["A1"] = "VEHICLE MAINTENANCE & SERVICE HISTORY"
        ws_m["A1"].font = Font(name="Calibri", size=14, bold=True, color="059669")
        m_headers = ["Date", "Vehicle No", "Service Type", "Workshop", "Cost", "Odometer (km)", "Next Service Date", "Next Odometer", "Invoice No", "Status"]
        border = TransportService._style_sheet_headers(ws_m, m_headers, header_row=3, fill_hex="047857")
        for idx, ml in enumerate(maint_logs, start=4):
            vals = [
                ml.service_date, ml.vehicle.vehicle_number if ml.vehicle else "-", ml.service_type,
                ml.workshop_name or "-", float(ml.cost or 0.0), ml.odometer_km,
                ml.next_service_date or "-", ml.next_service_odometer_km or "-", ml.invoice_no or "-", ml.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_m.cell(row=idx, column=c_idx, value=val)
                cell.border = border
        TransportService._autofit_sheet(ws_m)

        # Sheet 4: Insurance & Documents
        ws_d = wb.create_sheet("Insurance & Docs")
        ws_d["A1"] = "VEHICLE INSURANCE POLICIES & COMPLIANCE DOCUMENTS"
        ws_d["A1"].font = Font(name="Calibri", size=14, bold=True, color="7C3AED")
        d_headers = ["Kind", "Vehicle No", "Reference / Policy No", "Provider / Authority", "Start / Issue", "Expiry Date", "Premium / Notes", "Status"]
        border = TransportService._style_sheet_headers(ws_d, d_headers, header_row=3, fill_hex="5B21B6")
        row_d = 4
        for ins in insurances:
            vals = [
                f"Insurance ({ins.coverage_type})",
                ins.vehicle.vehicle_number if ins.vehicle else "-",
                ins.policy_number, ins.provider, ins.start_date, ins.expiry_date,
                float(ins.premium_amount or 0.0), ins.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_d.cell(row=row_d, column=c_idx, value=val)
                cell.border = border
            row_d += 1
        for doc in documents:
            vals = [
                f"Doc: {doc.document_type}",
                doc.vehicle.vehicle_number if doc.vehicle else "-",
                doc.document_number or "-", doc.issuing_authority or "-",
                doc.issue_date or "-", doc.expiry_date or "-", doc.notes or "-", doc.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_d.cell(row=row_d, column=c_idx, value=val)
                cell.border = border
            row_d += 1
        TransportService._autofit_sheet(ws_d)

        # Sheet 5: Reminders
        ws_r = wb.create_sheet("Reminders")
        ws_r["A1"] = "MAINTENANCE & EXPIRY REMINDER ALERTS"
        ws_r["A1"].font = Font(name="Calibri", size=14, bold=True, color="DC2626")
        r_headers = ["Severity", "Category", "Vehicle No", "Alert Title", "Due Date", "Due Odometer", "Days Left", "Details"]
        border = TransportService._style_sheet_headers(ws_r, r_headers, header_row=3, fill_hex="991B1B")
        for idx, rem in enumerate(reminders, start=4):
            vals = [
                rem["severity"], rem["category"], rem["vehicle_number"], rem["title"],
                rem["due_date"], rem.get("due_odometer_km") or "-",
                rem.get("days_remaining") if rem.get("days_remaining") is not None else "-",
                rem["details"],
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws_r.cell(row=idx, column=c_idx, value=val)
                cell.border = border
        TransportService._autofit_sheet(ws_r)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path

    @staticmethod
    def export_transport_fees_excel(
        session: Session,
        billing_month: Optional[str],
        output_path: str,
    ) -> str:
        """Exports monthly transport fee billing & collection ledger to Excel."""
        charges = TransportRepository.get_fee_charges(session, billing_month=billing_month)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transport Fees"
        ws["A1"] = "EDUMANAGE PRO - TRANSPORT FEE BILLING & COLLECTION LEDGER"
        ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="059669")
        ws["A2"] = f"Billing Month: {billing_month or 'All Months'} | Generated: {date.today().isoformat()}"
        headers = [
            "Month", "Pass Code", "Commuter Name", "Type", "Route", "Fee Amount",
            "Discount", "Net Payable", "Paid Amount", "Balance Due", "Method", "Receipt No", "Paid Date", "Status",
        ]
        border = TransportService._style_sheet_headers(ws, headers, header_row=4, fill_hex="047857")
        for idx, c in enumerate(charges, start=5):
            pax = c.passenger
            name = TransportService._passenger_display_info(pax)[0] if pax else "-"
            vals = [
                c.billing_month,
                pax.pass_code if pax else "-",
                name,
                pax.passenger_type if pax else "-",
                c.route.route_code if c.route else "-",
                float(c.amount or 0.0),
                float(c.discount or 0.0),
                c.net_payable,
                float(c.paid_amount or 0.0),
                c.balance_due,
                c.payment_method or "-",
                c.receipt_no or "-",
                c.paid_date or "-",
                c.status,
            ]
            for c_idx, val in enumerate(vals, 1):
                cell = ws.cell(row=idx, column=c_idx, value=val)
                cell.border = border
        TransportService._autofit_sheet(ws)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path
