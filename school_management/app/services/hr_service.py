"""
EduManage Pro - Enterprise HR Management Service
Covers Teacher & Non-Teaching Staff HR lifecycle with strict RBAC & Salary Confidentiality:
- Onboarding (Teacher & Staff: Office Staff, Accountant, Receptionist, Librarian, Security, Support)
- Qualifications & Work Experience
- Teacher Subject Assignments
- Employment Contracts
- Joining, Promotion, Department Transfer & Employment Status History
- Leave Management & Approval Workflow (auto-syncing approved leave into Attendance)
- Employee Attendance (Teachers & Staff)
- Document Vault
- Confidential Salary History & Revisions (strictly blocked for unauthorized roles)
- Performance Evaluations
- Emergency Contacts
- Chronological 360° Employee Timeline
"""

from datetime import date, datetime, timedelta
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.config.logging_config import app_logger, error_logger
from app.config.settings import DATA_DIR
from app.models.attendance import StaffAttendance, TeacherAttendance
from app.models.base import utc_now
from app.models.staff import (
    Department,
    EmployeeContract,
    EmployeeDocument,
    EmployeeEmergencyContact,
    EmployeeExperience,
    EmployeeLifecycleEvent,
    EmployeeLeaveRequest,
    EmployeePerformanceEvaluation,
    EmployeeQualification,
    EmployeeSalaryHistory,
    EmployeeStatus,
    Staff,
    Teacher,
    TeacherSubjectAssignment,
)
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.staff_repository import StaffRepository
from app.security.session import session as app_session
from app.services.database_service import DatabaseService

HR_DOCS_DIR = DATA_DIR / "hr_documents"
HR_PHOTOS_DIR = DATA_DIR / "hr_photos"
for _d in (HR_DOCS_DIR, HR_PHOTOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _store_hr_file(target_dir: Path, employee_code: str, source_path: str) -> Tuple[str, str, int]:
    src = Path(source_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"File not found: {source_path}")
    safe_code = "".join(ch for ch in employee_code if ch.isalnum() or ch in ("-", "_")) or "emp"
    emp_dir = target_dir / safe_code
    emp_dir.mkdir(parents=True, exist_ok=True)
    dest = emp_dir / f"{uuid.uuid4().hex[:8]}_{src.name}"
    shutil.copy2(str(src), str(dest))
    return str(dest), src.name, dest.stat().st_size


class HRSecurityGuard:
    """Central RBAC & Salary Confidentiality enforcement helper."""

    @staticmethod
    def resolve_actor(actor_user: Optional[User] = None) -> Optional[User]:
        if actor_user is not None:
            return actor_user
        if app_session.is_authenticated and app_session.current_user is not None:
            return app_session.current_user
        return None

    @staticmethod
    def actor_username(actor_user: Optional[User] = None, fallback: str = "admin") -> str:
        user = HRSecurityGuard.resolve_actor(actor_user)
        return user.username if user else fallback

    @staticmethod
    def has_permission(
        permission_code: str,
        actor_user: Optional[User] = None,
        *,
        module: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
        allow_when_no_session: bool = True,
    ) -> bool:
        user = HRSecurityGuard.resolve_actor(actor_user)
        if user is None:
            return allow_when_no_session
        return user.has_permission(permission_code, module=module, feature=feature, action=action)

    @staticmethod
    def can_view_salary(actor_user: Optional[User] = None, allow_when_no_session: bool = True) -> bool:
        return HRSecurityGuard.has_permission(
            "hr.salary.VIEW",
            actor_user=actor_user,
            allow_when_no_session=allow_when_no_session,
        )

    @staticmethod
    def can_manage_salary(actor_user: Optional[User] = None, allow_when_no_session: bool = True) -> bool:
        user = HRSecurityGuard.resolve_actor(actor_user)
        if user is None:
            return allow_when_no_session
        return (
            user.has_permission("hr.salary.EDIT")
            or user.has_permission("hr.salary.APPROVE")
            or user.has_permission("hr.salary.MANAGE")
            or user.has_permission("hr.salary.CREATE")
        )

    @staticmethod
    def require_permission(
        permission_code: str,
        actor_user: Optional[User] = None,
        error_msg: Optional[str] = None,
    ) -> None:
        user = HRSecurityGuard.resolve_actor(actor_user)
        if user is not None and not user.has_permission(permission_code):
            raise PermissionError(
                error_msg or f"Access denied: missing required permission '{permission_code}'."
            )

    @staticmethod
    def require_salary_view(actor_user: Optional[User] = None) -> None:
        if not HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True):
            raise PermissionError("Access denied: you are not authorized to view confidential salary information.")

    @staticmethod
    def require_salary_manage(actor_user: Optional[User] = None) -> None:
        if not HRSecurityGuard.can_manage_salary(actor_user=actor_user, allow_when_no_session=True):
            raise PermissionError("Access denied: you are not authorized to modify or approve employee salaries.")


class HRService:
    # ------------------------------------------------------------------
    # Onboarding & Profile Inspection (With Salary Redaction)
    # ------------------------------------------------------------------
    @staticmethod
    def _emp_filter(employee_type: str, emp: Any) -> Dict[str, Any]:
        etype = employee_type.strip().lower()
        return {
            "employee_type": etype,
            "teacher_id": emp.id if etype == "teacher" else None,
            "staff_id": emp.id if etype == "staff" else None,
        }

    @staticmethod
    def _log(
        db: Session,
        action: str,
        description: str,
        username: str,
        entity_type: str = "Employee",
        entity_id: Optional[int] = None,
        module: str = "HR",
    ) -> None:
        DatabaseService.log_activity(
            db,
            action=action,
            module=module,
            description=description,
            username=username,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            commit=False,
        )

    @staticmethod
    def onboard_employee(
        db: Session,
        employee_type: str,
        payload: Dict[str, Any],
        contract_data: Optional[Dict[str, Any]] = None,
        emergency_contact: Optional[Dict[str, Any]] = None,
        actor_user: Optional[User] = None,
        actor_username: str = "admin",
    ) -> Tuple[bool, Optional[Any], str]:
        """Onboard a Teacher or Staff member with initial lifecycle, contract & salary history."""
        try:
            HRSecurityGuard.require_permission("hr.directory.CREATE", actor_user)
            etype = employee_type.strip().lower()
            if etype not in ("teacher", "staff"):
                return False, None, "employee_type must be 'teacher' or 'staff'."

            username = HRSecurityGuard.actor_username(actor_user, actor_username)
            data = dict(payload)
            status_val = (data.get("status") or EmployeeStatus.ACTIVE).strip().lower()
            if status_val not in EmployeeStatus.ALL:
                return False, None, f"Invalid employment status '{status_val}'."
            data["status"] = status_val

            if data.get("photo_path") and Path(str(data["photo_path"])).exists():
                code_hint = data.get("employee_id") or data.get("full_name", "emp")
                stored, _, _ = _store_hr_file(HR_PHOTOS_DIR, str(code_hint), str(data["photo_path"]))
                data["photo_path"] = stored

            from app.services.staff_service import StaffService

            if etype == "teacher":
                if not data.get("teacher_id") or not data.get("employee_id"):
                    tid, eid = StaffService.generate_teacher_ids(db)
                    data["teacher_id"] = data.get("teacher_id") or tid
                    data["employee_id"] = data.get("employee_id") or eid
                if data.get("email") and db.query(Teacher).filter(Teacher.email == data["email"]).first():
                    return False, None, f"Teacher with email '{data['email']}' already exists."
                emp = StaffRepository.create_teacher(db, data)
                emp_code = emp.teacher_id
                role_label = emp.designation
            else:
                if not data.get("staff_id") or not data.get("employee_id"):
                    sid, eid = StaffService.generate_staff_ids(db)
                    data["staff_id"] = data.get("staff_id") or sid
                    data["employee_id"] = data.get("employee_id") or eid
                emp = StaffRepository.create_staff(db, data)
                emp_code = emp.staff_id
                role_label = emp.position

            emp_fk = HRService._emp_filter(etype, emp)

            # Joining lifecycle event
            db.add(
                EmployeeLifecycleEvent(
                    **emp_fk,
                    event_type="Joined",
                    effective_date=emp.joining_date or date.today(),
                    to_designation=role_label,
                    to_department_id=emp.department_id,
                    to_status=emp.status,
                    reason=f"Onboarded as {role_label}",
                    recorded_by=username,
                )
            )

            # Initial salary record
            db.add(
                EmployeeSalaryHistory(
                    **emp_fk,
                    previous_salary=0,
                    new_salary=emp.salary or 0,
                    allowances=(contract_data or {}).get("allowances", 0),
                    effective_date=emp.joining_date or date.today(),
                    change_reason="Initial Hiring",
                    approved_by=username,
                )
            )

            # Optional Contract
            if contract_data:
                c_num = contract_data.get("contract_number") or f"CTR-{emp.employee_id}-{uuid.uuid4().hex[:4].upper()}"
                db.add(
                    EmployeeContract(
                        **emp_fk,
                        contract_number=c_num,
                        contract_type=contract_data.get("contract_type", emp.contract_type or "Permanent"),
                        start_date=contract_data.get("start_date", emp.joining_date or date.today()),
                        end_date=contract_data.get("end_date"),
                        probation_end_date=contract_data.get("probation_end_date"),
                        basic_salary=contract_data.get("basic_salary", emp.salary or 0),
                        allowances=contract_data.get("allowances", 0),
                        working_hours_per_week=contract_data.get("working_hours_per_week", 40),
                        status=contract_data.get("status", "Active"),
                        signed_date=contract_data.get("signed_date", date.today()),
                        terms_summary=contract_data.get("terms_summary"),
                        created_by=username,
                    )
                )

            # Optional Emergency Contact
            if emergency_contact and emergency_contact.get("contact_name") and emergency_contact.get("primary_phone"):
                db.add(
                    EmployeeEmergencyContact(
                        **emp_fk,
                        contact_name=emergency_contact["contact_name"],
                        relationship_label=emergency_contact.get("relationship_label", "Relative"),
                        primary_phone=emergency_contact["primary_phone"],
                        secondary_phone=emergency_contact.get("secondary_phone"),
                        address=emergency_contact.get("address"),
                        priority_order=1,
                        is_primary=True,
                    )
                )

            HRService._log(
                db,
                action=f"HR_{etype.upper()}_ONBOARDED",
                description=f"Onboarded {etype} '{emp.full_name}' ({emp_code}, Role: {role_label})",
                username=username,
                entity_type=etype.capitalize(),
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(emp)
            return True, emp, f"{etype.capitalize()} '{emp.full_name}' onboarded successfully."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            error_logger.exception(f"Error onboarding {employee_type}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def get_employee_dossier(
        db: Session,
        employee_type: str,
        employee_pk: int,
        actor_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Return sanitized employee HR dossier.
        Strictly redacts salary, bank details, and salary history if caller lacks `hr.salary.VIEW`.
        """
        emp = StaffRepository.get_employee(db, employee_type, employee_pk)
        if not emp:
            raise ValueError("Employee record not found.")

        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        etype = employee_type.strip().lower()

        base: Dict[str, Any] = {
            "id": emp.id,
            "employee_type": etype,
            "code": emp.teacher_id if etype == "teacher" else emp.staff_id,
            "employee_id": emp.employee_id,
            "full_name": emp.full_name,
            "gender": emp.gender,
            "date_of_birth": emp.date_of_birth,
            "phone": emp.phone,
            "email": emp.email,
            "address": emp.address,
            "nid_number": emp.nid_number,
            "department_id": emp.department_id,
            "department_name": emp.department.name if emp.department else "-",
            "role_or_designation": emp.designation if etype == "teacher" else emp.position,
            "primary_subject": getattr(emp, "primary_subject", None),
            "shift": getattr(emp, "shift", "Day"),
            "qualification": emp.qualification,
            "joining_date": emp.joining_date,
            "experience_years": emp.experience_years,
            "contract_type": emp.contract_type,
            "status": emp.status,
            "emergency_contact_name": emp.emergency_contact_name,
            "emergency_contact_phone": emp.emergency_contact_phone,
            "salary_visible": can_salary,
            "salary": emp.salary if can_salary else None,
            "salary_display": f"{emp.salary:,}" if can_salary else "[RESTRICTED]",
            "bank_name": emp.bank_name if can_salary else "[RESTRICTED]",
            "bank_account_no": emp.bank_account_no if can_salary else "[RESTRICTED]",
        }
        return base

    @staticmethod
    def get_hr_kpis(db: Session, actor_user: Optional[User] = None) -> Dict[str, Any]:
        stats = StaffRepository.get_overview_statistics(db)
        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        stats["salary_visible"] = can_salary
        if not can_salary:
            stats["monthly_payroll"] = None
        return stats

    # ------------------------------------------------------------------
    # Qualifications, Experience & Teacher Subject Assignments
    # ------------------------------------------------------------------
    @staticmethod
    def add_qualification(
        db: Session,
        employee_type: str,
        employee_pk: int,
        data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeQualification], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."
            if not data.get("degree_or_cert") or not data.get("institution"):
                return False, None, "Degree/Certificate and Institution are required."

            rec = EmployeeQualification(**HRService._emp_filter(employee_type, emp), **data)
            db.add(rec)
            HRService._log(
                db,
                action="HR_QUALIFICATION_ADDED",
                description=f"Added qualification '{data['degree_or_cert']}' for '{emp.full_name}'",
                username=HRSecurityGuard.actor_username(actor_user),
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(rec)
            return True, rec, "Qualification added."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_experience(
        db: Session,
        employee_type: str,
        employee_pk: int,
        data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeExperience], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."
            if not data.get("organization") or not data.get("designation"):
                return False, None, "Organization and Designation are required."

            rec = EmployeeExperience(**HRService._emp_filter(employee_type, emp), **data)
            db.add(rec)
            db.flush()

            # Recompute total prior + recorded experience years when end_date exists
            start_d = data.get("start_date")
            end_d = data.get("end_date") or date.today()
            if isinstance(start_d, date) and isinstance(end_d, date) and end_d >= start_d:
                added_yrs = round((end_d - start_d).days / 365.25, 1)
                emp.experience_years = round(float(emp.experience_years or 0.0) + added_yrs, 1)

            HRService._log(
                db,
                action="HR_EXPERIENCE_ADDED",
                description=f"Added work experience at '{data['organization']}' for '{emp.full_name}'",
                username=HRSecurityGuard.actor_username(actor_user),
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(rec)
            return True, rec, "Work experience recorded."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def assign_subject_to_teacher(
        db: Session,
        teacher_pk: int,
        subject_id: int,
        class_id: int,
        academic_year_id: int,
        section_id: Optional[int] = None,
        is_primary: bool = True,
        weekly_periods: int = 5,
        remarks: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[TeacherSubjectAssignment], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            teacher = StaffRepository.get_teacher_by_id(db, teacher_pk)
            if not teacher:
                return False, None, "Teacher not found."

            existing = (
                db.query(TeacherSubjectAssignment)
                .filter_by(
                    teacher_id=teacher.id,
                    subject_id=subject_id,
                    class_id=class_id,
                    section_id=section_id,
                    academic_year_id=academic_year_id,
                )
                .first()
            )
            if existing:
                return False, existing, "This subject/class assignment already exists for the teacher."

            rec = TeacherSubjectAssignment(
                teacher_id=teacher.id,
                subject_id=subject_id,
                class_id=class_id,
                section_id=section_id,
                academic_year_id=academic_year_id,
                is_primary=is_primary,
                weekly_periods=weekly_periods,
                remarks=remarks,
            )
            db.add(rec)
            HRService._log(
                db,
                action="HR_SUBJECT_ASSIGNED",
                description=f"Assigned subject_id={subject_id}, class_id={class_id} to '{teacher.full_name}'",
                username=HRSecurityGuard.actor_username(actor_user),
                entity_id=teacher.id,
            )
            db.commit()
            db.refresh(rec)
            return True, rec, "Subject assigned to teacher."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # Contracts, Promotion, Transfer & Employment Status Workflows
    # ------------------------------------------------------------------
    @staticmethod
    def create_contract(
        db: Session,
        employee_type: str,
        employee_pk: int,
        contract_data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeContract], str]:
        try:
            HRSecurityGuard.require_permission("hr.contracts.CREATE", actor_user)
            if "basic_salary" in contract_data or "allowances" in contract_data:
                HRSecurityGuard.require_salary_manage(actor_user)

            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            username = HRSecurityGuard.actor_username(actor_user)
            emp_fk = HRService._emp_filter(employee_type, emp)

            # Mark previous active contracts as Renewed
            q_prev = db.query(EmployeeContract).filter(
                EmployeeContract.employee_type == emp_fk["employee_type"],
                EmployeeContract.status == "Active",
            )
            if emp_fk["teacher_id"]:
                q_prev = q_prev.filter(EmployeeContract.teacher_id == emp_fk["teacher_id"])
            else:
                q_prev = q_prev.filter(EmployeeContract.staff_id == emp_fk["staff_id"])
            had_prior = q_prev.count() > 0
            q_prev.update({"status": "Renewed"})

            c_num = contract_data.get("contract_number") or f"CTR-{emp.employee_id}-{uuid.uuid4().hex[:5].upper()}"
            basic_sal = int(contract_data.get("basic_salary", emp.salary or 0))
            allowances = int(contract_data.get("allowances", 0))
            ctype = contract_data.get("contract_type", "Permanent")

            contract = EmployeeContract(
                **emp_fk,
                contract_number=c_num,
                contract_type=ctype,
                start_date=contract_data.get("start_date", date.today()),
                end_date=contract_data.get("end_date"),
                probation_end_date=contract_data.get("probation_end_date"),
                basic_salary=basic_sal,
                allowances=allowances,
                working_hours_per_week=int(contract_data.get("working_hours_per_week", 40)),
                status=contract_data.get("status", "Active"),
                signed_date=contract_data.get("signed_date", date.today()),
                terms_summary=contract_data.get("terms_summary"),
                created_by=username,
            )
            db.add(contract)
            emp.contract_type = ctype

            if basic_sal != emp.salary and HRSecurityGuard.can_manage_salary(actor_user):
                old_sal = emp.salary or 0
                emp.salary = basic_sal
                db.add(
                    EmployeeSalaryHistory(
                        **emp_fk,
                        previous_salary=old_sal,
                        new_salary=basic_sal,
                        allowances=allowances,
                        effective_date=contract.start_date,
                        change_reason="Contract Renewal" if had_prior else "Contract Issuance",
                        reference_no=c_num,
                        approved_by=username,
                    )
                )

            db.add(
                EmployeeLifecycleEvent(
                    **emp_fk,
                    event_type="Contract Renewed" if had_prior else "Contract Signed",
                    effective_date=contract.start_date,
                    reference_no=c_num,
                    reason=f"{ctype} contract ({c_num})",
                    recorded_by=username,
                )
            )
            HRService._log(
                db,
                action="HR_CONTRACT_CREATED",
                description=f"Issued {ctype} contract '{c_num}' for '{emp.full_name}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(contract)
            return True, contract, f"Contract '{c_num}' issued successfully."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def promote_employee(
        db: Session,
        employee_type: str,
        employee_pk: int,
        new_role_or_designation: str,
        new_salary: Optional[int] = None,
        effective_date: Optional[date] = None,
        reason: str = "Merit / Performance Promotion",
        reference_no: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Any], str]:
        try:
            HRSecurityGuard.require_permission("hr.contracts.APPROVE", actor_user)
            if new_salary is not None:
                HRSecurityGuard.require_salary_manage(actor_user)

            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."
            if not new_role_or_designation or not new_role_or_designation.strip():
                return False, None, "New designation/position is required."

            etype = employee_type.strip().lower()
            username = HRSecurityGuard.actor_username(actor_user)
            eff = effective_date or date.today()
            emp_fk = HRService._emp_filter(etype, emp)

            old_role = emp.designation if etype == "teacher" else emp.position
            new_role = new_role_or_designation.strip()
            if etype == "teacher":
                emp.designation = new_role
            else:
                emp.position = new_role

            db.add(
                EmployeeLifecycleEvent(
                    **emp_fk,
                    event_type="Promotion",
                    effective_date=eff,
                    from_designation=old_role,
                    to_designation=new_role,
                    from_department_id=emp.department_id,
                    to_department_id=emp.department_id,
                    reference_no=reference_no,
                    reason=reason,
                    recorded_by=username,
                )
            )

            if new_salary is not None and int(new_salary) != (emp.salary or 0):
                old_sal = emp.salary or 0
                emp.salary = int(new_salary)
                db.add(
                    EmployeeSalaryHistory(
                        **emp_fk,
                        previous_salary=old_sal,
                        new_salary=int(new_salary),
                        allowances=0,
                        effective_date=eff,
                        change_reason="Promotion",
                        reference_no=reference_no,
                        remarks=reason,
                        approved_by=username,
                    )
                )

            HRService._log(
                db,
                action="HR_EMPLOYEE_PROMOTED",
                description=f"Promoted '{emp.full_name}' from '{old_role}' to '{new_role}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(emp)
            return True, emp, f"Promoted '{emp.full_name}' to '{new_role}'."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def transfer_employee(
        db: Session,
        employee_type: str,
        employee_pk: int,
        to_department_id: int,
        new_shift: Optional[str] = None,
        effective_date: Optional[date] = None,
        reason: str = "Departmental / Operational Transfer",
        reference_no: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Any], str]:
        try:
            HRSecurityGuard.require_permission("hr.contracts.APPROVE", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            target_dept = db.query(Department).filter_by(id=to_department_id).first()
            if not target_dept:
                return False, None, "Target department not found."

            etype = employee_type.strip().lower()
            username = HRSecurityGuard.actor_username(actor_user)
            eff = effective_date or date.today()
            old_dept_id = emp.department_id
            old_dept_name = emp.department.name if emp.department else "-"

            emp.department_id = target_dept.id
            if etype == "staff" and new_shift:
                emp.shift = new_shift

            db.add(
                EmployeeLifecycleEvent(
                    **HRService._emp_filter(etype, emp),
                    event_type="Transfer",
                    effective_date=eff,
                    from_department_id=old_dept_id,
                    to_department_id=target_dept.id,
                    reference_no=reference_no,
                    reason=reason,
                    recorded_by=username,
                )
            )
            HRService._log(
                db,
                action="HR_EMPLOYEE_TRANSFERRED",
                description=f"Transferred '{emp.full_name}' from '{old_dept_name}' to '{target_dept.name}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(emp)
            return True, emp, f"Transferred '{emp.full_name}' to '{target_dept.name}'."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def change_employment_status(
        db: Session,
        employee_type: str,
        employee_pk: int,
        new_status: str,
        effective_date: Optional[date] = None,
        reason: str = "",
        reference_no: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[Any], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            clean_status = (new_status or "").strip().lower()
            if clean_status not in EmployeeStatus.ALL:
                return False, None, f"Invalid status '{new_status}'. Allowed: {', '.join(EmployeeStatus.ALL)}"

            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            username = HRSecurityGuard.actor_username(actor_user)
            old_status = emp.status
            emp.status = clean_status

            db.add(
                EmployeeLifecycleEvent(
                    **HRService._emp_filter(employee_type, emp),
                    event_type="Status Change",
                    effective_date=effective_date or date.today(),
                    from_status=old_status,
                    to_status=clean_status,
                    reference_no=reference_no,
                    reason=reason or f"Status changed to {clean_status}",
                    recorded_by=username,
                )
            )
            HRService._log(
                db,
                action="HR_STATUS_CHANGED",
                description=f"Changed status for '{emp.full_name}' from '{old_status}' to '{clean_status}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(emp)
            return True, emp, f"Employment status updated to '{EmployeeStatus.LABELS.get(clean_status, clean_status)}'."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # Leave Management & Approval Workflow
    # ------------------------------------------------------------------
    @staticmethod
    def submit_leave_request(
        db: Session,
        employee_type: str,
        employee_pk: int,
        leave_type: str,
        start_date: date,
        end_date: date,
        reason: str,
        backup_assignee: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeLeaveRequest], str]:
        try:
            HRSecurityGuard.require_permission("hr.leave.CREATE", actor_user)
            if end_date < start_date:
                return False, None, "Leave end date cannot be earlier than start date."
            if not reason or not reason.strip():
                return False, None, "Leave reason is required."

            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            total_days = (end_date - start_date).days + 1
            emp_fk = HRService._emp_filter(employee_type, emp)
            req = EmployeeLeaveRequest(
                **emp_fk,
                leave_type=leave_type.strip(),
                start_date=start_date,
                end_date=end_date,
                total_days=total_days,
                reason=reason.strip(),
                backup_assignee=backup_assignee,
                status="Pending",
            )
            db.add(req)
            HRService._log(
                db,
                action="HR_LEAVE_REQUESTED",
                description=f"Leave requested ({leave_type}, {total_days} day(s)) by '{emp.full_name}'",
                username=HRSecurityGuard.actor_username(actor_user),
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(req)
            return True, req, "Leave request submitted for approval."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def approve_leave_request(
        db: Session,
        request_id: int,
        remarks: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeLeaveRequest], str]:
        try:
            HRSecurityGuard.require_permission(
                "hr.leave.APPROVE",
                actor_user,
                error_msg="Access denied: you do not have permission to approve employee leave.",
            )
            req = db.query(EmployeeLeaveRequest).filter_by(id=request_id).first()
            if not req:
                return False, None, "Leave request not found."
            if req.status != "Pending":
                return False, req, f"Leave request is already '{req.status}'."

            username = HRSecurityGuard.actor_username(actor_user)
            req.status = "Approved"
            req.reviewed_by = username
            req.reviewed_at = utc_now()
            req.review_remarks = remarks or "Approved"

            # Auto-mark approved leave dates in TeacherAttendance / StaffAttendance
            cur = req.start_date
            while cur <= req.end_date:
                if req.employee_type == "teacher" and req.teacher_id:
                    existing = (
                        db.query(TeacherAttendance)
                        .filter(TeacherAttendance.teacher_id == req.teacher_id, TeacherAttendance.date == cur)
                        .first()
                    )
                    if existing:
                        existing.status = "Leave"
                        existing.remarks = f"{req.leave_type} Leave (Approved)"
                        existing.marked_by = username
                    else:
                        db.add(
                            TeacherAttendance(
                                teacher_id=req.teacher_id,
                                date=cur,
                                status="Leave",
                                remarks=f"{req.leave_type} Leave (Approved)",
                                marked_by=username,
                            )
                        )
                elif req.employee_type == "staff" and req.staff_id:
                    existing = (
                        db.query(StaffAttendance)
                        .filter(StaffAttendance.staff_id == req.staff_id, StaffAttendance.date == cur)
                        .first()
                    )
                    if existing:
                        existing.status = "Leave"
                        existing.remarks = f"{req.leave_type} Leave (Approved)"
                        existing.marked_by = username
                    else:
                        db.add(
                            StaffAttendance(
                                staff_id=req.staff_id,
                                date=cur,
                                status="Leave",
                                remarks=f"{req.leave_type} Leave (Approved)",
                                marked_by=username,
                            )
                        )
                cur += timedelta(days=1)

            HRService._log(
                db,
                action="HR_LEAVE_APPROVED",
                description=f"Approved {req.leave_type} leave #{req.id} ({req.start_date} to {req.end_date})",
                username=username,
                entity_id=req.teacher_id or req.staff_id,
            )
            db.commit()
            db.refresh(req)
            return True, req, "Leave request approved and synced to attendance."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def reject_leave_request(
        db: Session,
        request_id: int,
        remarks: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeLeaveRequest], str]:
        try:
            HRSecurityGuard.require_permission(
                "hr.leave.APPROVE",
                actor_user,
                error_msg="Access denied: you do not have permission to reject employee leave.",
            )
            req = db.query(EmployeeLeaveRequest).filter_by(id=request_id).first()
            if not req:
                return False, None, "Leave request not found."
            if req.status != "Pending":
                return False, req, f"Leave request is already '{req.status}'."

            username = HRSecurityGuard.actor_username(actor_user)
            req.status = "Rejected"
            req.reviewed_by = username
            req.reviewed_at = utc_now()
            req.review_remarks = remarks or "Rejected"

            HRService._log(
                db,
                action="HR_LEAVE_REJECTED",
                description=f"Rejected {req.leave_type} leave #{req.id}: {req.review_remarks}",
                username=username,
                entity_id=req.teacher_id or req.staff_id,
            )
            db.commit()
            db.refresh(req)
            return True, req, "Leave request rejected."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # Employee Attendance (Teachers & Non-Teaching Staff)
    # ------------------------------------------------------------------
    @staticmethod
    def mark_employee_attendance(
        db: Session,
        employee_type: str,
        att_date: date,
        records: List[Dict[str, Any]],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        try:
            HRSecurityGuard.require_permission("hr.attendance.CREATE", actor_user)
            if att_date > date.today():
                return False, "Cannot mark employee attendance for future dates."

            etype = employee_type.strip().lower()
            username = HRSecurityGuard.actor_username(actor_user)
            if etype == "teacher":
                saved = AttendanceRepository.save_bulk_teacher_attendance(db, records, marked_by=username)
            elif etype == "staff":
                saved = StaffRepository.save_staff_attendance(db, records, marked_by=username)
            else:
                return False, "employee_type must be 'teacher' or 'staff'."

            HRService._log(
                db,
                action=f"HR_{etype.upper()}_ATTENDANCE",
                description=f"Recorded {etype} attendance for {att_date.isoformat()} ({saved} employee(s))",
                username=username,
            )
            db.commit()
            return True, f"Saved attendance for {saved} {etype} member(s)."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, str(exc)

    # ------------------------------------------------------------------
    # Employee Documents, Salary History (Protected), Evaluations, Emergency Contacts
    # ------------------------------------------------------------------
    @staticmethod
    def add_document(
        db: Session,
        employee_type: str,
        employee_pk: int,
        doc_type: str,
        title: str,
        source_file_path: Optional[str] = None,
        copy_to_vault: bool = True,
        issued_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
        notes: Optional[str] = None,
        is_verified: bool = False,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeDocument], str]:
        try:
            HRSecurityGuard.require_permission("hr.documents.CREATE", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            username = HRSecurityGuard.actor_username(actor_user)
            stored_path = source_file_path
            file_name = Path(source_file_path).name if source_file_path else None
            file_size = 0

            if source_file_path:
                src = Path(source_file_path)
                if src.exists() and src.is_file():
                    if copy_to_vault:
                        stored_path, file_name, file_size = _store_hr_file(
                            HR_DOCS_DIR, emp.employee_id, source_file_path
                        )
                    else:
                        file_size = src.stat().st_size

            doc = EmployeeDocument(
                **HRService._emp_filter(employee_type, emp),
                document_type=doc_type.strip(),
                title=title.strip(),
                file_name=file_name,
                file_path=stored_path,
                file_size_bytes=file_size,
                is_verified=is_verified,
                verified_by=username if is_verified else None,
                verified_at=utc_now() if is_verified else None,
                issued_date=issued_date,
                expiry_date=expiry_date,
                notes=notes,
                uploaded_by=username,
            )
            db.add(doc)
            HRService._log(
                db,
                action="HR_DOCUMENT_ADDED",
                description=f"Added HR document [{doc_type}] '{title}' for '{emp.full_name}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(doc)
            return True, doc, "Employee document recorded."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def verify_document(
        db: Session,
        doc_id: int,
        verified: bool = True,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, str]:
        HRSecurityGuard.require_permission("hr.documents.APPROVE", actor_user)
        doc = db.query(EmployeeDocument).filter_by(id=doc_id).first()
        if not doc:
            return False, "HR document not found."
        username = HRSecurityGuard.actor_username(actor_user)
        doc.is_verified = verified
        doc.verified_by = username if verified else None
        doc.verified_at = utc_now() if verified else None
        db.commit()
        return True, "HR document verification updated."

    @staticmethod
    def revise_salary(
        db: Session,
        employee_type: str,
        employee_pk: int,
        new_salary: int,
        allowances: int = 0,
        effective_date: Optional[date] = None,
        change_reason: str = "Annual Increment",
        reference_no: Optional[str] = None,
        remarks: Optional[str] = None,
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeSalaryHistory], str]:
        """Strictly authorized salary revision workflow."""
        HRSecurityGuard.require_salary_manage(actor_user)
        try:
            if new_salary < 0 or allowances < 0:
                return False, None, "Salary and allowances must be non-negative."
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            username = HRSecurityGuard.actor_username(actor_user)
            old_sal = emp.salary or 0
            emp.salary = int(new_salary)

            entry = EmployeeSalaryHistory(
                **HRService._emp_filter(employee_type, emp),
                previous_salary=old_sal,
                new_salary=int(new_salary),
                allowances=int(allowances),
                effective_date=effective_date or date.today(),
                change_reason=change_reason,
                reference_no=reference_no,
                remarks=remarks,
                approved_by=username,
            )
            db.add(entry)
            HRService._log(
                db,
                action="HR_SALARY_REVISED",
                description=f"Processed confidential salary revision for '{emp.full_name}' ({change_reason})",
                username=username,
                entity_id=emp.id,
                module="HR_SALARY",
            )
            db.commit()
            db.refresh(entry)
            return True, entry, "Salary revision saved."
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def get_salary_history(
        db: Session,
        employee_type: str,
        employee_pk: int,
        actor_user: Optional[User] = None,
    ) -> List[EmployeeSalaryHistory]:
        """Strictly blocks unauthorized roles from retrieving salary history."""
        HRSecurityGuard.require_salary_view(actor_user)
        emp = StaffRepository.get_employee(db, employee_type, employee_pk)
        if not emp:
            raise ValueError("Employee not found.")
        return list(emp.salary_history)

    @staticmethod
    def record_evaluation(
        db: Session,
        employee_type: str,
        employee_pk: int,
        eval_data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeePerformanceEvaluation], str]:
        try:
            HRSecurityGuard.require_permission("hr.evaluations.CREATE", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."

            p = float(eval_data.get("punctuality_score", 4.0))
            c = float(eval_data.get("competency_score", 4.0))
            t = float(eval_data.get("teamwork_score", 4.0))
            cp = float(eval_data.get("compliance_score", 4.0))
            overall = round((p + c + t + cp) / 4.0, 2)

            if overall >= 4.5:
                band = "Outstanding"
            elif overall >= 3.75:
                band = "Exceeds Expectations"
            elif overall >= 2.75:
                band = "Meets Expectations"
            else:
                band = "Needs Improvement"

            username = HRSecurityGuard.actor_username(actor_user)
            rec = EmployeePerformanceEvaluation(
                **HRService._emp_filter(employee_type, emp),
                review_period=eval_data.get("review_period") or f"{date.today().year} Annual",
                review_date=eval_data.get("review_date") or date.today(),
                reviewer_name=eval_data.get("reviewer_name") or username,
                punctuality_score=p,
                competency_score=c,
                teamwork_score=t,
                compliance_score=cp,
                overall_rating=overall,
                rating_band=band,
                strengths=eval_data.get("strengths"),
                areas_for_improvement=eval_data.get("areas_for_improvement"),
                goals=eval_data.get("goals"),
                status=eval_data.get("status", "Finalized"),
            )
            db.add(rec)
            HRService._log(
                db,
                action="HR_EVALUATION_RECORDED",
                description=f"Recorded performance evaluation ({rec.review_period}: {overall}/5.0) for '{emp.full_name}'",
                username=username,
                entity_id=emp.id,
            )
            db.commit()
            db.refresh(rec)
            return True, rec, "Performance evaluation recorded."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    @staticmethod
    def add_emergency_contact(
        db: Session,
        employee_type: str,
        employee_pk: int,
        contact_data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ) -> Tuple[bool, Optional[EmployeeEmergencyContact], str]:
        try:
            HRSecurityGuard.require_permission("hr.directory.EDIT", actor_user)
            emp = StaffRepository.get_employee(db, employee_type, employee_pk)
            if not emp:
                return False, None, "Employee not found."
            if not contact_data.get("contact_name") or not contact_data.get("primary_phone"):
                return False, None, "Contact name and primary phone are required."

            emp_fk = HRService._emp_filter(employee_type, emp)
            is_prim = bool(contact_data.get("is_primary", False))
            if is_prim:
                emp.emergency_contact_name = contact_data["contact_name"]
                emp.emergency_contact_phone = contact_data["primary_phone"]

            priority = contact_data.get("priority_order") or (len(emp.emergency_contacts) + 1)
            rec = EmployeeEmergencyContact(
                **emp_fk,
                contact_name=contact_data["contact_name"],
                relationship_label=contact_data.get("relationship_label", "Relative"),
                primary_phone=contact_data["primary_phone"],
                secondary_phone=contact_data.get("secondary_phone"),
                address=contact_data.get("address"),
                priority_order=priority,
                is_primary=is_prim,
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            return True, rec, "Emergency contact added."
        except PermissionError:
            raise
        except Exception as exc:
            db.rollback()
            return False, None, str(exc)

    # ------------------------------------------------------------------
    # Employee 360° Timeline (Confidentiality-Aware)
    # ------------------------------------------------------------------
    @staticmethod
    def get_employee_timeline(
        db: Session,
        employee_type: str,
        employee_pk: int,
        actor_user: Optional[User] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate chronological HR timeline for a Teacher or Staff member.
        Strictly omits confidential salary details/events if caller lacks `hr.salary.VIEW`.
        """
        emp = StaffRepository.get_employee(db, employee_type, employee_pk)
        if not emp:
            return []

        can_salary = HRSecurityGuard.can_view_salary(actor_user=actor_user, allow_when_no_session=True)
        events: List[Dict[str, Any]] = []

        for ev in emp.lifecycle_events:
            details_parts = []
            if ev.from_designation or ev.to_designation:
                details_parts.append(f"{ev.from_designation or '-'} -> {ev.to_designation or '-'}")
            if ev.from_department_id or ev.to_department_id:
                f_name = ev.from_department.name if ev.from_department else "-"
                t_name = ev.to_department.name if ev.to_department else "-"
                details_parts.append(f"Dept: {f_name} -> {t_name}")
            if ev.from_status or ev.to_status:
                details_parts.append(f"Status: {ev.from_status or 'New'} -> {ev.to_status}")
            if ev.reason:
                details_parts.append(ev.reason)
            events.append({
                "timestamp": datetime.combine(ev.effective_date, datetime.min.time()),
                "category": ev.event_type,
                "title": f"{ev.event_type}" + (f" ({ev.reference_no})" if ev.reference_no else ""),
                "details": " | ".join(details_parts) or ev.event_type,
                "actor": ev.recorded_by,
            })

        for c in emp.contracts:
            comp_str = f" | Salary: {c.basic_salary:,}" if can_salary else ""
            events.append({
                "timestamp": datetime.combine(c.start_date, datetime.min.time()),
                "category": "Contract",
                "title": f"{c.contract_type} Contract ({c.contract_number})",
                "details": f"Status: {c.status} | Weekly Hours: {c.working_hours_per_week}{comp_str}",
                "actor": c.created_by,
            })

        for lv in emp.leave_requests:
            events.append({
                "timestamp": datetime.combine(lv.start_date, datetime.min.time()),
                "category": "Leave",
                "title": f"{lv.leave_type} Leave ({lv.total_days}d) — {lv.status}",
                "details": f"{lv.start_date} to {lv.end_date} | {lv.reason}",
                "actor": lv.reviewed_by or "self",
            })

        for evl in emp.evaluations:
            events.append({
                "timestamp": datetime.combine(evl.review_date, datetime.min.time()),
                "category": "Evaluation",
                "title": f"{evl.review_period}: {evl.overall_rating}/5.0 ({evl.rating_band})",
                "details": evl.strengths or "Performance review finalized",
                "actor": evl.reviewer_name,
            })

        for doc in emp.documents:
            ts = doc.created_at.replace(tzinfo=None) if doc.created_at else datetime.now()
            events.append({
                "timestamp": ts,
                "category": "Document",
                "title": f"{doc.document_type}: {doc.title}",
                "details": "Verified" if doc.is_verified else "Pending Verification",
                "actor": doc.uploaded_by,
            })

        # Salary history ONLY when authorized
        if can_salary:
            for sh in emp.salary_history:
                events.append({
                    "timestamp": datetime.combine(sh.effective_date, datetime.min.time()),
                    "category": "Salary",
                    "title": f"Salary {sh.change_reason}: {sh.previous_salary:,} -> {sh.new_salary:,}",
                    "details": f"Allowances: {sh.allowances:,}" + (f" | {sh.remarks}" if sh.remarks else ""),
                    "actor": sh.approved_by,
                })

        # Attendance summary snapshot
        if employee_type.lower() == "teacher":
            att_rows = db.query(TeacherAttendance).filter_by(teacher_id=emp.id).all()
        else:
            att_rows = db.query(StaffAttendance).filter_by(staff_id=emp.id).all()
        if att_rows:
            present = sum(1 for a in att_rows if a.status == "Present")
            latest = max(a.date for a in att_rows)
            events.append({
                "timestamp": datetime.combine(latest, datetime.min.time()),
                "category": "Attendance",
                "title": f"Attendance Summary ({present}/{len(att_rows)} Present)",
                "details": f"Compliance Rate: {(present / len(att_rows)) * 100:.1f}%",
                "actor": "system",
            })

        events.sort(key=lambda item: item["timestamp"], reverse=True)
        return events
