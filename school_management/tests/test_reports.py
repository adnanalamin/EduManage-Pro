"""
EduManage Pro - Comprehensive Reports & Analytics Test Suite
Phase 14: Verifies cross-module KPI aggregation, openpyxl Master Excel export, CSV exports, and ReportLab Executive PDF generation.
"""

import os
import tempfile
import unittest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.student import Student
from app.models.staff import StaffMember
from app.models.academic import SchoolClass, Section
from app.models.fee import FeeInvoice
from app.models.attendance import StudentAttendance
from app.models.accounting import AccountTransaction
from app.models.exam import ExamTerm, ExamResultSummary
from app.models.school import SchoolSetting
from app.services.analytics_service import AnalyticsService
from app.reports.executive_summary_pdf import ExecutiveSummaryPdf


class TestReports(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = TestingSessionLocal()

        # Seed School Profile
        school = SchoolSetting(
            school_name="EduManage Test Academy",
            motto="Truth and Wisdom",
            eiin_number="999888",
            phone="+880 1700-000000",
            email="test@edumanage.pro",
            principal_name="Dr. Test Principal"
        )
        self.db.add(school)

        # Seed Academic Class & Section
        cls = SchoolClass(name="Class 10", numeric_value=10)
        self.db.add(cls)
        self.db.commit()
        self.db.refresh(cls)

        sec = Section(name="A", class_id=cls.id)
        self.db.add(sec)
        self.db.commit()
        self.db.refresh(sec)

        # Seed Students
        self.s1 = Student(
            admission_number="ADM-TEST-001",
            first_name="Rahim",
            last_name="Uddin",
            current_class_id=cls.id,
            current_section_id=sec.id,
            gender="Male",
            status="Active",
            guardian_phone="+8801811111111"
        )
        self.s2 = Student(
            admission_number="ADM-TEST-002",
            first_name="Fatima",
            last_name="Zahra",
            current_class_id=cls.id,
            current_section_id=sec.id,
            gender="Female",
            status="Active",
            guardian_phone="+8801822222222"
        )
        self.db.add_all([self.s1, self.s2])
        self.db.commit()

        # Seed Staff
        staff = StaffMember(
            employee_id="STF-001",
            first_name="Kamal",
            last_name="Hossain",
            designation="Senior Teacher",
            status="Active"
        )
        self.db.add(staff)

        # Seed Fee Invoice (one paid, one overdue defaulter)
        inv1 = FeeInvoice(
            invoice_number="INV-2024-001",
            student_id=self.s1.id,
            title="Tuition Fee May",
            total_amount=5000.0,
            paid_amount=5000.0,
            due_amount=0.0,
            status="Paid",
            due_date=date(2024, 5, 10)
        )
        inv2 = FeeInvoice(
            invoice_number="INV-2024-002",
            student_id=self.s2.id,
            title="Tuition Fee May",
            total_amount=5000.0,
            paid_amount=1500.0,
            due_amount=3500.0,
            status="Partial",
            due_date=date(2024, 5, 10)
        )
        self.db.add_all([inv1, inv2])

        # Seed Attendance
        att1 = StudentAttendance(student_id=self.s1.id, attendance_date=date.today(), status="Present")
        att2 = StudentAttendance(student_id=self.s2.id, attendance_date=date.today(), status="Absent")
        self.db.add_all([att1, att2])

        # Seed Accounting
        tx1 = AccountTransaction(
            voucher_number="TXN-001",
            title="Term Fees",
            transaction_type="Income",
            amount=6500.0,
            transaction_date=date.today()
        )
        tx2 = AccountTransaction(
            voucher_number="TXN-002",
            title="Utilities",
            transaction_type="Expense",
            amount=1200.0,
            transaction_date=date.today()
        )
        self.db.add_all([tx1, tx2])

        # Seed Exam Result
        term = ExamTerm(name="First Term", code="T1", is_active=True)
        self.db.add(term)
        self.db.commit()

        res1 = ExamResultSummary(
            student_id=self.s1.id,
            term_id=term.id,
            total_marks=450.0,
            gpa=4.5,
            grade="A",
            is_passed=True
        )
        self.db.add(res1)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_get_executive_kpis(self):
        kpis = AnalyticsService.get_executive_kpis(self.db)
        self.assertEqual(kpis["total_students"], 2)
        self.assertEqual(kpis["active_students"], 2)
        self.assertEqual(kpis["male_students"], 1)
        self.assertEqual(kpis["female_students"], 1)
        self.assertEqual(kpis["total_staff"], 1)
        self.assertEqual(kpis["total_invoiced"], 10000.0)
        self.assertEqual(kpis["total_collected"], 6500.0)
        self.assertEqual(kpis["total_dues"], 3500.0)
        self.assertEqual(kpis["collection_efficiency"], 65.0)
        self.assertEqual(kpis["defaulters_count"], 1)
        self.assertEqual(kpis["total_income"], 6500.0)
        self.assertEqual(kpis["total_expenses"], 1200.0)
        self.assertEqual(kpis["net_surplus"], 5300.0)
        self.assertEqual(kpis["total_assessed"], 1)
        self.assertEqual(kpis["pass_rate"], 100.0)
        self.assertEqual(kpis["avg_gpa"], 4.5)

    def test_get_fee_defaulters(self):
        defaulters = AnalyticsService.get_fee_defaulters(self.db)
        self.assertEqual(len(defaulters), 1)
        d = defaulters[0]
        self.assertEqual(d["invoice_number"], "INV-2024-002")
        self.assertEqual(d["student_name"], "Fatima Zahra")
        self.assertEqual(d["due_amount"], 3500.0)
        self.assertEqual(d["guardian_phone"], "+8801822222222")

    def test_get_attendance_analytics(self):
        res = AnalyticsService.get_attendance_analytics(self.db)
        self.assertEqual(res["overall_recorded_students"], 2)
        summary = res["class_summary"]
        self.assertGreaterEqual(len(summary), 1)
        cls_stat = next(s for s in summary if s["class_name"] == "Class 10")
        self.assertEqual(cls_stat["present_count"], 1)
        self.assertEqual(cls_stat["absent_count"], 1)
        self.assertEqual(cls_stat["attendance_percentage"], 50.0)

    def test_export_master_school_report_excel(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            excel_path = os.path.join(tmpdir, "master_report.xlsx")
            out = AnalyticsService.export_master_school_report_excel(self.db, excel_path)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 3000)

            import openpyxl
            wb = openpyxl.load_workbook(out)
            self.assertIn("Executive Summary", wb.sheetnames)
            self.assertIn("Student Demographics", wb.sheetnames)
            self.assertIn("Fee Defaulters", wb.sheetnames)
            self.assertIn("Attendance Analytics", wb.sheetnames)

    def test_export_defaulters_and_students_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_def = os.path.join(tmpdir, "defaulters.csv")
            out_def = AnalyticsService.export_defaulters_csv(self.db, csv_def)
            self.assertTrue(os.path.exists(out_def))
            with open(out_def, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("INV-2024-002", content)
                self.assertIn("Fatima Zahra", content)

            csv_stu = os.path.join(tmpdir, "students.csv")
            out_stu = AnalyticsService.export_students_csv(self.db, csv_stu)
            self.assertTrue(os.path.exists(out_stu))
            with open(out_stu, "r", encoding="utf-8") as f:
                content_stu = f.read()
                self.assertIn("ADM-TEST-001", content_stu)
                self.assertIn("Rahim", content_stu)

    def test_executive_summary_pdf_generation(self):
        kpis = AnalyticsService.get_executive_kpis(self.db)
        school = self.db.query(SchoolSetting).first()
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "executive_summary.pdf")
            out_pdf = ExecutiveSummaryPdf.generate(kpis, school, pdf_path)
            self.assertTrue(os.path.exists(out_pdf))
            self.assertGreater(os.path.getsize(out_pdf), 2000)


if __name__ == "__main__":
    unittest.main()
