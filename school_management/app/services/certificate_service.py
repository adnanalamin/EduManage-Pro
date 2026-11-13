"""
EduManage Pro - Certificate & Credentials Service
Business logic for issuing Student/Staff certificates, auto-updating TC transfer status, and seeding registry data.
"""

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from app.models.student import Student, StudentStatus
from app.models.staff import Staff, Teacher
from app.models.certificate import CertificateRecord
from app.repositories.certificate_repository import CertificateRepository


class CertificateService:
    CERTIFICATE_TYPES = [
        "Transfer Certificate",
        "Character Certificate",
        "Testimonial",
        "Bonafide Certificate",
        "Merit Certificate",
        "Staff Experience Letter",
    ]

    @staticmethod
    def issue_student_certificate(
        db: Session,
        student_id: int,
        certificate_type: str,
        conduct_grade: str = "Exemplary",
        reason_or_purpose: str = "Official Academic Requirement",
        leaving_date: Optional[date] = None,
        remarks: str = "",
        mark_student_transferred: bool = False,
        issued_by: str = "Principal Office",
    ) -> CertificateRecord:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"Student ID {student_id} not found.")

        cls_name = student.school_class.name if student.school_class else "Class 10"
        sec_name = student.section.name if student.section else "A"
        father_name = student.guardian.father_name or student.guardian.guardian_name if student.guardian else "N/A"

        cert = CertificateRepository.create(
            db,
            certificate_type=certificate_type,
            recipient_type="Student",
            student_id=student.id,
            recipient_name=student.full_name,
            recipient_code=student.student_id,
            class_or_designation=f"{cls_name} (Section {sec_name}, Roll {student.roll_number})",
            father_or_guardian=father_name,
            issue_date=date.today(),
            leaving_date=leaving_date,
            conduct_grade=conduct_grade,
            reason_or_purpose=reason_or_purpose,
            remarks=remarks,
            status="Issued",
            issued_by=issued_by,
        )

        if certificate_type == "Transfer Certificate" and mark_student_transferred:
            student.status = StudentStatus.TRANSFERRED
            db.commit()

        return cert

    @staticmethod
    def issue_staff_certificate(
        db: Session,
        staff_id: int,
        certificate_type: str = "Staff Experience Letter",
        conduct_grade: str = "Exemplary",
        reason_or_purpose: str = "Verification of Employment & Tenure",
        leaving_date: Optional[date] = None,
        remarks: str = "",
        issued_by: str = "Principal Office",
        is_teacher: bool = False,
    ) -> CertificateRecord:
        if is_teacher:
            person = db.query(Teacher).filter(Teacher.id == staff_id).first()
            if not person:
                raise ValueError(f"Teacher ID {staff_id} not found.")
            designation = person.designation
            code = person.teacher_id
            fk_staff_id = None
        else:
            person = db.query(Staff).filter(Staff.id == staff_id).first()
            if not person:
                raise ValueError(f"Staff ID {staff_id} not found.")
            designation = person.position
            code = person.employee_id
            fk_staff_id = person.id

        return CertificateRepository.create(
            db,
            certificate_type=certificate_type,
            recipient_type="Staff",
            staff_id=fk_staff_id,
            recipient_name=person.full_name,
            recipient_code=code,
            class_or_designation=designation,
            father_or_guardian="N/A",
            issue_date=date.today(),
            leaving_date=leaving_date,
            conduct_grade=conduct_grade,
            reason_or_purpose=reason_or_purpose,
            remarks=remarks,
            status="Issued",
            issued_by=issued_by,
        )

    @staticmethod
    def seed_sample_certificates(db: Session) -> int:
        if db.query(CertificateRecord).count() > 0:
            return 0

        students = db.query(Student).limit(3).all()
        created = 0
        samples = [
            ("Bonafide Certificate", "Passport & Student Visa Verification", "Exemplary"),
            ("Merit Certificate", "1st Position in Annual Science & Robotics Fair", "Exemplary"),
            ("Testimonial", "Board Examination & College Admission", "Good"),
        ]

        for idx, st in enumerate(students):
            ctype, purpose, conduct = samples[idx % len(samples)]
            CertificateService.issue_student_certificate(
                db,
                student_id=st.id,
                certificate_type=ctype,
                conduct_grade=conduct,
                reason_or_purpose=purpose,
                remarks="Digitally verified and signed by the Office of the Principal.",
            )
            created += 1

        return created
