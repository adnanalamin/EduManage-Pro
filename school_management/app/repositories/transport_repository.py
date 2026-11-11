"""
EduManage Pro - Transport Repository
Phase 11: Vehicle Registry, Route Network, Passenger Seat Allocations & Fleet KPIs
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from app.models.transport import Vehicle, TransportRoute, TransportStop, TransportPassenger
from app.models.student import Student
from app.models.staff import Teacher


class TransportRepository:
    """Repository handling fleet vehicles, route stops, passenger allocations, and revenue metrics."""

    # ---------------- Vehicle Fleet Operations ----------------
    @staticmethod
    def get_vehicles(session: Session, status: Optional[str] = None, vehicle_type: Optional[str] = None) -> List[Vehicle]:
        query = session.query(Vehicle).options(joinedload(Vehicle.routes), joinedload(Vehicle.passengers))
        if status:
            query = query.filter(Vehicle.status == status)
        if vehicle_type:
            query = query.filter(Vehicle.vehicle_type == vehicle_type)
        return query.order_by(Vehicle.id.desc()).all()

    @staticmethod
    def get_vehicle_by_id(session: Session, vehicle_id: int) -> Optional[Vehicle]:
        return session.query(Vehicle).options(
            joinedload(Vehicle.routes),
            joinedload(Vehicle.passengers)
        ).filter(Vehicle.id == vehicle_id).first()

    @staticmethod
    def create_vehicle(session: Session, **kwargs) -> Vehicle:
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

    # ---------------- Route Operations ----------------
    @staticmethod
    def get_routes(session: Session, status: Optional[str] = None) -> List[TransportRoute]:
        query = session.query(TransportRoute).options(
            joinedload(TransportRoute.vehicle),
            joinedload(TransportRoute.stops),
            joinedload(TransportRoute.passengers)
        )
        if status:
            query = query.filter(TransportRoute.status == status)
        return query.order_by(TransportRoute.route_code.asc()).all()

    @staticmethod
    def get_route_by_id(session: Session, route_id: int) -> Optional[TransportRoute]:
        return session.query(TransportRoute).options(
            joinedload(TransportRoute.vehicle),
            joinedload(TransportRoute.stops),
            joinedload(TransportRoute.passengers)
        ).filter(TransportRoute.id == route_id).first()

    @staticmethod
    def create_route(session: Session, **kwargs) -> TransportRoute:
        route = TransportRoute(**kwargs)
        session.add(route)
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
        fare: float = 0.0
    ) -> TransportStop:
        stop = TransportStop(
            route_id=route_id,
            stop_name=stop_name,
            stop_order=stop_order,
            pickup_time=pickup_time,
            drop_time=drop_time,
            fare=fare
        )
        session.add(stop)
        session.commit()
        session.refresh(stop)
        return stop

    # ---------------- Passenger Allocations ----------------
    @staticmethod
    def get_passengers(
        session: Session,
        route_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[TransportPassenger]:
        query = session.query(TransportPassenger).options(
            joinedload(TransportPassenger.student),
            joinedload(TransportPassenger.teacher),
            joinedload(TransportPassenger.route),
            joinedload(TransportPassenger.vehicle),
            joinedload(TransportPassenger.stop)
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
            joinedload(TransportPassenger.route),
            joinedload(TransportPassenger.vehicle),
            joinedload(TransportPassenger.stop)
        ).filter(TransportPassenger.id == passenger_id).first()

    @staticmethod
    def allocate_passenger(
        session: Session,
        passenger_type: str,
        route_id: int,
        allocation_date: str,
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        stop_id: Optional[int] = None,
        seat_number: Optional[str] = None,
        monthly_fare: Optional[float] = None,
        remarks: Optional[str] = None
    ) -> Tuple[Optional[TransportPassenger], Optional[str]]:
        """
        Allocates passenger to route and vehicle with seating capacity and duplicate checks.
        """
        route = session.query(TransportRoute).filter(TransportRoute.id == route_id).first()
        if not route:
            return None, "Transport route not found."

        # Target vehicle
        target_v_id = vehicle_id or route.vehicle_id
        if target_v_id:
            v = session.query(Vehicle).filter(Vehicle.id == target_v_id).first()
            if v:
                active_count = session.query(TransportPassenger).filter(
                    TransportPassenger.vehicle_id == target_v_id,
                    TransportPassenger.status == "Active"
                ).count()
                if active_count >= v.seating_capacity:
                    return None, f"Vehicle '{v.vehicle_number}' is fully booked ({active_count}/{v.seating_capacity} seats)."

        # Check existing active allocation
        if student_id:
            existing = session.query(TransportPassenger).filter(
                TransportPassenger.student_id == student_id,
                TransportPassenger.status == "Active"
            ).first()
            if existing:
                return None, f"Student is already allocated to active Route '{existing.route.route_name if existing.route else ''}'."
        elif teacher_id:
            existing = session.query(TransportPassenger).filter(
                TransportPassenger.teacher_id == teacher_id,
                TransportPassenger.status == "Active"
            ).first()
            if existing:
                return None, f"Teacher is already allocated to active Route '{existing.route.route_name if existing.route else ''}'."

        fare = monthly_fare if monthly_fare is not None else route.monthly_fee

        passenger = TransportPassenger(
            passenger_type=passenger_type,
            student_id=student_id,
            teacher_id=teacher_id,
            route_id=route_id,
            vehicle_id=target_v_id,
            stop_id=stop_id,
            seat_number=seat_number,
            allocation_date=allocation_date,
            monthly_fare=fare,
            status="Active",
            remarks=remarks
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

    # ---------------- Fleet Statistics ----------------
    @staticmethod
    def get_transport_stats(session: Session) -> Dict[str, Any]:
        """Calculates transport dashboard metrics."""
        total_vehicles = session.query(Vehicle).count()
        active_vehicles = session.query(Vehicle).filter(Vehicle.status == "Active").count()
        total_routes = session.query(TransportRoute).filter(TransportRoute.status == "Active").count()
        total_capacity = sum(v.seating_capacity for v in session.query(Vehicle).filter(Vehicle.status == "Active").all())
        allocated_passengers = session.query(TransportPassenger).filter(TransportPassenger.status == "Active").count()
        available_seats = max(0, total_capacity - allocated_passengers)
        monthly_revenue = sum(p.monthly_fare for p in session.query(TransportPassenger).filter(TransportPassenger.status == "Active").all())

        return {
            "total_vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "total_routes": total_routes,
            "total_capacity": total_capacity,
            "allocated_passengers": allocated_passengers,
            "available_seats": available_seats,
            "monthly_revenue": monthly_revenue,
        }
