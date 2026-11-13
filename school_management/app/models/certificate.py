"""
EduManage Pro - Certificate & Official Credentials Model
Phase 15: Transfer Certificates, Testimonials, Character, Bonafide, Merit & Staff Experience Letters
"""

from datetime import date
from sqlalchemy import Column, String, Integer, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.models.base import TimestampMixin


class CertificateRecord(Base, TimestampMixin):
    __tablename__ = "certificates"

    certificate_number = Column(String(60), unique=True, nullable=False, index=True)  # e.g. CERT-TC-2026-0001
    verification_code = Column(String(40), unique=True, nullable=False, index=True)   # e.g. VER-8F9A21C4
    certificate_type = Column(String(60), nullable=False, index=True)
    # Types: Transfer Certificate, Character Certificate, Testimonial, Bonafide Certificate, Merit Certificate, Staff Experience Letter

    recipient_type = Column(String(20), default="Student", nullable=False)  # Student | Staff
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff_members.id", ondelete="SET NULL"), nullable=True)

    recipient_name = Column(String(150), nullable=False)
    recipient_code = Column(String(50), nullable=False)  # STU-xxx or STF-xxx
    class_or_designation = Column(String(120), nullable=True)
    father_or_guardian = Column(String(150), nullable=True)

    issue_date = Column(Date, default=date.today, nullable=False)
    leaving_date = Column(Date, nullable=True)
    conduct_grade = Column(String(40), default="Exemplary", nullable=False)
    reason_or_purpose = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)

    status = Column(String(20), default="Issued", nullable=False)  # Issued | Revoked
    issued_by = Column(String(100), default="Principal Office", nullable=False)

    student = relationship("Student")

    def __repr__(self):
        return f"<CertificateRecord(no='{self.certificate_number}', type='{self.certificate_type}', recipient='{self.recipient_name}')>"
