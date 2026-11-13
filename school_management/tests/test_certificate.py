"""
EduManage Pro - Certificate & ID Card Generator Test Suite
Phase 15: Verifies certificate issuance, serial numbering, verification tokens, revocation,
Landscape A4 Certificate PDF, and Portrait A4 Batch CR80 ID Sheet generation.
"""

import os
import tempfile
import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.student import Student, Guardian, StudentStatus
from app.models.academic import SchoolClass, Section, AcademicYear
from app.models.school import SchoolSetting
from app.models.certificate import CertificateRecord
from app.repositories.certificate_repository import CertificateRepository
from app.services.certificate_service import CertificateService
from app.reports.certificate_pdf import CertificatePDFGenerator


class TestCertificates(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSession = sessionmaker(bind=self.engine)
        self.db = TestingSession()

        self.school = SchoolSetting(
            school_name="Ideal Model High School",
            motto="Excellence in Education",
            eiin_number="134211",
            principal_name="Prof. Dr. Rafiqul Islam",
        )
        self.db.add(self.school)

        ay = AcademicYear(name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True)
        cls = SchoolClass(name="Class 10", numeric_value=10)
        self.db.add_all([ay, cls])
        self.db.commit()

        sec = Section(name="A", class_id=cls.id)
        guardian = Guardian(
            father_name="Abdul Karim",
            guardian_name="Abdul Karim",
            guardian_phone="+8801711000001",
        )
        self.db.add_all([sec, guardian])
        self.db.commit()

        self.student = Student(
            student_id="STU-2026-001",
            admission_number="ADM-2026-001",
            roll_number=1,
            first_name="Samiul",
            last_name="Islam",
            full_name="Samiul Islam",
            gender="Male",
            date_of_birth=date(2010, 5, 14),
            blood_group="O+",
            class_id=cls.id,
            section_id=sec.id,
            academic_year_id=ay.id,
            guardian_id=guardian.id,
            status=StudentStatus.ACTIVE,
        )
        self.db.add(self.student)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_issue_verify_and_revoke_certificate(self):
        cert = CertificateService.issue_student_certificate(
            self.db,
            student_id=self.student.id,
            certificate_type="Transfer Certificate",
            conduct_grade="Exemplary",
            reason_or_purpose="Family Relocation",
            leaving_date=date.today(),
            mark_student_transferred=True,
        )
        self.assertTrue(cert.certificate_number.startswith("CERT-TC-"))
        self.assertTrue(cert.verification_code.startswith("VER-"))
        self.assertEqual(cert.status, "Issued")

        self.db.refresh(self.student)
        self.assertEqual(self.student.status, StudentStatus.TRANSFERRED)

        verified = CertificateRepository.verify_credential(self.db, cert.verification_code)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, cert.id)

        revoked = CertificateRepository.revoke(self.db, cert.id, "Duplicate error")
        self.assertEqual(revoked.status, "Revoked")

    def test_certificate_and_batch_id_pdfs(self):
        cert = CertificateService.issue_student_certificate(
            self.db,
            student_id=self.student.id,
            certificate_type="Merit Certificate",
            reason_or_purpose="1st Position in Science Fair",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_pdf = os.path.join(tmpdir, "merit_cert.pdf")
            out_cert = CertificatePDFGenerator.generate_certificate_pdf(cert, self.school, cert_pdf)
            self.assertTrue(os.path.exists(out_cert))
            self.assertGreater(os.path.getsize(out_cert), 1500)

            sheet_pdf = os.path.join(tmpdir, "batch_ids.pdf")
            out_sheet = CertificatePDFGenerator.generate_batch_student_id_sheet([self.student], self.school, sheet_pdf)
            self.assertTrue(os.path.exists(out_sheet))
            self.assertGreater(os.path.getsize(out_sheet), 1500)


if __name__ == "__main__":
    unittest.main()
