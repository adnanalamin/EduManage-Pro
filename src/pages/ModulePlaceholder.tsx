import React from 'react';
import { Layers, ArrowRight, Database, ShieldCheck, Sparkles, Plus, Download } from 'lucide-react';
import { MODULE_ITEMS } from '../components/Sidebar';

interface ModulePlaceholderProps {
  moduleId: string;
  isDark: boolean;
  onAdmitStudent?: () => void;
}

const PHASE_DETAILS: Record<string, { title: string; phase: number; description: string; features: string[]; models: string[] }> = {
  students: {
    title: 'Student Management System',
    phase: 2,
    description: 'Complete student admission, enrollment records, roll numbers, guardian profiles, ID cards, and student promotion.',
    features: ['Student Admission & Profile with Photo', 'Guardian & Emergency Contacts', 'Roll & Section Allocation', 'ID Card Generator with QR', 'Excel Student Import / Export (.xlsx)'],
    models: ['Student', 'Guardian', 'StudentDocument', 'StudentPromotionHistory'],
  },
  teachers: {
    title: 'Teacher & Faculty Management',
    phase: 3,
    description: 'Faculty directory, subject assignments, department designations, attendance, and salary tracking.',
    features: ['Teacher Profile & Qualifications', 'Department & Subject Allocation', 'Teacher Timetable Integration', 'Salary & Leave Records', 'ID Badge Printing'],
    models: ['Teacher', 'Department', 'TeacherLeave', 'TeacherSalary'],
  },
  staff: {
    title: 'Staff & Employee Directory',
    phase: 3,
    description: 'Staff directory for accountants, receptionists, librarians, security, and administrative personnel.',
    features: ['Employee IDs & Roles', 'Designation & Shifts', 'Payroll Info', 'Document Verification'],
    models: ['Staff', 'StaffDesignation', 'StaffAttendance'],
  },
  academics: {
    title: 'Academic Curriculum & Sessions',
    phase: 4,
    description: 'Academic calendar, grade levels, sections, shifts, and compulsory/optional subject definitions.',
    features: ['Academic Years Management', 'Class 1 to 12 Curriculum', 'Section Capacity & Rooms', 'Subject Pass/Full Marks Setup'],
    models: ['AcademicYear', 'SchoolClass', 'Section', 'Subject'],
  },
  attendance: {
    title: 'Student & Teacher Attendance',
    phase: 5,
    description: 'Daily biometric/manual class-wise attendance marking, monthly reports, and attendance percentage calculator.',
    features: ['One-click Mark All Present', 'Class-wise & Section-wise Entry', 'Monthly Attendance Sheets', 'Absence Alert Notifications'],
    models: ['StudentAttendance', 'TeacherAttendance'],
  },
  fees: {
    title: 'Fees & Billing Collection',
    phase: 6,
    description: 'Fee structures, partial payments, scholarship discounts, due tracking, and instant printed PDF receipts.',
    features: ['Fee Category Definition', 'Collect Cash, Bank, Bkash/Nagad', 'Partial Payment & Due Invoices', 'Printable Fee Receipt with Unique Voucher'],
    models: ['FeeStructure', 'FeeInvoice', 'FeePayment', 'ScholarshipDiscount'],
  },
  accounting: {
    title: 'School Accounts & Ledgers',
    phase: 7,
    description: 'School accounting, income ledgers, expense tracking (salary, utility, supplies), and monthly balance sheets.',
    features: ['Income Entry', 'Expense Vouchers & Approvals', 'Monthly Cashbook & Summary', 'Profit & Loss Statement'],
    models: ['Income', 'Expense', 'ExpenseCategory', 'AccountLedger'],
  },
  exams: {
    title: 'Examination Management',
    phase: 8,
    description: 'Exam scheduling, exam types (Class Test, Half-Yearly, Final), seating plans, and subject rosters.',
    features: ['Exam Schedule Creator', 'Full Marks & Pass Marks Matrix', 'Hall Ticket Printing', 'Admit Card Generation'],
    models: ['Exam', 'ExamSchedule', 'ExamHall'],
  },
  results: {
    title: 'Grading, Results & GPA Calculation',
    phase: 8,
    description: 'Automated GPA calculation, Bangladeshi grading system (A+, A, A-, B, C, D, F), report cards, and mark sheets.',
    features: ['Marks Entry by Subject Teachers', 'Automated GPA & Grade Calculation', 'Tabulation Sheet Generation', 'Printable Student Report Cards'],
    models: ['Mark', 'ExamResult', 'GradeScale'],
  },
  timetable: {
    title: 'Class & Teacher Timetable',
    phase: 9,
    description: 'Weekly schedule generator for classes and teachers across Saturday to Friday.',
    features: ['Conflict-free Routine Builder', 'Teacher Schedule View', 'Classroom Allocation', 'Printable Routine Grid'],
    models: ['TimetableSlot', 'Period', 'RoomAssignment'],
  },
  library: {
    title: 'Library Circulation & Inventory',
    phase: 10,
    description: 'Book inventory, ISBN tracking, student/teacher book issue & returns, and overdue fine calculations.',
    features: ['Book Catalog with Shelf Number', 'Issue & Return Workflow', 'Overdue Fine Calculation', 'Borrowing History'],
    models: ['Book', 'BookIssue', 'BookCategory'],
  },
  transport: {
    title: 'Transport & Fleet Management',
    phase: 11,
    description: 'School buses, drivers, pickup routes, vehicle maintenance, and student bus pass billing.',
    features: ['Vehicle Roster & Driver Info', 'Pickup Stoppage Routes', 'Student Assignment', 'Monthly Transport Fees'],
    models: ['Vehicle', 'TransportRoute', 'StudentTransport'],
  },
  hostel: {
    title: 'Hostel & Dormitory Management',
    phase: 12,
    description: 'Hostel buildings, floors, rooms, bed allotment, meal charges, and check-in/out records.',
    features: ['Hostel & Room Master', 'Bed Occupancy Tracker', 'Hostel Fee Invoices', 'Visitor Logbook'],
    models: ['HostelBuilding', 'HostelRoom', 'HostelAllotment'],
  },
  notices: {
    title: 'Notice Board & Circulars',
    phase: 13,
    description: 'Publish official campus circulars with priorities, category tags, and PDF attachment references.',
    features: ['General, Exam, Holiday Notices', 'Target Audience (Students, Teachers, All)', 'Emergency Push Notices', 'Printable Notice Format'],
    models: ['Notice', 'NoticeCategory', 'NoticeAttachment'],
  },
  events: {
    title: 'Events & Academic Calendar',
    phase: 13,
    description: 'School cultural programs, sports meets, parent-teacher meetings, and national holiday schedules.',
    features: ['Event Date & Venue Scheduler', 'Organizer Assignment', 'Upcoming Events Countdown', 'Event Agenda'],
    models: ['SchoolEvent', 'EventOrganizer'],
  },
  reports: {
    title: 'Executive Reports & Analytics',
    phase: 14,
    description: 'Comprehensive cross-module report generation with date range filters, Excel (.xlsx) export, and ReportLab PDF.',
    features: ['Student Enrollment Reports', 'Fee Collection Ledger Reports', 'Teacher Attendance Summaries', 'Export to Excel & PDF'],
    models: ['ReportConfig', 'ExportJob'],
  },
  certificates: {
    title: 'Certificates & ID Card Generator',
    phase: 15,
    description: 'Generate Transfer Certificates (TC), Testimonials, Bonafide Certificates, and Printable PVC/Paper ID Cards.',
    features: ['Transfer Certificate Generator', 'Character Testimonials', 'Student & Teacher ID Cards with QR', 'Print Layout Customizer'],
    models: ['CertificateTemplate', 'IssuedCertificate', 'IDCardBadge'],
  },
  settings: {
    title: 'School Profile & System Settings',
    phase: 1,
    description: 'Institution identity, logo, official seal, currency, grading policy, and backup management.',
    features: ['Institution Name (English & Bangla)', 'EIIN & Registration Codes', 'Currency (BDT ৳ / USD $)', 'Academic Year Default'],
    models: ['SchoolSetting', 'User', 'Role', 'Permission'],
  },
};

export const ModulePlaceholder: React.FC<ModulePlaceholderProps> = ({ moduleId, isDark }) => {
  const current = MODULE_ITEMS.find((m) => m.id === moduleId);
  const details = PHASE_DETAILS[moduleId] || {
    title: current?.label || 'Module',
    phase: current?.phase || 2,
    description: 'This operational module is defined in the EduManage Pro architecture.',
    features: ['Full CRUD Operations', 'Local SQLite Persistence', 'Role-Based Permissions', 'Print & Export Support'],
    models: ['DomainModel'],
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 select-none">
      {/* Header card */}
      <div
        className={`p-6 rounded-2xl border ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center text-2xl font-bold">
              {current?.icon ? React.createElement(current.icon, { className: 'w-6 h-6 text-blue-400' }) : '📋'}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-100">{details.title}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  Phase {details.phase} Module
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">{details.description}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 font-medium text-xs border border-emerald-500/20 flex items-center space-x-1.5">
              <Database className="w-3.5 h-3.5" />
              <span>Schema Ready in SQLite</span>
            </span>
          </div>
        </div>
      </div>

      {/* Feature Capabilities grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Planned Functional Operations */}
        <div
          className={`p-5 rounded-2xl border ${
            isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center space-x-2 pb-3 border-b border-inherit mb-3">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold">Planned Phase Capabilities</h3>
          </div>
          <ul className="space-y-2 text-xs">
            {details.features.map((feat, idx) => (
              <li key={idx} className="flex items-center space-x-2 text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Database ORM Entities */}
        <div
          className={`p-5 rounded-2xl border ${
            isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="flex items-center space-x-2 pb-3 border-b border-inherit mb-3">
            <Database className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold">SQLAlchemy ORM Data Models</h3>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            The database schemas and relations are declared in the Clean Architecture repository:
          </p>
          <div className="flex flex-wrap gap-2">
            {details.models.map((model) => (
              <span
                key={model}
                className="px-2.5 py-1 rounded-lg bg-slate-800 font-mono text-xs text-blue-300 border border-slate-700"
              >
                {model}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Notice about building phase by phase */}
      <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-start space-x-3">
        <ShieldCheck className="w-5 h-5 shrink-0 text-blue-400 mt-0.5" />
        <div>
          <p className="font-semibold text-slate-200">Phase 1 Foundation Active</p>
          <p className="mt-0.5 text-slate-400 leading-relaxed">
            Per development rules, Phase 1 establishes the core foundation: SQLite engine, WAL mode, Bcrypt security,
            Role-Based Access Control, First-Run Wizard, Main Dashboard, and PySide6 Desktop UI. Subsequent phases
            (Phase 2: Students, Phase 3: Teachers, etc.) will progressively build out each respective module's full forms,
            dialogs, and ReportLab PDF generators!
          </p>
        </div>
      </div>
    </div>
  );
};
