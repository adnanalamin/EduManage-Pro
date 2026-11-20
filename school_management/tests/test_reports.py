"""
EduManage Pro - Executive Reports & Analytics Test Suite
Verifies real-DB KPI aggregation (and zero-value empty DB state),
openpyxl Master Excel export, CSV exports, and Executive PDF generation.
"""

import os
import tempfile
import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.attendance import StudentAttendance
from app.models.exam import ExamResultSummary, ExamTerm, ExamType
from app.models.fee import FeeCategory, FeePayment, FeeStructure, StudentFee
from app.models.school import SchoolSetting
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student
from app.reports.executive_summary_pdf import ExecutiveSummaryPdf
from app.services.analytics_service import AnalyticsService


class TestReports(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = TestingSessionLocal()

        # School Profile
        school = SchoolSetting(
            school_name="EduManage Test Academy",
            motto="Truth and Wisdom",
            eiin_number="999888",
            phone="+880 1700-000000",
            email="test@edumanage.pro",
            principal_name="Dr. Test Principal",
        )
        self.db.add(school)

        # Academic Year, Class & Section
        self.ay = AcademicYear(
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        self.db.add(self.ay)
        self.db.flush()

        cls = SchoolClass(name="Class 10", numeric_order=10, academic_year_id=self.ay.id)
        self.db.add(cls)
        self.db.flush()

        sec = Section(name="A", class_id=cls.id)
        self.db.add(sec)
        self.db.flush()

        # Guardians & Students
        g1 = Guardian(guardian_name="Abdul Rahman", guardian_phone="+8801811111111")
        g2 = Guardian(guardian_name="Khadija Begum", guardian_phone="+8801822222222")
        self.db.add_all([g1, g2])
        self.db.flush()

        self.s1 = Student(
            student_id="STU-2026-001",
            admission_number="ADM-TEST-001",
            roll_number=1,
            first_name="Rahim",
            last_name="Uddin",
            full_name="Rahim Uddin",
            gender="Male",
            date_of_birth=date(2010, 3, 15),
            class_id=cls.id,
            section_id=sec.id,
            academic_year_id=self.ay.id,
            guardian_id=g1.id,
            status="Active",
        )
        self.s2 = Student(
            student_id="STU-2026-002",
            admission_number="ADM-TEST-002",
            roll_number=2,
            first_name="Fatima",
            last_name="Zahra",
            full_name="Fatima Zahra",
            gender="Female",
            date_of_birth=date(2010, 6, 20),
            class_id=cls.id,
            section_id=sec.id,
            academic_year_id=self.ay.id,
            guardian_id=g2.id,
            status="Active",
        )
        self.db.add_all([self.s1, self.s2])
        self.db.flush()

        # Department, Teacher & Staff
        dept = Department(name="Science", code="SCI")
        self.db.add(dept)
        self.db.flush()

        teacher = Teacher(
            teacher_id="TCH-001",
            employee_id="EMP-T-001",
            full_name="Kamal Hossain",
            gender="Male",
            date_of_birth=date(1985, 1, 10),
            phone="+8801711111111",
            email="kamal@test.edu",
            qualification="M.Sc in Physics",
            designation="Senior Teacher",
            department_id=dept.id,
            primary_subject="Physics",
            status="active",
        )
        self.db.add(teacher)

        # Fee Category, Structure & StudentFee Invoices
        fcat = FeeCategory(name="Tuition Fee", code="TUI")
        self.db.add(fcat)
        self.db.flush()

        fstruct = FeeStructure(
            title="Class 10 Monthly Tuition",
            category_id=fcat.id,
            class_id=cls.id,
            academic_year_id=self.ay.id,
            amount=5000.0,
            due_date=date(2026, 5, 10),
        )
        self.db.add(fstruct)
        self.db.flush()

        inv1 = StudentFee(
            invoice_no="INV-2026-001",
            student_id=self.s1.id,
            fee_structure_id=fstruct.id,
            academic_year_id=self.ay.id,
            title="Tuition Fee May",
            total_amount=5000.0,
            net_amount=5000.0,
            paid_amount=5000.0,
            due_amount=0.0,
            status="Paid",
            due_date=date(2026, 5, 10),
        )
        inv2 = StudentFee(
            invoice_no="INV-2026-002",
            student_id=self.s2.id,
            fee_structure_id=fstruct.id,
            academic_year_id=self.ay.id,
            title="Tuition Fee May",
            total_amount=5000.0,
            net_amount=5000.0,
            paid_amount=1500.0,
            due_amount=3500.0,
            status="Partial",
            due_date=date(2026, 5, 10),
        )
        self.db.add_all([inv1, inv2])
        self.db.flush()

        # Attendance
        att1 = StudentAttendance(
            student_id=self.s1.id,
            class_id=cls.id,
            section_id=sec.id,
            academic_year_id=self.ay.id,
            date=date.today(),
            status="Present",
        )
        att2 = StudentAttendance(
            student_id=self.s2.id,
            class_id=cls.id,
            section_id=sec.id,
            academic_year_id=self.ay.id,
            date=date.today(),
            status="Absent",
        )
        self.db.add_all([att1, att2])

        # Accounting
        ac_inc = AccountCategory(name="Tuition Income", code="INC-TUI", type="Income")
        ac_exp = AccountCategory(name="Utilities", code="EXP-UTL", type="Expense")
        self.db.add_all([ac_inc, ac_exp])
        self.db.flush()

        tx1 = AccountTransaction(
            voucher_no="TXN-001",
            transaction_date=date.today(),
            type="Income",
            category_id=ac_inc.id,
            academic_year_id=self.ay.id,
            amount=6500.0,
            paid_to_received_from="Student Fee Collection",
            description="Term Fees",
        )
        tx2 = AccountTransaction(
            voucher_no="TXN-002",
            transaction_date=date.today(),
            type="Expense",
            category_id=ac_exp.id,
            academic_year_id=self.ay.id,
            amount=1200.0,
            paid_to_received_from="Electric Utility Co",
            description="Electricity Bill",
        )
        self.db.add_all([tx1, tx2])

        # Exam Result
        etype = ExamType(name="Terminal", code="TERM")
        self.db.add(etype)
        self.db.flush()

        term = ExamTerm(
            name="First Term",
            exam_code="T1-2026",
            academic_year_id=self.ay.id,
            exam_type_id=etype.id,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 15),
        )
        self.db.add(term)
        self.db.flush()

        res1 = ExamResultSummary(
            exam_term_id=term.id,
            student_id=self.s1.id,
            class_id=cls.id,
            total_obtained=450.0,
            total_full_marks=500.0,
            percentage=90.0,
            gpa=4.5,
            cgpa=4.5,
            overall_grade="A",
            class_rank=1,
            passed_all=True,
        )
        self.db.add(res1)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_empty_db_has_zero_kpis_no_fake_fallbacks(self):
        empty_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(empty_engine)
        SessionEmpty = sessionmaker(bind=empty_engine)
        edb = SessionEmpty()
        try:
            kpis = AnalyticsService.get_executive_kpis(edb)
            self.assertEqual(kpis["total_students"], 0)
            self.assertEqual(kpis["attendance_rate"], 0.0)
            self.assertEqual(kpis["pass_rate"], 0.0)
            self.assertEqual(kpis["avg_gpa"], 0.0)
            self.assertEqual(kpis["collection_efficiency"], 0.0)

            dash = AnalyticsService.get_dashboard_analytics(edb)
            self.assertEqual(dash["enrollment_by_class"], [])
            self.assertEqual(dash["finance_monthly_series"], [])
            self.assertEqual(dash["attendance_distribution"], [])
        finally:
            edb.close()

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
        self.assertEqual(kpis["attendance_rate"], 50.0)
        self.assertEqual(kpis["total_assessed"], 1)
        self.assertEqual(kpis["pass_rate"], 100.0)
        self.assertEqual(kpis["avg_gpa"], 4.5)

    def test_get_fee_defaulters(self):
        defaulters = AnalyticsService.get_fee_defaulters(self.db)
        self.assertEqual(len(defaulters), 1)
        d = defaulters[0]
        self.assertEqual(d["invoice_number"], "INV-2026-002")
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
                self.assertIn("INV-2026-002", content)
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
