"""
EduManage Pro - Professional 11-Domain Reporting Engine & Report Builder Test Suite
Verifies:
  1. All 11 reporting domains query real ORM data:
     students, attendance, finance, payroll, academic, exam, library, transport, hostel, inventory, hr
  2. Dynamic Report Builder: column projection, multi-operator filters, grouping/rollups,
     ascending/descending sorting, date range filtering, and academic year scoping
  3. Saved Report Templates persistence & execution
  4. Universal PDF (ReportLab), Excel (openpyxl), and CSV exports
  5. Strictly real DB dashboard analytics (no fabricated defaults)
"""

import os
import tempfile
import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.connection import Base
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.attendance import StudentAttendance
from app.models.exam import ExamResultSummary, ExamTerm, ExamType
from app.models.fee import FeeCategory, FeeStructure, StudentFee
from app.models.hostel import HostelAllocation, HostelBlock, HostelRoom
from app.models.inventory import FixedAsset, InventoryCategory, InventoryItem
from app.models.library import Book, BookCategory, BookCirculation, LibraryMember
from app.models.payroll import PayrollPayslip, PayrollPeriodRun
from app.models.school import SchoolSetting
from app.models.staff import Department, Staff, Teacher
from app.models.student import Guardian, Student
from app.models.transport import TransportPassenger, TransportRoute, Vehicle
from app.reports.dynamic_report_pdf import DynamicReportPDFGenerator
from app.services.analytics_service import AnalyticsService
from app.services.reporting_engine import REPORT_DOMAIN_CATALOG, ReportingEngine


class TestProfessionalReportingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()

        self.school = SchoolSetting(school_name="Apex Public School", eiin_number="554433")
        self.db.add(self.school)

        self.ay_2025 = AcademicYear(
            name="2025", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=False
        )
        self.ay_2026 = AcademicYear(
            name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_current=True
        )
        self.db.add_all([self.ay_2025, self.ay_2026])
        self.db.flush()

        self.cls9 = SchoolClass(name="Class 9", numeric_order=9, academic_year_id=self.ay_2026.id)
        self.cls8 = SchoolClass(name="Class 8", numeric_order=8, academic_year_id=self.ay_2025.id)
        self.db.add_all([self.cls9, self.cls8])
        self.db.flush()

        self.sec_a = Section(name="Section A", class_id=self.cls9.id)
        self.db.add(self.sec_a)
        self.db.flush()

        self.dept = Department(name="Mathematics", code="MATH")
        self.db.add(self.dept)
        self.db.flush()

        self.teacher = Teacher(
            teacher_id="TCH-101",
            employee_id="EMP-101",
            full_name="Prof. Arif Mahmud",
            gender="Male",
            date_of_birth=date(1980, 5, 12),
            phone="+8801710000101",
            email="arif@apex.edu",
            qualification="M.Sc Mathematics",
            designation="Senior Lecturer",
            department_id=self.dept.id,
            primary_subject="Mathematics",
            joining_date=date(2024, 1, 15),
            salary=45000,
            status="active",
        )
        self.staff = Staff(
            staff_id="STF-201",
            employee_id="EMP-201",
            full_name="Karim Mia",
            gender="Male",
            date_of_birth=date(1988, 7, 1),
            phone="+8801720000201",
            position="Accountant",
            department_id=self.dept.id,
            joining_date=date(2025, 2, 1),
            salary=28000,
            status="active",
        )
        self.db.add_all([self.teacher, self.staff])
        self.db.flush()

        self.sub_math = Subject(
            subject_id="SUB-MATH-9",
            name="Mathematics",
            code="109",
            class_id=self.cls9.id,
            teacher_id=self.teacher.id,
            full_marks=100,
            pass_marks=33,
        )
        self.db.add(self.sub_math)

        g = Guardian(guardian_name="Tariq Islam", guardian_phone="+8801911223344")
        self.db.add(g)
        self.db.flush()

        self.s1 = Student(
            student_id="STU-2026-010",
            admission_number="ADM-2026-010",
            roll_number=1,
            first_name="Nadia",
            last_name="Rahman",
            full_name="Nadia Rahman",
            gender="Female",
            date_of_birth=date(2011, 4, 10),
            admission_date=date(2026, 1, 10),
            class_id=self.cls9.id,
            section_id=self.sec_a.id,
            academic_year_id=self.ay_2026.id,
            guardian_id=g.id,
            status="active",
        )
        self.s2 = Student(
            student_id="STU-2025-005",
            admission_number="ADM-2025-005",
            roll_number=5,
            first_name="Sajib",
            last_name="Ahmed",
            full_name="Sajib Ahmed",
            gender="Male",
            date_of_birth=date(2012, 8, 22),
            admission_date=date(2025, 1, 15),
            class_id=self.cls8.id,
            academic_year_id=self.ay_2025.id,
            guardian_id=g.id,
            status="active",
        )
        self.db.add_all([self.s1, self.s2])
        self.db.flush()

        # Attendance
        self.db.add(StudentAttendance(
            student_id=self.s1.id,
            class_id=self.cls9.id,
            section_id=self.sec_a.id,
            academic_year_id=self.ay_2026.id,
            date=date(2026, 3, 10),
            status="Present",
        ))

        # Finance (Fee + Accounting)
        fcat = FeeCategory(name="Tuition", code="TUI")
        self.db.add(fcat)
        self.db.flush()
        fstruct = FeeStructure(
            title="Class 9 Tuition", category_id=fcat.id, class_id=self.cls9.id,
            academic_year_id=self.ay_2026.id, amount=4000.0, due_date=date(2026, 3, 5),
        )
        self.db.add(fstruct)
        self.db.flush()
        self.db.add(StudentFee(
            invoice_no="INV-9001", student_id=self.s1.id, fee_structure_id=fstruct.id,
            academic_year_id=self.ay_2026.id, title="March Tuition",
            total_amount=4000.0, net_amount=4000.0, paid_amount=2500.0, due_amount=1500.0,
            status="Partial", due_date=date(2026, 3, 5),
        ))
        acat = AccountCategory(name="Fee Income", code="INC-FEE", type="Income")
        self.db.add(acat)
        self.db.flush()
        self.db.add(AccountTransaction(
            voucher_no="VCH-2026-01", transaction_date=date(2026, 3, 5),
            type="Income", category_id=acat.id, academic_year_id=self.ay_2026.id,
            amount=2500.0, paid_to_received_from="Nadia Rahman", description="Fee Receipt",
        ))

        # Payroll
        prun = PayrollPeriodRun(
            run_code="PAY-2026-03", payroll_year=2026, payroll_month=3,
            academic_year_id=self.ay_2026.id, period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        )
        self.db.add(prun)
        self.db.flush()
        self.db.add_all([
            PayrollPayslip(
                slip_no="SLP-202603-01", payroll_run_id=prun.id, employee_type="teacher",
                teacher_id=self.teacher.id, employee_code=self.teacher.employee_id,
                employee_name=self.teacher.full_name, designation=self.teacher.designation,
                department_name="Mathematics", payroll_year=2026, payroll_month=3,
                basic_salary=45000.0, gross_earnings=45000.0, tax_deduction=2000.0,
                total_deductions=2000.0, net_payable=43000.0, payment_status="Paid", paid_date=date(2026, 3, 31),
            ),
            PayrollPayslip(
                slip_no="SLP-202603-02", payroll_run_id=prun.id, employee_type="staff",
                staff_id=self.staff.id, employee_code=self.staff.employee_id,
                employee_name=self.staff.full_name, designation="Accountant",
                department_name="Mathematics", payroll_year=2026, payroll_month=3,
                basic_salary=28000.0, gross_earnings=28000.0, tax_deduction=500.0,
                total_deductions=500.0, net_payable=27500.0, payment_status="Paid", paid_date=date(2026, 3, 31),
            ),
        ])

        # Exam
        et = ExamType(name="Midterm", code="MID")
        self.db.add(et)
        self.db.flush()
        term = ExamTerm(
            name="Midterm 2026", exam_code="MID-2026", academic_year_id=self.ay_2026.id,
            exam_type_id=et.id, start_date=date(2026, 4, 1), end_date=date(2026, 4, 10),
        )
        self.db.add(term)
        self.db.flush()
        self.db.add(ExamResultSummary(
            exam_term_id=term.id, student_id=self.s1.id, class_id=self.cls9.id,
            total_obtained=465.0, total_full_marks=500.0, percentage=93.0,
            gpa=5.0, cgpa=5.0, overall_grade="A+", class_rank=1, section_rank=1,
            passed_all=True, result_status="Published", is_published=True,
        ))

        # Library
        bcat = BookCategory(name="Science", code="SCI")
        self.db.add(bcat)
        self.db.flush()
        bk = Book(accession_no="LIB-001", title="Higher Algebra", author="H.S. Hall", category_id=bcat.id, total_copies=5, available_copies=4)
        self.db.add(bk)
        self.db.flush()
        mem = LibraryMember(member_id="MEM-001", member_type="Student", student_id=self.s1.id, card_issue_date="2026-01-15")
        self.db.add(mem)
        self.db.flush()
        self.db.add(BookCirculation(
            book_id=bk.id, member_id=mem.id, issue_date="2026-03-01", due_date="2026-03-15", status="Issued",
        ))

        # Transport
        veh = Vehicle(vehicle_number="BUS-01", vehicle_model="Hino AK", vehicle_type="Bus", seating_capacity=40, driver_name="Rafiq", driver_phone="017000001")
        self.db.add(veh)
        self.db.flush()
        rt = TransportRoute(route_name="Uttara Express", route_code="RT-01", start_point="Uttara", end_point="Campus", vehicle_id=veh.id)
        self.db.add(rt)
        self.db.flush()
        self.db.add(TransportPassenger(
            passenger_type="Student", student_id=self.s1.id, route_id=rt.id, vehicle_id=veh.id,
            allocation_date="2026-01-15", monthly_fare=2500.0, status="Active",
        ))

        # Hostel
        blk = HostelBlock(block_name="North Hall", gender_type="Girls")
        self.db.add(blk)
        self.db.flush()
        rm = HostelRoom(block_id=blk.id, room_number="101", floor_number=1, capacity=2, monthly_fee=3500.0)
        self.db.add(rm)
        self.db.flush()
        self.db.add(HostelAllocation(
            room_id=rm.id, student_id=self.s1.id, bed_number="Bed-1",
            admission_date=date(2026, 1, 15), check_in_date=date(2026, 1, 15), status="Active",
        ))

        # Inventory & Fixed Asset
        icat = InventoryCategory(name="IT Equipment", code="ITEQ")
        self.db.add(icat)
        self.db.flush()
        self.db.add(InventoryItem(
            item_code="ITM-001", name="A4 Paper Rim", category_id=icat.id,
            quantity_in_stock=3, reorder_level=10, unit_cost=450.0, status="Low Stock",
        ))
        self.db.add(FixedAsset(
            asset_id="AST-001", name="Smart Projector", category_id=icat.id,
            serial_number="SN-PROJ-99", purchase_date=date(2026, 2, 1), cost=65000.0,
            location="Room 9A", department_name="Mathematics", assigned_employee="Prof. Arif Mahmud",
            warranty="24 Months", status="Active",
        ))

        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_all_11_domains_return_real_records(self):
        self.assertEqual(len(REPORT_DOMAIN_CATALOG), 11)
        expected_domains = {
            "students", "attendance", "finance", "payroll", "academic",
            "exam", "library", "transport", "hostel", "inventory", "hr",
        }
        self.assertEqual(set(REPORT_DOMAIN_CATALOG.keys()), expected_domains)

        for dkey in expected_domains:
            res = ReportingEngine.build_report(self.db, domain_key=dkey)
            self.assertGreaterEqual(res["row_count"], 1, f"Domain '{dkey}' returned no records")

    def test_report_builder_columns_filters_grouping_sorting_dates_and_year(self):
        # 1. Academic year scoping on students
        res_2026 = ReportingEngine.build_report(self.db, "students", academic_year_id=self.ay_2026.id)
        self.assertEqual(res_2026["row_count"], 1)
        self.assertEqual(res_2026["rows"][0]["admission_number"], "ADM-2026-010")

        # 2. Custom column selection + Filter + Grouping + Sorting on Payroll
        pay_res = ReportingEngine.build_report(
            self.db,
            domain_key="payroll",
            selected_columns=["employee_code", "employee_name", "department_name", "gross_earnings", "net_payable"],
            filters=[{"field": "net_payable", "op": "gte", "value": "25000"}],
            group_by="department_name",
            sort_by="net_payable",
            sort_desc=True,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 31),
            academic_year_id=self.ay_2026.id,
        )
        self.assertEqual([c["key"] for c in pay_res["columns"]], ["employee_code", "employee_name", "department_name", "gross_earnings", "net_payable"])
        self.assertEqual(pay_res["row_count"], 2)
        self.assertEqual(pay_res["rows"][0]["net_payable"], 43000.0)  # sorted desc
        self.assertEqual(pay_res["totals"]["net_payable"], 70500.0)
        self.assertEqual(len(pay_res["grouped_rows"]), 1)
        self.assertEqual(pay_res["grouped_rows"][0]["_record_count"], 2)
        self.assertEqual(pay_res["grouped_rows"][0]["net_payable_sum"], 70500.0)
        self.assertEqual(pay_res["grouped_rows"][0]["net_payable_avg"], 35250.0)

    def test_saved_report_template_lifecycle_and_exports(self):
        tpl = ReportingEngine.save_report_definition(
            self.db,
            name="March High-Pay Audit",
            domain_key="payroll",
            selected_columns=["slip_no", "employee_name", "department_name", "net_payable"],
            filters=[{"field": "employee_type", "op": "eq", "value": "Teacher"}],
            group_by="department_name",
            sort_by="net_payable",
            sort_desc=True,
            academic_year_id=self.ay_2026.id,
        )
        self.assertIsNotNone(tpl.id)

        run_res = ReportingEngine.run_saved_definition(self.db, tpl.id)
        self.assertEqual(run_res["row_count"], 1)
        self.assertEqual(run_res["rows"][0]["employee_name"], "Prof. Arif Mahmud")

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_out = DynamicReportPDFGenerator.generate_pdf(run_res, self.school, os.path.join(tmpdir, "custom.pdf"))
            xlsx_out = ReportingEngine.export_to_excel(run_res, os.path.join(tmpdir, "custom.xlsx"))
            csv_out = ReportingEngine.export_to_csv(run_res, os.path.join(tmpdir, "custom.csv"))

            self.assertTrue(os.path.exists(pdf_out) and os.path.getsize(pdf_out) > 1500)
            self.assertTrue(os.path.exists(xlsx_out) and os.path.getsize(xlsx_out) > 2000)
            self.assertTrue(os.path.exists(csv_out) and os.path.getsize(csv_out) > 30)

        self.assertTrue(ReportingEngine.delete_saved_definition(self.db, tpl.id))

    def test_dashboard_real_analytics_series(self):
        dash = AnalyticsService.get_dashboard_analytics(self.db, academic_year_id=self.ay_2026.id)
        self.assertEqual(dash["kpis"]["total_students"], 1)
        self.assertEqual(dash["enrollment_by_class"], [{"label": "Class 9", "value": 1}])
        self.assertEqual(dash["exam_grade_distribution"], [{"label": "A+", "value": 1}])
        self.assertEqual(len(dash["payroll_monthly_series"]), 1)
        self.assertEqual(dash["payroll_monthly_series"][0]["value"], 70500.0)


if __name__ == "__main__":
    unittest.main()
