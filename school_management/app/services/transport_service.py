"""
EduManage Pro - Transport Service
Phase 11: Fleet Seeding, Route Network, Passenger Excel Export & Audit
"""

import os
from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.models.transport import Vehicle, TransportRoute, TransportStop, TransportPassenger
from app.models.student import Student
from app.models.staff import Teacher
from app.repositories.transport_repository import TransportRepository


DEFAULT_VEHICLES = [
    {
        "vehicle_number": "DHK-METRO-CHA-11-2041",
        "vehicle_model": "Tata Marcopolo CityBus 42-S",
        "vehicle_type": "Bus",
        "seating_capacity": 42,
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
        "vehicle_model": "Toyota Coaster Deluxe 28-S",
        "vehicle_type": "Minibus",
        "seating_capacity": 28,
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
        "vehicle_model": "Hino Rainbow 32-S",
        "vehicle_type": "Bus",
        "seating_capacity": 32,
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


class TransportService:
    """High-level business service for transport seeding, seat allocations, and Excel audit."""

    @staticmethod
    def seed_default_transport_data(session: Session) -> Dict[str, int]:
        """Seeds fleet vehicles, route stops, and sample passenger allocations idempotently."""
        vehicle_count = 0
        route_count = 0
        stop_count = 0
        passenger_count = 0

        # 1. Vehicles
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

        # 2. Routes & Stops
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
                    status="Active"
                )
                session.add(r)
                session.commit()
                session.refresh(r)
                route_count += 1

                # Seed stops for route
                for s_data in r_data.get("stops", []):
                    stop = TransportStop(
                        route_id=r.id,
                        stop_name=s_data["stop_name"],
                        stop_order=s_data["stop_order"],
                        pickup_time=s_data.get("pickup_time"),
                        drop_time=s_data.get("drop_time"),
                        fare=s_data.get("fare", 0.0)
                    )
                    session.add(stop)
                    stop_count += 1
                session.commit()

        # 3. Passenger Allocations
        existing_passengers = session.query(TransportPassenger).count()
        if existing_passengers == 0:
            routes = session.query(TransportRoute).all()
            students = session.query(Student).order_by(Student.id.asc()).limit(6).all()
            teachers = session.query(Teacher).order_by(Teacher.id.asc()).limit(2).all()
            today_str = date.today().isoformat()

            if routes and students:
                # Student 1 -> Route 1
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
                    remarks="Regular school commute"
                )
                passenger_count += 1

                # Student 2 -> Route 1
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
                        remarks="Sibling discount requested"
                    )
                    passenger_count += 1

                # Student 3 -> Route 2
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
                        remarks="Agargaon boarding"
                    )
                    passenger_count += 1

                # Teacher 1 -> Route 3
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
                        monthly_fare=0.0,  # Complimentary faculty transport
                        remarks="Faculty staff transport benefit"
                    )
                    passenger_count += 1

        return {
            "vehicles_seeded": vehicle_count,
            "routes_seeded": route_count,
            "stops_seeded": stop_count,
            "passengers_seeded": passenger_count,
        }

    @staticmethod
    def export_passengers_excel(session: Session, route_id: Optional[int], output_path: str) -> str:
        """Exports route passenger list to formatted openpyxl Excel spreadsheet."""
        passengers = TransportRepository.get_passengers(session, route_id=route_id, status="Active")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Passenger Manifest"

        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy 900
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=10, italic=True, color="475569")
        data_font = Font(name="Calibri", size=10)
        bold_font = Font(name="Calibri", size=10, bold=True)

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        ws["A1"] = "EDUMANAGE PRO - TRANSPORT PASSENGER MANIFEST & SEAT ALLOCATION"
        ws["A1"].font = title_font
        ws["A2"] = f"Generated on: {date.today().strftime('%B %d, %Y')} | Active Route Commuter Audit Sheet"
        ws["A2"].font = sub_font

        headers = [
            "Pass ID", "Passenger Name", "Type", "Class / Designation", "Contact Phone",
            "Emergency Phone", "Route Code", "Boarding Stop", "Vehicle No", "Seat No",
            "Monthly Fee ($)", "Status"
        ]

        row_num = 4
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        ws.row_dimensions[4].height = 26

        for p in passengers:
            row_num += 1
            name = "Unknown"
            affil = "-"
            phone = "-"
            emg = "-"

            if p.student:
                name = p.student.full_name
                affil = f"Class {p.student.school_class.name if p.student.school_class else '-'} (Roll {p.student.roll_number})"
                phone = p.student.phone or "-"
                emg = p.student.emergency_contact or "-"
            elif p.teacher:
                name = p.teacher.full_name
                affil = p.teacher.designation or "Faculty"
                phone = p.teacher.phone or "-"
                emg = p.teacher.phone or "-"

            route_code = p.route.route_code if p.route else "-"
            stop_name = p.stop.stop_name if p.stop else "Campus Origin"
            v_no = p.vehicle.vehicle_number if p.vehicle else "-"

            ws.cell(row=row_num, column=1, value=f"#{p.id:04d}").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=2, value=name)
            ws.cell(row=row_num, column=3, value=p.passenger_type).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=4, value=affil)
            ws.cell(row=row_num, column=5, value=phone).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=6, value=emg).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=7, value=route_code).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=8, value=stop_name)
            ws.cell(row=row_num, column=9, value=v_no).alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=10, value=p.seat_number or "-").alignment = Alignment(horizontal="center")
            ws.cell(row=row_num, column=11, value=f"${p.monthly_fare:.2f}").alignment = Alignment(horizontal="right")
            ws.cell(row=row_num, column=12, value=p.status).alignment = Alignment(horizontal="center")

            for c in range(1, 13):
                cell = ws.cell(row=row_num, column=c)
                cell.font = data_font
                cell.border = thin_border

        # Summary Row
        row_num += 1
        ws.cell(row=row_num, column=1, value="TOTAL ALLOCATED").font = bold_font
        ws.cell(row=row_num, column=2, value=f"{len(passengers)} Passengers").font = bold_font
        ws.cell(row=row_num, column=11, value=f"${sum(p.monthly_fare for p in passengers):.2f}").font = bold_font

        sum_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for c in range(1, 13):
            cell = ws.cell(row=row_num, column=c)
            cell.fill = sum_fill
            cell.border = thin_border

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        return output_path
