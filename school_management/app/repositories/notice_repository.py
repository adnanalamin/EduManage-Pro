"""
EduManage Pro - Notice Board & Event Calendar Repository
Phase 13: Notices, Circulars, Academic Events & Holiday Queries
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.models.notice import SchoolNotice, SchoolEvent


class NoticeRepository:
    """Repository handling all database queries for Notices, Circulars, and Calendar Events."""

    # -------------------------------------------------------------
    # 1. School Notices & Circulars
    # -------------------------------------------------------------
    @staticmethod
    def get_all_notices(
        session: Session,
        audience: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SchoolNotice]:
        query = session.query(SchoolNotice)
        if audience and audience != "All":
            query = query.filter(or_(SchoolNotice.target_audience == audience, SchoolNotice.target_audience == "All"))
        if category and category != "All":
            query = query.filter(SchoolNotice.category == category)
        if status:
            query = query.filter(SchoolNotice.status == status)

        # Pinned notices first, then newest publish date
        return query.order_by(SchoolNotice.is_pinned.desc(), SchoolNotice.publish_date.desc(), SchoolNotice.id.desc()).all()

    @staticmethod
    def get_notice_by_id(session: Session, notice_id: int) -> Optional[SchoolNotice]:
        return session.query(SchoolNotice).filter(SchoolNotice.id == notice_id).first()

    @staticmethod
    def get_notice_by_ref(session: Session, ref_no: str) -> Optional[SchoolNotice]:
        return session.query(SchoolNotice).filter(SchoolNotice.reference_no == ref_no).first()

    @staticmethod
    def create_notice(
        session: Session,
        title: str,
        content: str,
        category: str = "Academic",
        target_audience: str = "All",
        target_class_id: Optional[int] = None,
        priority: str = "Normal",
        is_pinned: bool = False,
        publish_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        attachment_name: Optional[str] = None,
        status: str = "Published",
        created_by: str = "Principal Office"
    ) -> SchoolNotice:
        # Generate auto reference: CIR-YYYY/XXXX
        year = (publish_date or date.today()).year
        count = session.query(SchoolNotice).count() + 1
        ref_no = f"CIR-{year}/{count:03d}"

        notice = SchoolNotice(
            reference_no=ref_no,
            title=title.strip(),
            content=content.strip(),
            category=category,
            target_audience=target_audience,
            target_class_id=target_class_id,
            priority=priority,
            is_pinned=is_pinned or (priority == "Urgent"),
            publish_date=publish_date or date.today(),
            expiry_date=expiry_date,
            attachment_name=attachment_name.strip() if attachment_name else None,
            status=status,
            created_by=created_by.strip()
        )
        session.add(notice)
        session.commit()
        session.refresh(notice)
        return notice

    @staticmethod
    def update_notice(session: Session, notice_id: int, **kwargs) -> Optional[SchoolNotice]:
        notice = session.query(SchoolNotice).filter(SchoolNotice.id == notice_id).first()
        if not notice:
            return None
        for key, value in kwargs.items():
            if hasattr(notice, key):
                setattr(notice, key, value)
        session.commit()
        session.refresh(notice)
        return notice

    @staticmethod
    def delete_notice(session: Session, notice_id: int) -> bool:
        notice = session.query(SchoolNotice).filter(SchoolNotice.id == notice_id).first()
        if not notice:
            return False
        session.delete(notice)
        session.commit()
        return True

    # -------------------------------------------------------------
    # 2. School Events & Academic Calendar
    # -------------------------------------------------------------
    @staticmethod
    def get_all_events(
        session: Session,
        start_after: Optional[date] = None,
        category: Optional[str] = None
    ) -> List[SchoolEvent]:
        query = session.query(SchoolEvent)
        if start_after:
            query = query.filter(SchoolEvent.end_date >= start_after)
        if category and category != "All":
            query = query.filter(SchoolEvent.event_category == category)
        return query.order_by(SchoolEvent.start_date.asc()).all()

    @staticmethod
    def get_events_between(session: Session, from_date: date, to_date: date) -> List[SchoolEvent]:
        return session.query(SchoolEvent).filter(
            or_(
                and_(SchoolEvent.start_date >= from_date, SchoolEvent.start_date <= to_date),
                and_(SchoolEvent.end_date >= from_date, SchoolEvent.end_date <= to_date),
                and_(SchoolEvent.start_date <= from_date, SchoolEvent.end_date >= to_date)
            )
        ).order_by(SchoolEvent.start_date.asc()).all()

    @staticmethod
    def is_date_holiday(session: Session, check_date: date) -> bool:
        """Checks if a given calendar date falls within an official school holiday."""
        event = session.query(SchoolEvent).filter(
            SchoolEvent.is_holiday == True,
            SchoolEvent.start_date <= check_date,
            SchoolEvent.end_date >= check_date
        ).first()
        return event is not None

    @staticmethod
    def create_event(
        session: Session,
        event_title: str,
        start_date: date,
        end_date: date,
        event_category: str = "Academic",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        venue: str = "Campus Main Auditorium",
        target_audience: str = "All",
        is_holiday: bool = False,
        color_code: Optional[str] = None,
        description: Optional[str] = None,
        organizer: str = "School Administration"
    ) -> SchoolEvent:
        if not color_code:
            if is_holiday or event_category == "Holiday":
                color_code = "#DC2626"  # Red for holidays
            elif event_category == "Exam":
                color_code = "#D97706"  # Amber for exams
            elif event_category == "Sports":
                color_code = "#2563EB"  # Blue for sports
            elif event_category == "Cultural":
                color_code = "#7C3AED"  # Purple for cultural
            else:
                color_code = "#059669"  # Emerald

        event = SchoolEvent(
            event_title=event_title.strip(),
            start_date=start_date,
            end_date=end_date,
            event_category=event_category,
            start_time=start_time,
            end_time=end_time,
            venue=venue.strip(),
            target_audience=target_audience,
            is_holiday=is_holiday or (event_category == "Holiday"),
            color_code=color_code,
            description=description.strip() if description else None,
            organizer=organizer.strip()
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    @staticmethod
    def update_event(session: Session, event_id: int, **kwargs) -> Optional[SchoolEvent]:
        event = session.query(SchoolEvent).filter(SchoolEvent.id == event_id).first()
        if not event:
            return None
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)
        session.commit()
        session.refresh(event)
        return event

    @staticmethod
    def delete_event(session: Session, event_id: int) -> bool:
        event = session.query(SchoolEvent).filter(SchoolEvent.id == event_id).first()
        if not event:
            return False
        session.delete(event)
        session.commit()
        return True

    # -------------------------------------------------------------
    # 3. Aggregations & Metrics
    # -------------------------------------------------------------
    @staticmethod
    def get_notice_stats(session: Session) -> Dict[str, Any]:
        total_notices = session.query(SchoolNotice).count()
        published_notices = session.query(SchoolNotice).filter(SchoolNotice.status == "Published").count()
        urgent_alerts = session.query(SchoolNotice).filter(
            SchoolNotice.priority == "Urgent",
            SchoolNotice.status == "Published"
        ).count()

        today = date.today()
        upcoming_events = session.query(SchoolEvent).filter(SchoolEvent.end_date >= today).count()
        total_holidays = session.query(SchoolEvent).filter(SchoolEvent.is_holiday == True).count()

        return {
            "total_notices": total_notices,
            "published_notices": published_notices,
            "urgent_alerts": urgent_alerts,
            "upcoming_events": upcoming_events,
            "total_holidays": total_holidays
        }
