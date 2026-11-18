"""
EduManage Pro - Transport Repository
Complete Fleet Vehicles, Routes & Pickup Points, Commuter Allocations, Transport Fees,
Fuel Logs, Maintenance Logs & Reminders, Insurance, Compliance Documents, and
Hardware-Optional GPS Telemetry Integration.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
import uuid
from sqlalchemy.orm import Session, joinedload

from app.models.base import utc_now
from app.models.transport import (
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


def _parse_iso_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return datetime.strptime(val.strip()[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _compute_doc_status(expiry_str: Optional[str], ref_date: Optional[date] = None) -> str:
    exp = _parse_iso_date(expiry_str)
    if not exp:
        return "Valid"
    today = ref_date or date.today()
    delta = (exp - today).days
    if delta < 0:
        return "Expired"
    if delta <= 30:
        return "Expiring Soon"
    return "Valid"


class TransportRepository:
    """Repository handling fleet vehicles, routes, pickup points, fees, fuel, maintenance, insurance, docs, and GPS."""

    # ---------------- Vehicle Fleet Operations ----------------
    @staticmethod
    def get_vehicles(
        session: Session,
        status: Optional[str] = None,
        vehicle_type: Optional[str] = None,
    ) -> List[Vehicle]:
        query = session.query(Vehicle).options(
            joinedload(Vehicle.routes),
            joinedload(Vehicle.passengers),
            joinedload(Vehicle.driver_staff),
            joinedload(Vehicle.helper_staff),
        )
        if status:
            query = query.filter(Vehicle.status == status)
        if vehicle_type:
            if vehicle_type == "Microbus":
                query = query.filter(Vehicle.vehicle_type.in_(["Microbus", "Minibus"]))
            else:
                query = query.filter(Vehicle.vehicle_type == vehicle_type)
        return query.order_by(Vehicle.id.desc()).all()

    @staticmethod
    def get_vehicle_by_id(session: Session, vehicle_id: int) -> Optional[Vehicle]:
        return session.query(Vehicle).options(
            joinedload(Vehicle.routes),
            joinedload(Vehicle.passengers),
            joinedload(Vehicle.fuel_logs),
            joinedload(Vehicle.maintenance_logs),
            joinedload(Vehicle.insurances),
            joinedload(Vehicle.documents),
            joinedload(Vehicle.gps_devices),
        ).filter(Vehicle.id == vehicle_id).first()

    @staticmethod
    def create_vehicle(session: Session, **kwargs) -> Vehicle:
        if not kwargs.get("registration_no") and kwargs.get("vehicle_number"):
            kwargs["registration_no"] = kwargs["vehicle_number"]
        vehicle = Vehicle(**kwargs)
        session.add(vehicle)
        session.commit()
        session.refresh(vehicle)
        return vehicle

    @staticmethod
    def update_vehicle(session: Session, vehicle_id: int, **kwargs) -> Optional[Vehicle]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None
        for k, v in kwargs.items():
            if hasattr(vehicle, k):
                setattr(vehicle, k, v)
        session.commit()
        session.refresh(vehicle)
        return vehicle

    @staticmethod
    def delete_vehicle(session: Session, vehicle_id: int) -> bool:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return False
        session.delete(vehicle)
        session.commit()
        return True

    # ---------------- Route & Pickup Point Operations ----------------
    @staticmethod
    def get_routes(session: Session, status: Optional[str] = None) -> List[TransportRoute]:
        query = session.query(TransportRoute).options(
            joinedload(TransportRoute.vehicle),
            joinedload(TransportRoute.stops),
            joinedload(TransportRoute.passengers),
        )
        if status:
            query = query.filter(TransportRoute.status == status)
        return query.order_by(TransportRoute.route_code.asc()).all()

    @staticmethod
    def get_route_by_id(session: Session, route_id: int) -> Optional[TransportRoute]:
        return session.query(TransportRoute).options(
            joinedload(TransportRoute.vehicle),
            joinedload(TransportRoute.stops),
            joinedload(TransportRoute.passengers),
        ).filter(TransportRoute.id == route_id).first()

    @staticmethod
    def create_route(session: Session, **kwargs) -> TransportRoute:
        stops_data = kwargs.pop("stops", None)
        route = TransportRoute(**kwargs)
        session.add(route)
        session.flush()
        if stops_data:
            for idx, s in enumerate(stops_data, start=1):
                stop = TransportStop(
                    route_id=route.id,
                    stop_name=s["stop_name"],
                    stop_order=int(s.get("stop_order", idx)),
                    pickup_time=s.get("pickup_time"),
                    drop_time=s.get("drop_time"),
                    fare=float(s.get("fare", 0.0) or 0.0),
                    landmark=s.get("landmark"),
                    latitude=s.get("latitude"),
                    longitude=s.get("longitude"),
                )
                session.add(stop)
        session.commit()
        session.refresh(route)
        return route

    @staticmethod
    def update_route(session: Session, route_id: int, **kwargs) -> Optional[TransportRoute]:
        route = session.query(TransportRoute).filter(TransportRoute.id == route_id).first()
        if not route:
            return None
        for k, v in kwargs.items():
            if hasattr(route, k):
                setattr(route, k, v)
        session.commit()
        session.refresh(route)
        return route

    @staticmethod
    def delete_route(session: Session, route_id: int) -> bool:
        route = session.query(TransportRoute).filter(TransportRoute.id == route_id).first()
        if not route:
            return False
        session.delete(route)
        session.commit()
        return True

    @staticmethod
    def add_stop_to_route(
        session: Session,
        route_id: int,
        stop_name: str,
        stop_order: int,
        pickup_time: Optional[str] = None,
        drop_time: Optional[str] = None,
        fare: float = 0.0,
        landmark: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> TransportStop:
        stop = TransportStop(
            route_id=route_id,
            stop_name=stop_name,
            stop_order=stop_order,
            pickup_time=pickup_time,
            drop_time=drop_time,
            fare=fare,
            landmark=landmark,
            latitude=latitude,
            longitude=longitude,
        )
        session.add(stop)
        session.commit()
        session.refresh(stop)
        return stop

    @staticmethod
    def update_stop(session: Session, stop_id: int, **kwargs) -> Optional[TransportStop]:
        stop = session.query(TransportStop).filter(TransportStop.id == stop_id).first()
        if not stop:
            return None
        for k, v in kwargs.items():
            if hasattr(stop, k):
                setattr(stop, k, v)
        session.commit()
        session.refresh(stop)
        return stop

    @staticmethod
    def delete_stop(session: Session, stop_id: int) -> bool:
        stop = session.query(TransportStop).filter(TransportStop.id == stop_id).first()
        if not stop:
            return False
        session.query(TransportPassenger).filter(TransportPassenger.stop_id == stop_id).update(
            {TransportPassenger.stop_id: None}, synchronize_session=False
        )
        session.delete(stop)
        session.commit()
        return True

    @staticmethod
    def replace_route_stops(session: Session, route_id: int, stops_data: List[Dict[str, Any]]) -> List[TransportStop]:
        existing = session.query(TransportStop).filter(TransportStop.route_id == route_id).all()
        existing_ids = [s.id for s in existing]
        if existing_ids:
            session.query(TransportPassenger).filter(TransportPassenger.stop_id.in_(existing_ids)).update(
                {TransportPassenger.stop_id: None}, synchronize_session=False
            )
            for s in existing:
                session.delete(s)
            session.flush()

        created: List[TransportStop] = []
        for idx, s in enumerate(stops_data, start=1):
            name = (s.get("stop_name") or "").strip()
            if not name:
                continue
            stop = TransportStop(
                route_id=route_id,
                stop_name=name,
                stop_order=int(s.get("stop_order", idx)),
                pickup_time=s.get("pickup_time") or None,
                drop_time=s.get("drop_time") or None,
                fare=float(s.get("fare", 0.0) or 0.0),
                landmark=s.get("landmark") or None,
                latitude=s.get("latitude"),
                longitude=s.get("longitude"),
            )
            session.add(stop)
            created.append(stop)
        session.commit()
        for stop in created:
            session.refresh(stop)
        return created

    # ---------------- Passenger Allocations ----------------
    @staticmethod
    def get_passengers(
        session: Session,
        route_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TransportPassenger]:
        query = session.query(TransportPassenger).options(
            joinedload(TransportPassenger.student),
            joinedload(TransportPassenger.teacher),
            joinedload(TransportPassenger.staff),
            joinedload(TransportPassenger.route),
            joinedload(TransportPassenger.vehicle),
            joinedload(TransportPassenger.stop),
        )
        if route_id:
            query = query.filter(TransportPassenger.route_id == route_id)
        if vehicle_id:
            query = query.filter(TransportPassenger.vehicle_id == vehicle_id)
        if status:
            query = query.filter(TransportPassenger.status == status)
        return query.order_by(TransportPassenger.id.desc()).all()

    @staticmethod
    def get_passenger_by_id(session: Session, passenger_id: int) -> Optional[TransportPassenger]:
        return session.query(TransportPassenger).options(
            joinedload(TransportPassenger.student),
            joinedload(TransportPassenger.teacher),
            joinedload(TransportPassenger.staff),
            joinedload(TransportPassenger.route),
            joinedload(TransportPassenger.vehicle),
            joinedload(TransportPassenger.stop),
        ).filter(TransportPassenger.id == passenger_id).first()

    @staticmethod
    def allocate_passenger(
        session: Session,
        passenger_type: str,
        route_id: int,
        allocation_date: str,
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        stop_id: Optional[int] = None,
        seat_number: Optional[str] = None,
        monthly_fare: Optional[float] = None,
        pickup_address: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> Tuple[Optional[TransportPassenger], Optional[str]]:
        """
        Allocates student, teacher, or staff commuter to route and vehicle
        with seating capacity and duplicate checks.
        """
        route = session.query(TransportRoute).filter(TransportRoute.id == route_id).first()
        if not route:
            return None, "Transport route not found."

        target_v_id = vehicle_id or route.vehicle_id
        if target_v_id:
            v = session.query(Vehicle).filter(Vehicle.id == target_v_id).first()
            if v:
                active_count = session.query(TransportPassenger).filter(
                    TransportPassenger.vehicle_id == target_v_id,
                    TransportPassenger.status == "Active",
                ).count()
                if active_count >= v.seating_capacity:
                    return None, f"Vehicle '{v.vehicle_number}' is fully booked ({active_count}/{v.seating_capacity} seats)."

        if student_id:
            existing = session.query(TransportPassenger).filter(
                TransportPassenger.student_id == student_id,
                TransportPassenger.status == "Active",
            ).first()
            if existing:
                return None, f"Student is already allocated to active Route '{existing.route.route_name if existing.route else ''}'."
        elif teacher_id:
            existing = session.query(TransportPassenger).filter(
                TransportPassenger.teacher_id == teacher_id,
                TransportPassenger.status == "Active",
            ).first()
            if existing:
                return None, f"Teacher is already allocated to active Route '{existing.route.route_name if existing.route else ''}'."
        elif staff_id:
            existing = session.query(TransportPassenger).filter(
                TransportPassenger.staff_id == staff_id,
                TransportPassenger.status == "Active",
            ).first()
            if existing:
                return None, f"Staff member is already allocated to active Route '{existing.route.route_name if existing.route else ''}'."

        if monthly_fare is not None:
            fare = float(monthly_fare)
        elif stop_id:
            stop = session.query(TransportStop).filter(TransportStop.id == stop_id).first()
            fare = float(stop.fare) if (stop and float(stop.fare or 0.0) > 0.0) else float(route.monthly_fee or 0.0)
        else:
            fare = float(route.monthly_fee or 0.0)

        pass_code = f"TRP-{uuid.uuid4().hex[:8].upper()}"
        qr_payload = f"EDUMANAGE|PASS|{pass_code}|RT:{route.route_code}|TYPE:{passenger_type}"

        passenger = TransportPassenger(
            passenger_type=passenger_type,
            student_id=student_id,
            teacher_id=teacher_id,
            staff_id=staff_id,
            route_id=route_id,
            vehicle_id=target_v_id,
            stop_id=stop_id,
            seat_number=seat_number,
            allocation_date=allocation_date,
            monthly_fare=fare,
            pass_code=pass_code,
            qr_payload=qr_payload,
            pickup_address=pickup_address,
            status="Active",
            remarks=remarks,
        )
        session.add(passenger)
        session.commit()
        session.refresh(passenger)
        return passenger, None

    @staticmethod
    def cancel_allocation(session: Session, passenger_id: int, reason: Optional[str] = None) -> bool:
        p = session.query(TransportPassenger).filter(TransportPassenger.id == passenger_id).first()
        if not p:
            return False
        p.status = "Cancelled"
        if reason:
            p.remarks = f"{p.remarks or ''} [Cancelled: {reason}]".strip()
        session.commit()
        return True

    # ---------------- Transport Fee Billing & Collection ----------------
    @staticmethod
    def get_fee_charges(
        session: Session,
        billing_month: Optional[str] = None,
        route_id: Optional[int] = None,
        status: Optional[str] = None,
        passenger_id: Optional[int] = None,
    ) -> List[TransportFeeCharge]:
        query = session.query(TransportFeeCharge).options(
            joinedload(TransportFeeCharge.passenger).joinedload(TransportPassenger.student),
            joinedload(TransportFeeCharge.passenger).joinedload(TransportPassenger.teacher),
            joinedload(TransportFeeCharge.passenger).joinedload(TransportPassenger.staff),
            joinedload(TransportFeeCharge.route),
        )
        if billing_month:
            query = query.filter(TransportFeeCharge.billing_month == billing_month)
        if route_id:
            query = query.filter(TransportFeeCharge.route_id == route_id)
        if status:
            query = query.filter(TransportFeeCharge.status == status)
        if passenger_id:
            query = query.filter(TransportFeeCharge.passenger_id == passenger_id)
        return query.order_by(TransportFeeCharge.billing_month.desc(), TransportFeeCharge.id.desc()).all()

    @staticmethod
    def generate_monthly_fees(
        session: Session,
        billing_month: str,
        due_date: Optional[str] = None,
        route_id: Optional[int] = None,
        include_zero_fare: bool = False,
    ) -> Dict[str, int]:
        """Idempotently generates transport fee bills for active commuters for YYYY-MM."""
        query = session.query(TransportPassenger).filter(TransportPassenger.status == "Active")
        if route_id:
            query = query.filter(TransportPassenger.route_id == route_id)
        passengers = query.all()

        created = 0
        skipped = 0
        default_due = due_date or f"{billing_month}-10"

        for p in passengers:
            fare = float(p.monthly_fare or 0.0)
            if fare <= 0.0 and not include_zero_fare:
                skipped += 1
                continue
            existing = session.query(TransportFeeCharge).filter(
                TransportFeeCharge.passenger_id == p.id,
                TransportFeeCharge.billing_month == billing_month,
            ).first()
            if existing:
                skipped += 1
                continue
            charge = TransportFeeCharge(
                passenger_id=p.id,
                student_id=p.student_id,
                route_id=p.route_id,
                billing_month=billing_month,
                due_date=default_due,
                amount=fare,
                discount=0.0,
                paid_amount=0.0,
                status="Pending",
            )
            session.add(charge)
            created += 1

        session.commit()
        return {"created": created, "skipped": skipped}

    @staticmethod
    def record_fee_payment(
        session: Session,
        charge_id: int,
        amount: float,
        payment_method: str = "Cash",
        discount: Optional[float] = None,
        paid_date: Optional[str] = None,
        collected_by: str = "admin",
        remarks: Optional[str] = None,
    ) -> Tuple[Optional[TransportFeeCharge], Optional[str]]:
        charge = session.query(TransportFeeCharge).filter(TransportFeeCharge.id == charge_id).first()
        if not charge:
            return None, "Transport fee charge not found."
        if charge.status == "Waived":
            return None, "Charge has already been waived."
        if amount < 0:
            return None, "Payment amount cannot be negative."

        if discount is not None:
            if discount < 0:
                return None, "Discount cannot be negative."
            charge.discount = float(discount)

        net = charge.net_payable
        new_paid = min(net, float(charge.paid_amount or 0.0) + float(amount))
        charge.paid_amount = round(new_paid, 2)
        charge.payment_method = payment_method
        charge.paid_date = paid_date or date.today().isoformat()
        charge.collected_by = collected_by
        if not charge.receipt_no and amount > 0:
            charge.receipt_no = f"TRN-RCP-{date.today().strftime('%Y%m')}-{charge.id:04d}-{uuid.uuid4().hex[:4].upper()}"
        if remarks:
            charge.remarks = f"{charge.remarks + ' | ' if charge.remarks else ''}{remarks}"

        if charge.paid_amount >= net and net > 0:
            charge.status = "Paid"
        elif net == 0:
            charge.status = "Paid"
        elif charge.paid_amount > 0:
            charge.status = "Partial"
        else:
            charge.status = "Pending"

        session.commit()
        session.refresh(charge)
        return charge, None

    @staticmethod
    def waive_fee_charge(session: Session, charge_id: int, remarks: Optional[str] = None) -> Optional[TransportFeeCharge]:
        charge = session.query(TransportFeeCharge).filter(TransportFeeCharge.id == charge_id).first()
        if not charge:
            return None
        charge.status = "Waived"
        charge.discount = float(charge.amount or 0.0)
        if remarks:
            charge.remarks = f"{charge.remarks + ' | ' if charge.remarks else ''}Waived: {remarks}"
        session.commit()
        session.refresh(charge)
        return charge

    # ---------------- Fuel Management ----------------
    @staticmethod
    def get_fuel_logs(session: Session, vehicle_id: Optional[int] = None) -> List[TransportFuelLog]:
        query = session.query(TransportFuelLog).options(joinedload(TransportFuelLog.vehicle))
        if vehicle_id:
            query = query.filter(TransportFuelLog.vehicle_id == vehicle_id)
        return query.order_by(TransportFuelLog.fill_date.desc(), TransportFuelLog.id.desc()).all()

    @staticmethod
    def add_fuel_log(
        session: Session,
        vehicle_id: int,
        fill_date: str,
        liters: float,
        price_per_liter: float,
        odometer_km: float,
        fuel_type: Optional[str] = None,
        total_cost: Optional[float] = None,
        station_name: Optional[str] = None,
        receipt_no: Optional[str] = None,
        filled_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[TransportFuelLog], Optional[str]]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None, "Vehicle not found."
        if liters <= 0:
            return None, "Fuel quantity (liters) must be greater than zero."
        if odometer_km < 0:
            return None, "Odometer reading cannot be negative."

        last_fuel = (
            session.query(TransportFuelLog)
            .filter(TransportFuelLog.vehicle_id == vehicle_id)
            .order_by(TransportFuelLog.odometer_km.desc(), TransportFuelLog.id.desc())
            .first()
        )
        prev_odo = float(last_fuel.odometer_km) if last_fuel else float(vehicle.current_odometer_km or 0.0)
        computed_total = float(total_cost) if total_cost is not None else round(float(liters) * float(price_per_liter), 2)

        log = TransportFuelLog(
            vehicle_id=vehicle_id,
            fill_date=fill_date,
            fuel_type=fuel_type or vehicle.fuel_type or "Diesel",
            liters=float(liters),
            price_per_liter=float(price_per_liter),
            total_cost=computed_total,
            previous_odometer_km=prev_odo,
            odometer_km=float(odometer_km),
            station_name=station_name,
            receipt_no=receipt_no,
            filled_by=filled_by,
            notes=notes,
        )
        session.add(log)

        if float(odometer_km) > float(vehicle.current_odometer_km or 0.0):
            vehicle.current_odometer_km = float(odometer_km)

        session.commit()
        session.refresh(log)
        return log, None

    @staticmethod
    def delete_fuel_log(session: Session, log_id: int) -> bool:
        log = session.query(TransportFuelLog).filter(TransportFuelLog.id == log_id).first()
        if not log:
            return False
        session.delete(log)
        session.commit()
        return True

    # ---------------- Maintenance & Reminders ----------------
    @staticmethod
    def get_maintenance_logs(
        session: Session,
        vehicle_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TransportMaintenanceLog]:
        query = session.query(TransportMaintenanceLog).options(joinedload(TransportMaintenanceLog.vehicle))
        if vehicle_id:
            query = query.filter(TransportMaintenanceLog.vehicle_id == vehicle_id)
        if status:
            query = query.filter(TransportMaintenanceLog.status == status)
        return query.order_by(TransportMaintenanceLog.service_date.desc(), TransportMaintenanceLog.id.desc()).all()

    @staticmethod
    def add_maintenance_log(
        session: Session,
        vehicle_id: int,
        service_type: str,
        service_date: str,
        workshop_name: Optional[str] = None,
        cost: float = 0.0,
        odometer_km: float = 0.0,
        next_service_date: Optional[str] = None,
        next_service_odometer_km: Optional[float] = None,
        invoice_no: Optional[str] = None,
        status: str = "Completed",
        notes: Optional[str] = None,
    ) -> Tuple[Optional[TransportMaintenanceLog], Optional[str]]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None, "Vehicle not found."

        log = TransportMaintenanceLog(
            vehicle_id=vehicle_id,
            service_type=service_type,
            service_date=service_date,
            workshop_name=workshop_name,
            cost=float(cost or 0.0),
            odometer_km=float(odometer_km or 0.0),
            next_service_date=next_service_date or None,
            next_service_odometer_km=float(next_service_odometer_km) if next_service_odometer_km is not None else None,
            invoice_no=invoice_no,
            status=status,
            notes=notes,
        )
        session.add(log)

        if float(odometer_km or 0.0) > float(vehicle.current_odometer_km or 0.0):
            vehicle.current_odometer_km = float(odometer_km)
        if status == "Completed":
            vehicle.last_service_date = service_date
            if next_service_date:
                vehicle.next_service_date = next_service_date
            if next_service_odometer_km is not None:
                vehicle.next_service_odometer_km = float(next_service_odometer_km)

        session.commit()
        session.refresh(log)
        return log, None

    @staticmethod
    def update_maintenance_log(session: Session, log_id: int, **kwargs) -> Optional[TransportMaintenanceLog]:
        log = session.query(TransportMaintenanceLog).filter(TransportMaintenanceLog.id == log_id).first()
        if not log:
            return None
        for k, v in kwargs.items():
            if hasattr(log, k):
                setattr(log, k, v)
        if log.status == "Completed":
            vehicle = session.query(Vehicle).filter(Vehicle.id == log.vehicle_id).first()
            if vehicle:
                vehicle.last_service_date = log.service_date
                if log.next_service_date:
                    vehicle.next_service_date = log.next_service_date
                if log.next_service_odometer_km is not None:
                    vehicle.next_service_odometer_km = log.next_service_odometer_km
        session.commit()
        session.refresh(log)
        return log

    @staticmethod
    def delete_maintenance_log(session: Session, log_id: int) -> bool:
        log = session.query(TransportMaintenanceLog).filter(TransportMaintenanceLog.id == log_id).first()
        if not log:
            return False
        session.delete(log)
        session.commit()
        return True

    # ---------------- Insurance Management ----------------
    @staticmethod
    def get_insurances(
        session: Session,
        vehicle_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TransportInsurance]:
        query = session.query(TransportInsurance).options(joinedload(TransportInsurance.vehicle))
        if vehicle_id:
            query = query.filter(TransportInsurance.vehicle_id == vehicle_id)
        if status:
            query = query.filter(TransportInsurance.status == status)
        return query.order_by(TransportInsurance.expiry_date.asc(), TransportInsurance.id.desc()).all()

    @staticmethod
    def add_insurance(
        session: Session,
        vehicle_id: int,
        policy_number: str,
        provider: str,
        start_date: str,
        expiry_date: str,
        coverage_type: str = "Comprehensive",
        premium_amount: float = 0.0,
        insured_value: float = 0.0,
        status: str = "Active",
        document_path: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[TransportInsurance], Optional[str]]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None, "Vehicle not found."

        ins = TransportInsurance(
            vehicle_id=vehicle_id,
            policy_number=policy_number,
            provider=provider,
            coverage_type=coverage_type,
            start_date=start_date,
            expiry_date=expiry_date,
            premium_amount=float(premium_amount or 0.0),
            insured_value=float(insured_value or 0.0),
            status=status,
            document_path=document_path,
            notes=notes,
        )
        session.add(ins)
        if status == "Active":
            vehicle.insurance_expiry = expiry_date
        session.commit()
        session.refresh(ins)
        return ins, None

    @staticmethod
    def update_insurance(session: Session, insurance_id: int, **kwargs) -> Optional[TransportInsurance]:
        ins = session.query(TransportInsurance).filter(TransportInsurance.id == insurance_id).first()
        if not ins:
            return None
        for k, v in kwargs.items():
            if hasattr(ins, k):
                setattr(ins, k, v)
        if ins.status == "Active" and ins.vehicle:
            ins.vehicle.insurance_expiry = ins.expiry_date
        session.commit()
        session.refresh(ins)
        return ins

    @staticmethod
    def delete_insurance(session: Session, insurance_id: int) -> bool:
        ins = session.query(TransportInsurance).filter(TransportInsurance.id == insurance_id).first()
        if not ins:
            return False
        session.delete(ins)
        session.commit()
        return True

    # ---------------- Vehicle Document Vault ----------------
    @staticmethod
    def get_documents(
        session: Session,
        vehicle_id: Optional[int] = None,
        document_type: Optional[str] = None,
    ) -> List[TransportDocument]:
        query = session.query(TransportDocument).options(joinedload(TransportDocument.vehicle))
        if vehicle_id:
            query = query.filter(TransportDocument.vehicle_id == vehicle_id)
        if document_type:
            query = query.filter(TransportDocument.document_type == document_type)
        return query.order_by(TransportDocument.expiry_date.asc(), TransportDocument.id.desc()).all()

    @staticmethod
    def add_document(
        session: Session,
        vehicle_id: int,
        document_type: str,
        document_number: Optional[str] = None,
        issuing_authority: Optional[str] = None,
        issue_date: Optional[str] = None,
        expiry_date: Optional[str] = None,
        file_path: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[TransportDocument], Optional[str]]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None, "Vehicle not found."

        computed_status = status or _compute_doc_status(expiry_date)
        doc = TransportDocument(
            vehicle_id=vehicle_id,
            document_type=document_type,
            document_number=document_number,
            issuing_authority=issuing_authority,
            issue_date=issue_date,
            expiry_date=expiry_date,
            file_path=file_path,
            status=computed_status,
            notes=notes,
        )
        session.add(doc)

        # Keep summary expiry dates synced on Vehicle
        if expiry_date:
            if document_type == "Registration":
                vehicle.registration_expiry = expiry_date
                if document_number and not vehicle.registration_no:
                    vehicle.registration_no = document_number
            elif document_type == "Fitness":
                vehicle.fitness_expiry = expiry_date
            elif document_type == "Insurance":
                vehicle.insurance_expiry = expiry_date
            elif document_type == "Driver License":
                vehicle.driver_license_expiry = expiry_date

        session.commit()
        session.refresh(doc)
        return doc, None

    @staticmethod
    def update_document(session: Session, doc_id: int, **kwargs) -> Optional[TransportDocument]:
        doc = session.query(TransportDocument).filter(TransportDocument.id == doc_id).first()
        if not doc:
            return None
        for k, v in kwargs.items():
            if hasattr(doc, k):
                setattr(doc, k, v)
        if "status" not in kwargs and "expiry_date" in kwargs:
            doc.status = _compute_doc_status(doc.expiry_date)
        session.commit()
        session.refresh(doc)
        return doc

    @staticmethod
    def delete_document(session: Session, doc_id: int) -> bool:
        doc = session.query(TransportDocument).filter(TransportDocument.id == doc_id).first()
        if not doc:
            return False
        session.delete(doc)
        session.commit()
        return True

    # ---------------- Automated Maintenance & Compliance Reminder Engine ----------------
    @staticmethod
    def get_maintenance_reminders(
        session: Session,
        horizon_days: int = 30,
        odometer_buffer_km: float = 500.0,
        vehicle_id: Optional[int] = None,
        reference_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans vehicles, scheduled maintenance logs, insurance policies, and compliance
        documents to generate actionable Overdue / Due Soon / Upcoming alerts.
        """
        today = reference_date or date.today()
        reminders: List[Dict[str, Any]] = []
        seen_keys = set()

        def _classify_date(due_str: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
            d = _parse_iso_date(due_str)
            if not d:
                return None, None
            delta = (d - today).days
            if delta < 0:
                return "Overdue", delta
            if delta <= horizon_days:
                return "Due Soon", delta
            return None, delta

        def _add_reminder(
            key: Tuple,
            severity: str,
            category: str,
            veh: Vehicle,
            title: str,
            due_date_str: Optional[str] = None,
            due_odo: Optional[float] = None,
            days_rem: Optional[int] = None,
            km_rem: Optional[float] = None,
            details: str = "",
        ):
            if key in seen_keys:
                return
            seen_keys.add(key)
            reminders.append({
                "severity": severity,
                "category": category,
                "vehicle_id": veh.id,
                "vehicle_number": veh.vehicle_number,
                "vehicle_type": veh.vehicle_type,
                "title": title,
                "due_date": due_date_str or "-",
                "due_odometer_km": due_odo,
                "current_odometer_km": float(veh.current_odometer_km or 0.0),
                "days_remaining": days_rem,
                "km_remaining": km_rem,
                "details": details,
            })

        v_query = session.query(Vehicle)
        if vehicle_id:
            v_query = v_query.filter(Vehicle.id == vehicle_id)
        vehicles = v_query.all()
        v_map = {v.id: v for v in vehicles}

        for v in vehicles:
            if v.status == "Out of Service":
                continue

            # 1. Vehicle-level next service by date
            sev, days_rem = _classify_date(v.next_service_date)
            if sev:
                _add_reminder(
                    ("veh_svc_date", v.id, v.next_service_date),
                    sev,
                    "Maintenance (Date)",
                    v,
                    "Scheduled Preventive Service Due",
                    due_date_str=v.next_service_date,
                    due_odo=v.next_service_odometer_km,
                    days_rem=days_rem,
                    details=f"Next service date: {v.next_service_date}",
                )

            # 2. Vehicle-level next service by odometer
            if v.next_service_odometer_km is not None:
                km_rem = round(float(v.next_service_odometer_km) - float(v.current_odometer_km or 0.0), 1)
                if km_rem <= 0:
                    _add_reminder(
                        ("veh_svc_odo", v.id, v.next_service_odometer_km),
                        "Overdue",
                        "Maintenance (Odometer)",
                        v,
                        "Odometer Service Threshold Exceeded",
                        due_date_str=v.next_service_date,
                        due_odo=v.next_service_odometer_km,
                        km_rem=km_rem,
                        details=f"Current {v.current_odometer_km:.0f} km >= Target {v.next_service_odometer_km:.0f} km",
                    )
                elif km_rem <= odometer_buffer_km:
                    _add_reminder(
                        ("veh_svc_odo", v.id, v.next_service_odometer_km),
                        "Due Soon",
                        "Maintenance (Odometer)",
                        v,
                        "Odometer Service Approaching",
                        due_date_str=v.next_service_date,
                        due_odo=v.next_service_odometer_km,
                        km_rem=km_rem,
                        details=f"{km_rem:.0f} km remaining until service ({v.next_service_odometer_km:.0f} km)",
                    )

            # 3. Vehicle summary expiries (Insurance, Fitness, Registration, Driver License)
            summary_checks = [
                ("Insurance", v.insurance_expiry, "Vehicle Insurance Policy Expiry"),
                ("Fitness", v.fitness_expiry, "Vehicle Fitness Certificate Expiry"),
                ("Registration", v.registration_expiry, "Vehicle Registration Renewal"),
                ("Driver License", v.driver_license_expiry, f"Driver License Renewal ({v.driver_name})"),
            ]
            for cat, exp_str, title in summary_checks:
                sev, days_rem = _classify_date(exp_str)
                if sev:
                    _add_reminder(
                        ("veh_exp", v.id, cat, exp_str),
                        sev,
                        cat,
                        v,
                        title,
                        due_date_str=exp_str,
                        days_rem=days_rem,
                        details=f"Expiry date: {exp_str}",
                    )

        # 4. Scheduled / In-Progress maintenance logs & next_service_date from recent logs
        m_query = session.query(TransportMaintenanceLog)
        if vehicle_id:
            m_query = m_query.filter(TransportMaintenanceLog.vehicle_id == vehicle_id)
        for m in m_query.all():
            veh = v_map.get(m.vehicle_id)
            if not veh:
                continue
            if m.status in ("Scheduled", "In Progress"):
                sev, days_rem = _classify_date(m.service_date)
                sev = sev or "Upcoming"
                _add_reminder(
                    ("maint_sched", m.id),
                    sev,
                    "Maintenance (Scheduled)",
                    veh,
                    f"{m.service_type} ({m.status})",
                    due_date_str=m.service_date,
                    due_odo=m.odometer_km,
                    days_rem=days_rem,
                    details=f"Workshop: {m.workshop_name or 'TBD'}",
                )
            elif m.next_service_date:
                sev, days_rem = _classify_date(m.next_service_date)
                if sev:
                    _add_reminder(
                        ("veh_svc_date", veh.id, m.next_service_date),
                        sev,
                        "Maintenance (Follow-Up)",
                        veh,
                        f"Follow-up: {m.service_type}",
                        due_date_str=m.next_service_date,
                        due_odo=m.next_service_odometer_km,
                        days_rem=days_rem,
                        details=f"Last done {m.service_date} at {m.workshop_name or 'workshop'}",
                    )

        # 5. Active Insurance policies
        i_query = session.query(TransportInsurance).filter(TransportInsurance.status == "Active")
        if vehicle_id:
            i_query = i_query.filter(TransportInsurance.vehicle_id == vehicle_id)
        for ins in i_query.all():
            veh = v_map.get(ins.vehicle_id)
            if not veh:
                continue
            sev, days_rem = _classify_date(ins.expiry_date)
            if sev:
                _add_reminder(
                    ("veh_exp", veh.id, "Insurance", ins.expiry_date),
                    sev,
                    "Insurance",
                    veh,
                    f"Policy {ins.policy_number} ({ins.provider})",
                    due_date_str=ins.expiry_date,
                    days_rem=days_rem,
                    details=f"{ins.coverage_type} policy expires {ins.expiry_date}",
                )

        # 6. Compliance Documents
        d_query = session.query(TransportDocument)
        if vehicle_id:
            d_query = d_query.filter(TransportDocument.vehicle_id == vehicle_id)
        for doc in d_query.all():
            veh = v_map.get(doc.vehicle_id)
            if not veh:
                continue
            sev, days_rem = _classify_date(doc.expiry_date)
            if sev:
                _add_reminder(
                    ("doc_exp", veh.id, doc.document_type, doc.expiry_date),
                    sev,
                    doc.document_type,
                    veh,
                    f"{doc.document_type} Document ({doc.document_number or 'On File'})",
                    due_date_str=doc.expiry_date,
                    days_rem=days_rem,
                    details=f"Issuer: {doc.issuing_authority or '-'} | Expires {doc.expiry_date}",
                )

        severity_rank = {"Overdue": 0, "Due Soon": 1, "Upcoming": 2}
        reminders.sort(
            key=lambda r: (
                severity_rank.get(r["severity"], 9),
                r["days_remaining"] if r["days_remaining"] is not None else 9999,
                r["vehicle_number"],
            )
        )
        return reminders

    # ---------------- Hardware-Optional GPS Integration ----------------
    @staticmethod
    def get_gps_devices(session: Session, vehicle_id: Optional[int] = None) -> List[TransportGPSDevice]:
        query = session.query(TransportGPSDevice).options(joinedload(TransportGPSDevice.vehicle))
        if vehicle_id:
            query = query.filter(TransportGPSDevice.vehicle_id == vehicle_id)
        return query.order_by(TransportGPSDevice.id.desc()).all()

    @staticmethod
    def register_gps_device(
        session: Session,
        device_code: str,
        vehicle_id: Optional[int] = None,
        provider_type: str = "Manual",
        imei_or_serial: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        is_enabled: bool = False,
        config_json: Optional[str] = None,
    ) -> TransportGPSDevice:
        device = TransportGPSDevice(
            device_code=device_code,
            vehicle_id=vehicle_id,
            provider_type=provider_type,
            imei_or_serial=imei_or_serial,
            endpoint_url=endpoint_url,
            is_enabled=bool(is_enabled),
            is_mandatory=False,  # GPS hardware is never mandatory
            status="Online" if is_enabled else "Standby",
            config_json=config_json,
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        return device

    @staticmethod
    def update_gps_device(session: Session, device_id: int, **kwargs) -> Optional[TransportGPSDevice]:
        device = session.query(TransportGPSDevice).filter(TransportGPSDevice.id == device_id).first()
        if not device:
            return None
        kwargs.pop("is_mandatory", None)  # Never enforce GPS hardware as mandatory
        for k, v in kwargs.items():
            if hasattr(device, k):
                setattr(device, k, v)
        if "is_enabled" in kwargs and "status" not in kwargs:
            device.status = "Standby" if kwargs["is_enabled"] else "Disabled"
        session.commit()
        session.refresh(device)
        return device

    @staticmethod
    def ingest_gps_ping(
        session: Session,
        vehicle_id: int,
        latitude: float,
        longitude: float,
        speed_kmh: float = 0.0,
        heading_deg: Optional[float] = None,
        ignition_on: bool = True,
        odometer_km: Optional[float] = None,
        device_id: Optional[int] = None,
        route_id: Optional[int] = None,
        source: str = "Manual",
        location_label: Optional[str] = None,
        raw_payload: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ) -> Tuple[Optional[TransportGPSPing], Optional[str]]:
        vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            return None, "Vehicle not found."

        ts = recorded_at or utc_now()
        ping = TransportGPSPing(
            vehicle_id=vehicle_id,
            device_id=device_id,
            route_id=route_id,
            latitude=float(latitude),
            longitude=float(longitude),
            speed_kmh=float(speed_kmh or 0.0),
            heading_deg=float(heading_deg) if heading_deg is not None else None,
            ignition_on=bool(ignition_on),
            odometer_km=float(odometer_km) if odometer_km is not None else None,
            recorded_at=ts,
            source=source,
            location_label=location_label,
            raw_payload=raw_payload,
        )
        session.add(ping)

        if device_id:
            dev = session.query(TransportGPSDevice).filter(TransportGPSDevice.id == device_id).first()
            if dev:
                dev.last_ping_at = ts
                if dev.is_enabled:
                    dev.status = "Online"

        if odometer_km is not None and float(odometer_km) > float(vehicle.current_odometer_km or 0.0):
            vehicle.current_odometer_km = float(odometer_km)

        session.commit()
        session.refresh(ping)
        return ping, None

    @staticmethod
    def get_gps_ping_history(
        session: Session,
        vehicle_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[TransportGPSPing]:
        query = session.query(TransportGPSPing).options(
            joinedload(TransportGPSPing.vehicle),
            joinedload(TransportGPSPing.device),
            joinedload(TransportGPSPing.route),
        )
        if vehicle_id:
            query = query.filter(TransportGPSPing.vehicle_id == vehicle_id)
        return query.order_by(TransportGPSPing.recorded_at.desc(), TransportGPSPing.id.desc()).limit(limit).all()

    @staticmethod
    def get_latest_vehicle_positions(session: Session) -> List[Dict[str, Any]]:
        """
        Returns live or manual telemetry snapshot for every fleet vehicle.
        Works cleanly even when zero GPS hardware devices are registered.
        """
        vehicles = session.query(Vehicle).order_by(Vehicle.vehicle_number.asc()).all()
        snapshots: List[Dict[str, Any]] = []
        for v in vehicles:
            dev = (
                session.query(TransportGPSDevice)
                .filter(TransportGPSDevice.vehicle_id == v.id)
                .order_by(TransportGPSDevice.is_enabled.desc(), TransportGPSDevice.id.desc())
                .first()
            )
            ping = (
                session.query(TransportGPSPing)
                .filter(TransportGPSPing.vehicle_id == v.id)
                .order_by(TransportGPSPing.recorded_at.desc(), TransportGPSPing.id.desc())
                .first()
            )
            snapshots.append({
                "vehicle_id": v.id,
                "vehicle_number": v.vehicle_number,
                "vehicle_type": v.vehicle_type,
                "vehicle_status": v.status,
                "driver_name": v.driver_name,
                "gps_mode": (
                    f"{dev.provider_type} ({'Enabled' if dev.is_enabled else 'Standby'})"
                    if dev
                    else "Hardware-Free (Manual Mode)"
                ),
                "device_code": dev.device_code if dev else None,
                "latitude": ping.latitude if ping else None,
                "longitude": ping.longitude if ping else None,
                "speed_kmh": ping.speed_kmh if ping else None,
                "location_label": ping.location_label if ping else None,
                "last_ping_at": ping.recorded_at.isoformat() if (ping and ping.recorded_at) else None,
                "source": ping.source if ping else "None",
            })
        return snapshots

    # ---------------- Fleet Statistics ----------------
    @staticmethod
    def get_transport_stats(session: Session) -> Dict[str, Any]:
        """Calculates comprehensive transport dashboard metrics."""
        total_vehicles = session.query(Vehicle).count()
        active_vehicles = session.query(Vehicle).filter(Vehicle.status == "Active").count()
        total_routes = session.query(TransportRoute).filter(TransportRoute.status == "Active").count()
        total_capacity = sum(
            v.seating_capacity for v in session.query(Vehicle).filter(Vehicle.status == "Active").all()
        )
        active_pax = session.query(TransportPassenger).filter(TransportPassenger.status == "Active").all()
        allocated_passengers = len(active_pax)
        available_seats = max(0, total_capacity - allocated_passengers)
        monthly_revenue = sum(float(p.monthly_fare or 0.0) for p in active_pax)

        fuel_logs = session.query(TransportFuelLog).all()
        maint_logs = session.query(TransportMaintenanceLog).all()
        fee_charges = session.query(TransportFeeCharge).all()
        reminders = TransportRepository.get_maintenance_reminders(session)
        gps_enabled = session.query(TransportGPSDevice).filter(TransportGPSDevice.is_enabled == True).count()

        fee_billed = sum(c.net_payable for c in fee_charges if c.status != "Waived")
        fee_collected = sum(float(c.paid_amount or 0.0) for c in fee_charges)
        fee_due = sum(c.balance_due for c in fee_charges)

        return {
            "total_vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "total_routes": total_routes,
            "total_capacity": total_capacity,
            "allocated_passengers": allocated_passengers,
            "available_seats": available_seats,
            "monthly_revenue": monthly_revenue,
            "total_fuel_cost": round(sum(float(f.total_cost or 0.0) for f in fuel_logs), 2),
            "total_maintenance_cost": round(sum(float(m.cost or 0.0) for m in maint_logs), 2),
            "fee_billed": round(fee_billed, 2),
            "fee_collected": round(fee_collected, 2),
            "fee_due": round(fee_due, 2),
            "active_reminders": len(reminders),
            "overdue_reminders": sum(1 for r in reminders if r["severity"] == "Overdue"),
            "gps_enabled_vehicles": gps_enabled,
        }
