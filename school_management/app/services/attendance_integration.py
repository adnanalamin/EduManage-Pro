"""
EduManage Pro - Optional Attendance Capture Integration Architecture
Provides a pluggable, non-mandatory adapter layer for:
- QR Code scanning (integrates out-of-the-box with Student Digital IDs & Employee IDs)
- RFID Card / Badge readers
- Biometric Fingerprint terminals
- Future Face Recognition gateways

CRITICAL DESIGN PRINCIPLE:
Physical hardware is strictly OPTIONAL. Manual attendance workflows in AttendanceService
never require any configured device or adapter to operate.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time
import json
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.attendance import (
    AttendanceCredentialMapping,
    AttendanceDeviceConfig,
    AttendanceScanLog,
    AttendanceStatus,
    StaffAttendance,
    StudentAttendance,
    TeacherAttendance,
)
from app.models.base import utc_now
from app.models.staff import Staff, Teacher
from app.models.student import Student


class AdapterType:
    QR = "QR"
    RFID = "RFID"
    BIOMETRIC = "Biometric"
    FACE_RECOGNITION = "FaceRecognition"

    ALL: List[str] = [QR, RFID, BIOMETRIC, FACE_RECOGNITION]


@dataclass
class ScanPayload:
    adapter_type: str
    raw_identifier: str
    device_code: Optional[str] = None
    direction: str = "CHECK_IN"  # CHECK_IN | CHECK_OUT
    scan_timestamp: Optional[datetime] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolvedSubject:
    subject_type: str  # student | teacher | staff
    subject_id: int
    full_name: str
    identifier_display: str
    class_id: Optional[int] = None
    section_id: Optional[int] = None


def _build_subject_from_mapping(db: Session, mapping: AttendanceCredentialMapping) -> Optional[ResolvedSubject]:
    if not mapping or not mapping.is_active:
        return None
    if mapping.subject_type == "student" and mapping.student_id:
        stu = db.query(Student).filter(Student.id == mapping.student_id, Student.is_deleted == False).first()
        if stu:
            return ResolvedSubject(
                subject_type="student",
                subject_id=stu.id,
                full_name=stu.full_name,
                identifier_display=stu.student_id,
                class_id=stu.class_id,
                section_id=stu.section_id,
            )
    elif mapping.subject_type == "teacher" and mapping.teacher_id:
        t = db.query(Teacher).filter(Teacher.id == mapping.teacher_id, Teacher.is_deleted == False).first()
        if t:
            return ResolvedSubject(
                subject_type="teacher",
                subject_id=t.id,
                full_name=t.full_name,
                identifier_display=t.employee_id,
            )
    elif mapping.subject_type == "staff" and mapping.staff_id:
        s = db.query(Staff).filter(Staff.id == mapping.staff_id, Staff.is_deleted == False).first()
        if s:
            return ResolvedSubject(
                subject_type="staff",
                subject_id=s.id,
                full_name=s.full_name,
                identifier_display=s.employee_id,
            )
    return None


class BaseAttendanceAdapter(ABC):
    adapter_type: str = "Generic"
    display_name: str = "Generic Capture Adapter"
    requires_physical_hardware: bool = False

    def normalize_token(self, raw_identifier: str) -> str:
        return (raw_identifier or "").strip()

    def validate_payload(self, payload: ScanPayload, device_cfg: Optional[AttendanceDeviceConfig] = None) -> Tuple[bool, str]:
        token = self.normalize_token(payload.raw_identifier)
        if not token:
            return False, f"{self.adapter_type} scan identifier cannot be empty."
        direction = (payload.direction or "CHECK_IN").strip().upper()
        if direction not in ("CHECK_IN", "CHECK_OUT"):
            return False, "Scan direction must be 'CHECK_IN' or 'CHECK_OUT'."
        return True, "OK"

    @abstractmethod
    def resolve_subject(self, db: Session, token: str) -> Optional[ResolvedSubject]:
        raise NotImplementedError


class QRAttendanceAdapter(BaseAttendanceAdapter):
    adapter_type = AdapterType.QR
    display_name = "QR Digital ID Scanner (Software / Webcam / USB Scanner)"
    requires_physical_hardware = False

    def normalize_token(self, raw_identifier: str) -> str:
        raw = (raw_identifier or "").strip()
        if raw.startswith("{") and raw.endswith("}"):
            try:
                parsed = json.loads(raw)
                for key in ("digital_id_code", "digital_id", "qr_code", "student_id", "employee_id", "teacher_id", "staff_id", "code"):
                    if parsed.get(key):
                        return str(parsed[key]).strip()
            except Exception:
                pass
        return raw

    def resolve_subject(self, db: Session, token: str) -> Optional[ResolvedSubject]:
        # 1. Explicit credential binding
        mapping = (
            db.query(AttendanceCredentialMapping)
            .filter(
                AttendanceCredentialMapping.qr_code_value == token,
                AttendanceCredentialMapping.is_active == True,
            )
            .first()
        )
        if mapping:
            subj = _build_subject_from_mapping(db, mapping)
            if subj:
                return subj

        # 2. Student Digital ID / Student ID / QR Payload (out-of-the-box Student CRM integration)
        stu = (
            db.query(Student)
            .filter(
                Student.is_deleted == False,
                or_(
                    Student.digital_id_code == token,
                    Student.student_id == token,
                    Student.qr_payload == token,
                ),
            )
            .first()
        )
        if stu:
            return ResolvedSubject(
                subject_type="student",
                subject_id=stu.id,
                full_name=stu.full_name,
                identifier_display=stu.student_id,
                class_id=stu.class_id,
                section_id=stu.section_id,
            )

        # 3. Teacher Employee ID / Teacher ID
        tch = (
            db.query(Teacher)
            .filter(
                Teacher.is_deleted == False,
                or_(Teacher.teacher_id == token, Teacher.employee_id == token),
            )
            .first()
        )
        if tch:
            return ResolvedSubject(
                subject_type="teacher",
                subject_id=tch.id,
                full_name=tch.full_name,
                identifier_display=tch.employee_id,
            )

        # 4. Staff Employee ID / Staff ID
        stf = (
            db.query(Staff)
            .filter(
                Staff.is_deleted == False,
                or_(Staff.staff_id == token, Staff.employee_id == token),
            )
            .first()
        )
        if stf:
            return ResolvedSubject(
                subject_type="staff",
                subject_id=stf.id,
                full_name=stf.full_name,
                identifier_display=stf.employee_id,
            )
        return None


class RFIDAttendanceAdapter(BaseAttendanceAdapter):
    adapter_type = AdapterType.RFID
    display_name = "RFID Badge / Smart Card Reader"
    requires_physical_hardware = False

    def normalize_token(self, raw_identifier: str) -> str:
        return (raw_identifier or "").strip().replace(":", "").replace(" ", "").upper()

    def resolve_subject(self, db: Session, token: str) -> Optional[ResolvedSubject]:
        mapping = (
            db.query(AttendanceCredentialMapping)
            .filter(
                AttendanceCredentialMapping.rfid_uid == token,
                AttendanceCredentialMapping.is_active == True,
            )
            .first()
        )
        return _build_subject_from_mapping(db, mapping) if mapping else None


class BiometricAttendanceAdapter(BaseAttendanceAdapter):
    adapter_type = AdapterType.BIOMETRIC
    display_name = "Biometric Fingerprint / Palm Terminal"
    requires_physical_hardware = False

    def validate_payload(self, payload: ScanPayload, device_cfg: Optional[AttendanceDeviceConfig] = None) -> Tuple[bool, str]:
        ok, msg = super().validate_payload(payload, device_cfg)
        if not ok:
            return False, msg
        if payload.confidence_score is not None and payload.confidence_score < 0.5:
            return False, f"Biometric verification match score ({payload.confidence_score:.2f}) is below acceptance threshold."
        return True, "OK"

    def resolve_subject(self, db: Session, token: str) -> Optional[ResolvedSubject]:
        mapping = (
            db.query(AttendanceCredentialMapping)
            .filter(
                AttendanceCredentialMapping.biometric_template_id == token,
                AttendanceCredentialMapping.is_active == True,
            )
            .first()
        )
        return _build_subject_from_mapping(db, mapping) if mapping else None


class FaceRecognitionAdapter(BaseAttendanceAdapter):
    adapter_type = AdapterType.FACE_RECOGNITION
    display_name = "AI Face Recognition Camera Gateway (Future-Ready)"
    requires_physical_hardware = False
    DEFAULT_MIN_CONFIDENCE = 0.85

    def validate_payload(self, payload: ScanPayload, device_cfg: Optional[AttendanceDeviceConfig] = None) -> Tuple[bool, str]:
        ok, msg = super().validate_payload(payload, device_cfg)
        if not ok:
            return False, msg
        min_conf = self.DEFAULT_MIN_CONFIDENCE
        if device_cfg and device_cfg.config_json:
            try:
                cfg = json.loads(device_cfg.config_json)
                min_conf = float(cfg.get("min_confidence", min_conf))
            except Exception:
                pass
        if payload.confidence_score is None:
            return False, "Face recognition scan requires a confidence_score (0.0 - 1.0)."
        if payload.confidence_score < min_conf:
            return (
                False,
                f"Face match confidence {payload.confidence_score:.2f} is below required threshold {min_conf:.2f}.",
            )
        return True, "OK"

    def resolve_subject(self, db: Session, token: str) -> Optional[ResolvedSubject]:
        mapping = (
            db.query(AttendanceCredentialMapping)
            .filter(
                AttendanceCredentialMapping.face_profile_id == token,
                AttendanceCredentialMapping.is_active == True,
            )
            .first()
        )
        return _build_subject_from_mapping(db, mapping) if mapping else None


class AttendanceIntegrationManager:
    """Central registry & processor for optional automated attendance capture channels."""

    _ADAPTERS: Dict[str, BaseAttendanceAdapter] = {
        AdapterType.QR: QRAttendanceAdapter(),
        AdapterType.RFID: RFIDAttendanceAdapter(),
        AdapterType.BIOMETRIC: BiometricAttendanceAdapter(),
        AdapterType.FACE_RECOGNITION: FaceRecognitionAdapter(),
    }

    @classmethod
    def register_adapter(cls, adapter: BaseAttendanceAdapter) -> None:
        cls._ADAPTERS[adapter.adapter_type] = adapter

    @classmethod
    def get_adapter(cls, adapter_type: str) -> Optional[BaseAttendanceAdapter]:
        if not adapter_type:
            return None
        for key, adapter in cls._ADAPTERS.items():
            if key.lower() == adapter_type.strip().lower():
                return adapter
        return None

    @classmethod
    def list_supported_adapters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "adapter_type": a.adapter_type,
                "display_name": a.display_name,
                "requires_physical_hardware": a.requires_physical_hardware,
            }
            for a in cls._ADAPTERS.values()
        ]

    @classmethod
    def register_device(
        cls,
        db: Session,
        device_code: str,
        name: str,
        adapter_type: str,
        connection_mode: str = "Simulated",
        endpoint_or_port: Optional[str] = None,
        location: Optional[str] = None,
        is_enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[AttendanceDeviceConfig], str]:
        adapter = cls.get_adapter(adapter_type)
        if not adapter:
            return False, None, f"Unsupported adapter type '{adapter_type}'."

        code = (device_code or "").strip().upper()
        if not code:
            return False, None, "Device code is required."

        existing = db.query(AttendanceDeviceConfig).filter_by(device_code=code).first()
        cfg_json = json.dumps(config) if config else None
        if existing:
            existing.name = name.strip()
            existing.adapter_type = adapter.adapter_type
            existing.connection_mode = connection_mode
            existing.endpoint_or_port = endpoint_or_port
            existing.location = location
            existing.is_enabled = is_enabled
            existing.is_mandatory = False  # Hardware is strictly optional
            if cfg_json is not None:
                existing.config_json = cfg_json
            db.commit()
            db.refresh(existing)
            return True, existing, f"Updated optional {adapter.adapter_type} device '{code}'."

        dev = AttendanceDeviceConfig(
            device_code=code,
            name=name.strip(),
            adapter_type=adapter.adapter_type,
            connection_mode=connection_mode,
            endpoint_or_port=endpoint_or_port,
            location=location,
            is_enabled=is_enabled,
            is_mandatory=False,
            config_json=cfg_json,
        )
        db.add(dev)
        db.commit()
        db.refresh(dev)
        return True, dev, f"Registered optional {adapter.adapter_type} device '{code}'."

    @classmethod
    def list_devices(cls, db: Session, adapter_type: Optional[str] = None) -> List[AttendanceDeviceConfig]:
        q = db.query(AttendanceDeviceConfig)
        if adapter_type:
            q = q.filter(AttendanceDeviceConfig.adapter_type == adapter_type)
        return q.order_by(AttendanceDeviceConfig.adapter_type.asc(), AttendanceDeviceConfig.name.asc()).all()

    @classmethod
    def bind_credential(
        cls,
        db: Session,
        subject_type: str,
        subject_pk: int,
        qr_code_value: Optional[str] = None,
        rfid_uid: Optional[str] = None,
        biometric_template_id: Optional[str] = None,
        face_profile_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Tuple[bool, Optional[AttendanceCredentialMapping], str]:
        stype = (subject_type or "").strip().lower()
        if stype not in ("student", "teacher", "staff"):
            return False, None, "subject_type must be 'student', 'teacher', or 'staff'."

        fk_col = {
            "student": AttendanceCredentialMapping.student_id,
            "teacher": AttendanceCredentialMapping.teacher_id,
            "staff": AttendanceCredentialMapping.staff_id,
        }[stype]

        # Validate subject exists
        model_cls = {"student": Student, "teacher": Teacher, "staff": Staff}[stype]
        subject_obj = db.query(model_cls).filter(model_cls.id == subject_pk).first()
        if not subject_obj:
            return False, None, f"{stype.capitalize()} record not found."

        norm_rfid = cls._ADAPTERS[AdapterType.RFID].normalize_token(rfid_uid) if rfid_uid else None
        norm_qr = qr_code_value.strip() if qr_code_value else None
        norm_bio = biometric_template_id.strip() if biometric_template_id else None
        norm_face = face_profile_id.strip() if face_profile_id else None

        existing = db.query(AttendanceCredentialMapping).filter(fk_col == subject_pk).first()
        try:
            if existing:
                if norm_qr is not None:
                    existing.qr_code_value = norm_qr or None
                if norm_rfid is not None:
                    existing.rfid_uid = norm_rfid or None
                if norm_bio is not None:
                    existing.biometric_template_id = norm_bio or None
                if norm_face is not None:
                    existing.face_profile_id = norm_face or None
                if notes is not None:
                    existing.notes = notes
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                return True, existing, f"Updated capture credentials for {subject_obj.full_name}."

            kwargs: Dict[str, Any] = {
                "subject_type": stype,
                f"{stype}_id": subject_pk,
                "qr_code_value": norm_qr or None,
                "rfid_uid": norm_rfid or None,
                "biometric_template_id": norm_bio or None,
                "face_profile_id": norm_face or None,
                "notes": notes,
                "is_active": True,
            }
            mapping = AttendanceCredentialMapping(**kwargs)
            db.add(mapping)
            db.commit()
            db.refresh(mapping)
            return True, mapping, f"Bound capture credentials for {subject_obj.full_name}."
        except Exception as exc:
            db.rollback()
            return False, None, f"Failed to bind credential (possible duplicate token): {exc}"

    @classmethod
    def ingest_scan(
        cls,
        db: Session,
        payload: ScanPayload,
        late_cutoff: dt_time = dt_time(8, 30),
        actor: str = "scan_gateway",
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Process a scan from QR, RFID, Biometric, or Face Recognition.
        Hardware device configuration is optional; works directly even with zero configured devices.
        """
        adapter = cls.get_adapter(payload.adapter_type)
        if not adapter:
            return False, None, f"Unsupported adapter '{payload.adapter_type}'."

        device_cfg: Optional[AttendanceDeviceConfig] = None
        if payload.device_code:
            device_cfg = (
                db.query(AttendanceDeviceConfig)
                .filter(AttendanceDeviceConfig.device_code == payload.device_code.strip().upper())
                .first()
            )
            if device_cfg and not device_cfg.is_enabled:
                return False, None, f"Device '{device_cfg.device_code}' is currently disabled."

        ok, val_msg = adapter.validate_payload(payload, device_cfg)
        if not ok:
            log = AttendanceScanLog(
                adapter_type=adapter.adapter_type,
                device_id=payload.device_code,
                raw_identifier=(payload.raw_identifier or "")[:180],
                scan_timestamp=payload.scan_timestamp or utc_now(),
                direction=(payload.direction or "CHECK_IN").upper(),
                confidence_score=payload.confidence_score,
                processing_status="Error",
                notes=val_msg[:255],
            )
            db.add(log)
            db.commit()
            return False, None, val_msg

        token = adapter.normalize_token(payload.raw_identifier)
        subject = adapter.resolve_subject(db, token)
        scan_dt = payload.scan_timestamp or datetime.now()
        scan_date = scan_dt.date()
        scan_time_str = scan_dt.strftime("%I:%M %p")
        direction = (payload.direction or "CHECK_IN").strip().upper()

        if not subject:
            log = AttendanceScanLog(
                adapter_type=adapter.adapter_type,
                device_id=payload.device_code,
                raw_identifier=token[:180],
                scan_timestamp=utc_now(),
                direction=direction,
                confidence_score=payload.confidence_score,
                processing_status="Unmatched",
                notes="No matching active student, teacher, or staff found.",
            )
            db.add(log)
            db.commit()
            return False, None, f"Unmatched {adapter.adapter_type} identifier '{token}'."

        computed_status = (
            AttendanceStatus.LATE if scan_dt.time() > late_cutoff else AttendanceStatus.PRESENT
        )

        # Upsert attendance row for resolved subject
        proc_status = "Applied"
        if subject.subject_type == "student":
            att = (
                db.query(StudentAttendance)
                .filter(StudentAttendance.student_id == subject.subject_id, StudentAttendance.date == scan_date)
                .first()
            )
            if direction == "CHECK_IN":
                if att and att.capture_source == adapter.adapter_type and att.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
                    proc_status = "Duplicate"
                elif att:
                    att.status = computed_status
                    att.check_in_time = scan_time_str
                    att.capture_source = adapter.adapter_type
                    att.device_id = payload.device_code
                    att.marked_by = actor
                else:
                    att = StudentAttendance(
                        student_id=subject.subject_id,
                        class_id=subject.class_id,
                        section_id=subject.section_id,
                        date=scan_date,
                        status=computed_status,
                        check_in_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            else:  # CHECK_OUT
                if att:
                    att.check_out_time = scan_time_str
                else:
                    att = StudentAttendance(
                        student_id=subject.subject_id,
                        class_id=subject.class_id,
                        section_id=subject.section_id,
                        date=scan_date,
                        status=AttendanceStatus.PRESENT,
                        check_out_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Check-out captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            final_status = att.status

        elif subject.subject_type == "teacher":
            att = (
                db.query(TeacherAttendance)
                .filter(TeacherAttendance.teacher_id == subject.subject_id, TeacherAttendance.date == scan_date)
                .first()
            )
            if direction == "CHECK_IN":
                if att and att.capture_source == adapter.adapter_type and att.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
                    proc_status = "Duplicate"
                elif att:
                    att.status = computed_status
                    att.check_in_time = scan_time_str
                    att.capture_source = adapter.adapter_type
                    att.device_id = payload.device_code
                    att.marked_by = actor
                else:
                    att = TeacherAttendance(
                        teacher_id=subject.subject_id,
                        date=scan_date,
                        status=computed_status,
                        check_in_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            else:
                if att:
                    att.check_out_time = scan_time_str
                else:
                    att = TeacherAttendance(
                        teacher_id=subject.subject_id,
                        date=scan_date,
                        status=AttendanceStatus.PRESENT,
                        check_out_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Check-out captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            final_status = att.status

        else:  # staff
            att = (
                db.query(StaffAttendance)
                .filter(StaffAttendance.staff_id == subject.subject_id, StaffAttendance.date == scan_date)
                .first()
            )
            if direction == "CHECK_IN":
                if att and att.capture_source == adapter.adapter_type and att.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
                    proc_status = "Duplicate"
                elif att:
                    att.status = computed_status
                    att.check_in_time = scan_time_str
                    att.capture_source = adapter.adapter_type
                    att.device_id = payload.device_code
                    att.marked_by = actor
                else:
                    att = StaffAttendance(
                        staff_id=subject.subject_id,
                        date=scan_date,
                        status=computed_status,
                        check_in_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            else:
                if att:
                    att.check_out_time = scan_time_str
                else:
                    att = StaffAttendance(
                        staff_id=subject.subject_id,
                        date=scan_date,
                        status=AttendanceStatus.PRESENT,
                        check_out_time=scan_time_str,
                        capture_source=adapter.adapter_type,
                        device_id=payload.device_code,
                        remarks=f"Check-out captured via {adapter.adapter_type}",
                        marked_by=actor,
                    )
                    db.add(att)
            final_status = att.status

        if device_cfg:
            device_cfg.last_sync_at = utc_now()

        log = AttendanceScanLog(
            adapter_type=adapter.adapter_type,
            device_id=payload.device_code,
            raw_identifier=token[:180],
            matched_subject_type=subject.subject_type,
            matched_subject_id=subject.subject_id,
            scan_timestamp=utc_now(),
            direction=direction,
            confidence_score=payload.confidence_score,
            processing_status=proc_status,
            notes=f"{subject.full_name} ({subject.identifier_display}) -> {final_status} [{direction}]",
        )
        db.add(log)
        db.commit()

        result_data = {
            "subject_type": subject.subject_type,
            "subject_id": subject.subject_id,
            "full_name": subject.full_name,
            "identifier": subject.identifier_display,
            "date": scan_date.isoformat(),
            "time": scan_time_str,
            "direction": direction,
            "status": final_status,
            "adapter_type": adapter.adapter_type,
            "processing_status": proc_status,
        }
        msg = f"{adapter.adapter_type} {direction}: {subject.full_name} marked {final_status} at {scan_time_str}."
        return True, result_data, msg

    @classmethod
    def get_recent_scan_logs(cls, db: Session, limit: int = 50, adapter_type: Optional[str] = None) -> List[AttendanceScanLog]:
        q = db.query(AttendanceScanLog)
        if adapter_type:
            q = q.filter(AttendanceScanLog.adapter_type == adapter_type)
        return q.order_by(AttendanceScanLog.id.desc()).limit(limit).all()
