"""
EduManage Pro - Certificate Repository
Handles certificate serial numbering, verification queries, and registry CRUD.
"""

import uuid
from datetime import date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.certificate import CertificateRecord


TYPE_PREFIX_MAP = {
    "Transfer Certificate": "TC",
    "Character Certificate": "CC",
    "Testimonial": "TM",
    "Bonafide Certificate": "BF",
    "Merit Certificate": "MR",
    "Staff Experience Letter": "EX",
}


class CertificateRepository:
    @staticmethod
    def generate_serial_number(db: Session, certificate_type: str) -> str:
        prefix = TYPE_PREFIX_MAP.get(certificate_type, "CT")
        year = date.today().year
        count = db.query(CertificateRecord).filter(
            CertificateRecord.certificate_type == certificate_type
        ).count()
        return f"CERT-{prefix}-{year}-{count + 1:04d}"

    @staticmethod
    def generate_verification_code() -> str:
        return f"VER-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def create(db: Session, **kwargs) -> CertificateRecord:
        if "certificate_number" not in kwargs or not kwargs["certificate_number"]:
            kwargs["certificate_number"] = CertificateRepository.generate_serial_number(
                db, kwargs.get("certificate_type", "Bonafide Certificate")
            )
        if "verification_code" not in kwargs or not kwargs["verification_code"]:
            kwargs["verification_code"] = CertificateRepository.generate_verification_code()

        record = CertificateRecord(**kwargs)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_all(
        db: Session,
        certificate_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[CertificateRecord]:
        query = db.query(CertificateRecord)
        if certificate_type and certificate_type != "All":
            query = query.filter(CertificateRecord.certificate_type == certificate_type)
        if status and status != "All":
            query = query.filter(CertificateRecord.status == status)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                (CertificateRecord.certificate_number.ilike(term))
                | (CertificateRecord.recipient_name.ilike(term))
                | (CertificateRecord.recipient_code.ilike(term))
                | (CertificateRecord.verification_code.ilike(term))
            )
        return query.order_by(CertificateRecord.id.desc()).all()

    @staticmethod
    def get_by_id(db: Session, cert_id: int) -> Optional[CertificateRecord]:
        return db.query(CertificateRecord).filter(CertificateRecord.id == cert_id).first()

    @staticmethod
    def verify_credential(db: Session, token_or_serial: str) -> Optional[CertificateRecord]:
        clean = token_or_serial.strip()
        if not clean:
            return None
        return db.query(CertificateRecord).filter(
            (CertificateRecord.certificate_number == clean)
            | (CertificateRecord.verification_code == clean)
        ).first()

    @staticmethod
    def revoke(db: Session, cert_id: int, reason: Optional[str] = None) -> Optional[CertificateRecord]:
        record = db.query(CertificateRecord).filter(CertificateRecord.id == cert_id).first()
        if not record:
            return None
        record.status = "Revoked"
        if reason:
            record.remarks = f"[REVOKED: {reason}] " + (record.remarks or "")
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        all_certs = db.query(CertificateRecord).all()
        issued = [c for c in all_certs if c.status == "Issued"]
        revoked = [c for c in all_certs if c.status == "Revoked"]
        tc_count = len([c for c in issued if c.certificate_type == "Transfer Certificate"])
        merit_count = len([c for c in issued if c.certificate_type in ("Merit Certificate", "Testimonial")])
        return {
            "total": len(all_certs),
            "issued": len(issued),
            "revoked": len(revoked),
            "transfer_certificates": tc_count,
            "merit_and_testimonials": merit_count,
        }
