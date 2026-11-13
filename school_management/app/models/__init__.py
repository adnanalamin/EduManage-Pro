"""
EduManage Pro - Central ORM Model Registry
Importing this module ensures every SQLAlchemy table is registered on Base.metadata.
"""

from app.models.base import (
    Base,
    utc_now,
    generate_uuid,
    PublicIdMixin,
    TimestampMixin,
    SoftDeleteMixin,
)
from app.models.schema_version import SchemaVersion
from app.models.user import (
    User,
    Role,
    Permission,
    LoginHistory,
    PasswordResetToken,
    role_permissions,
)
from app.models.school import SchoolSetting
from app.models.activity import ActivityLog
from app.models.academic import AcademicYear, SchoolClass, Section, Subject
from app.models.student import (
    StudentStatus,
    Guardian,
    Student,
    StudentGuardianLink,
    StudentFamilyRelationship,
    StudentAdmissionHistory,
    StudentAcademicHistory,
    StudentPreviousSchool,
    StudentDocument,
    StudentMedicalProfile,
    StudentEmergencyContact,
    StudentNote,
    StudentTag,
    StudentStatusHistory,
    StudentPromotionHistory,
    student_tag_assignments,
)
from app.models.staff import (
    EmployeeStatus,
    STAFF_ROLE_CATALOG,
    Department,
    Teacher,
    Staff,
    EmployeeQualification,
    EmployeeExperience,
    TeacherSubjectAssignment,
    EmployeeContract,
    EmployeeLeaveRequest,
    EmployeeDocument,
    EmployeeSalaryHistory,
    EmployeePerformanceEvaluation,
    EmployeeLifecycleEvent,
    EmployeeEmergencyContact,
)
from app.models.attendance import AttendanceStatus, StudentAttendance, TeacherAttendance, StaffAttendance
from app.models.fee import FeeCategory, FeeStructure, StudentFee, FeePayment
from app.models.accounting import AccountCategory, AccountTransaction
from app.models.exam import ExamTerm, GradingScale, ExamSchedule, StudentMark, ExamResultSummary
from app.models.timetable import PeriodSlot, TimetableEntry
from app.models.library import BookCategory, Book, LibraryMember, BookCirculation
from app.models.transport import Vehicle, TransportRoute, TransportStop, TransportPassenger
from app.models.hostel import HostelBlock, HostelRoom, HostelAllocation, HostelGatePass
from app.models.inventory import InventoryCategory, InventoryItem, InventoryTransaction
from app.models.notice import SchoolNotice, SchoolEvent
from app.models.certificate import CertificateRecord

__all__ = [
    "Base",
    "utc_now",
    "generate_uuid",
    "PublicIdMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "SchemaVersion",
    "User",
    "Role",
    "Permission",
    "LoginHistory",
    "PasswordResetToken",
    "role_permissions",
    "SchoolSetting",
    "ActivityLog",
    "AcademicYear",
    "SchoolClass",
    "Section",
    "Subject",
    "StudentStatus",
    "Guardian",
    "Student",
    "StudentGuardianLink",
    "StudentFamilyRelationship",
    "StudentAdmissionHistory",
    "StudentAcademicHistory",
    "StudentPreviousSchool",
    "StudentDocument",
    "StudentMedicalProfile",
    "StudentEmergencyContact",
    "StudentNote",
    "StudentTag",
    "StudentStatusHistory",
    "StudentPromotionHistory",
    "student_tag_assignments",
    "EmployeeStatus",
    "STAFF_ROLE_CATALOG",
    "Department",
    "Teacher",
    "Staff",
    "EmployeeQualification",
    "EmployeeExperience",
    "TeacherSubjectAssignment",
    "EmployeeContract",
    "EmployeeLeaveRequest",
    "EmployeeDocument",
    "EmployeeSalaryHistory",
    "EmployeePerformanceEvaluation",
    "EmployeeLifecycleEvent",
    "EmployeeEmergencyContact",
    "AttendanceStatus",
    "StudentAttendance",
    "TeacherAttendance",
    "StaffAttendance",
    "FeeCategory",
    "FeeStructure",
    "StudentFee",
    "FeePayment",
    "AccountCategory",
    "AccountTransaction",
    "ExamTerm",
    "GradingScale",
    "ExamSchedule",
    "StudentMark",
    "ExamResultSummary",
    "PeriodSlot",
    "TimetableEntry",
    "BookCategory",
    "Book",
    "LibraryMember",
    "BookCirculation",
    "Vehicle",
    "TransportRoute",
    "TransportStop",
    "TransportPassenger",
    "HostelBlock",
    "HostelRoom",
    "HostelAllocation",
    "HostelGatePass",
    "InventoryCategory",
    "InventoryItem",
    "InventoryTransaction",
    "SchoolNotice",
    "SchoolEvent",
    "CertificateRecord",
]
