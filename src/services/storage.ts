import {
  User,
  SchoolSetting,
  ActivityLogItem,
  AcademicClass,
  UserRole,
  Student,
  Teacher,
  Staff,
  AcademicYearInfo,
  SchoolClassInfo,
  SectionInfo,
  SubjectInfo,
  AttendanceStatus,
  StudentAttendanceRecord,
  TeacherAttendanceRecord,
  FeeCategoryInfo,
  FeeStructureInfo,
  StudentFeeInvoice,
  FeePaymentRecord,
  AccountCategoryInfo,
  AccountTransactionRecord,
  FinancialSummary,
  ExamTermInfo,
  GradingScaleInfo,
  ExamScheduleInfo,
  StudentMarkRecord,
  ExamResultSummaryInfo,
  PeriodSlotInfo,
  TimetableEntryInfo,
  TimetableConflict,
  BookCategoryInfo,
  BookInfo,
  LibraryMemberInfo,
  BookCirculationRecord,
  LibraryStatsInfo,
  VehicleInfo,
  TransportStopInfo,
  TransportRouteInfo,
  TransportPassengerInfo,
  TransportStatsInfo,
  HostelBlockInfo,
  HostelRoomInfo,
  HostelAllocationInfo,
  HostelGatePassInfo,
  HostelStatsInfo,
  SchoolNoticeInfo,
  SchoolEventInfo,
  NoticeStatsInfo,
  FeeDefaulterRecord,
  ClassAttendanceAuditItem,
  ComprehensiveReportAnalytics,
  CertificateType,
  CertificateRecordInfo,
  CertificateStatsInfo,
} from '../types';

const STORAGE_KEYS = {
  SCHOOL_SETTINGS: 'edumanage_school_settings',
  USERS: 'edumanage_users',
  CURRENT_USER: 'edumanage_current_user',
  LOGS: 'edumanage_activity_logs',
  THEME: 'edumanage_theme',
  CLASSES: 'edumanage_classes',
  STUDENTS: 'edumanage_students',
  TEACHERS: 'edumanage_teachers',
  STAFF: 'edumanage_staff',
  ACADEMIC_YEARS: 'edumanage_academic_years',
  DETAILED_CLASSES: 'edumanage_detailed_classes',
  SECTIONS: 'edumanage_sections',
  SUBJECTS: 'edumanage_subjects',
  STUDENT_ATTENDANCES: 'edumanage_student_attendances',
  TEACHER_ATTENDANCES: 'edumanage_teacher_attendances',
  FEE_CATEGORIES: 'edumanage_fee_categories',
  FEE_STRUCTURES: 'edumanage_fee_structures',
  STUDENT_FEES: 'edumanage_student_fees',
  FEE_PAYMENTS: 'edumanage_fee_payments',
  ACCOUNT_CATEGORIES: 'edumanage_account_categories',
  ACCOUNT_TRANSACTIONS: 'edumanage_account_transactions',
  EXAM_TERMS: 'edumanage_exam_terms',
  GRADING_SCALES: 'edumanage_grading_scales',
  EXAM_SCHEDULES: 'edumanage_exam_schedules',
  STUDENT_MARKS: 'edumanage_student_marks',
  EXAM_RESULT_SUMMARIES: 'edumanage_exam_result_summaries',
  TIMETABLE_PERIODS: 'edumanage_timetable_periods',
  TIMETABLE_ENTRIES: 'edumanage_timetable_entries',
  BOOK_CATEGORIES: 'edumanage_book_categories',
  LIBRARY_BOOKS: 'edumanage_library_books',
  LIBRARY_MEMBERS: 'edumanage_library_members',
  BOOK_CIRCULATIONS: 'edumanage_book_circulations',
  TRANSPORT_VEHICLES: 'edumanage_transport_vehicles',
  TRANSPORT_ROUTES: 'edumanage_transport_routes',
  TRANSPORT_PASSENGERS: 'edumanage_transport_passengers',
  HOSTEL_BLOCKS: 'edumanage_hostel_blocks',
  HOSTEL_ROOMS: 'edumanage_hostel_rooms',
  HOSTEL_ALLOCATIONS: 'edumanage_hostel_allocations',
  HOSTEL_GATE_PASSES: 'edumanage_hostel_gate_passes',
  NOTICES: 'edumanage_school_notices',
  EVENTS: 'edumanage_school_events',
  CERTIFICATES: 'edumanage_certificates',
};

const DEFAULT_SCHOOL_SETTINGS: SchoolSetting = {
  schoolName: 'Ideal Model High School & College',
  schoolNameBn: 'আইডিয়াল মডেল হাই স্কুল অ্যান্ড কলেজ',
  motto: 'Excellence in Education & Character',
  eiinNumber: '134211',
  registrationNo: 'REG-DH-2024-889',
  address: 'Plot 12, Road 4, Sector 7, Uttara',
  city: 'Dhaka',
  district: 'Dhaka',
  country: 'Bangladesh',
  phone: '+880 1712-345678',
  email: 'contact@idealmodel.edu.bd',
  website: 'https://idealmodel.edu.bd',
  principalName: 'Prof. Dr. Mohammad Rafiqul Islam',
  currencyCode: 'BDT',
  currencySymbol: '৳',
  language: 'en',
  isSetupCompleted: true,
};

const DEFAULT_USERS: User[] = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@school.local',
    fullName: 'System Super Administrator',
    phone: '+880 1700-000000',
    role: 'super_admin',
    roleDisplayName: 'Super Admin',
    isActive: true,
    isDefaultPassword: true,
    failedLoginAttempts: 0,
    lockedUntil: null,
    lastLoginAt: '2026-11-09 08:30:00',
  },
  {
    id: 2,
    username: 'principal',
    email: 'principal@idealmodel.edu.bd',
    fullName: 'Dr. Mohammad Rafiqul Islam',
    phone: '+880 1711-223344',
    role: 'administrator',
    roleDisplayName: 'Administrator',
    isActive: true,
    isDefaultPassword: false,
    failedLoginAttempts: 0,
    lockedUntil: null,
    lastLoginAt: '2026-11-08 14:15:00',
  },
  {
    id: 3,
    username: 'teacher.kamal',
    email: 'kamal.hossain@idealmodel.edu.bd',
    fullName: 'Kamal Hossain (Senior Science Teacher)',
    phone: '+880 1819-334455',
    role: 'teacher',
    roleDisplayName: 'Teacher',
    isActive: true,
    isDefaultPassword: false,
    failedLoginAttempts: 0,
    lockedUntil: null,
    lastLoginAt: '2026-11-09 09:00:00',
  },
  {
    id: 4,
    username: 'accountant.shafiq',
    email: 'accounts@idealmodel.edu.bd',
    fullName: 'Shafiqul Alam (Chief Accountant)',
    phone: '+880 1912-778899',
    role: 'accountant',
    roleDisplayName: 'Accountant',
    isActive: true,
    isDefaultPassword: false,
    failedLoginAttempts: 0,
    lockedUntil: null,
    lastLoginAt: '2026-11-09 08:45:00',
  },
];

const DEFAULT_CLASSES: AcademicClass[] = [
  { id: 1, name: 'Class 6', code: 'C6', sections: ['A', 'B', 'Padma'], studentCount: 280 },
  { id: 2, name: 'Class 7', code: 'C7', sections: ['A', 'B', 'Meghna'], studentCount: 295 },
  { id: 3, name: 'Class 8', code: 'C8', sections: ['A', 'B', 'Jamuna'], studentCount: 310 },
  { id: 4, name: 'Class 9', code: 'C9', sections: ['Science', 'Commerce', 'Arts'], studentCount: 265 },
  { id: 5, name: 'Class 10', code: 'C10', sections: ['Science', 'Commerce', 'Arts'], studentCount: 270 },
];

const DEFAULT_STUDENTS: Student[] = [
  {
    id: 1,
    studentId: 'STU-2024-0001',
    admissionNumber: 'ADM-2024-0101',
    rollNumber: 1,
    firstName: 'Tahsin',
    lastName: 'Rahman',
    fullName: 'Tahsin Rahman',
    fullNameBn: 'তাহসিন রহমান',
    gender: 'Male',
    dateOfBirth: '2009-04-12',
    bloodGroup: 'A+',
    phone: '+880 1711-987654',
    email: 'tahsin.rahman@student.edu.bd',
    address: 'House 24, Road 7, Sector 4, Uttara',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-05',
    className: 'Class 10',
    sectionName: 'Science',
    group: 'Science',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 1,
      fatherName: 'Dr. Lutfor Rahman',
      motherName: 'Nusrat Jahan',
      guardianName: 'Dr. Lutfor Rahman',
      relation: 'Father',
      guardianPhone: '+880 1711-223344',
      guardianOccupation: 'Doctor',
      guardianAddress: 'Uttara, Dhaka',
    },
    emergencyContact: '+880 1711-223344',
    medicalNotes: 'No known allergies. Good eyesight.',
  },
  {
    id: 2,
    studentId: 'STU-2024-0002',
    admissionNumber: 'ADM-2024-0102',
    rollNumber: 2,
    firstName: 'Sadia',
    lastName: 'Jahan',
    fullName: 'Sadia Jahan',
    fullNameBn: 'সাদিয়া জাহান',
    gender: 'Female',
    dateOfBirth: '2009-08-20',
    bloodGroup: 'B+',
    phone: '+880 1819-112233',
    email: 'sadia.jahan@student.edu.bd',
    address: 'Flat 4B, Green Road',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-05',
    className: 'Class 10',
    sectionName: 'Science',
    group: 'Science',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 2,
      fatherName: 'Jahangir Alam',
      motherName: 'Rokeya Begum',
      guardianName: 'Jahangir Alam',
      relation: 'Father',
      guardianPhone: '+880 1819-556677',
      guardianOccupation: 'Govt Officer',
    },
    emergencyContact: '+880 1819-556677',
  },
  {
    id: 3,
    studentId: 'STU-2024-0003',
    admissionNumber: 'ADM-2024-0103',
    rollNumber: 3,
    firstName: 'Tanvir',
    lastName: 'Hasan',
    fullName: 'Tanvir Hasan',
    fullNameBn: 'তানভীর হাসান',
    gender: 'Male',
    dateOfBirth: '2009-11-15',
    bloodGroup: 'O+',
    phone: '+880 1912-334455',
    email: 'tanvir.hasan@student.edu.bd',
    address: 'Dhanmondi 9/A',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-06',
    className: 'Class 10',
    sectionName: 'Commerce',
    group: 'Business Studies',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 3,
      fatherName: 'Kamrul Hasan',
      motherName: 'Farhana Yasmin',
      guardianName: 'Kamrul Hasan',
      relation: 'Father',
      guardianPhone: '+880 1912-889900',
      guardianOccupation: 'Businessman',
    },
    emergencyContact: '+880 1912-889900',
  },
  {
    id: 4,
    studentId: 'STU-2024-0004',
    admissionNumber: 'ADM-2024-0104',
    rollNumber: 1,
    firstName: 'Farhana',
    lastName: 'Akter',
    fullName: 'Farhana Akter',
    fullNameBn: 'ফারহানা আক্তার',
    gender: 'Female',
    dateOfBirth: '2010-02-18',
    bloodGroup: 'AB+',
    phone: '+880 1612-445566',
    address: 'Mirpur 10, Block C',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-08',
    className: 'Class 9',
    sectionName: 'Science',
    group: 'Science',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 4,
      fatherName: 'Mustafizur Rahman',
      motherName: 'Shamsun Nahar',
      guardianName: 'Mustafizur Rahman',
      relation: 'Father',
      guardianPhone: '+880 1612-990011',
      guardianOccupation: 'Engineer',
    },
    emergencyContact: '+880 1612-990011',
  },
  {
    id: 5,
    studentId: 'STU-2024-0005',
    admissionNumber: 'ADM-2024-0105',
    rollNumber: 2,
    firstName: 'Abrar',
    lastName: 'Fahim',
    fullName: 'Abrar Fahim',
    fullNameBn: 'আবরার ফাহিম',
    gender: 'Male',
    dateOfBirth: '2010-06-25',
    bloodGroup: 'A-',
    phone: '+880 1713-778899',
    address: 'Banasree Block F',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-10',
    className: 'Class 9',
    sectionName: 'Science',
    group: 'Science',
    shift: 'Morning',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 5,
      fatherName: 'Mahbub Alam',
      motherName: 'Salma Begum',
      guardianName: 'Mahbub Alam',
      relation: 'Father',
      guardianPhone: '+880 1713-112233',
      guardianOccupation: 'Banker',
    },
    emergencyContact: '+880 1713-112233',
  },
  {
    id: 6,
    studentId: 'STU-2024-0006',
    admissionNumber: 'ADM-2024-0106',
    rollNumber: 1,
    firstName: 'Mehnaz',
    lastName: 'Chowdhury',
    fullName: 'Mehnaz Chowdhury',
    fullNameBn: 'মেহনাজ চৌধুরী',
    gender: 'Female',
    dateOfBirth: '2011-09-05',
    bloodGroup: 'O-',
    phone: '+880 1814-223344',
    address: 'Gulshan 2',
    city: 'Dhaka',
    district: 'Dhaka',
    admissionDate: '2024-01-12',
    className: 'Class 8',
    sectionName: 'A',
    group: 'General',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    guardian: {
      id: 6,
      fatherName: 'Enamul Chowdhury',
      motherName: 'Nasrin Sultana',
      guardianName: 'Enamul Chowdhury',
      relation: 'Father',
      guardianPhone: '+880 1814-778899',
      guardianOccupation: 'Architect',
    },
    emergencyContact: '+880 1814-778899',
  },
];

const DEFAULT_LOGS: ActivityLogItem[] = [
  {
    id: 1,
    timestamp: '2026-11-09 08:30:14',
    username: 'admin',
    action: 'LOGIN_SUCCESS',
    module: 'AUTH',
    description: "User 'admin' logged in successfully as Super Admin",
    severity: 'INFO',
  },
  {
    id: 2,
    timestamp: '2026-11-09 08:35:22',
    username: 'admin',
    action: 'SYSTEM_STARTUP',
    module: 'SYSTEM',
    description: 'SQLite database engine initialized in WAL mode',
    severity: 'INFO',
  },
  {
    id: 3,
    timestamp: '2026-11-09 08:45:10',
    username: 'accountant.shafiq',
    action: 'FEE_COLLECTION',
    module: 'FEES',
    description: 'Collected monthly tuition fees for 12 students (Class 9)',
    severity: 'INFO',
  },
  {
    id: 4,
    timestamp: '2026-11-09 09:05:02',
    username: 'teacher.kamal',
    action: 'ATTENDANCE_MARKED',
    module: 'ATTENDANCE',
    description: 'Attendance recorded for Class 10 (Science Section A): 48 Present, 2 Absent',
    severity: 'INFO',
  },
];

const DEFAULT_TEACHERS: Teacher[] = [
  {
    id: 1,
    teacherId: 'TCH-2024-0001',
    employeeId: 'EMP-2024-1001',
    fullName: 'Kamal Hossain',
    fullNameBn: 'কামাল হোসেন',
    gender: 'Male',
    dateOfBirth: '1984-06-15',
    bloodGroup: 'B+',
    phone: '+880 1819-334455',
    email: 'kamal.hossain@idealmodel.edu.bd',
    qualification: 'M.Sc. in Physics (DU), B.Ed',
    designation: 'Senior Faculty Specialist',
    department: 'Science',
    primarySubject: 'Physics',
    joiningDate: '2016-02-01',
    salary: 48000,
    status: 'active',
    attendanceToday: 'present',
  },
  {
    id: 2,
    teacherId: 'TCH-2024-0002',
    employeeId: 'EMP-2024-1002',
    fullName: 'Nazmul Islam',
    fullNameBn: 'নাজমুল ইসলাম',
    gender: 'Male',
    dateOfBirth: '1982-10-10',
    bloodGroup: 'A+',
    phone: '+880 1712-445566',
    email: 'nazmul.islam@idealmodel.edu.bd',
    qualification: 'M.Sc. in Applied Mathematics (JU)',
    designation: 'Department Head',
    department: 'Mathematics',
    primarySubject: 'Higher Mathematics',
    joiningDate: '2014-08-15',
    salary: 55000,
    status: 'active',
    attendanceToday: 'present',
  },
  {
    id: 3,
    teacherId: 'TCH-2024-0003',
    employeeId: 'EMP-2024-1003',
    fullName: 'Fahmida Sultana',
    fullNameBn: 'ফাহমিদা সুলতানা',
    gender: 'Female',
    dateOfBirth: '1989-03-24',
    bloodGroup: 'O+',
    phone: '+880 1913-223344',
    email: 'fahmida.sultana@idealmodel.edu.bd',
    qualification: 'M.A. in English Literature (RU)',
    designation: 'Assistant Teacher',
    department: 'Languages',
    primarySubject: 'English 1st & 2nd Paper',
    joiningDate: '2019-01-10',
    salary: 38000,
    status: 'active',
    attendanceToday: 'present',
  },
  {
    id: 4,
    teacherId: 'TCH-2024-0004',
    employeeId: 'EMP-2024-1004',
    fullName: 'Abdur Razzaq',
    fullNameBn: 'আব্দুর রাজ্জাক',
    gender: 'Male',
    dateOfBirth: '1987-12-05',
    bloodGroup: 'AB+',
    phone: '+880 1614-556677',
    email: 'abdur.razzaq@idealmodel.edu.bd',
    qualification: 'M.Sc. in Computer Science',
    designation: 'ICT Lecturer',
    department: 'ICT & Computer Science',
    primarySubject: 'Information & Comm. Technology',
    joiningDate: '2018-07-01',
    salary: 42000,
    status: 'active',
    attendanceToday: 'present',
  },
  {
    id: 5,
    teacherId: 'TCH-2024-0005',
    employeeId: 'EMP-2024-1005',
    fullName: 'Nusrat Jahan Chowdhury',
    fullNameBn: 'নুসরাত জাহান চৌধুরী',
    gender: 'Female',
    dateOfBirth: '1991-07-19',
    bloodGroup: 'B-',
    phone: '+880 1715-889900',
    email: 'nusrat.jahan@idealmodel.edu.bd',
    qualification: 'M.Sc. in Botany & Chemistry',
    designation: 'Assistant Teacher',
    department: 'Science',
    primarySubject: 'Biology',
    joiningDate: '2021-03-01',
    salary: 36000,
    status: 'active',
    attendanceToday: 'leave',
  },
];

const DEFAULT_STAFF: Staff[] = [
  {
    id: 1,
    staffId: 'STF-2024-0001',
    employeeId: 'EMP-2024-2001',
    fullName: 'Shafiqul Alam',
    fullNameBn: 'শফিকুল আলম',
    gender: 'Male',
    dateOfBirth: '1985-04-18',
    phone: '+880 1912-778899',
    email: 'accounts@idealmodel.edu.bd',
    position: 'Chief Accountant',
    department: 'Administration & Accounts',
    shift: 'Day',
    joiningDate: '2015-09-01',
    salary: 38000,
    status: 'active',
  },
  {
    id: 2,
    staffId: 'STF-2024-0002',
    employeeId: 'EMP-2024-2002',
    fullName: 'Farhana Yasmin',
    fullNameBn: 'ফারহানা ইয়াসমিন',
    gender: 'Female',
    dateOfBirth: '1990-11-20',
    phone: '+880 1815-332211',
    email: 'library@idealmodel.edu.bd',
    position: 'Librarian',
    department: 'Library & Support',
    shift: 'Day',
    joiningDate: '2018-04-15',
    salary: 28000,
    status: 'active',
  },
  {
    id: 3,
    staffId: 'STF-2024-0003',
    employeeId: 'EMP-2024-2003',
    fullName: 'Tania Akter',
    fullNameBn: 'তানিয়া আক্তার',
    gender: 'Female',
    dateOfBirth: '1994-08-14',
    phone: '+880 1716-112244',
    email: 'reception@idealmodel.edu.bd',
    position: 'Front Desk Receptionist',
    department: 'Administration & Accounts',
    shift: 'Morning',
    joiningDate: '2022-01-05',
    salary: 24000,
    status: 'active',
  },
  {
    id: 4,
    staffId: 'STF-2024-0004',
    employeeId: 'EMP-2024-2004',
    fullName: 'Md. Jahangir Alam',
    fullNameBn: 'মোঃ জাহাঙ্গীর আলম',
    gender: 'Male',
    dateOfBirth: '1980-02-10',
    phone: '+880 1818-990011',
    position: 'Security Supervisor',
    department: 'Security & Facilities',
    shift: 'Night',
    joiningDate: '2017-06-01',
    salary: 22000,
    status: 'active',
  },
];

const DEFAULT_ACADEMIC_YEARS: AcademicYearInfo[] = [
  {
    id: 1,
    name: '2025-2026',
    startDate: '2025-01-01',
    endDate: '2025-12-31',
    isCurrent: true,
    status: 'Active',
  },
  {
    id: 2,
    name: '2026-2027',
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    isCurrent: false,
    status: 'Upcoming',
  },
];

const DEFAULT_SECTIONS: SectionInfo[] = [
  {
    id: 1,
    name: 'Section A (Padma)',
    classId: 4,
    className: 'Class 9',
    roomNumber: 'Room 201',
    capacity: 50,
    shift: 'Morning',
    group: 'Science',
    classTeacherId: 1,
    classTeacherName: 'Kamal Hossain',
    studentCount: 48,
  },
  {
    id: 2,
    name: 'Section B (Meghna)',
    classId: 4,
    className: 'Class 9',
    roomNumber: 'Room 202',
    capacity: 50,
    shift: 'Day',
    group: 'Science',
    classTeacherId: 2,
    classTeacherName: 'Nasreen Akter',
    studentCount: 46,
  },
  {
    id: 3,
    name: 'Section A (Jamuna)',
    classId: 5,
    className: 'Class 10',
    roomNumber: 'Room 301',
    capacity: 48,
    shift: 'Day',
    group: 'Science',
    classTeacherId: 3,
    classTeacherName: 'Mahmudur Rahman',
    studentCount: 45,
  },
  {
    id: 4,
    name: 'Section B (Surma)',
    classId: 5,
    className: 'Class 10',
    roomNumber: 'Room 302',
    capacity: 45,
    shift: 'Morning',
    group: 'Science',
    classTeacherId: 4,
    classTeacherName: 'Sultana Razia',
    studentCount: 42,
  },
  {
    id: 5,
    name: 'Section A',
    classId: 1,
    className: 'Class 6',
    roomNumber: 'Room 101',
    capacity: 50,
    shift: 'Morning',
    group: 'General',
    classTeacherId: 5,
    classTeacherName: 'Mohammad Ali',
    studentCount: 49,
  },
  {
    id: 6,
    name: 'Section A',
    classId: 3,
    className: 'Class 8',
    roomNumber: 'Room 104',
    capacity: 50,
    shift: 'Morning',
    group: 'General',
    classTeacherId: 1,
    classTeacherName: 'Kamal Hossain',
    studentCount: 50,
  },
];

const DEFAULT_DETAILED_CLASSES: SchoolClassInfo[] = [
  {
    id: 1,
    name: 'Class 6',
    code: 'C06',
    numericOrder: 6,
    group: 'General',
    shift: 'Morning',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 7,
    studentCount: 49,
  },
  {
    id: 2,
    name: 'Class 7',
    code: 'C07',
    numericOrder: 7,
    group: 'General',
    shift: 'Morning',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 7,
    studentCount: 52,
  },
  {
    id: 3,
    name: 'Class 8',
    code: 'C08',
    numericOrder: 8,
    group: 'General',
    shift: 'Morning',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 8,
    studentCount: 50,
  },
  {
    id: 4,
    name: 'Class 9',
    code: 'C09-SCI',
    numericOrder: 9,
    group: 'Science',
    shift: 'Day',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 9,
    studentCount: 94,
  },
  {
    id: 5,
    name: 'Class 10',
    code: 'C10-SCI',
    numericOrder: 10,
    group: 'Science',
    shift: 'Day',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 9,
    studentCount: 87,
  },
  {
    id: 6,
    name: 'Class 11',
    code: 'C11-SCI',
    numericOrder: 11,
    group: 'Science',
    shift: 'Morning',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 8,
    studentCount: 65,
  },
  {
    id: 7,
    name: 'Class 12',
    code: 'C12-BS',
    numericOrder: 12,
    group: 'Business Studies',
    shift: 'Day',
    academicYearId: 1,
    academicYearName: '2025-2026',
    sections: [],
    subjectCount: 8,
    studentCount: 58,
  },
];

const DEFAULT_SUBJECTS: SubjectInfo[] = [
  {
    id: 1,
    subjectId: 'SUB-2026-0001',
    name: 'Bangla 1st Paper',
    code: '101',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 100,
    practicalMarks: 0,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 4,
    teacherName: 'Sultana Razia',
  },
  {
    id: 2,
    subjectId: 'SUB-2026-0002',
    name: 'English 1st Paper',
    code: '107',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 100,
    practicalMarks: 0,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 5,
    teacherName: 'Mohammad Ali',
  },
  {
    id: 3,
    subjectId: 'SUB-2026-0003',
    name: 'General Mathematics',
    code: '109',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 100,
    practicalMarks: 0,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 1,
    teacherName: 'Kamal Hossain',
  },
  {
    id: 4,
    subjectId: 'SUB-2026-0004',
    name: 'Higher Mathematics',
    code: '126',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Optional',
    isOptional: true,
    teacherId: 1,
    teacherName: 'Kamal Hossain',
  },
  {
    id: 5,
    subjectId: 'SUB-2026-0005',
    name: 'Physics',
    code: '174',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 2,
    teacherName: 'Nasreen Akter',
  },
  {
    id: 6,
    subjectId: 'SUB-2026-0006',
    name: 'Chemistry',
    code: '176',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 2,
    teacherName: 'Nasreen Akter',
  },
  {
    id: 7,
    subjectId: 'SUB-2026-0007',
    name: 'Biology',
    code: '178',
    classId: 5,
    className: 'Class 10',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 3,
    teacherName: 'Mahmudur Rahman',
  },
  {
    id: 8,
    subjectId: 'SUB-2026-0008',
    name: 'General Science',
    code: '127',
    classId: 3,
    className: 'Class 8',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 2,
    teacherName: 'Nasreen Akter',
  },
  {
    id: 9,
    subjectId: 'SUB-2026-0009',
    name: 'Principles of Accounting',
    code: '146',
    classId: 7,
    className: 'Class 12',
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 100,
    practicalMarks: 0,
    subjectType: 'Mandatory',
    isOptional: false,
    teacherId: 1,
    teacherName: 'Kamal Hossain',
  },
];

const DEFAULT_STUDENT_ATTENDANCES: StudentAttendanceRecord[] = [
  {
    id: 1,
    studentId: 1,
    studentCode: 'STU-2024-0001',
    studentName: 'Abrar Fahim',
    rollNumber: 1,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '08:10 AM',
    remarks: 'On time',
  },
  {
    id: 2,
    studentId: 2,
    studentCode: 'STU-2024-0002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '08:14 AM',
    remarks: 'On time',
  },
  {
    id: 3,
    studentId: 3,
    studentCode: 'STU-2024-0003',
    studentName: 'Tanvir Ahmed',
    rollNumber: 3,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Late',
    checkInTime: '08:35 AM',
    remarks: 'School bus delayed in traffic',
  },
  {
    id: 4,
    studentId: 4,
    studentCode: 'STU-2024-0004',
    studentName: 'Sadia Rahman',
    rollNumber: 4,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Leave',
    checkInTime: '-',
    remarks: 'Approved sick leave (Fever)',
  },
  {
    id: 5,
    studentId: 5,
    studentCode: 'STU-2024-0005',
    studentName: 'Mahir Faisal',
    rollNumber: 5,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '08:05 AM',
    remarks: 'On time',
  },
  {
    id: 6,
    studentId: 6,
    studentCode: 'STU-2024-0006',
    studentName: 'Tasnim Chowdhury',
    rollNumber: 6,
    classId: 5,
    className: 'Class 10',
    sectionId: 3,
    sectionName: 'Section A (Jamuna)',
    date: '2026-11-09',
    status: 'Absent',
    checkInTime: '-',
    remarks: 'Uninformed absence',
  },
];

const DEFAULT_TEACHER_ATTENDANCES: TeacherAttendanceRecord[] = [
  {
    id: 1,
    teacherId: 1,
    employeeId: 'EMP-2024-1001',
    teacherName: 'Kamal Hossain',
    department: 'Mathematics',
    subject: 'General Mathematics',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '07:45 AM',
    checkOutTime: '03:30 PM',
    remarks: 'Morning assembly duty',
  },
  {
    id: 2,
    teacherId: 2,
    employeeId: 'EMP-2024-1002',
    teacherName: 'Nasreen Akter',
    department: 'Science',
    subject: 'Physics & Chemistry',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '07:50 AM',
    checkOutTime: '03:15 PM',
    remarks: '',
  },
  {
    id: 3,
    teacherId: 3,
    employeeId: 'EMP-2024-1003',
    teacherName: 'Mahmudur Rahman',
    department: 'Science',
    subject: 'Biology & Zoology',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '07:55 AM',
    checkOutTime: '03:15 PM',
    remarks: '',
  },
  {
    id: 4,
    teacherId: 4,
    employeeId: 'EMP-2024-1004',
    teacherName: 'Sultana Razia',
    department: 'Languages',
    subject: 'Bangla Literature',
    date: '2026-11-09',
    status: 'Present',
    checkInTime: '07:40 AM',
    checkOutTime: '03:20 PM',
    remarks: '',
  },
  {
    id: 5,
    teacherId: 5,
    employeeId: 'EMP-2024-1005',
    teacherName: 'Mohammad Ali',
    department: 'Languages',
    subject: 'English Language',
    date: '2026-11-09',
    status: 'Leave',
    checkInTime: '-',
    checkOutTime: '-',
    remarks: 'Casual leave approved',
  },
];

export const StorageService = {
  getSchoolSettings(): SchoolSetting {
    const raw = localStorage.getItem(STORAGE_KEYS.SCHOOL_SETTINGS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.SCHOOL_SETTINGS, JSON.stringify(DEFAULT_SCHOOL_SETTINGS));
      return DEFAULT_SCHOOL_SETTINGS;
    }
    return JSON.parse(raw);
  },

  saveSchoolSettings(settings: SchoolSetting): void {
    localStorage.setItem(STORAGE_KEYS.SCHOOL_SETTINGS, JSON.stringify(settings));
  },

  getUsers(): User[] {
    const raw = localStorage.getItem(STORAGE_KEYS.USERS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(DEFAULT_USERS));
      return DEFAULT_USERS;
    }
    return JSON.parse(raw);
  },

  saveUsers(users: User[]): void {
    localStorage.setItem(STORAGE_KEYS.USERS, JSON.stringify(users));
  },

  getCurrentUser(): User | null {
    const raw = localStorage.getItem(STORAGE_KEYS.CURRENT_USER);
    if (!raw) {
      const defaultUser = DEFAULT_USERS[0];
      localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(defaultUser));
      return defaultUser;
    }
    return JSON.parse(raw);
  },

  setCurrentUser(user: User | null): void {
    if (user) {
      localStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEYS.CURRENT_USER);
    }
  },

  getActivityLogs(): ActivityLogItem[] {
    const raw = localStorage.getItem(STORAGE_KEYS.LOGS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.LOGS, JSON.stringify(DEFAULT_LOGS));
      return DEFAULT_LOGS;
    }
    return JSON.parse(raw);
  },

  addActivityLog(log: Omit<ActivityLogItem, 'id' | 'timestamp'>): void {
    const logs = this.getActivityLogs();
    const now = new Date();
    const timestamp = now.toISOString().replace('T', ' ').substring(0, 19);
    const newLog: ActivityLogItem = {
      id: Date.now(),
      timestamp,
      ...log,
    };
    const updated = [newLog, ...logs].slice(0, 50);
    localStorage.setItem(STORAGE_KEYS.LOGS, JSON.stringify(updated));
  },

  getClasses(): AcademicClass[] {
    const raw = localStorage.getItem(STORAGE_KEYS.CLASSES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.CLASSES, JSON.stringify(DEFAULT_CLASSES));
      return DEFAULT_CLASSES;
    }
    return JSON.parse(raw);
  },

  getTheme(): 'dark' | 'light' {
    const raw = localStorage.getItem(STORAGE_KEYS.THEME);
    return (raw as 'dark' | 'light') || 'dark';
  },

  setTheme(theme: 'dark' | 'light'): void {
    localStorage.setItem(STORAGE_KEYS.THEME, theme);
  },

  // Students CRUD
  getStudents(): Student[] {
    const raw = localStorage.getItem(STORAGE_KEYS.STUDENTS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.STUDENTS, JSON.stringify(DEFAULT_STUDENTS));
      return DEFAULT_STUDENTS;
    }
    return JSON.parse(raw);
  },

  saveStudents(students: Student[]): void {
    localStorage.setItem(STORAGE_KEYS.STUDENTS, JSON.stringify(students));
  },

  addStudent(studentData: Omit<Student, 'id' | 'studentId' | 'admissionNumber'>): Student {
    const students = this.getStudents();
    const newId = Date.now();
    const count = students.length + 1;
    const year = new Date().getFullYear();
    const studentId = `STU-${year}-${String(count).padStart(4, '0')}`;
    const admissionNumber = `ADM-${year}-${String(count).padStart(4, '0')}`;

    const newStudent: Student = {
      ...studentData,
      id: newId,
      studentId,
      admissionNumber,
      guardian: {
        ...studentData.guardian,
        id: newId,
      },
    };

    const updated = [newStudent, ...students];
    this.saveStudents(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'STUDENT_ADMITTED',
      module: 'STUDENTS',
      description: `Admitted student '${newStudent.fullName}' (${newStudent.studentId}, Class: ${newStudent.className})`,
      severity: 'INFO',
    });
    return newStudent;
  },

  updateStudent(id: number, studentData: Partial<Student>): Student | null {
    const students = this.getStudents();
    const idx = students.findIndex((s) => s.id === id);
    if (idx === -1) return null;

    const existing = students[idx];
    const updatedStudent: Student = {
      ...existing,
      ...studentData,
      guardian: {
        ...existing.guardian,
        ...(studentData.guardian || {}),
      },
    };

    students[idx] = updatedStudent;
    this.saveStudents(students);
    this.addActivityLog({
      username: 'admin',
      action: 'STUDENT_UPDATED',
      module: 'STUDENTS',
      description: `Updated profile for student '${updatedStudent.fullName}' (${updatedStudent.studentId})`,
      severity: 'INFO',
    });
    return updatedStudent;
  },

  deleteStudent(id: number, soft: boolean = true): boolean {
    const students = this.getStudents();
    const student = students.find((s) => s.id === id);
    if (!student) return false;

    if (soft) {
      student.status = 'inactive';
      this.saveStudents([...students]);
    } else {
      this.saveStudents(students.filter((s) => s.id !== id));
    }

    this.addActivityLog({
      username: 'admin',
      action: 'STUDENT_ARCHIVED',
      module: 'STUDENTS',
      description: `Archived student record '${student.fullName}' (${student.studentId})`,
      severity: 'WARNING',
    });
    return true;
  },

  bulkPromote(studentIds: number[], targetClass: string, targetYear: string): number {
    const students = this.getStudents();
    let count = 0;
    students.forEach((s) => {
      if (studentIds.includes(s.id)) {
        s.className = targetClass;
        s.academicYear = targetYear;
        count++;
      }
    });
    this.saveStudents([...students]);
    this.addActivityLog({
      username: 'admin',
      action: 'STUDENT_PROMOTED',
      module: 'STUDENTS',
      description: `Promoted ${count} students to ${targetClass} (${targetYear})`,
      severity: 'INFO',
    });
    return count;
  },

  // Teachers
  getTeachers(): Teacher[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TEACHERS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TEACHERS, JSON.stringify(DEFAULT_TEACHERS));
      return DEFAULT_TEACHERS;
    }
    return JSON.parse(raw);
  },

  saveTeachers(teachers: Teacher[]): void {
    localStorage.setItem(STORAGE_KEYS.TEACHERS, JSON.stringify(teachers));
  },

  addTeacher(teacherData: Omit<Teacher, 'id' | 'teacherId' | 'employeeId'>): Teacher {
    const teachers = this.getTeachers();
    const newId = Date.now();
    const count = teachers.length + 1;
    const year = new Date().getFullYear();
    const teacherId = `TCH-${year}-${String(count).padStart(4, '0')}`;
    const employeeId = `EMP-${year}-${1000 + count}`;

    const newTeacher: Teacher = {
      ...teacherData,
      id: newId,
      teacherId,
      employeeId,
    };

    const updated = [newTeacher, ...teachers];
    this.saveTeachers(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'TEACHER_REGISTERED',
      module: 'TEACHERS',
      description: `Registered faculty member '${newTeacher.fullName}' (${newTeacher.teacherId}, ${newTeacher.primarySubject})`,
      severity: 'INFO',
    });
    return newTeacher;
  },

  updateTeacher(id: number, teacherData: Partial<Teacher>): Teacher | null {
    const teachers = this.getTeachers();
    const idx = teachers.findIndex((t) => t.id === id);
    if (idx === -1) return null;

    const updated: Teacher = { ...teachers[idx], ...teacherData };
    teachers[idx] = updated;
    this.saveTeachers(teachers);
    this.addActivityLog({
      username: 'admin',
      action: 'TEACHER_UPDATED',
      module: 'TEACHERS',
      description: `Updated profile for teacher '${updated.fullName}' (${updated.teacherId})`,
      severity: 'INFO',
    });
    return updated;
  },

  // Staff
  getStaff(): Staff[] {
    const raw = localStorage.getItem(STORAGE_KEYS.STAFF);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.STAFF, JSON.stringify(DEFAULT_STAFF));
      return DEFAULT_STAFF;
    }
    return JSON.parse(raw);
  },

  saveStaff(staffList: Staff[]): void {
    localStorage.setItem(STORAGE_KEYS.STAFF, JSON.stringify(staffList));
  },

  addStaff(staffData: Omit<Staff, 'id' | 'staffId' | 'employeeId'>): Staff {
    const staffList = this.getStaff();
    const newId = Date.now();
    const count = staffList.length + 1;
    const year = new Date().getFullYear();
    const staffId = `STF-${year}-${String(count).padStart(4, '0')}`;
    const employeeId = `EMP-${year}-${2000 + count}`;

    const newStaff: Staff = {
      ...staffData,
      id: newId,
      staffId,
      employeeId,
    };

    const updated = [newStaff, ...staffList];
    this.saveStaff(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'STAFF_REGISTERED',
      module: 'STAFF',
      description: `Registered staff member '${newStaff.fullName}' (${newStaff.position})`,
      severity: 'INFO',
    });
    return newStaff;
  },

  updateStaff(id: number, staffData: Partial<Staff>): Staff | null {
    const staffList = this.getStaff();
    const idx = staffList.findIndex((s) => s.id === id);
    if (idx === -1) return null;

    const updated: Staff = { ...staffList[idx], ...staffData };
    staffList[idx] = updated;
    this.saveStaff(staffList);
    this.addActivityLog({
      username: 'admin',
      action: 'STAFF_UPDATED',
      module: 'STAFF',
      description: `Updated profile for staff member '${updated.fullName}' (${updated.staffId})`,
      severity: 'INFO',
    });
    return updated;
  },

  // ==================== ACADEMIC YEARS ====================
  getAcademicYears(): AcademicYearInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.ACADEMIC_YEARS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.ACADEMIC_YEARS, JSON.stringify(DEFAULT_ACADEMIC_YEARS));
      return DEFAULT_ACADEMIC_YEARS;
    }
    return JSON.parse(raw);
  },

  saveAcademicYears(years: AcademicYearInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.ACADEMIC_YEARS, JSON.stringify(years));
  },

  addAcademicYear(data: Omit<AcademicYearInfo, 'id'>): AcademicYearInfo {
    const list = this.getAcademicYears();
    const newId = Date.now();
    let updatedList = list;
    if (data.isCurrent) {
      updatedList = updatedList.map((y) => ({ ...y, isCurrent: false }));
    }
    const newYear: AcademicYearInfo = { ...data, id: newId };
    updatedList = [newYear, ...updatedList];
    this.saveAcademicYears(updatedList);
    this.addActivityLog({
      username: 'admin',
      action: 'ACADEMIC_YEAR_CREATED',
      module: 'ACADEMICS',
      description: `Created academic session '${newYear.name}' (${newYear.status})`,
      severity: 'INFO',
    });
    return newYear;
  },

  setActiveAcademicYear(id: number): void {
    const list = this.getAcademicYears();
    const updated = list.map((y) => ({
      ...y,
      isCurrent: y.id === id,
      status: (y.id === id ? 'Active' : y.status === 'Active' ? 'Completed' : y.status) as AcademicYearInfo['status'],
    }));
    this.saveAcademicYears(updated);
    const target = list.find((y) => y.id === id);
    this.addActivityLog({
      username: 'admin',
      action: 'ACTIVE_SESSION_CHANGED',
      module: 'ACADEMICS',
      description: `Switched active school session to '${target?.name || id}'`,
      severity: 'INFO',
    });
  },

  // ==================== CLASSES ====================
  getDetailedClasses(): SchoolClassInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.DETAILED_CLASSES);
    let classes: SchoolClassInfo[] = raw ? JSON.parse(raw) : DEFAULT_DETAILED_CLASSES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.DETAILED_CLASSES, JSON.stringify(DEFAULT_DETAILED_CLASSES));
    }
    const allSections = this.getSections();
    const allSubjects = this.getSubjects();

    // Map live sections and counts into classes
    return classes.map((c) => {
      const classSections = allSections.filter((s) => s.classId === c.id);
      const subCount = allSubjects.filter((s) => s.classId === c.id).length;
      const stuCount = classSections.reduce((sum, s) => sum + (s.studentCount || 0), 0);
      return {
        ...c,
        sections: classSections,
        subjectCount: subCount || c.subjectCount,
        studentCount: stuCount || c.studentCount,
      };
    });
  },

  saveDetailedClasses(classes: SchoolClassInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.DETAILED_CLASSES, JSON.stringify(classes));
  },

  addClass(classData: Omit<SchoolClassInfo, 'id' | 'sections' | 'subjectCount' | 'studentCount'>): SchoolClassInfo {
    const list = this.getDetailedClasses();
    const newId = Date.now();
    const newClass: SchoolClassInfo = {
      ...classData,
      id: newId,
      sections: [],
      subjectCount: 0,
      studentCount: 0,
    };
    const updated = [...list, newClass].sort((a, b) => a.numericOrder - b.numericOrder);
    this.saveDetailedClasses(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'CLASS_CREATED',
      module: 'ACADEMICS',
      description: `Created new school class '${newClass.name}' (${newClass.group}, ${newClass.shift})`,
      severity: 'INFO',
    });
    return newClass;
  },

  updateClass(id: number, classData: Partial<SchoolClassInfo>): SchoolClassInfo | null {
    const list = this.getDetailedClasses();
    const idx = list.findIndex((c) => c.id === id);
    if (idx === -1) return null;
    const updated = { ...list[idx], ...classData };
    list[idx] = updated;
    this.saveDetailedClasses(list);
    this.addActivityLog({
      username: 'admin',
      action: 'CLASS_UPDATED',
      module: 'ACADEMICS',
      description: `Updated class details for '${updated.name}'`,
      severity: 'INFO',
    });
    return updated;
  },

  deleteClass(id: number): boolean {
    const list = this.getDetailedClasses();
    const target = list.find((c) => c.id === id);
    if (!target) return false;
    const updated = list.filter((c) => c.id !== id);
    this.saveDetailedClasses(updated);

    // Cascade delete sections and subjects for this class
    const sections = this.getSections().filter((s) => s.classId !== id);
    this.saveSections(sections);
    const subjects = this.getSubjects().filter((s) => s.classId !== id);
    this.saveSubjects(subjects);

    this.addActivityLog({
      username: 'admin',
      action: 'CLASS_DELETED',
      module: 'ACADEMICS',
      description: `Removed class '${target.name}' and all associated sections/subjects`,
      severity: 'WARNING',
    });
    return true;
  },

  // ==================== SECTIONS ====================
  getSections(): SectionInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.SECTIONS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.SECTIONS, JSON.stringify(DEFAULT_SECTIONS));
      return DEFAULT_SECTIONS;
    }
    return JSON.parse(raw);
  },

  saveSections(sections: SectionInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.SECTIONS, JSON.stringify(sections));
  },

  addSection(sectionData: Omit<SectionInfo, 'id' | 'studentCount'>): SectionInfo {
    const list = this.getSections();
    const newId = Date.now();
    const newSec: SectionInfo = {
      ...sectionData,
      id: newId,
      studentCount: 0,
    };
    const updated = [...list, newSec];
    this.saveSections(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'SECTION_CREATED',
      module: 'ACADEMICS',
      description: `Created section '${newSec.name}' for ${newSec.className} (Room: ${newSec.roomNumber || 'TBD'})`,
      severity: 'INFO',
    });
    return newSec;
  },

  updateSection(id: number, sectionData: Partial<SectionInfo>): SectionInfo | null {
    const list = this.getSections();
    const idx = list.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    const updated = { ...list[idx], ...sectionData };
    list[idx] = updated;
    this.saveSections(list);
    this.addActivityLog({
      username: 'admin',
      action: 'SECTION_UPDATED',
      module: 'ACADEMICS',
      description: `Updated section '${updated.name}' (${updated.className})`,
      severity: 'INFO',
    });
    return updated;
  },

  deleteSection(id: number): boolean {
    const list = this.getSections();
    const target = list.find((s) => s.id === id);
    if (!target) return false;
    const updated = list.filter((s) => s.id !== id);
    this.saveSections(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'SECTION_DELETED',
      module: 'ACADEMICS',
      description: `Deleted section '${target.name}' from ${target.className}`,
      severity: 'WARNING',
    });
    return true;
  },

  // ==================== SUBJECTS ====================
  getSubjects(): SubjectInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.SUBJECTS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.SUBJECTS, JSON.stringify(DEFAULT_SUBJECTS));
      return DEFAULT_SUBJECTS;
    }
    return JSON.parse(raw);
  },

  saveSubjects(subjects: SubjectInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.SUBJECTS, JSON.stringify(subjects));
  },

  addSubject(subData: Omit<SubjectInfo, 'id' | 'subjectId'>): SubjectInfo {
    const list = this.getSubjects();
    const newId = Date.now();
    const count = list.length + 1;
    const year = new Date().getFullYear();
    const subjectId = `SUB-${year}-${String(count).padStart(4, '0')}`;

    const newSub: SubjectInfo = {
      ...subData,
      id: newId,
      subjectId,
    };
    const updated = [...list, newSub];
    this.saveSubjects(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'SUBJECT_CREATED',
      module: 'ACADEMICS',
      description: `Created subject '${newSub.name}' (Code: ${newSub.code}, ${newSub.className})`,
      severity: 'INFO',
    });
    return newSub;
  },

  updateSubject(id: number, subData: Partial<SubjectInfo>): SubjectInfo | null {
    const list = this.getSubjects();
    const idx = list.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    const updated = { ...list[idx], ...subData };
    list[idx] = updated;
    this.saveSubjects(list);
    this.addActivityLog({
      username: 'admin',
      action: 'SUBJECT_UPDATED',
      module: 'ACADEMICS',
      description: `Updated syllabus for subject '${updated.name}' (${updated.code})`,
      severity: 'INFO',
    });
    return updated;
  },

  deleteSubject(id: number): boolean {
    const list = this.getSubjects();
    const target = list.find((s) => s.id === id);
    if (!target) return false;
    const updated = list.filter((s) => s.id !== id);
    this.saveSubjects(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'SUBJECT_DELETED',
      module: 'ACADEMICS',
      description: `Deleted subject '${target.name}' (${target.code})`,
      severity: 'WARNING',
    });
    return true;
  },

  // ==================== ATTENDANCE ====================
  getStudentAttendances(): StudentAttendanceRecord[] {
    const raw = localStorage.getItem(STORAGE_KEYS.STUDENT_ATTENDANCES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.STUDENT_ATTENDANCES, JSON.stringify(DEFAULT_STUDENT_ATTENDANCES));
      return DEFAULT_STUDENT_ATTENDANCES;
    }
    return JSON.parse(raw);
  },

  saveStudentAttendances(records: StudentAttendanceRecord[]): void {
    localStorage.setItem(STORAGE_KEYS.STUDENT_ATTENDANCES, JSON.stringify(records));
  },

  recordStudentAttendance(newRecords: StudentAttendanceRecord[]): void {
    const list = this.getStudentAttendances();
    // Upsert by (studentId, date)
    const recordMap = new Map<string, StudentAttendanceRecord>();
    list.forEach((r) => recordMap.set(`${r.studentId}_${r.date}`, r));

    newRecords.forEach((r) => {
      const key = `${r.studentId}_${r.date}`;
      const existing = recordMap.get(key);
      recordMap.set(key, {
        ...(existing || {}),
        ...r,
        id: existing ? existing.id : Date.now() + Math.floor(Math.random() * 1000),
      });
    });

    const updated = Array.from(recordMap.values());
    this.saveStudentAttendances(updated);

    const presentCount = newRecords.filter((r) => r.status === 'Present').length;
    const absentCount = newRecords.filter((r) => r.status === 'Absent').length;
    const sample = newRecords[0];

    this.addActivityLog({
      username: 'admin',
      action: 'ATTENDANCE_RECORDED',
      module: 'ATTENDANCE',
      description: `Marked attendance for ${sample?.className || 'Class'} on ${sample?.date} (${presentCount} Present, ${absentCount} Absent)`,
      severity: 'INFO',
    });
  },

  getTeacherAttendances(): TeacherAttendanceRecord[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TEACHER_ATTENDANCES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TEACHER_ATTENDANCES, JSON.stringify(DEFAULT_TEACHER_ATTENDANCES));
      return DEFAULT_TEACHER_ATTENDANCES;
    }
    return JSON.parse(raw);
  },

  saveTeacherAttendances(records: TeacherAttendanceRecord[]): void {
    localStorage.setItem(STORAGE_KEYS.TEACHER_ATTENDANCES, JSON.stringify(records));
  },

  recordTeacherAttendance(newRecords: TeacherAttendanceRecord[]): void {
    const list = this.getTeacherAttendances();
    const recordMap = new Map<string, TeacherAttendanceRecord>();
    list.forEach((r) => recordMap.set(`${r.teacherId}_${r.date}`, r));

    newRecords.forEach((r) => {
      const key = `${r.teacherId}_${r.date}`;
      const existing = recordMap.get(key);
      recordMap.set(key, {
        ...(existing || {}),
        ...r,
        id: existing ? existing.id : Date.now() + Math.floor(Math.random() * 1000),
      });
    });

    const updated = Array.from(recordMap.values());
    this.saveTeacherAttendances(updated);

    const presentCount = newRecords.filter((r) => r.status === 'Present').length;
    this.addActivityLog({
      username: 'admin',
      action: 'TEACHER_ATTENDANCE_RECORDED',
      module: 'ATTENDANCE',
      description: `Recorded faculty attendance on ${newRecords[0]?.date} (${presentCount} Present)`,
      severity: 'INFO',
    });
  },

  // ==========================================
  // PHASE 6: FEES & BILLING MANAGEMENT
  // ==========================================

  getFeeCategories(): FeeCategoryInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.FEE_CATEGORIES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.FEE_CATEGORIES, JSON.stringify(DEFAULT_FEE_CATEGORIES));
      return DEFAULT_FEE_CATEGORIES;
    }
    return JSON.parse(raw);
  },

  saveFeeCategories(cats: FeeCategoryInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.FEE_CATEGORIES, JSON.stringify(cats));
  },

  addFeeCategory(cat: Omit<FeeCategoryInfo, 'id'>): FeeCategoryInfo {
    const list = this.getFeeCategories();
    const newCat: FeeCategoryInfo = {
      ...cat,
      id: list.length > 0 ? Math.max(...list.map((c) => c.id)) + 1 : 1,
    };
    const updated = [...list, newCat];
    this.saveFeeCategories(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'FEE_CATEGORY_CREATED',
      module: 'FEES',
      description: `Created fee category: ${newCat.name} (${newCat.frequency})`,
      severity: 'INFO',
    });
    return newCat;
  },

  getFeeStructures(): FeeStructureInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.FEE_STRUCTURES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.FEE_STRUCTURES, JSON.stringify(DEFAULT_FEE_STRUCTURES));
      return DEFAULT_FEE_STRUCTURES;
    }
    return JSON.parse(raw);
  },

  saveFeeStructures(structures: FeeStructureInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.FEE_STRUCTURES, JSON.stringify(structures));
  },

  addFeeStructure(
    structure: Omit<FeeStructureInfo, 'id' | 'assignedCount' | 'createdAt'>,
    assignToClass = true
  ): FeeStructureInfo {
    const list = this.getFeeStructures();
    const students = this.getStudents();
    const classStudents = students.filter(
      (s) => s.className.toLowerCase().trim() === structure.className.toLowerCase().trim()
    );

    const newStruct: FeeStructureInfo = {
      ...structure,
      id: list.length > 0 ? Math.max(...list.map((s) => s.id)) + 1 : 1,
      assignedCount: assignToClass ? classStudents.length : 0,
      createdAt: new Date().toISOString().split('T')[0],
    };

    const updated = [newStruct, ...list];
    this.saveFeeStructures(updated);

    // If assignToClass is true, automatically create invoices for each active student in the class
    if (assignToClass && classStudents.length > 0) {
      const invoices = this.getStudentFeeInvoices();
      const newInvoices: StudentFeeInvoice[] = classStudents.map((s, idx) => ({
        id: Date.now() + idx,
        studentId: s.id,
        studentCode: s.studentId,
        studentName: s.fullName,
        rollNumber: s.rollNumber,
        classId: structure.classId,
        className: structure.className,
        sectionName: s.sectionName,
        feeStructureId: newStruct.id,
        feeTitle: newStruct.title,
        categoryName: newStruct.categoryName,
        totalAmount: newStruct.amount,
        discountAmount: 0,
        netAmount: newStruct.amount,
        paidAmount: 0,
        dueAmount: newStruct.amount,
        dueDate: newStruct.dueDate,
        status: 'Unpaid',
        createdAt: newStruct.createdAt,
        payments: [],
      }));
      this.saveStudentFeeInvoices([...newInvoices, ...invoices]);
    }

    this.addActivityLog({
      username: 'admin',
      action: 'FEE_STRUCTURE_CREATED',
      module: 'FEES',
      description: `Created fee schedule: ${newStruct.title} (৳${newStruct.amount.toLocaleString()}) assigned to ${newStruct.assignedCount} students`,
      severity: 'INFO',
    });

    return newStruct;
  },

  getStudentFeeInvoices(): StudentFeeInvoice[] {
    const raw = localStorage.getItem(STORAGE_KEYS.STUDENT_FEES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.STUDENT_FEES, JSON.stringify(DEFAULT_STUDENT_FEES));
      return DEFAULT_STUDENT_FEES;
    }
    return JSON.parse(raw);
  },

  saveStudentFeeInvoices(invoices: StudentFeeInvoice[]): void {
    localStorage.setItem(STORAGE_KEYS.STUDENT_FEES, JSON.stringify(invoices));
  },

  generateReceiptNumber(): string {
    const invoices = this.getStudentFeeInvoices();
    const allPayments = invoices.flatMap((inv) => inv.payments);
    const year = new Date().getFullYear();
    const count = allPayments.length + 105;
    return `REC-${year}-${count.toString().padStart(5, '0')}`;
  },

  recordFeePayment(paymentData: {
    studentFeeId: number;
    amount: number;
    discountAmount?: number;
    paymentMethod: FeePaymentRecord['paymentMethod'];
    transactionRef?: string;
    receivedBy: string;
    notes?: string;
  }): { payment: FeePaymentRecord; invoice: StudentFeeInvoice } {
    const invoices = this.getStudentFeeInvoices();
    const invIndex = invoices.findIndex((i) => i.id === paymentData.studentFeeId);
    if (invIndex === -1) {
      throw new Error('Invoice not found');
    }

    const inv = { ...invoices[invIndex] };
    const addDiscount = Math.max(0, paymentData.discountAmount || 0);
    const newDiscountTotal = (inv.discountAmount || 0) + addDiscount;
    const netAmount = Math.max(0, inv.totalAmount - newDiscountTotal);

    if (paymentData.amount <= 0) {
      throw new Error('Payment amount must be greater than zero');
    }

    const currentDue = Math.max(0, netAmount - inv.paidAmount);
    if (paymentData.amount > currentDue + 0.01) {
      throw new Error(`Payment amount (৳${paymentData.amount}) cannot exceed balance due (৳${currentDue})`);
    }

    const newPaidAmount = inv.paidAmount + paymentData.amount;
    const newDueAmount = Math.max(0, netAmount - newPaidAmount);

    let newStatus: 'Paid' | 'Partial' | 'Unpaid' = 'Unpaid';
    if (newDueAmount <= 0.01) {
      newStatus = 'Paid';
    } else if (newPaidAmount > 0) {
      newStatus = 'Partial';
    }

    const receiptNo = this.generateReceiptNumber();
    const newPayment: FeePaymentRecord = {
      id: Date.now(),
      studentFeeId: inv.id,
      receiptNumber: receiptNo,
      amount: paymentData.amount,
      discountAmount: addDiscount,
      paymentMethod: paymentData.paymentMethod,
      transactionRef: paymentData.transactionRef,
      paymentDate: new Date().toISOString().split('T')[0],
      receivedBy: paymentData.receivedBy || 'Accounts Officer',
      notes: paymentData.notes,
    };

    inv.discountAmount = newDiscountTotal;
    inv.netAmount = netAmount;
    inv.paidAmount = newPaidAmount;
    inv.dueAmount = newDueAmount;
    inv.status = newStatus;
    inv.payments = [newPayment, ...(inv.payments || [])];

    invoices[invIndex] = inv;
    this.saveStudentFeeInvoices(invoices);

    this.addActivityLog({
      username: 'admin',
      action: 'FEE_PAYMENT_COLLECTED',
      module: 'FEES',
      description: `Collected ৳${paymentData.amount.toLocaleString()} for ${inv.studentName} (${inv.feeTitle}) via ${paymentData.paymentMethod} [${receiptNo}]`,
      severity: 'INFO',
    });

    return { payment: newPayment, invoice: inv };
  },

  getFeeStats() {
    const invoices = this.getStudentFeeInvoices();
    let totalInvoiced = 0;
    let totalCollected = 0;
    let totalDue = 0;
    let totalDiscounts = 0;
    let paidInvoices = 0;
    let partialInvoices = 0;
    let unpaidInvoices = 0;

    invoices.forEach((inv) => {
      totalInvoiced += inv.netAmount;
      totalCollected += inv.paidAmount;
      totalDue += inv.dueAmount;
      totalDiscounts += inv.discountAmount || 0;
      if (inv.status === 'Paid') paidInvoices++;
      else if (inv.status === 'Partial') partialInvoices++;
      else unpaidInvoices++;
    });

    const collectionRate = totalInvoiced > 0 ? (totalCollected / totalInvoiced) * 100 : 0;

    return {
      totalInvoiced,
      totalCollected,
      totalDue,
      totalDiscounts,
      collectionRate,
      paidInvoices,
      partialInvoices,
      unpaidInvoices,
      totalInvoices: invoices.length,
    };
  },

  // ==========================================
  // PHASE 7: ACCOUNTING & EXPENSE MANAGEMENT
  // ==========================================

  getAccountCategories(type?: 'Income' | 'Expense'): AccountCategoryInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.ACCOUNT_CATEGORIES);
    let cats: AccountCategoryInfo[];
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.ACCOUNT_CATEGORIES, JSON.stringify(DEFAULT_ACCOUNT_CATEGORIES));
      cats = DEFAULT_ACCOUNT_CATEGORIES;
    } else {
      cats = JSON.parse(raw);
    }
    if (type) {
      return cats.filter((c) => c.type === type && c.isActive);
    }
    return cats.filter((c) => c.isActive);
  },

  saveAccountCategories(cats: AccountCategoryInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.ACCOUNT_CATEGORIES, JSON.stringify(cats));
  },

  addAccountCategory(cat: Omit<AccountCategoryInfo, 'id'>): AccountCategoryInfo {
    const list = this.getAccountCategories();
    const newCat: AccountCategoryInfo = {
      ...cat,
      id: list.length > 0 ? Math.max(...list.map((c) => c.id)) + 1 : 1,
    };
    const updated = [...list, newCat];
    this.saveAccountCategories(updated);
    this.addActivityLog({
      username: 'admin',
      action: 'ACCOUNT_CATEGORY_CREATED',
      module: 'ACCOUNTING',
      description: `Created account category: ${newCat.name} (${newCat.type}) [${newCat.code}]`,
      severity: 'INFO',
    });
    return newCat;
  },

  getAccountTransactions(): AccountTransactionRecord[] {
    const raw = localStorage.getItem(STORAGE_KEYS.ACCOUNT_TRANSACTIONS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.ACCOUNT_TRANSACTIONS, JSON.stringify(DEFAULT_ACCOUNT_TRANSACTIONS));
      return DEFAULT_ACCOUNT_TRANSACTIONS;
    }
    return JSON.parse(raw);
  },

  saveAccountTransactions(txs: AccountTransactionRecord[]): void {
    localStorage.setItem(STORAGE_KEYS.ACCOUNT_TRANSACTIONS, JSON.stringify(txs));
  },

  generateVoucherNumber(type: 'Income' | 'Expense'): string {
    const txs = this.getAccountTransactions();
    const year = new Date().getFullYear();
    const prefix = type === 'Income' ? 'INC' : 'EXP';
    const count = txs.filter((t) => t.type === type).length + 10;
    return `VCH-${year}-${prefix}-${count.toString().padStart(5, '0')}`;
  },

  recordAccountTransaction(txData: {
    type: 'Income' | 'Expense';
    categoryId: number;
    amount: number;
    transactionDate?: string;
    paymentMethod: AccountTransactionRecord['paymentMethod'];
    referenceNo?: string;
    paidToReceivedFrom: string;
    description?: string;
    recordedBy?: string;
  }): AccountTransactionRecord {
    const cats = this.getAccountCategories();
    const cat = cats.find((c) => c.id === txData.categoryId);
    if (!cat) throw new Error('Selected account category does not exist');
    if (txData.amount <= 0) throw new Error('Transaction amount must be greater than zero');

    const txs = this.getAccountTransactions();
    const vchNo = this.generateVoucherNumber(txData.type);
    const newTx: AccountTransactionRecord = {
      id: Date.now(),
      voucherNo: vchNo,
      transactionDate: txData.transactionDate || new Date().toISOString().split('T')[0],
      type: txData.type,
      categoryId: cat.id,
      categoryName: cat.name,
      categoryCode: cat.code,
      amount: txData.amount,
      paymentMethod: txData.paymentMethod,
      referenceNo: txData.referenceNo,
      paidToReceivedFrom: txData.paidToReceivedFrom.trim(),
      description: txData.description?.trim(),
      recordedBy: txData.recordedBy || 'Chief Accountant',
      status: 'Approved',
    };

    const updated = [newTx, ...txs];
    this.saveAccountTransactions(updated);

    this.addActivityLog({
      username: 'admin',
      action: 'VOUCHER_RECORDED',
      module: 'ACCOUNTING',
      description: `Posted ${newTx.type} voucher ${vchNo}: ৳${newTx.amount.toLocaleString()} for ${newTx.paidToReceivedFrom} (${cat.name})`,
      severity: 'INFO',
    });

    return newTx;
  },

  getFinancialSummary(): FinancialSummary {
    const txs = this.getAccountTransactions().filter((t) => t.status === 'Approved');
    let totalIncome = 0;
    let totalExpense = 0;
    let cashIn = 0;
    let cashOut = 0;

    txs.forEach((t) => {
      if (t.type === 'Income') {
        totalIncome += t.amount;
        if (t.paymentMethod === 'Cash') cashIn += t.amount;
      } else {
        totalExpense += t.amount;
        if (t.paymentMethod === 'Cash') cashOut += t.amount;
      }
    });

    const netSurplus = totalIncome - totalExpense;
    return {
      totalIncome,
      totalExpense,
      netSurplus,
      cashInHand: cashIn - cashOut,
      isProfit: netSurplus >= 0,
    };
  },

  getAccountingCategoryBreakdown(type: 'Income' | 'Expense') {
    const txs = this.getAccountTransactions().filter((t) => t.type === type && t.status === 'Approved');
    const map = new Map<number, { category: string; code: string; amount: number; count: number }>();

    txs.forEach((t) => {
      const existing = map.get(t.categoryId) || {
        category: t.categoryName,
        code: t.categoryCode,
        amount: 0,
        count: 0,
      };
      existing.amount += t.amount;
      existing.count += 1;
      map.set(t.categoryId, existing);
    });

    return Array.from(map.values()).sort((a, b) => b.amount - a.amount);
  },

  // --- Phase 8: Exam Management, Grading & Results ---
  getExamTerms(): ExamTermInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.EXAM_TERMS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.EXAM_TERMS, JSON.stringify(DEFAULT_EXAM_TERMS));
      return DEFAULT_EXAM_TERMS;
    }
    return JSON.parse(raw);
  },

  createExamTerm(data: Omit<ExamTermInfo, 'id'>): ExamTermInfo {
    const terms = this.getExamTerms();
    const newTerm: ExamTermInfo = {
      ...data,
      id: terms.length > 0 ? Math.max(...terms.map((t) => t.id)) + 1 : 1,
    };
    terms.push(newTerm);
    localStorage.setItem(STORAGE_KEYS.EXAM_TERMS, JSON.stringify(terms));
    return newTerm;
  },

  updateExamTerm(id: number, data: Partial<ExamTermInfo>): ExamTermInfo | null {
    const terms = this.getExamTerms();
    const idx = terms.findIndex((t) => t.id === id);
    if (idx === -1) return null;
    terms[idx] = { ...terms[idx], ...data };
    localStorage.setItem(STORAGE_KEYS.EXAM_TERMS, JSON.stringify(terms));
    return terms[idx];
  },

  deleteExamTerm(id: number): boolean {
    const terms = this.getExamTerms();
    const filtered = terms.filter((t) => t.id !== id);
    if (filtered.length === terms.length) return false;
    localStorage.setItem(STORAGE_KEYS.EXAM_TERMS, JSON.stringify(filtered));
    return true;
  },

  getGradingScales(): GradingScaleInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.GRADING_SCALES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.GRADING_SCALES, JSON.stringify(DEFAULT_GRADING_SCALES));
      return DEFAULT_GRADING_SCALES;
    }
    return JSON.parse(raw);
  },

  getGradeForScore(score: number): { gradeName: string; gradePoint: number; remarks: string; isPassed: boolean } {
    const scales = this.getGradingScales();
    for (const scale of scales) {
      if (score >= scale.markFrom && score <= scale.markTo) {
        return {
          gradeName: scale.gradeName,
          gradePoint: scale.gradePoint,
          remarks: scale.remarks,
          isPassed: scale.gradePoint > 0,
        };
      }
    }
    if (score >= 80) return { gradeName: 'A+', gradePoint: 5.0, remarks: 'Outstanding', isPassed: true };
    return { gradeName: 'F', gradePoint: 0.0, remarks: 'Fail', isPassed: false };
  },

  getExamSchedules(termId?: number, classId?: number): ExamScheduleInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.EXAM_SCHEDULES);
    let schedules: ExamScheduleInfo[] = raw ? JSON.parse(raw) : DEFAULT_EXAM_SCHEDULES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.EXAM_SCHEDULES, JSON.stringify(DEFAULT_EXAM_SCHEDULES));
    }
    if (termId) schedules = schedules.filter((s) => s.examTermId === termId);
    if (classId) schedules = schedules.filter((s) => s.classId === classId);
    return schedules;
  },

  createExamSchedule(data: Omit<ExamScheduleInfo, 'id'>): ExamScheduleInfo {
    const schedules = this.getExamSchedules();
    const newSchedule: ExamScheduleInfo = {
      ...data,
      id: schedules.length > 0 ? Math.max(...schedules.map((s) => s.id)) + 1 : 1,
    };
    schedules.push(newSchedule);
    localStorage.setItem(STORAGE_KEYS.EXAM_SCHEDULES, JSON.stringify(schedules));
    return newSchedule;
  },

  updateExamSchedule(id: number, data: Partial<ExamScheduleInfo>): ExamScheduleInfo | null {
    const schedules = this.getExamSchedules();
    const idx = schedules.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    schedules[idx] = { ...schedules[idx], ...data };
    localStorage.setItem(STORAGE_KEYS.EXAM_SCHEDULES, JSON.stringify(schedules));
    return schedules[idx];
  },

  deleteExamSchedule(id: number): boolean {
    const schedules = this.getExamSchedules();
    const filtered = schedules.filter((s) => s.id !== id);
    if (filtered.length === schedules.length) return false;
    localStorage.setItem(STORAGE_KEYS.EXAM_SCHEDULES, JSON.stringify(filtered));
    return true;
  },

  getStudentMarks(termId?: number, classId?: number, subjectId?: number): StudentMarkRecord[] {
    const raw = localStorage.getItem(STORAGE_KEYS.STUDENT_MARKS);
    let marks: StudentMarkRecord[] = raw ? JSON.parse(raw) : DEFAULT_STUDENT_MARKS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.STUDENT_MARKS, JSON.stringify(DEFAULT_STUDENT_MARKS));
    }
    if (termId) marks = marks.filter((m) => m.examTermId === termId);
    if (classId) marks = marks.filter((m) => m.classId === classId);
    if (subjectId) marks = marks.filter((m) => m.subjectId === subjectId);
    return marks;
  },

  upsertStudentMarks(
    termId: number,
    classId: number,
    subjectId: number,
    marksList: Array<{
      studentId: number;
      theoryMarks: number;
      mcqMarks: number;
      practicalMarks: number;
      caMarks: number;
      isAbsent: boolean;
      remarks?: string;
    }>
  ): StudentMarkRecord[] {
    const allMarks = this.getStudentMarks();
    const students = this.getStudents();
    const classes = this.getDetailedClasses();
    const subjects = this.getSubjects();

    const targetClass = classes.find((c) => c.id === classId);
    const targetSubject = subjects.find((s) => s.id === subjectId);
    const className = targetClass ? targetClass.name : 'Unknown Class';
    const subjectName = targetSubject ? targetSubject.name : 'Unknown Subject';
    const subjectCode = targetSubject ? targetSubject.code : 'SUB';

    const updated: StudentMarkRecord[] = [];

    for (const item of marksList) {
      const student = students.find((s) => s.id === item.studentId);
      const studentName = student ? `${student.firstName} ${student.lastName}` : 'Unknown Student';
      const studentCode = student ? student.studentId : `STD-${item.studentId}`;
      const rollNumber = student ? student.rollNumber : 0;

      const total = item.isAbsent ? 0 : Number(item.theoryMarks || 0) + Number(item.mcqMarks || 0) + Number(item.practicalMarks || 0) + Number(item.caMarks || 0);
      const grade = item.isAbsent ? { gradeName: 'F', gradePoint: 0.0, isPassed: false } : this.getGradeForScore(total);

      const existingIdx = allMarks.findIndex(
        (m) => m.examTermId === termId && m.classId === classId && m.subjectId === subjectId && m.studentId === item.studentId
      );

      const markRecord: StudentMarkRecord = {
        id: existingIdx >= 0 ? allMarks[existingIdx].id : allMarks.length > 0 ? Math.max(...allMarks.map((m) => m.id)) + 1 : 1,
        examTermId: termId,
        classId,
        className,
        subjectId,
        subjectName,
        subjectCode,
        studentId: item.studentId,
        studentCode,
        studentName,
        rollNumber,
        theoryMarks: item.isAbsent ? 0 : Number(item.theoryMarks || 0),
        mcqMarks: item.isAbsent ? 0 : Number(item.mcqMarks || 0),
        practicalMarks: item.isAbsent ? 0 : Number(item.practicalMarks || 0),
        caMarks: item.isAbsent ? 0 : Number(item.caMarks || 0),
        totalMarks: total,
        isAbsent: item.isAbsent,
        gradeName: grade.gradeName,
        gradePoint: grade.gradePoint,
        isPassed: !item.isAbsent && grade.isPassed,
        remarks: item.remarks || '',
      };

      if (existingIdx >= 0) {
        allMarks[existingIdx] = markRecord;
      } else {
        allMarks.push(markRecord);
      }
      updated.push(markRecord);
    }

    localStorage.setItem(STORAGE_KEYS.STUDENT_MARKS, JSON.stringify(allMarks));
    // Auto compile results for the class & term
    this.compileClassResults(termId, classId);
    return updated;
  },

  compileClassResults(termId: number, classId: number): ExamResultSummaryInfo[] {
    const terms = this.getExamTerms();
    const currentTerm = terms.find((t) => t.id === termId);
    const termName = currentTerm ? currentTerm.name : 'Terminal Exam';

    const classes = this.getDetailedClasses();
    const targetClass = classes.find((c) => c.id === classId);
    const className = targetClass ? targetClass.name : 'Unknown Class';

    const students = this.getStudents().filter(
      (s) =>
        (s.className === className ||
          s.className.toLowerCase().includes((targetClass?.name || '').toLowerCase())) &&
        s.status === 'active'
    );

    const allMarks = this.getStudentMarks(termId, classId);
    const summaries: ExamResultSummaryInfo[] = [];

    students.forEach((student) => {
      const studentMarks = allMarks.filter((m) => m.studentId === student.id);
      if (studentMarks.length === 0) return;

      let totalObtained = 0;
      let totalFull = studentMarks.length * 100;
      let totalPoints = 0;
      let failedCount = 0;

      studentMarks.forEach((m) => {
        totalObtained += m.totalMarks;
        totalPoints += m.gradePoint;
        if (!m.isPassed || m.isAbsent) {
          failedCount += 1;
        }
      });

      const passedAll = failedCount === 0;
      const calculatedGpa = studentMarks.length > 0 ? Number((totalPoints / studentMarks.length).toFixed(2)) : 0;
      // Fail-lock rule: if failed in any subject, GPA is 0.00 and overall grade is F
      const gpa = passedAll ? Math.min(5.0, calculatedGpa) : 0.0;
      let overallGrade = 'F';
      if (passedAll) {
        if (gpa >= 5.0) overallGrade = 'A+';
        else if (gpa >= 4.0) overallGrade = 'A';
        else if (gpa >= 3.5) overallGrade = 'A-';
        else if (gpa >= 3.0) overallGrade = 'B';
        else if (gpa >= 2.0) overallGrade = 'C';
        else if (gpa >= 1.0) overallGrade = 'D';
      }

      const percentage = totalFull > 0 ? Number(((totalObtained / totalFull) * 100).toFixed(2)) : 0;

      summaries.push({
        id: summaries.length + 1,
        examTermId: termId,
        examTermName: termName,
        studentId: student.id,
        studentCode: student.studentId,
        studentName: `${student.firstName} ${student.lastName}`,
        rollNumber: student.rollNumber,
        classId,
        className,
        sectionName: student.sectionName,
        totalObtained,
        totalFullMarks: totalFull,
        percentage,
        gpa,
        overallGrade,
        classRank: null,
        passedAll,
        failedSubjectCount: failedCount,
        remarks: passedAll ? (gpa === 5.0 ? 'Golden A+ (Outstanding)' : 'Passed Successfully') : `Failed in ${failedCount} Subject(s)`,
      });
    });

    // Merit Ranking: Passed students first, sorted by GPA desc, then totalObtained desc
    summaries.sort((a, b) => {
      if (a.passedAll !== b.passedAll) return a.passedAll ? -1 : 1;
      if (b.gpa !== a.gpa) return b.gpa - a.gpa;
      return b.totalObtained - a.totalObtained;
    });

    summaries.forEach((s, idx) => {
      s.classRank = idx + 1;
      s.id = idx + 1;
    });

    const allSummaries = this.getExamResultSummaries();
    const otherSummaries = allSummaries.filter((s) => !(s.examTermId === termId && s.classId === classId));
    const merged = [...otherSummaries, ...summaries];
    localStorage.setItem(STORAGE_KEYS.EXAM_RESULT_SUMMARIES, JSON.stringify(merged));
    return summaries;
  },

  getExamResultSummaries(termId?: number, classId?: number): ExamResultSummaryInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.EXAM_RESULT_SUMMARIES);
    let list: ExamResultSummaryInfo[] = raw ? JSON.parse(raw) : DEFAULT_EXAM_RESULT_SUMMARIES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.EXAM_RESULT_SUMMARIES, JSON.stringify(DEFAULT_EXAM_RESULT_SUMMARIES));
    }
    if (termId) list = list.filter((s) => s.examTermId === termId);
    if (classId) list = list.filter((s) => s.classId === classId);
    return list;
  },

  getExamStats() {
    const terms = this.getExamTerms();
    const summaries = this.getExamResultSummaries();
    const schedules = this.getExamSchedules();
    const totalExaminees = summaries.length;
    const passedExaminees = summaries.filter((s) => s.passedAll).length;
    const passRate = totalExaminees > 0 ? Number(((passedExaminees / totalExaminees) * 100).toFixed(1)) : 0;
    const gpa5Count = summaries.filter((s) => s.gpa === 5.0).length;

    return {
      totalTerms: terms.length,
      upcomingRoutines: schedules.length,
      totalExaminees,
      passRate,
      gpa5Count,
    };
  },

  // --- Phase 9: Class Timetable & Teacher Routine Management ---
  getPeriodSlots(): PeriodSlotInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TIMETABLE_PERIODS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TIMETABLE_PERIODS, JSON.stringify(DEFAULT_PERIOD_SLOTS));
      return DEFAULT_PERIOD_SLOTS;
    }
    return JSON.parse(raw);
  },

  createPeriodSlot(data: Omit<PeriodSlotInfo, 'id'>): PeriodSlotInfo {
    const slots = this.getPeriodSlots();
    const newSlot: PeriodSlotInfo = {
      ...data,
      id: slots.length > 0 ? Math.max(...slots.map((s) => s.id)) + 1 : 1,
    };
    slots.push(newSlot);
    localStorage.setItem(STORAGE_KEYS.TIMETABLE_PERIODS, JSON.stringify(slots));
    return newSlot;
  },

  updatePeriodSlot(id: number, data: Partial<PeriodSlotInfo>): PeriodSlotInfo | null {
    const slots = this.getPeriodSlots();
    const idx = slots.findIndex((s) => s.id === id);
    if (idx === -1) return null;
    slots[idx] = { ...slots[idx], ...data };
    localStorage.setItem(STORAGE_KEYS.TIMETABLE_PERIODS, JSON.stringify(slots));
    return slots[idx];
  },

  deletePeriodSlot(id: number): boolean {
    const slots = this.getPeriodSlots();
    const filtered = slots.filter((s) => s.id !== id);
    if (filtered.length === slots.length) return false;
    localStorage.setItem(STORAGE_KEYS.TIMETABLE_PERIODS, JSON.stringify(filtered));
    return true;
  },

  getTimetableEntries(classId?: number, sectionId?: number, teacherId?: number, dayOfWeek?: string): TimetableEntryInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TIMETABLE_ENTRIES);
    let entries: TimetableEntryInfo[] = raw ? JSON.parse(raw) : DEFAULT_TIMETABLE_ENTRIES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TIMETABLE_ENTRIES, JSON.stringify(DEFAULT_TIMETABLE_ENTRIES));
    }
    if (classId) entries = entries.filter((e) => e.classId === classId);
    if (sectionId) entries = entries.filter((e) => e.sectionId === sectionId);
    if (teacherId) entries = entries.filter((e) => e.teacherId === teacherId);
    if (dayOfWeek) entries = entries.filter((e) => e.dayOfWeek === dayOfWeek);
    return entries;
  },

  checkTimetableConflict(
    dayOfWeek: string,
    periodSlotId: number,
    teacherId: number,
    roomNumber: string,
    excludeEntryId?: number
  ): TimetableConflict[] {
    const allEntries = this.getTimetableEntries();
    const periods = this.getPeriodSlots();
    const period = periods.find((p) => p.id === periodSlotId);
    const periodName = period ? period.name : `Period #${periodSlotId}`;
    const conflicts: TimetableConflict[] = [];

    const normalizedRoom = roomNumber.trim().toLowerCase();

    for (const e of allEntries) {
      if (excludeEntryId && e.id === excludeEntryId) continue;
      if (e.dayOfWeek === dayOfWeek && e.periodSlotId === periodSlotId) {
        // Teacher conflict
        if (e.teacherId === teacherId) {
          conflicts.push({
            conflictType: 'teacher',
            message: `Teacher Double-Booking: ${e.teacherName} is already assigned to ${e.className} (${e.sectionName || 'All'}) on ${dayOfWeek} during ${periodName}.`,
            dayOfWeek,
            periodName,
            conflictingClass: e.className,
          });
        }
        // Room conflict
        if (e.roomNumber.trim().toLowerCase() === normalizedRoom) {
          conflicts.push({
            conflictType: 'room',
            message: `Room Collision: ${e.roomNumber} is already booked by ${e.className} (${e.sectionName || 'All'}) on ${dayOfWeek} during ${periodName}.`,
            dayOfWeek,
            periodName,
            conflictingClass: e.className,
          });
        }
      }
    }

    return conflicts;
  },

  assignTimetableEntry(data: {
    academicYearId: number;
    classId: number;
    sectionId?: number;
    dayOfWeek: any;
    periodSlotId: number;
    subjectId: number;
    teacherId: number;
    roomNumber: string;
    notes?: string;
    id?: number;
  }): { entry: TimetableEntryInfo | null; conflicts: TimetableConflict[] } {
    const conflicts = this.checkTimetableConflict(
      data.dayOfWeek,
      data.periodSlotId,
      data.teacherId,
      data.roomNumber,
      data.id
    );

    if (conflicts.length > 0) {
      return { entry: null, conflicts };
    }

    const classes = this.getDetailedClasses();
    const subjects = this.getSubjects();
    const teachers = this.getTeachers();
    const periods = this.getPeriodSlots();
    const sections = this.getSections();

    const targetClass = classes.find((c) => c.id === data.classId);
    const targetSubject = subjects.find((s) => s.id === data.subjectId);
    const targetTeacher = teachers.find((t) => t.id === data.teacherId);
    const targetPeriod = periods.find((p) => p.id === data.periodSlotId);
    const targetSection = data.sectionId ? sections.find((s) => s.id === data.sectionId) : undefined;

    const allEntries = this.getTimetableEntries();

    const entryRecord: TimetableEntryInfo = {
      id: data.id || (allEntries.length > 0 ? Math.max(...allEntries.map((e) => e.id)) + 1 : 1),
      academicYearId: data.academicYearId || 1,
      classId: data.classId,
      className: targetClass ? targetClass.name : 'Unknown Class',
      sectionId: data.sectionId,
      sectionName: targetSection ? targetSection.name : undefined,
      dayOfWeek: data.dayOfWeek,
      periodSlotId: data.periodSlotId,
      periodName: targetPeriod ? targetPeriod.name : 'Period',
      periodTime: targetPeriod ? `${targetPeriod.startTime} - ${targetPeriod.endTime}` : '',
      subjectId: data.subjectId,
      subjectName: targetSubject ? targetSubject.name : 'Subject',
      subjectCode: targetSubject ? targetSubject.code : 'SUB',
      teacherId: data.teacherId,
      teacherName: targetTeacher ? targetTeacher.fullName : 'Teacher',
      roomNumber: data.roomNumber,
      notes: data.notes || '',
    };

    if (data.id) {
      const idx = allEntries.findIndex((e) => e.id === data.id);
      if (idx >= 0) allEntries[idx] = entryRecord;
    } else {
      // If class already has assignment for this day & period, replace it
      const existingIdx = allEntries.findIndex(
        (e) =>
          e.classId === data.classId &&
          e.sectionId === data.sectionId &&
          e.dayOfWeek === data.dayOfWeek &&
          e.periodSlotId === data.periodSlotId
      );
      if (existingIdx >= 0) {
        entryRecord.id = allEntries[existingIdx].id;
        allEntries[existingIdx] = entryRecord;
      } else {
        allEntries.push(entryRecord);
      }
    }

    localStorage.setItem(STORAGE_KEYS.TIMETABLE_ENTRIES, JSON.stringify(allEntries));
    return { entry: entryRecord, conflicts: [] };
  },

  deleteTimetableEntry(id: number): boolean {
    const entries = this.getTimetableEntries();
    const filtered = entries.filter((e) => e.id !== id);
    if (filtered.length === entries.length) return false;
    localStorage.setItem(STORAGE_KEYS.TIMETABLE_ENTRIES, JSON.stringify(filtered));
    return true;
  },

  getClassTimetableMatrix(classId: number, sectionId?: number): Record<string, Record<number, TimetableEntryInfo>> {
    const entries = this.getTimetableEntries(classId, sectionId);
    const matrix: Record<string, Record<number, TimetableEntryInfo>> = {};
    for (const e of entries) {
      if (!matrix[e.dayOfWeek]) matrix[e.dayOfWeek] = {};
      matrix[e.dayOfWeek][e.periodSlotId] = e;
    }
    return matrix;
  },

  getTeacherRoutineMatrix(teacherId: number): Record<string, Record<number, TimetableEntryInfo>> {
    const entries = this.getTimetableEntries(undefined, undefined, teacherId);
    const matrix: Record<string, Record<number, TimetableEntryInfo>> = {};
    for (const e of entries) {
      if (!matrix[e.dayOfWeek]) matrix[e.dayOfWeek] = {};
      matrix[e.dayOfWeek][e.periodSlotId] = e;
    }
    return matrix;
  },

  getTimetableStats() {
    const periods = this.getPeriodSlots();
    const entries = this.getTimetableEntries();
    const teachingPeriods = periods.filter((p) => !p.isBreak);
    const activeTeachers = new Set(entries.map((e) => e.teacherId)).size;
    const rooms = new Set(entries.map((e) => e.roomNumber)).size;

    return {
      totalPeriods: periods.length,
      teachingPeriodsCount: teachingPeriods.length,
      totalAssignedSlots: entries.length,
      activeTeachingFaculty: activeTeachers,
      allocatedRooms: rooms,
    };
  },

  // --- Phase 10: Library Circulation & Book Management ---
  getBookCategories(): BookCategoryInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.BOOK_CATEGORIES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.BOOK_CATEGORIES, JSON.stringify(DEFAULT_BOOK_CATEGORIES));
      return DEFAULT_BOOK_CATEGORIES;
    }
    return JSON.parse(raw);
  },

  saveBookCategory(categoryData: Partial<BookCategoryInfo>): BookCategoryInfo {
    const categories = this.getBookCategories();
    if (categoryData.id) {
      const idx = categories.findIndex((c) => c.id === categoryData.id);
      if (idx !== -1) {
        categories[idx] = { ...categories[idx], ...categoryData } as BookCategoryInfo;
        localStorage.setItem(STORAGE_KEYS.BOOK_CATEGORIES, JSON.stringify(categories));
        return categories[idx];
      }
    }
    const newCategory: BookCategoryInfo = {
      id: categories.length > 0 ? Math.max(...categories.map((c) => c.id)) + 1 : 1,
      name: categoryData.name || 'New Category',
      code: categoryData.code || 'CAT',
      description: categoryData.description,
    };
    categories.push(newCategory);
    localStorage.setItem(STORAGE_KEYS.BOOK_CATEGORIES, JSON.stringify(categories));
    return newCategory;
  },

  getBooks(categoryId?: number, searchQuery?: string, onlyAvailable?: boolean): BookInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.LIBRARY_BOOKS);
    let books: BookInfo[] = raw ? JSON.parse(raw) : DEFAULT_BOOKS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(DEFAULT_BOOKS));
    }
    if (categoryId) {
      books = books.filter((b) => b.categoryId === categoryId);
    }
    if (onlyAvailable) {
      books = books.filter((b) => b.availableCopies > 0);
    }
    if (searchQuery && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      books = books.filter(
        (b) =>
          b.title.toLowerCase().includes(q) ||
          b.author.toLowerCase().includes(q) ||
          b.accessionNo.toLowerCase().includes(q) ||
          (b.isbn && b.isbn.toLowerCase().includes(q))
      );
    }
    return books;
  },

  getBookById(id: number): BookInfo | undefined {
    return this.getBooks().find((b) => b.id === id);
  },

  saveBook(bookData: Partial<BookInfo>): BookInfo {
    const books = this.getBooks();
    const categories = this.getBookCategories();
    const cat = categories.find((c) => c.id === bookData.categoryId);
    const catName = cat ? cat.name : (bookData.categoryName || 'General');

    if (bookData.id) {
      const idx = books.findIndex((b) => b.id === bookData.id);
      if (idx !== -1) {
        const total = bookData.totalCopies ?? books[idx].totalCopies;
        const issued = books[idx].issuedCopies;
        const avail = Math.max(0, total - issued);
        books[idx] = {
          ...books[idx],
          ...bookData,
          categoryName: catName,
          totalCopies: total,
          availableCopies: avail,
          status: avail > 0 ? 'Available' : 'Out of Stock',
        } as BookInfo;
        localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(books));
        return books[idx];
      }
    }

    const total = bookData.totalCopies ?? 1;
    const newBook: BookInfo = {
      id: books.length > 0 ? Math.max(...books.map((b) => b.id)) + 1 : 1,
      accessionNo: bookData.accessionNo || `ACC-${new Date().getFullYear()}-${String(books.length + 1).padStart(4, '0')}`,
      title: bookData.title || 'Untitled Book',
      author: bookData.author || 'Unknown Author',
      publisher: bookData.publisher,
      isbn: bookData.isbn,
      edition: bookData.edition,
      publicationYear: bookData.publicationYear,
      categoryId: bookData.categoryId || (categories[0]?.id || 1),
      categoryName: catName,
      rackNumber: bookData.rackNumber,
      shelfNumber: bookData.shelfNumber,
      totalCopies: total,
      availableCopies: total,
      issuedCopies: 0,
      price: bookData.price ?? 20.0,
      status: total > 0 ? 'Available' : 'Out of Stock',
    };
    books.push(newBook);
    localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(books));
    return newBook;
  },

  deleteBook(id: number): boolean {
    const books = this.getBooks();
    const filtered = books.filter((b) => b.id !== id);
    if (filtered.length === books.length) return false;
    localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(filtered));
    return true;
  },

  getLibraryMembers(memberType?: string): LibraryMemberInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.LIBRARY_MEMBERS);
    let members: LibraryMemberInfo[] = raw ? JSON.parse(raw) : DEFAULT_LIBRARY_MEMBERS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.LIBRARY_MEMBERS, JSON.stringify(DEFAULT_LIBRARY_MEMBERS));
    }
    // Update activeLoanCount dynamically
    const circs = this.getCirculations('Active');
    members = members.map((m) => ({
      ...m,
      activeLoanCount: circs.filter((c) => c.memberId === m.id).length,
    }));
    if (memberType) {
      members = members.filter((m) => m.memberType === memberType);
    }
    return members;
  },

  getLibraryMemberById(id: number): LibraryMemberInfo | undefined {
    return this.getLibraryMembers().find((m) => m.id === id);
  },

  saveLibraryMember(memberData: Partial<LibraryMemberInfo>): LibraryMemberInfo {
    const members = this.getLibraryMembers();
    if (memberData.id) {
      const idx = members.findIndex((m) => m.id === memberData.id);
      if (idx !== -1) {
        members[idx] = { ...members[idx], ...memberData } as LibraryMemberInfo;
        localStorage.setItem(STORAGE_KEYS.LIBRARY_MEMBERS, JSON.stringify(members));
        return members[idx];
      }
    }
    const newMember: LibraryMemberInfo = {
      id: members.length > 0 ? Math.max(...members.map((m) => m.id)) + 1 : 1,
      memberId: memberData.memberId || `LIB-MEM-${String(members.length + 1001)}`,
      memberType: memberData.memberType || 'Student',
      studentId: memberData.studentId,
      teacherId: memberData.teacherId,
      staffId: memberData.staffId,
      patronName: memberData.patronName || 'New Member',
      rollOrDesignation: memberData.rollOrDesignation,
      cardIssueDate: memberData.cardIssueDate || new Date().toISOString().split('T')[0],
      maxAllowedBooks: memberData.maxAllowedBooks || (memberData.memberType === 'Teacher' ? 5 : 3),
      activeLoanCount: 0,
      status: memberData.status || 'Active',
    };
    members.push(newMember);
    localStorage.setItem(STORAGE_KEYS.LIBRARY_MEMBERS, JSON.stringify(members));
    return newMember;
  },

  getCirculations(status?: string, memberId?: number, bookId?: number): BookCirculationRecord[] {
    const raw = localStorage.getItem(STORAGE_KEYS.BOOK_CIRCULATIONS);
    let circs: BookCirculationRecord[] = raw ? JSON.parse(raw) : DEFAULT_BOOK_CIRCULATIONS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.BOOK_CIRCULATIONS, JSON.stringify(DEFAULT_BOOK_CIRCULATIONS));
    }
    const today = new Date().toISOString().split('T')[0];
    // Automatically update overdue status for unreturned loans past due date
    circs = circs.map((c) => {
      if (c.status === 'Issued' && c.dueDate < today) {
        const diffDays = Math.max(0, Math.ceil((new Date(today).getTime() - new Date(c.dueDate).getTime()) / (1000 * 3600 * 24)));
        return {
          ...c,
          status: 'Overdue' as const,
          fineAmount: diffDays * 5.0,
        };
      }
      return c;
    });

    if (status) {
      if (status === 'Active') {
        circs = circs.filter((c) => c.status === 'Issued' || c.status === 'Overdue');
      } else {
        circs = circs.filter((c) => c.status === status);
      }
    }
    if (memberId) {
      circs = circs.filter((c) => c.memberId === memberId);
    }
    if (bookId) {
      circs = circs.filter((c) => c.bookId === bookId);
    }
    return circs.sort((a, b) => b.id - a.id);
  },

  issueBook(
    bookId: number,
    memberId: number,
    issueDate: string,
    dueDate: string,
    issuedBy?: string,
    remarks?: string
  ): { success: boolean; message?: string; circulation?: BookCirculationRecord } {
    const book = this.getBookById(bookId);
    if (!book) return { success: false, message: 'Book title not found.' };
    if (book.availableCopies <= 0) return { success: false, message: `No copies of '${book.title}' are available.` };

    const member = this.getLibraryMemberById(memberId);
    if (!member) return { success: false, message: 'Library patron member not found.' };
    if (member.status !== 'Active') return { success: false, message: `Member is currently ${member.status}.` };

    const activeLoans = this.getCirculations('Active', memberId);
    if (activeLoans.length >= member.maxAllowedBooks) {
      return { success: false, message: `Borrower has reached maximum limit of ${member.maxAllowedBooks} borrowed books.` };
    }

    // Decrement available copies
    const books = this.getBooks();
    const bIdx = books.findIndex((b) => b.id === bookId);
    if (bIdx !== -1) {
      books[bIdx].availableCopies -= 1;
      books[bIdx].issuedCopies += 1;
      books[bIdx].status = books[bIdx].availableCopies > 0 ? 'Available' : 'Out of Stock';
      localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(books));
    }

    const circs = this.getCirculations();
    const newCirc: BookCirculationRecord = {
      id: circs.length > 0 ? Math.max(...circs.map((c) => c.id)) + 1 : 1,
      bookId,
      accessionNo: book.accessionNo,
      bookTitle: book.title,
      memberId,
      memberCode: member.memberId,
      patronName: member.patronName,
      memberType: member.memberType,
      issueDate,
      dueDate,
      status: 'Issued',
      fineAmount: 0,
      finePaid: false,
      issuedBy: issuedBy || 'Chief Librarian',
      remarks,
    };
    circs.unshift(newCirc);
    localStorage.setItem(STORAGE_KEYS.BOOK_CIRCULATIONS, JSON.stringify(circs));
    return { success: true, circulation: newCirc };
  },

  returnBook(
    circulationId: number,
    returnDate: string,
    fineRatePerDay: number = 5.0,
    finePaid: boolean = false,
    remarks?: string
  ): { success: boolean; message?: string; circulation?: BookCirculationRecord } {
    const circs = this.getCirculations();
    const idx = circs.findIndex((c) => c.id === circulationId);
    if (idx === -1) return { success: false, message: 'Circulation record not found.' };
    if (circs[idx].status === 'Returned') return { success: false, message: 'Book has already been returned.' };

    const target = circs[idx];
    const dueTime = new Date(target.dueDate).getTime();
    const retTime = new Date(returnDate).getTime();
    const diffDays = Math.max(0, Math.ceil((retTime - dueTime) / (1000 * 3600 * 24)));
    const fineAmt = diffDays * fineRatePerDay;

    target.returnDate = returnDate;
    target.status = 'Returned';
    target.fineAmount = fineAmt;
    target.finePaid = finePaid || fineAmt === 0;
    if (remarks) target.remarks = remarks;

    localStorage.setItem(STORAGE_KEYS.BOOK_CIRCULATIONS, JSON.stringify(circs));

    // Replenish copy count
    const books = this.getBooks();
    const bIdx = books.findIndex((b) => b.id === target.bookId);
    if (bIdx !== -1) {
      books[bIdx].availableCopies += 1;
      books[bIdx].issuedCopies = Math.max(0, books[bIdx].issuedCopies - 1);
      books[bIdx].status = 'Available';
      localStorage.setItem(STORAGE_KEYS.LIBRARY_BOOKS, JSON.stringify(books));
    }

    return { success: true, circulation: target };
  },

  getLibraryStats(): LibraryStatsInfo {
    const books = this.getBooks();
    const totalTitles = books.length;
    const totalInventoryCopies = books.reduce((acc, b) => acc + b.totalCopies, 0);
    const availableCopies = books.reduce((acc, b) => acc + b.availableCopies, 0);
    const circs = this.getCirculations();
    const currentlyIssued = circs.filter((c) => c.status === 'Issued' || c.status === 'Overdue').length;
    const today = new Date().toISOString().split('T')[0];
    const overdueCount = circs.filter((c) => (c.status === 'Issued' || c.status === 'Overdue') && c.dueDate < today).length;
    const members = this.getLibraryMembers();
    const activeMembers = members.filter((m) => m.status === 'Active').length;
    const totalFineCollected = circs
      .filter((c) => c.finePaid && c.fineAmount > 0)
      .reduce((acc, c) => acc + c.fineAmount, 0);

    return {
      totalTitles,
      totalInventoryCopies,
      availableCopies,
      currentlyIssued,
      overdueCount,
      activeMembers,
      totalFineCollected,
    };
  },

  // --- Phase 11: Transport & Fleet Management ---
  getVehicles(status?: string): VehicleInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TRANSPORT_VEHICLES);
    let list: VehicleInfo[] = raw ? JSON.parse(raw) : DEFAULT_VEHICLES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TRANSPORT_VEHICLES, JSON.stringify(DEFAULT_VEHICLES));
    }
    if (status) {
      list = list.filter((v) => v.status === status);
    }
    return list;
  },

  saveVehicle(vehicleData: Partial<VehicleInfo>): VehicleInfo {
    const vehicles = this.getVehicles();
    if (vehicleData.id) {
      const idx = vehicles.findIndex((v) => v.id === vehicleData.id);
      if (idx !== -1) {
        vehicles[idx] = { ...vehicles[idx], ...vehicleData } as VehicleInfo;
        localStorage.setItem(STORAGE_KEYS.TRANSPORT_VEHICLES, JSON.stringify(vehicles));
        return vehicles[idx];
      }
    }
    const newVehicle: VehicleInfo = {
      id: vehicles.length > 0 ? Math.max(...vehicles.map((v) => v.id)) + 1 : 1,
      vehicleNumber: vehicleData.vehicleNumber || `DHK-METRO-${String(vehicles.length + 1001)}`,
      vehicleModel: vehicleData.vehicleModel || 'Standard School Bus',
      vehicleType: vehicleData.vehicleType || 'Bus',
      seatingCapacity: vehicleData.seatingCapacity || 40,
      driverName: vehicleData.driverName || 'Designated Driver',
      driverPhone: vehicleData.driverPhone || '+880 1700-000000',
      driverLicense: vehicleData.driverLicense,
      helperName: vehicleData.helperName,
      helperPhone: vehicleData.helperPhone,
      insuranceExpiry: vehicleData.insuranceExpiry,
      fitnessExpiry: vehicleData.fitnessExpiry,
      status: vehicleData.status || 'Active',
    };
    vehicles.push(newVehicle);
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_VEHICLES, JSON.stringify(vehicles));
    return newVehicle;
  },

  deleteVehicle(id: number): boolean {
    const vehicles = this.getVehicles();
    const filtered = vehicles.filter((v) => v.id !== id);
    if (filtered.length === vehicles.length) return false;
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_VEHICLES, JSON.stringify(filtered));
    return true;
  },

  getRoutes(status?: string): TransportRouteInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TRANSPORT_ROUTES);
    let routes: TransportRouteInfo[] = raw ? JSON.parse(raw) : DEFAULT_ROUTES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TRANSPORT_ROUTES, JSON.stringify(DEFAULT_ROUTES));
    }
    if (status) {
      routes = routes.filter((r) => r.status === status);
    }
    return routes;
  },

  getRouteById(id: number): TransportRouteInfo | undefined {
    return this.getRoutes().find((r) => r.id === id);
  },

  saveRoute(routeData: Partial<TransportRouteInfo>): TransportRouteInfo {
    const routes = this.getRoutes();
    const vehicles = this.getVehicles();
    const v = vehicles.find((veh) => veh.id === routeData.vehicleId);
    const vNumber = v ? v.vehicleNumber : routeData.vehicleNumber;

    if (routeData.id) {
      const idx = routes.findIndex((r) => r.id === routeData.id);
      if (idx !== -1) {
        routes[idx] = {
          ...routes[idx],
          ...routeData,
          vehicleNumber: vNumber,
        } as TransportRouteInfo;
        localStorage.setItem(STORAGE_KEYS.TRANSPORT_ROUTES, JSON.stringify(routes));
        return routes[idx];
      }
    }

    const newRoute: TransportRouteInfo = {
      id: routes.length > 0 ? Math.max(...routes.map((r) => r.id)) + 1 : 1,
      routeCode: routeData.routeCode || `RT-${String(routes.length + 1).padStart(2, '0')}`,
      routeName: routeData.routeName || 'New Route',
      startPoint: routeData.startPoint || 'Origin Point',
      endPoint: routeData.endPoint || 'School Main Campus',
      distanceKm: routeData.distanceKm || 10.0,
      monthlyFee: routeData.monthlyFee || 2500.0,
      vehicleId: routeData.vehicleId,
      vehicleNumber: vNumber,
      pickupTime: routeData.pickupTime || '06:45 AM',
      dropTime: routeData.dropTime || '02:30 PM',
      stops: routeData.stops || [],
      status: routeData.status || 'Active',
    };
    routes.push(newRoute);
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_ROUTES, JSON.stringify(routes));
    return newRoute;
  },

  deleteRoute(id: number): boolean {
    const routes = this.getRoutes();
    const filtered = routes.filter((r) => r.id !== id);
    if (filtered.length === routes.length) return false;
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_ROUTES, JSON.stringify(filtered));
    return true;
  },

  getTransportPassengers(routeId?: number, status?: string): TransportPassengerInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.TRANSPORT_PASSENGERS);
    let passengers: TransportPassengerInfo[] = raw ? JSON.parse(raw) : DEFAULT_PASSENGERS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.TRANSPORT_PASSENGERS, JSON.stringify(DEFAULT_PASSENGERS));
    }
    if (routeId) {
      passengers = passengers.filter((p) => p.routeId === routeId);
    }
    if (status) {
      passengers = passengers.filter((p) => p.status === status);
    }
    return passengers;
  },

  allocatePassenger(data: {
    passengerType: 'Student' | 'Teacher' | 'Staff';
    studentId?: number;
    teacherId?: number;
    patronName?: string;
    rollOrDesignation?: string;
    phone?: string;
    emergencyContact?: string;
    routeId: number;
    stopId?: number;
    seatNumber?: string;
    allocationDate: string;
    monthlyFare?: number;
    remarks?: string;
  }): { success: boolean; message?: string; passenger?: TransportPassengerInfo } {
    const route = this.getRouteById(data.routeId);
    if (!route) return { success: false, message: 'Route not found.' };

    const passengers = this.getTransportPassengers();
    const activeRoutePassengers = passengers.filter((p) => p.routeId === data.routeId && p.status === 'Active');

    // Check vehicle capacity
    if (route.vehicleId) {
      const v = this.getVehicles().find((veh) => veh.id === route.vehicleId);
      if (v && activeRoutePassengers.length >= v.seatingCapacity) {
        return { success: false, message: `Bus '${v.vehicleNumber}' is fully booked (${activeRoutePassengers.length}/${v.seatingCapacity} seats).` };
      }
    }

    // Check duplicate active allocation
    if (data.studentId) {
      const existing = passengers.find((p) => p.studentId === data.studentId && p.status === 'Active');
      if (existing) {
        return { success: false, message: `Student is already allocated to active Route '${existing.routeName}'.` };
      }
    } else if (data.teacherId) {
      const existing = passengers.find((p) => p.teacherId === data.teacherId && p.status === 'Active');
      if (existing) {
        return { success: false, message: `Teacher is already allocated to active Route '${existing.routeName}'.` };
      }
    }

    const stop = route.stops.find((s) => s.id === data.stopId);
    const stopTitle = stop ? stop.stopName : (route.stops[0]?.stopName || 'Campus Origin');

    const newPassenger: TransportPassengerInfo = {
      id: passengers.length > 0 ? Math.max(...passengers.map((p) => p.id)) + 1 : 1,
      passengerType: data.passengerType,
      studentId: data.studentId,
      teacherId: data.teacherId,
      patronName: data.patronName || 'New Commuter',
      rollOrDesignation: data.rollOrDesignation,
      phone: data.phone,
      emergencyContact: data.emergencyContact || data.phone,
      routeId: data.routeId,
      routeCode: route.routeCode,
      routeName: route.routeName,
      vehicleId: route.vehicleId,
      vehicleNumber: route.vehicleNumber,
      stopId: data.stopId,
      stopName: stopTitle,
      seatNumber: data.seatNumber || `Seat ${String(activeRoutePassengers.length + 1).padStart(2, '0')}`,
      allocationDate: data.allocationDate,
      monthlyFare: data.monthlyFare !== undefined ? data.monthlyFare : route.monthlyFee,
      status: 'Active',
      remarks: data.remarks,
    };

    passengers.unshift(newPassenger);
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_PASSENGERS, JSON.stringify(passengers));
    return { success: true, passenger: newPassenger };
  },

  cancelPassengerAllocation(passengerId: number, reason?: string): boolean {
    const passengers = this.getTransportPassengers();
    const idx = passengers.findIndex((p) => p.id === passengerId);
    if (idx === -1) return false;
    passengers[idx].status = 'Cancelled';
    if (reason) {
      passengers[idx].remarks = `${passengers[idx].remarks || ''} [Cancelled: ${reason}]`.trim();
    }
    localStorage.setItem(STORAGE_KEYS.TRANSPORT_PASSENGERS, JSON.stringify(passengers));
    return true;
  },

  getTransportStats(): TransportStatsInfo {
    const vehicles = this.getVehicles();
    const routes = this.getRoutes();
    const passengers = this.getTransportPassengers();

    const totalVehicles = vehicles.length;
    const activeVehicles = vehicles.filter((v) => v.status === 'Active').length;
    const totalRoutes = routes.filter((r) => r.status === 'Active').length;
    const totalCapacity = vehicles
      .filter((v) => v.status === 'Active')
      .reduce((acc, v) => acc + v.seatingCapacity, 0);
    const allocatedPassengers = passengers.filter((p) => p.status === 'Active').length;
    const availableSeats = Math.max(0, totalCapacity - allocatedPassengers);
    const monthlyRevenue = passengers
      .filter((p) => p.status === 'Active')
      .reduce((acc, p) => acc + p.monthlyFare, 0);

    return {
      totalVehicles,
      activeVehicles,
      totalRoutes,
      totalCapacity,
      allocatedPassengers,
      availableSeats,
      monthlyRevenue,
    };
  },

  // ==================== PHASE 12: HOSTEL & DORMITORY ====================
  getHostelBlocks(): HostelBlockInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.HOSTEL_BLOCKS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.HOSTEL_BLOCKS, JSON.stringify(DEFAULT_HOSTEL_BLOCKS));
      return DEFAULT_HOSTEL_BLOCKS;
    }
    return JSON.parse(raw);
  },

  saveHostelBlock(block: Partial<HostelBlockInfo> & { blockName: string }): HostelBlockInfo {
    const blocks = this.getHostelBlocks();
    if (block.id) {
      const idx = blocks.findIndex((b) => b.id === block.id);
      if (idx !== -1) {
        blocks[idx] = { ...blocks[idx], ...block } as HostelBlockInfo;
        localStorage.setItem(STORAGE_KEYS.HOSTEL_BLOCKS, JSON.stringify(blocks));
        return blocks[idx];
      }
    }
    const newId = blocks.length > 0 ? Math.max(...blocks.map((b) => b.id)) + 1 : 1;
    const newBlock: HostelBlockInfo = {
      id: newId,
      blockName: block.blockName,
      genderType: block.genderType || 'Boys',
      wardenName: block.wardenName || 'Staff Warden',
      wardenPhone: block.wardenPhone || '+880 1700-000000',
      address: block.address || 'Campus Residential Quadrangle',
      totalFloors: block.totalFloors || 3,
      status: block.status || 'Active',
    };
    blocks.push(newBlock);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_BLOCKS, JSON.stringify(blocks));
    return newBlock;
  },

  deleteHostelBlock(id: number): boolean {
    let blocks = this.getHostelBlocks();
    blocks = blocks.filter((b) => b.id !== id);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_BLOCKS, JSON.stringify(blocks));
    return true;
  },

  getHostelRooms(blockId?: number): HostelRoomInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.HOSTEL_ROOMS);
    let rooms: HostelRoomInfo[] = raw ? JSON.parse(raw) : DEFAULT_HOSTEL_ROOMS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.HOSTEL_ROOMS, JSON.stringify(DEFAULT_HOSTEL_ROOMS));
    }
    const allocations = this.getHostelAllocations();
    const blocks = this.getHostelBlocks();

    // Dynamically calculate occupied count and status
    rooms = rooms.map((r) => {
      const occupied = allocations.filter((a) => a.roomId === r.id && a.status === 'Active').length;
      const blk = blocks.find((b) => b.id === r.blockId);
      const isFull = occupied >= r.capacity;
      return {
        ...r,
        blockName: blk?.blockName || r.blockName,
        occupiedCount: occupied,
        status: (isFull ? 'Full' : r.status === 'Full' ? 'Available' : r.status) as HostelRoomInfo['status'],
      };
    });

    if (blockId) {
      rooms = rooms.filter((r) => r.blockId === blockId);
    }
    return rooms;
  },

  saveHostelRoom(room: Partial<HostelRoomInfo> & { blockId: number; roomNumber: string }): HostelRoomInfo {
    const rooms = this.getHostelRooms();
    const blocks = this.getHostelBlocks();
    const block = blocks.find((b) => b.id === room.blockId);

    if (room.id) {
      const idx = rooms.findIndex((r) => r.id === room.id);
      if (idx !== -1) {
        rooms[idx] = {
          ...rooms[idx],
          ...room,
          blockName: block?.blockName || rooms[idx].blockName,
        } as HostelRoomInfo;
        localStorage.setItem(STORAGE_KEYS.HOSTEL_ROOMS, JSON.stringify(rooms));
        return rooms[idx];
      }
    }
    const newId = rooms.length > 0 ? Math.max(...rooms.map((r) => r.id)) + 1 : 1;
    const newRoom: HostelRoomInfo = {
      id: newId,
      blockId: room.blockId,
      blockName: block?.blockName || 'Residential Block',
      roomNumber: room.roomNumber,
      floorNumber: room.floorNumber || 1,
      roomType: room.roomType || 'Double',
      capacity: room.capacity || 2,
      monthlyFee: room.monthlyFee || 3000.0,
      amenities: room.amenities || 'Attached Bath, Study Table, Wi-Fi',
      status: room.status || 'Available',
    };
    rooms.push(newRoom);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_ROOMS, JSON.stringify(rooms));
    return newRoom;
  },

  deleteHostelRoom(id: number): boolean {
    let rooms = this.getHostelRooms();
    rooms = rooms.filter((r) => r.id !== id);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_ROOMS, JSON.stringify(rooms));
    return true;
  },

  getHostelAllocations(roomId?: number): HostelAllocationInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.HOSTEL_ALLOCATIONS);
    let list: HostelAllocationInfo[] = raw ? JSON.parse(raw) : DEFAULT_HOSTEL_ALLOCATIONS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.HOSTEL_ALLOCATIONS, JSON.stringify(DEFAULT_HOSTEL_ALLOCATIONS));
    }
    if (roomId) {
      list = list.filter((a) => a.roomId === roomId);
    }
    return list;
  },

  allocateHostelBed(data: {
    roomId: number;
    studentId: number;
    bedNumber: string;
    admissionDate?: string;
    guardianContact?: string;
    emergencyPhone?: string;
    remarks?: string;
  }): { success: boolean; message?: string; allocation?: HostelAllocationInfo } {
    const allocations = this.getHostelAllocations();
    const rooms = this.getHostelRooms();
    const room = rooms.find((r) => r.id === data.roomId);
    if (!room) {
      return { success: false, message: 'Hostel room not found.' };
    }

    // 1. Capacity check
    const activeInRoom = allocations.filter((a) => a.roomId === data.roomId && a.status === 'Active');
    if (activeInRoom.length >= room.capacity) {
      return {
        success: false,
        message: `Room ${room.roomNumber} is at maximum capacity (${room.capacity} beds occupied).`,
      };
    }

    // 2. Duplicate active bed check
    const existing = allocations.find((a) => a.studentId === data.studentId && a.status === 'Active');
    if (existing) {
      return {
        success: false,
        message: `Student already holds an active bed in Room ${existing.roomNumber} (${existing.blockName}).`,
      };
    }

    // 3. Gender check
    const students = this.getStudents();
    const student = students.find((s) => s.id === data.studentId);
    const blocks = this.getHostelBlocks();
    const block = blocks.find((b) => b.id === room.blockId);

    if (student && block && block.genderType !== 'Co-ed') {
      const sGender = (student.gender || '').toLowerCase();
      if (block.genderType === 'Boys' && (sGender === 'female' || sGender === 'girl')) {
        return { success: false, message: 'Gender mismatch: Female student cannot be assigned to Boys Hostel Block.' };
      }
      if (block.genderType === 'Girls' && (sGender === 'male' || sGender === 'boy')) {
        return { success: false, message: 'Gender mismatch: Male student cannot be assigned to Girls Hostel Block.' };
      }
    }

    const newId = allocations.length > 0 ? Math.max(...allocations.map((a) => a.id)) + 1 : 1;
    const newAllocation: HostelAllocationInfo = {
      id: newId,
      roomId: room.id,
      roomNumber: room.roomNumber,
      blockId: room.blockId,
      blockName: block?.blockName || room.blockName,
      studentId: data.studentId,
      studentRegNo: student?.studentId || `STU-${data.studentId}`,
      studentName: student ? `${student.firstName} ${student.lastName}` : 'Resident Student',
      studentGender: student?.gender,
      bedNumber: data.bedNumber || `Bed-${activeInRoom.length + 1}`,
      admissionDate: data.admissionDate || new Date().toISOString().split('T')[0],
      guardianContact: data.guardianContact || student?.emergencyContact || '+880 1700-000000',
      emergencyPhone: data.emergencyPhone || student?.emergencyContact || '+880 1700-000000',
      remarks: data.remarks,
      status: 'Active',
    };

    allocations.unshift(newAllocation);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_ALLOCATIONS, JSON.stringify(allocations));
    return { success: true, allocation: newAllocation };
  },

  vacateHostelBed(allocationId: number, remarks?: string): boolean {
    const allocations = this.getHostelAllocations();
    const idx = allocations.findIndex((a) => a.id === allocationId);
    if (idx === -1) return false;

    allocations[idx].status = 'Vacated';
    allocations[idx].vacateDate = new Date().toISOString().split('T')[0];
    if (remarks) {
      allocations[idx].remarks = `${allocations[idx].remarks || ''} [Vacated: ${remarks}]`.trim();
    }
    localStorage.setItem(STORAGE_KEYS.HOSTEL_ALLOCATIONS, JSON.stringify(allocations));
    return true;
  },

  getHostelGatePasses(): HostelGatePassInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.HOSTEL_GATE_PASSES);
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.HOSTEL_GATE_PASSES, JSON.stringify(DEFAULT_HOSTEL_GATE_PASSES));
      return DEFAULT_HOSTEL_GATE_PASSES;
    }
    return JSON.parse(raw);
  },

  createHostelGatePass(data: {
    allocationId: number;
    purpose: string;
    leaveDate: string;
    expectedReturnDate: string;
    remarks?: string;
  }): { success: boolean; message?: string; gatePass?: HostelGatePassInfo } {
    const passes = this.getHostelGatePasses();
    const allocations = this.getHostelAllocations();
    const alloc = allocations.find((a) => a.id === data.allocationId);
    if (!alloc) {
      return { success: false, message: 'Resident allocation record not found.' };
    }

    const todayStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const passNo = `GP-${todayStr}-${String(passes.length + 1).padStart(4, '0')}`;

    const newPass: HostelGatePassInfo = {
      id: passes.length > 0 ? Math.max(...passes.map((p) => p.id)) + 1 : 1,
      passNumber: passNo,
      allocationId: alloc.id,
      studentName: alloc.studentName,
      studentRegNo: alloc.studentRegNo,
      roomNumber: alloc.roomNumber,
      blockName: alloc.blockName,
      purpose: data.purpose,
      leaveDate: data.leaveDate,
      expectedReturnDate: data.expectedReturnDate,
      wardenApproval: 'Approved',
      status: 'Out',
      remarks: data.remarks,
    };

    passes.unshift(newPass);
    localStorage.setItem(STORAGE_KEYS.HOSTEL_GATE_PASSES, JSON.stringify(passes));
    return { success: true, gatePass: newPass };
  },

  returnHostelGatePass(gatePassId: number): boolean {
    const passes = this.getHostelGatePasses();
    const idx = passes.findIndex((p) => p.id === gatePassId);
    if (idx === -1) return false;

    const todayStr = new Date().toISOString().split('T')[0];
    passes[idx].actualReturnDate = todayStr;
    if (todayStr > passes[idx].expectedReturnDate) {
      passes[idx].status = 'Overstayed';
    } else {
      passes[idx].status = 'Returned';
    }
    localStorage.setItem(STORAGE_KEYS.HOSTEL_GATE_PASSES, JSON.stringify(passes));
    return true;
  },

  getHostelStats(): HostelStatsInfo {
    const blocks = this.getHostelBlocks();
    const rooms = this.getHostelRooms();
    const allocations = this.getHostelAllocations();
    const gatePasses = this.getHostelGatePasses();

    const totalBlocks = blocks.length;
    const totalRooms = rooms.length;
    const totalCapacity = rooms.reduce((acc, r) => acc + r.capacity, 0);
    const activeAllocations = allocations.filter((a) => a.status === 'Active');
    const occupiedBeds = activeAllocations.length;
    const availableBeds = Math.max(0, totalCapacity - occupiedBeds);
    const occupancyRate = totalCapacity > 0 ? Math.round((occupiedBeds / totalCapacity) * 100) : 0;
    const boardersOut = gatePasses.filter((g) => g.status === 'Out' || g.status === 'Overstayed').length;
    const presentInHostel = Math.max(0, occupiedBeds - boardersOut);

    return {
      totalBlocks,
      totalRooms,
      totalCapacity,
      occupiedBeds,
      availableBeds,
      occupancyRate,
      boardersOut,
      presentInHostel,
    };
  },

  // ==================== PHASE 13: NOTICES & EVENTS ====================
  getNotices(audience?: string, category?: string, status?: string): SchoolNoticeInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.NOTICES);
    let list: SchoolNoticeInfo[] = raw ? JSON.parse(raw) : DEFAULT_NOTICES;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.NOTICES, JSON.stringify(DEFAULT_NOTICES));
    }
    if (audience && audience !== 'All') {
      list = list.filter((n) => n.targetAudience === audience || n.targetAudience === 'All');
    }
    if (category && category !== 'All') {
      list = list.filter((n) => n.category === category);
    }
    if (status) {
      list = list.filter((n) => n.status === status);
    }

    // Sort: Pinned first, then publish date descending
    return list.sort((a, b) => {
      if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
      return new Date(b.publishDate).getTime() - new Date(a.publishDate).getTime();
    });
  },

  saveNotice(notice: Partial<SchoolNoticeInfo> & { title: string; content: string }): SchoolNoticeInfo {
    const list = this.getNotices();
    if (notice.id) {
      const idx = list.findIndex((n) => n.id === notice.id);
      if (idx !== -1) {
        list[idx] = { ...list[idx], ...notice } as SchoolNoticeInfo;
        localStorage.setItem(STORAGE_KEYS.NOTICES, JSON.stringify(list));
        return list[idx];
      }
    }

    const year = new Date().getFullYear();
    const count = list.length + 1;
    const refNo = `CIR-${year}/${String(count).padStart(3, '0')}`;
    const newId = list.length > 0 ? Math.max(...list.map((n) => n.id)) + 1 : 1;

    const newNotice: SchoolNoticeInfo = {
      id: newId,
      referenceNo: notice.referenceNo || refNo,
      title: notice.title,
      category: notice.category || 'Academic',
      targetAudience: notice.targetAudience || 'All',
      targetClassId: notice.targetClassId,
      priority: notice.priority || 'Normal',
      isPinned: notice.isPinned ?? (notice.priority === 'Urgent'),
      publishDate: notice.publishDate || new Date().toISOString().split('T')[0],
      expiryDate: notice.expiryDate,
      content: notice.content,
      attachmentName: notice.attachmentName,
      status: notice.status || 'Published',
      createdBy: notice.createdBy || 'Principal Office',
    };

    list.unshift(newNotice);
    localStorage.setItem(STORAGE_KEYS.NOTICES, JSON.stringify(list));
    return newNotice;
  },

  deleteNotice(id: number): boolean {
    let list = this.getNotices();
    list = list.filter((n) => n.id !== id);
    localStorage.setItem(STORAGE_KEYS.NOTICES, JSON.stringify(list));
    return true;
  },

  getEvents(category?: string): SchoolEventInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.EVENTS);
    let list: SchoolEventInfo[] = raw ? JSON.parse(raw) : DEFAULT_EVENTS;
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.EVENTS, JSON.stringify(DEFAULT_EVENTS));
    }
    if (category && category !== 'All') {
      list = list.filter((e) => e.eventCategory === category);
    }
    // Sort chronologically
    return list.sort((a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime());
  },

  saveEvent(event: Partial<SchoolEventInfo> & { eventTitle: string; startDate: string; endDate: string }): SchoolEventInfo {
    const list = this.getEvents();
    if (event.id) {
      const idx = list.findIndex((e) => e.id === event.id);
      if (idx !== -1) {
        list[idx] = { ...list[idx], ...event } as SchoolEventInfo;
        localStorage.setItem(STORAGE_KEYS.EVENTS, JSON.stringify(list));
        return list[idx];
      }
    }

    const newId = list.length > 0 ? Math.max(...list.map((e) => e.id)) + 1 : 1;
    let color = event.colorCode;
    if (!color) {
      if (event.isHoliday || event.eventCategory === 'Holiday') color = '#DC2626';
      else if (event.eventCategory === 'Exam') color = '#D97706';
      else if (event.eventCategory === 'Sports') color = '#2563EB';
      else if (event.eventCategory === 'Cultural') color = '#7C3AED';
      else color = '#059669';
    }

    const newEvent: SchoolEventInfo = {
      id: newId,
      eventTitle: event.eventTitle,
      eventCategory: event.eventCategory || 'Academic',
      startDate: event.startDate,
      endDate: event.endDate,
      startTime: event.startTime,
      endTime: event.endTime,
      venue: event.venue || 'Campus Main Auditorium',
      targetAudience: event.targetAudience || 'All',
      isHoliday: event.isHoliday ?? (event.eventCategory === 'Holiday'),
      colorCode: color,
      description: event.description,
      organizer: event.organizer || 'School Administration',
    };

    list.push(newEvent);
    localStorage.setItem(STORAGE_KEYS.EVENTS, JSON.stringify(list));
    return newEvent;
  },

  deleteEvent(id: number): boolean {
    let list = this.getEvents();
    list = list.filter((e) => e.id !== id);
    localStorage.setItem(STORAGE_KEYS.EVENTS, JSON.stringify(list));
    return true;
  },

  isDateHoliday(dateStr: string): boolean {
    const events = this.getEvents();
    const target = new Date(dateStr).getTime();
    return events.some((e) => {
      if (!e.isHoliday) return false;
      const s = new Date(e.startDate).getTime();
      const end = new Date(e.endDate).getTime();
      return target >= s && target <= end;
    });
  },

  getNoticeStats(): NoticeStatsInfo {
    const notices = this.getNotices();
    const events = this.getEvents();
    const todayStr = new Date().toISOString().split('T')[0];

    const totalNotices = notices.length;
    const publishedNotices = notices.filter((n) => n.status === 'Published').length;
    const urgentAlerts = notices.filter((n) => n.priority === 'Urgent' && n.status === 'Published').length;
    const upcomingEvents = events.filter((e) => e.endDate >= todayStr).length;
    const totalHolidays = events.filter((e) => e.isHoliday).length;

    return {
      totalNotices,
      publishedNotices,
      urgentAlerts,
      upcomingEvents,
      totalHolidays,
    };
  },

  // ==========================================
  // Phase 14: Comprehensive Reports & Analytics
  // ==========================================
  getComprehensiveReportAnalytics(classIdFilter?: number): ComprehensiveReportAnalytics {
    const students = this.getStudents();
    const teachers = this.getTeachers();
    const staff = this.getStaff();
    const invoices = this.getStudentFeeInvoices();
    const financial = this.getFinancialSummary();
    const attendances = this.getStudentAttendances();
    const examTerms = this.getExamTerms();
    const examResults = this.getExamResultSummaries();
    const libStats = this.getLibraryStats();
    const transportStats = this.getTransportStats();
    const hostelStats = this.getHostelStats();

    const activeStudents = students.filter((s) => s.status === 'active').length;
    const maleStudents = students.filter((s) => s.gender === 'Male').length;
    const femaleStudents = students.filter((s) => s.gender === 'Female').length;

    const totalStaff = teachers.length + staff.length;
    const activeStaff =
      teachers.filter((t) => t.status === 'active').length +
      staff.filter((st) => st.status === 'active').length;
    const teachingStaff = teachers.length;

    const totalInvoiced = invoices.reduce((sum, inv) => sum + (inv.netAmount || inv.totalAmount || 0), 0);
    const totalCollected = invoices.reduce((sum, inv) => sum + (inv.paidAmount || 0), 0);
    const totalDues = invoices.reduce((sum, inv) => sum + (inv.dueAmount || 0), 0);
    const collectionEfficiency = totalInvoiced > 0 ? Number(((totalCollected / totalInvoiced) * 100).toFixed(2)) : 0;

    const todayMs = new Date().setHours(0, 0, 0, 0);
    const defaultersList: FeeDefaulterRecord[] = invoices
      .filter((inv) => {
        if ((inv.dueAmount || 0) <= 0) return false;
        if (classIdFilter && inv.classId !== classIdFilter) return false;
        return true;
      })
      .map((inv) => {
        const studentObj = students.find((s) => s.id === inv.studentId);
        const dueMs = inv.dueDate ? new Date(inv.dueDate).getTime() : todayMs;
        const diffDays = dueMs < todayMs ? Math.floor((todayMs - dueMs) / (1000 * 60 * 60 * 24)) : 0;
        return {
          invoiceId: inv.id,
          invoiceNumber: `INV-${String(inv.id).padStart(4, '0')}`,
          studentId: inv.studentId,
          studentName: inv.studentName,
          admissionNumber: inv.studentCode,
          classSection: `${inv.className}${inv.sectionName ? ` - ${inv.sectionName}` : ''}`,
          guardianPhone: studentObj?.guardian?.guardianPhone || '+880 1700-000000',
          title: inv.feeTitle,
          totalAmount: inv.netAmount || inv.totalAmount,
          paidAmount: inv.paidAmount,
          dueAmount: inv.dueAmount,
          dueDate: inv.dueDate,
          daysOverdue: Math.max(0, diffDays),
          status: inv.status,
        };
      })
      .sort((a, b) => b.daysOverdue - a.daysOverdue);

    const totalAtt = attendances.length;
    const presentAtt = attendances.filter((a) => a.status === 'Present').length;
    const attendanceRate = totalAtt > 0 ? Number(((presentAtt / totalAtt) * 100).toFixed(2)) : 92.5;

    const classStatsMap: Record<string, { total: number; present: number; absent: number; late: number }> = {};
    students.forEach((st) => {
      const clsName = st.className || 'Unassigned';
      if (!classStatsMap[clsName]) {
        classStatsMap[clsName] = { total: 0, present: 0, absent: 0, late: 0 };
      }
      const stRecords = attendances.filter((a) => a.studentId === st.id);
      stRecords.forEach((r) => {
        classStatsMap[clsName].total += 1;
        if (r.status === 'Present') classStatsMap[clsName].present += 1;
        else if (r.status === 'Absent') classStatsMap[clsName].absent += 1;
        else if (r.status === 'Late') classStatsMap[clsName].late += 1;
      });
    });

    const classAttendanceList: ClassAttendanceAuditItem[] = Object.entries(classStatsMap).map(([className, c]) => ({
      className,
      totalRecords: c.total,
      presentCount: c.present,
      absentCount: c.absent,
      lateCount: c.late,
      attendancePercentage: c.total > 0 ? Number(((c.present / c.total) * 100).toFixed(2)) : 91.5,
    }));

    const totalAssessed = examResults.length;
    const passedCount = examResults.filter((r) => r.passedAll).length;
    const passRate = totalAssessed > 0 ? Number(((passedCount / totalAssessed) * 100).toFixed(2)) : 95.0;
    const avgGpa =
      totalAssessed > 0
        ? Number((examResults.reduce((s, r) => s + (r.gpa || 0), 0) / totalAssessed).toFixed(2))
        : 3.92;

    return {
      totalStudents: students.length,
      activeStudents,
      maleStudents,
      femaleStudents,
      totalStaff,
      activeStaff,
      teachingStaff,
      totalInvoiced,
      totalCollected,
      totalDues,
      collectionEfficiency,
      defaultersCount: defaultersList.length,
      totalIncome: financial.totalIncome,
      totalExpenses: financial.totalExpense,
      netSurplus: financial.netSurplus,
      attendanceRate,
      examTermsCount: examTerms.length,
      totalAssessed,
      passRate,
      avgGpa,
      totalBooks: libStats.totalTitles,
      activeLoans: libStats.currentlyIssued,
      totalRoutes: transportStats.totalRoutes,
      transportPassengers: transportStats.allocatedPassengers,
      hostelCapacity: hostelStats.totalCapacity,
      hostelOccupancy: hostelStats.occupiedBeds,
      hostelOccupancyRate: hostelStats.occupancyRate,
      classAttendanceList,
      defaultersList,
    };
  },

  generateCsvExport(
    reportType: 'defaulters' | 'demographics' | 'attendance' | 'financial',
    classIdFilter?: number
  ): { filename: string; csvContent: string } {
    const dateStamp = new Date().toISOString().split('T')[0];
    const esc = (val: unknown) => `"${String(val ?? '').replace(/"/g, '""')}"`;

    if (reportType === 'defaulters') {
      const analytics = this.getComprehensiveReportAnalytics(classIdFilter);
      const headers = [
        'Invoice No',
        'Admission No',
        'Student Name',
        'Class & Section',
        'Fee Description',
        'Billed (BDT)',
        'Paid (BDT)',
        'Due (BDT)',
        'Due Date',
        'Days Overdue',
        'Status',
        'Guardian Contact',
      ];
      const rows = analytics.defaultersList.map((d) =>
        [
          d.invoiceNumber,
          d.admissionNumber,
          d.studentName,
          d.classSection,
          d.title,
          d.totalAmount.toFixed(2),
          d.paidAmount.toFixed(2),
          d.dueAmount.toFixed(2),
          d.dueDate,
          d.daysOverdue,
          d.status,
          d.guardianPhone,
        ]
          .map(esc)
          .join(',')
      );
      return {
        filename: `EduManage_Fee_Defaulters_${dateStamp}.csv`,
        csvContent: [headers.map(esc).join(','), ...rows].join('\n'),
      };
    }

    if (reportType === 'demographics') {
      const classes = this.getDetailedClasses();
      const targetClassName = classIdFilter ? classes.find((c) => c.id === classIdFilter)?.name : undefined;
      const students = this.getStudents().filter((s) => !targetClassName || s.className === targetClassName);
      const headers = [
        'Student ID',
        'Admission No',
        'Full Name',
        'Class',
        'Section',
        'Roll',
        'Gender',
        'Date of Birth',
        'Blood Group',
        'Guardian Name',
        'Guardian Phone',
        'Status',
      ];
      const rows = students.map((s) =>
        [
          s.studentId,
          s.admissionNumber,
          s.fullName,
          s.className,
          s.sectionName || '',
          s.rollNumber,
          s.gender,
          s.dateOfBirth,
          s.bloodGroup || '',
          s.guardian?.guardianName || '',
          s.guardian?.guardianPhone || '',
          s.status,
        ]
          .map(esc)
          .join(',')
      );
      return {
        filename: `EduManage_Student_Roster_${dateStamp}.csv`,
        csvContent: [headers.map(esc).join(','), ...rows].join('\n'),
      };
    }

    if (reportType === 'attendance') {
      const analytics = this.getComprehensiveReportAnalytics();
      const headers = ['Class / Grade', 'Total Sessions', 'Present', 'Absent', 'Late', 'Attendance Rate (%)'];
      const rows = analytics.classAttendanceList.map((c) =>
        [c.className, c.totalRecords, c.presentCount, c.absentCount, c.lateCount, `${c.attendancePercentage}%`]
          .map(esc)
          .join(',')
      );
      return {
        filename: `EduManage_Attendance_Compliance_${dateStamp}.csv`,
        csvContent: [headers.map(esc).join(','), ...rows].join('\n'),
      };
    }

    // financial
    const txs = this.getAccountTransactions();
    const headers = ['Voucher No', 'Date', 'Type', 'Category', 'Party / Description', 'Amount (BDT)', 'Payment Mode', 'Status'];
    const rows = txs.map((t) =>
      [t.voucherNo, t.transactionDate, t.type, t.categoryName, t.description || t.paidToReceivedFrom, t.amount.toFixed(2), t.paymentMethod, t.status]
        .map(esc)
        .join(',')
    );
    return {
      filename: `EduManage_Financial_Ledger_${dateStamp}.csv`,
      csvContent: [headers.map(esc).join(','), ...rows].join('\n'),
    };
  },

  // ==========================================
  // Phase 15: Certificate & Official Credentials
  // ==========================================
  getCertificates(typeFilter?: string, statusFilter?: string): CertificateRecordInfo[] {
    const raw = localStorage.getItem(STORAGE_KEYS.CERTIFICATES);
    let list: CertificateRecordInfo[];
    if (!raw) {
      localStorage.setItem(STORAGE_KEYS.CERTIFICATES, JSON.stringify(DEFAULT_CERTIFICATES));
      list = DEFAULT_CERTIFICATES;
    } else {
      list = JSON.parse(raw);
    }
    return list
      .filter((c) => {
        if (typeFilter && typeFilter !== 'All' && c.certificateType !== typeFilter) return false;
        if (statusFilter && statusFilter !== 'All' && c.status !== statusFilter) return false;
        return true;
      })
      .sort((a, b) => b.id - a.id);
  },

  saveCertificates(list: CertificateRecordInfo[]): void {
    localStorage.setItem(STORAGE_KEYS.CERTIFICATES, JSON.stringify(list));
  },

  issueCertificate(payload: {
    certificateType: CertificateType;
    recipientType: 'Student' | 'Teacher' | 'Staff';
    studentId?: number;
    staffOrTeacherId?: number;
    recipientName: string;
    recipientCode: string;
    classOrDesignation: string;
    fatherOrGuardian: string;
    leavingDate?: string;
    conductGrade: string;
    reasonOrPurpose: string;
    remarks?: string;
    markStudentTransferred?: boolean;
  }): CertificateRecordInfo {
    const existing = this.getCertificates();
    const prefixMap: Record<CertificateType, string> = {
      'Transfer Certificate': 'TC',
      'Character Certificate': 'CC',
      Testimonial: 'TM',
      'Bonafide Certificate': 'BF',
      'Merit Certificate': 'MR',
      'Staff Experience Letter': 'EX',
    };
    const prefix = prefixMap[payload.certificateType] || 'CT';
    const year = new Date().getFullYear();
    const seq = existing.filter((c) => c.certificateType === payload.certificateType).length + 1;
    const certificateNumber = `CERT-${prefix}-${year}-${String(seq).padStart(4, '0')}`;
    const verificationCode = `VER-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;

    const newRecord: CertificateRecordInfo = {
      id: Date.now(),
      certificateNumber,
      verificationCode,
      certificateType: payload.certificateType,
      recipientType: payload.recipientType,
      studentId: payload.studentId,
      staffOrTeacherId: payload.staffOrTeacherId,
      recipientName: payload.recipientName,
      recipientCode: payload.recipientCode,
      classOrDesignation: payload.classOrDesignation,
      fatherOrGuardian: payload.fatherOrGuardian,
      issueDate: new Date().toISOString().split('T')[0],
      leavingDate: payload.leavingDate,
      conductGrade: payload.conductGrade,
      reasonOrPurpose: payload.reasonOrPurpose,
      remarks: payload.remarks,
      status: 'Issued',
      issuedBy: this.getCurrentUser()?.fullName || 'Principal Office',
    };

    this.saveCertificates([newRecord, ...existing]);

    if (
      payload.certificateType === 'Transfer Certificate' &&
      payload.markStudentTransferred &&
      payload.studentId
    ) {
      this.updateStudent(payload.studentId, { status: 'transferred' });
    }

    this.addActivityLog({
      username: this.getCurrentUser()?.username || 'admin',
      action: 'CERTIFICATE_ISSUED',
      module: 'CERTIFICATES',
      description: `Issued ${payload.certificateType} (${certificateNumber}) to ${payload.recipientName}`,
      severity: 'INFO',
    });

    return newRecord;
  },

  revokeCertificate(certId: number, reason: string = 'Revoked by Administration'): CertificateRecordInfo | null {
    const existing = this.getCertificates();
    const target = existing.find((c) => c.id === certId);
    if (!target) return null;
    const updated = existing.map((c) =>
      c.id === certId
        ? {
            ...c,
            status: 'Revoked' as const,
            remarks: `[REVOKED: ${reason}] ${c.remarks || ''}`.trim(),
          }
        : c
    );
    this.saveCertificates(updated);
    this.addActivityLog({
      username: this.getCurrentUser()?.username || 'admin',
      action: 'CERTIFICATE_REVOKED',
      module: 'CERTIFICATES',
      description: `Revoked credential ${target.certificateNumber} (${target.recipientName})`,
      severity: 'WARNING',
    });
    return updated.find((c) => c.id === certId) || null;
  },

  verifyCertificate(tokenOrSerial: string): CertificateRecordInfo | null {
    const clean = tokenOrSerial.trim().toUpperCase();
    if (!clean) return null;
    const all = this.getCertificates();
    return (
      all.find(
        (c) =>
          c.certificateNumber.toUpperCase() === clean ||
          c.verificationCode.toUpperCase() === clean
      ) || null
    );
  },

  getCertificateStats(): CertificateStatsInfo {
    const all = this.getCertificates();
    const issued = all.filter((c) => c.status === 'Issued');
    const revoked = all.filter((c) => c.status === 'Revoked');
    return {
      total: all.length,
      issued: issued.length,
      revoked: revoked.length,
      transferCertificates: issued.filter((c) => c.certificateType === 'Transfer Certificate').length,
      meritAndTestimonials: issued.filter(
        (c) => c.certificateType === 'Merit Certificate' || c.certificateType === 'Testimonial'
      ).length,
    };
  },
};

const DEFAULT_FEE_CATEGORIES: FeeCategoryInfo[] = [
  { id: 1, name: 'Tuition Fee', code: 'TUI', description: 'Regular monthly academic tuition', isRecurring: true, frequency: 'Monthly', isActive: true },
  { id: 2, name: 'Admission & Session Fee', code: 'ADM', description: 'Annual session registration and admission', isRecurring: false, frequency: 'One-Time', isActive: true },
  { id: 3, name: 'Examination Fee', code: 'EXM', description: 'Term exams, board registration, and test papers', isRecurring: true, frequency: 'Quarterly', isActive: true },
  { id: 4, name: 'ICT & Computer Lab Fee', code: 'ICT', description: 'Computer lab hardware and broadband internet maintenance', isRecurring: true, frequency: 'Monthly', isActive: true },
  { id: 5, name: 'Library & Reading Club Fee', code: 'LIB', description: 'Book acquisitions, library cards, and journals', isRecurring: false, frequency: 'Yearly', isActive: true },
  { id: 6, name: 'Transport & Bus Service', code: 'TRN', description: 'School bus pick-and-drop transportation', isRecurring: true, frequency: 'Monthly', isActive: true },
  { id: 7, name: 'Hostel & Mess Charges', code: 'HST', description: 'Dormitory accommodation and meal plans', isRecurring: true, frequency: 'Monthly', isActive: true },
  { id: 8, name: 'School Development Fee', code: 'DEV', description: 'Campus infrastructure and science laboratory renovation', isRecurring: false, frequency: 'Yearly', isActive: true },
];

const DEFAULT_FEE_STRUCTURES: FeeStructureInfo[] = [
  {
    id: 1,
    categoryId: 1,
    categoryName: 'Tuition Fee',
    classId: 4,
    className: 'Class 9',
    academicYearId: 1,
    academicYearName: '2025-2026',
    title: 'Class 9 - Monthly Tuition Fee (March 2025)',
    amount: 2500,
    dueDate: '2025-03-15',
    assignedCount: 4,
    createdAt: '2025-03-01',
  },
  {
    id: 2,
    categoryId: 1,
    categoryName: 'Tuition Fee',
    classId: 5,
    className: 'Class 10',
    academicYearId: 1,
    academicYearName: '2025-2026',
    title: 'Class 10 - Monthly Tuition Fee (March 2025)',
    amount: 2800,
    dueDate: '2025-03-15',
    assignedCount: 4,
    createdAt: '2025-03-01',
  },
  {
    id: 3,
    categoryId: 3,
    categoryName: 'Examination Fee',
    classId: 5,
    className: 'Class 10',
    academicYearId: 1,
    academicYearName: '2025-2026',
    title: 'SSC Pre-Test & Model Examination 2025',
    amount: 1500,
    dueDate: '2025-03-25',
    assignedCount: 4,
    createdAt: '2025-03-05',
  },
  {
    id: 4,
    categoryId: 4,
    categoryName: 'ICT & Computer Lab Fee',
    classId: 4,
    className: 'Class 9',
    academicYearId: 1,
    academicYearName: '2025-2026',
    title: 'Class 9 - Practical ICT Lab & Coding Club (Q1)',
    amount: 600,
    dueDate: '2025-03-20',
    assignedCount: 4,
    createdAt: '2025-03-01',
  },
];

const DEFAULT_STUDENT_FEES: StudentFeeInvoice[] = [
  {
    id: 1,
    studentId: 1,
    studentCode: 'STU-2024-0001',
    studentName: 'Ahsan Habib',
    rollNumber: 1,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Section A (Jamuna)',
    feeStructureId: 2,
    feeTitle: 'Class 10 - Monthly Tuition Fee (March 2025)',
    categoryName: 'Tuition Fee',
    totalAmount: 2800,
    discountAmount: 0,
    netAmount: 2800,
    paidAmount: 2800,
    dueAmount: 0,
    dueDate: '2025-03-15',
    status: 'Paid',
    createdAt: '2025-03-01',
    payments: [
      {
        id: 1,
        studentFeeId: 1,
        receiptNumber: 'REC-2025-00101',
        amount: 2800,
        discountAmount: 0,
        paymentMethod: 'bKash',
        transactionRef: 'BK9948271A',
        paymentDate: '2025-03-05',
        receivedBy: 'Shafiqul Alam (Accounts)',
        notes: 'bKash Merchant Pay',
      },
    ],
  },
  {
    id: 2,
    studentId: 2,
    studentCode: 'STU-2024-0002',
    studentName: 'Tasnim Sultana',
    rollNumber: 2,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Section A (Jamuna)',
    feeStructureId: 2,
    feeTitle: 'Class 10 - Monthly Tuition Fee (March 2025)',
    categoryName: 'Tuition Fee',
    totalAmount: 2800,
    discountAmount: 500,
    netAmount: 2300,
    paidAmount: 2300,
    dueAmount: 0,
    dueDate: '2025-03-15',
    status: 'Paid',
    createdAt: '2025-03-01',
    payments: [
      {
        id: 2,
        studentFeeId: 2,
        receiptNumber: 'REC-2025-00102',
        amount: 2300,
        discountAmount: 500,
        paymentMethod: 'Bank Transfer',
        transactionRef: 'IBBL-7740192',
        paymentDate: '2025-03-06',
        receivedBy: 'Shafiqul Alam (Accounts)',
        notes: 'Merit scholarship waiver ৳ 500 applied',
      },
    ],
  },
  {
    id: 3,
    studentId: 3,
    studentCode: 'STU-2024-0003',
    studentName: 'Tanvir Ahmed',
    rollNumber: 3,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Section A (Jamuna)',
    feeStructureId: 2,
    feeTitle: 'Class 10 - Monthly Tuition Fee (March 2025)',
    categoryName: 'Tuition Fee',
    totalAmount: 2800,
    discountAmount: 0,
    netAmount: 2800,
    paidAmount: 1500,
    dueAmount: 1300,
    dueDate: '2025-03-15',
    status: 'Partial',
    createdAt: '2025-03-01',
    payments: [
      {
        id: 3,
        studentFeeId: 3,
        receiptNumber: 'REC-2025-00103',
        amount: 1500,
        discountAmount: 0,
        paymentMethod: 'Cash',
        paymentDate: '2025-03-07',
        receivedBy: 'Tania Akter (Front Desk)',
        notes: '1st installment paid; remaining due on 20th',
      },
    ],
  },
  {
    id: 4,
    studentId: 4,
    studentCode: 'STU-2024-0004',
    studentName: 'Naimur Rahman',
    rollNumber: 1,
    classId: 4,
    className: 'Class 9',
    sectionName: 'Section A (Padma)',
    feeStructureId: 1,
    feeTitle: 'Class 9 - Monthly Tuition Fee (March 2025)',
    categoryName: 'Tuition Fee',
    totalAmount: 2500,
    discountAmount: 0,
    netAmount: 2500,
    paidAmount: 0,
    dueAmount: 2500,
    dueDate: '2025-03-15',
    status: 'Unpaid',
    createdAt: '2025-03-01',
    payments: [],
  },
  {
    id: 5,
    studentId: 5,
    studentCode: 'STU-2024-0005',
    studentName: 'Sadia Islam',
    rollNumber: 2,
    classId: 4,
    className: 'Class 9',
    sectionName: 'Section A (Padma)',
    feeStructureId: 1,
    feeTitle: 'Class 9 - Monthly Tuition Fee (March 2025)',
    categoryName: 'Tuition Fee',
    totalAmount: 2500,
    discountAmount: 300,
    netAmount: 2200,
    paidAmount: 2200,
    dueAmount: 0,
    dueDate: '2025-03-15',
    status: 'Paid',
    createdAt: '2025-03-01',
    payments: [
      {
        id: 4,
        studentFeeId: 5,
        receiptNumber: 'REC-2025-00104',
        amount: 2200,
        discountAmount: 300,
        paymentMethod: 'Nagad',
        transactionRef: 'NGD3821092',
        paymentDate: '2025-03-08',
        receivedBy: 'Shafiqul Alam (Accounts)',
        notes: 'Sibling discount ৳ 300 applied',
      },
    ],
  },
  {
    id: 6,
    studentId: 1,
    studentCode: 'STU-2024-0001',
    studentName: 'Ahsan Habib',
    rollNumber: 1,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Section A (Jamuna)',
    feeStructureId: 3,
    feeTitle: 'SSC Pre-Test & Model Examination 2025',
    categoryName: 'Examination Fee',
    totalAmount: 1500,
    discountAmount: 0,
    netAmount: 1500,
    paidAmount: 0,
    dueAmount: 1500,
    dueDate: '2025-03-25',
    status: 'Unpaid',
    createdAt: '2025-03-05',
    payments: [],
  },
];

const DEFAULT_ACCOUNT_CATEGORIES: AccountCategoryInfo[] = [
  { id: 1, name: 'Student Fees & Tuition', code: 'INC-FEES', type: 'Income', description: 'Student regular tuition and session fees', isSystem: true, isActive: true },
  { id: 2, name: 'Government & Board Grants', code: 'INC-GRNT', type: 'Income', description: 'Government education subsidies & stipends', isSystem: true, isActive: true },
  { id: 3, name: 'Philanthropic Donations & Endowments', code: 'INC-DONT', type: 'Income', description: 'Trustee gifts, patron contributions, and alumni endowment', isSystem: false, isActive: true },
  { id: 4, name: 'Facilities & Hall Rentals', code: 'INC-RENT', type: 'Income', description: 'Auditorium and playground event rental revenues', isSystem: false, isActive: true },
  { id: 5, name: 'Other School Incomes', code: 'INC-MISC', type: 'Income', description: 'Syllabus sales, ID replacements, and sundry receipts', isSystem: false, isActive: true },
  { id: 6, name: 'Teacher Salaries & Honorarium', code: 'EXP-TSAL', type: 'Expense', description: 'Monthly payroll for academic faculty', isSystem: true, isActive: true },
  { id: 7, name: 'Staff Salaries & Allowances', code: 'EXP-SSAL', type: 'Expense', description: 'Payroll for non-teaching administrative and support staff', isSystem: true, isActive: true },
  { id: 8, name: 'Electricity & Water Utilities', code: 'EXP-UTIL', type: 'Expense', description: 'DESCO electricity and municipal utilities', isSystem: true, isActive: true },
  { id: 9, name: 'Internet, IT & Software', code: 'EXP-IT', type: 'Expense', description: 'Broadband internet, domains, and IT lab maintenance', isSystem: false, isActive: true },
  { id: 10, name: 'Campus Building & Maintenance', code: 'EXP-MAINT', type: 'Expense', description: 'Facility maintenance, whitewash, and repairs', isSystem: false, isActive: true },
  { id: 11, name: 'Office Supplies & Stationery', code: 'EXP-STAT', type: 'Expense', description: 'Printing papers, toner, registers, and office stationery', isSystem: false, isActive: true },
  { id: 12, name: 'Sports, Cultural & Annual Events', code: 'EXP-EVNT', type: 'Expense', description: 'Annual sports day, debate competitions, and awards', isSystem: false, isActive: true },
  { id: 13, name: 'Exam Papers & Printing Logistics', code: 'EXP-EXAM', type: 'Expense', description: 'Test papers, answer booklets, and invigilation', isSystem: false, isActive: true },
  { id: 14, name: 'General Miscellaneous Expenses', code: 'EXP-MISC', type: 'Expense', description: 'Refreshments, postages, and minor contingencies', isSystem: false, isActive: true },
];

const DEFAULT_ACCOUNT_TRANSACTIONS: AccountTransactionRecord[] = [
  {
    id: 1,
    voucherNo: 'VCH-2026-INC-00001',
    transactionDate: '2026-03-01',
    type: 'Income',
    categoryId: 1,
    categoryName: 'Student Fees & Tuition',
    categoryCode: 'INC-FEES',
    amount: 72500,
    paymentMethod: 'Bank Transfer',
    referenceNo: 'IBBL-CR-99201',
    paidToReceivedFrom: 'Accounts Collection Counter Batch #1',
    description: 'Consolidated Class 9 & 10 tuition fees deposit',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 2,
    voucherNo: 'VCH-2026-INC-00002',
    transactionDate: '2026-03-02',
    type: 'Income',
    categoryId: 2,
    categoryName: 'Government & Board Grants',
    categoryCode: 'INC-GRNT',
    amount: 50000,
    paymentMethod: 'Bank Transfer',
    referenceNo: 'BB-EFT-40019',
    paidToReceivedFrom: 'Directorate of Secondary Education (DSHE)',
    description: 'Annual secondary school laboratory development grant tranche',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 3,
    voucherNo: 'VCH-2026-INC-00003',
    transactionDate: '2026-03-04',
    type: 'Income',
    categoryId: 3,
    categoryName: 'Philanthropic Donations & Endowments',
    categoryCode: 'INC-DONT',
    amount: 30000,
    paymentMethod: 'Cheque',
    referenceNo: 'CHQ-DBBL-7712',
    paidToReceivedFrom: 'Al-Haj Latif Welfare Foundation',
    description: 'Scholarship endowment for underprivileged students',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 4,
    voucherNo: 'VCH-2026-EXP-00001',
    transactionDate: '2026-03-05',
    type: 'Expense',
    categoryId: 6,
    categoryName: 'Teacher Salaries & Honorarium',
    categoryCode: 'EXP-TSAL',
    amount: 45000,
    paymentMethod: 'Bank Transfer',
    referenceNo: 'SAL-MAR-1001',
    paidToReceivedFrom: 'Kamal Hossain (Head of Mathematics)',
    description: 'February 2026 monthly salary and allowance transfer',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 5,
    voucherNo: 'VCH-2026-EXP-00002',
    transactionDate: '2026-03-05',
    type: 'Expense',
    categoryId: 7,
    categoryName: 'Staff Salaries & Allowances',
    categoryCode: 'EXP-SSAL',
    amount: 28000,
    paymentMethod: 'Bank Transfer',
    referenceNo: 'SAL-MAR-2002',
    paidToReceivedFrom: 'Farhana Yasmin (Head Librarian)',
    description: 'February 2026 monthly payroll disbursement',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 6,
    voucherNo: 'VCH-2026-EXP-00003',
    transactionDate: '2026-03-06',
    type: 'Expense',
    categoryId: 8,
    categoryName: 'Electricity & Water Utilities',
    categoryCode: 'EXP-UTIL',
    amount: 14250,
    paymentMethod: 'Cash',
    referenceNo: 'DESCO-BILL-88219',
    paidToReceivedFrom: 'Dhaka Electric Supply Company (DESCO)',
    description: 'February 2026 electricity bill for main academic building',
    recordedBy: 'Tania Akter',
    status: 'Approved',
  },
  {
    id: 7,
    voucherNo: 'VCH-2026-EXP-00004',
    transactionDate: '2026-03-07',
    type: 'Expense',
    categoryId: 9,
    categoryName: 'Internet, IT & Software',
    categoryCode: 'EXP-IT',
    amount: 6500,
    paymentMethod: 'bKash',
    referenceNo: 'BK-TRX-55192A',
    paidToReceivedFrom: 'AmberIT Broadband Services Ltd.',
    description: 'Dedicated 100 Mbps optical fiber internet for computer lab',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 8,
    voucherNo: 'VCH-2026-EXP-00005',
    transactionDate: '2026-03-08',
    type: 'Expense',
    categoryId: 11,
    categoryName: 'Office Supplies & Stationery',
    categoryCode: 'EXP-STAT',
    amount: 8400,
    paymentMethod: 'Cash',
    referenceNo: 'CASH-MEMO-4410',
    paidToReceivedFrom: 'Bismillah Stationery Mart',
    description: 'Purchased 20 reams A4 paper, whiteboard markers, official registers',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
  {
    id: 9,
    voucherNo: 'VCH-2026-EXP-00006',
    transactionDate: '2026-03-08',
    type: 'Expense',
    categoryId: 10,
    categoryName: 'Campus Building & Maintenance',
    categoryCode: 'EXP-MAINT',
    amount: 9800,
    paymentMethod: 'Cash',
    referenceNo: 'VOUCHER-MAINT-102',
    paidToReceivedFrom: 'M/S Uttara Electric & Plumbing Works',
    description: 'Repair of 8 classroom ceiling fans and science lab water lines',
    recordedBy: 'Shafiqul Alam',
    status: 'Approved',
  },
];

const DEFAULT_EXAM_TERMS: ExamTermInfo[] = [
  {
    id: 1,
    name: '1st Term Examination 2026',
    examCode: 'EXM-2026-T1',
    academicYearId: 1,
    academicYearName: '2025-2026',
    startDate: '2026-04-10',
    endDate: '2026-04-24',
    status: 'Published',
    description: 'First terminal examination for all classes from Class 1 to 12.',
  },
  {
    id: 2,
    name: 'Mid-Term Examination 2026',
    examCode: 'EXM-2026-MT',
    academicYearId: 1,
    academicYearName: '2025-2026',
    startDate: '2026-08-15',
    endDate: '2026-08-30',
    status: 'In Progress',
    description: 'Mid-term evaluation and model assessment before board exams.',
  },
  {
    id: 3,
    name: 'Annual Final Examination 2026',
    examCode: 'EXM-2026-FN',
    academicYearId: 1,
    academicYearName: '2025-2026',
    startDate: '2026-11-20',
    endDate: '2026-12-05',
    status: 'Scheduled',
    description: 'Session final promotional examination for academic year 2025-2026.',
  },
];

const DEFAULT_GRADING_SCALES: GradingScaleInfo[] = [
  { id: 1, gradeName: 'A+', gradePoint: 5.0, markFrom: 80, markTo: 100, remarks: 'Outstanding' },
  { id: 2, gradeName: 'A', gradePoint: 4.0, markFrom: 70, markTo: 79.99, remarks: 'Excellent' },
  { id: 3, gradeName: 'A-', gradePoint: 3.5, markFrom: 60, markTo: 69.99, remarks: 'Very Good' },
  { id: 4, gradeName: 'B', gradePoint: 3.0, markFrom: 50, markTo: 59.99, remarks: 'Good' },
  { id: 5, gradeName: 'C', gradePoint: 2.0, markFrom: 40, markTo: 49.99, remarks: 'Satisfactory' },
  { id: 6, gradeName: 'D', gradePoint: 1.0, markFrom: 33, markTo: 39.99, remarks: 'Pass' },
  { id: 7, gradeName: 'F', gradePoint: 0.0, markFrom: 0, markTo: 32.99, remarks: 'Fail' },
];

const DEFAULT_EXAM_SCHEDULES: ExamScheduleInfo[] = [
  {
    id: 1,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 1,
    subjectName: 'Bangla 1st Paper',
    subjectCode: 'BAN-101',
    examDate: '2026-04-12',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Room 301',
    fullMarks: 100,
    theoryFull: 70,
    mcqFull: 30,
    practicalFull: 0,
  },
  {
    id: 2,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 2,
    subjectName: 'English 1st Paper',
    subjectCode: 'ENG-107',
    examDate: '2026-04-15',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Room 301',
    fullMarks: 100,
    theoryFull: 100,
    mcqFull: 0,
    practicalFull: 0,
  },
  {
    id: 3,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 3,
    subjectName: 'General Mathematics',
    subjectCode: 'MAT-109',
    examDate: '2026-04-18',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Room 302',
    fullMarks: 100,
    theoryFull: 70,
    mcqFull: 30,
    practicalFull: 0,
  },
  {
    id: 4,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 4,
    subjectName: 'Physics',
    subjectCode: 'PHY-136',
    examDate: '2026-04-20',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Science Lab 1',
    fullMarks: 100,
    theoryFull: 50,
    mcqFull: 25,
    practicalFull: 25,
  },
  {
    id: 5,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 5,
    subjectName: 'Chemistry',
    subjectCode: 'CHE-137',
    examDate: '2026-04-22',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Science Lab 2',
    fullMarks: 100,
    theoryFull: 50,
    mcqFull: 25,
    practicalFull: 25,
  },
  {
    id: 6,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 6,
    subjectName: 'Information & Communication Tech',
    subjectCode: 'ICT-154',
    examDate: '2026-04-24',
    startTime: '10:00 AM',
    endTime: '12:00 PM',
    roomNumber: 'Computer Lab 1',
    fullMarks: 100,
    theoryFull: 50,
    mcqFull: 25,
    practicalFull: 25,
  },
];

const DEFAULT_STUDENT_MARKS: StudentMarkRecord[] = [
  // Student 1 (Tanvir Ahmed, Roll 1, Class 10)
  {
    id: 1,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 1,
    subjectName: 'Bangla 1st Paper',
    subjectCode: 'BAN-101',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 62,
    mcqMarks: 26,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 88,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Splendid essay composition',
  },
  {
    id: 2,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 2,
    subjectName: 'English 1st Paper',
    subjectCode: 'ENG-107',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 85,
    mcqMarks: 0,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 85,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Excellent grammatical precision',
  },
  {
    id: 3,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 3,
    subjectName: 'General Mathematics',
    subjectCode: 'MAT-109',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 65,
    mcqMarks: 28,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 93,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Flawless problem solving',
  },
  {
    id: 4,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 4,
    subjectName: 'Physics',
    subjectCode: 'PHY-136',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 44,
    mcqMarks: 23,
    practicalMarks: 24,
    caMarks: 0,
    totalMarks: 91,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Clear conceptual diagrams',
  },
  {
    id: 5,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 5,
    subjectName: 'Chemistry',
    subjectCode: 'CHE-137',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 42,
    mcqMarks: 22,
    practicalMarks: 23,
    caMarks: 0,
    totalMarks: 87,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Solid titration experiment',
  },
  {
    id: 6,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 6,
    subjectName: 'Information & Communication Tech',
    subjectCode: 'ICT-154',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    theoryMarks: 46,
    mcqMarks: 24,
    practicalMarks: 25,
    caMarks: 0,
    totalMarks: 95,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Distinction in HTML & Algorithms',
  },

  // Student 2 (Nusrat Jahan, Roll 2, Class 10)
  {
    id: 7,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 1,
    subjectName: 'Bangla 1st Paper',
    subjectCode: 'BAN-101',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 58,
    mcqMarks: 24,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 82,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Very neat presentation',
  },
  {
    id: 8,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 2,
    subjectName: 'English 1st Paper',
    subjectCode: 'ENG-107',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 76,
    mcqMarks: 0,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 76,
    isAbsent: false,
    gradeName: 'A',
    gradePoint: 4.0,
    isPassed: true,
    remarks: 'Good vocabulary',
  },
  {
    id: 9,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 3,
    subjectName: 'General Mathematics',
    subjectCode: 'MAT-109',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 60,
    mcqMarks: 25,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 85,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Accurate geometry proofs',
  },
  {
    id: 10,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 4,
    subjectName: 'Physics',
    subjectCode: 'PHY-136',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 38,
    mcqMarks: 20,
    practicalMarks: 22,
    caMarks: 0,
    totalMarks: 80,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Good lab work',
  },
  {
    id: 11,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 5,
    subjectName: 'Chemistry',
    subjectCode: 'CHE-137',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 36,
    mcqMarks: 18,
    practicalMarks: 20,
    caMarks: 0,
    totalMarks: 74,
    isAbsent: false,
    gradeName: 'A',
    gradePoint: 4.0,
    isPassed: true,
    remarks: 'Needs slight organic formula practice',
  },
  {
    id: 12,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 6,
    subjectName: 'Information & Communication Tech',
    subjectCode: 'ICT-154',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    theoryMarks: 42,
    mcqMarks: 22,
    practicalMarks: 24,
    caMarks: 0,
    totalMarks: 88,
    isAbsent: false,
    gradeName: 'A+',
    gradePoint: 5.0,
    isPassed: true,
    remarks: 'Proficient database queries',
  },

  // Student 3 (Farhan Kabir, Roll 3, Class 10)
  {
    id: 13,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 1,
    subjectName: 'Bangla 1st Paper',
    subjectCode: 'BAN-101',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 48,
    mcqMarks: 20,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 68,
    isAbsent: false,
    gradeName: 'A-',
    gradePoint: 3.5,
    isPassed: true,
    remarks: 'Satisfactory handwriting',
  },
  {
    id: 14,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 2,
    subjectName: 'English 1st Paper',
    subjectCode: 'ENG-107',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 64,
    mcqMarks: 0,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 64,
    isAbsent: false,
    gradeName: 'A-',
    gradePoint: 3.5,
    isPassed: true,
    remarks: 'Fair reading comprehension',
  },
  {
    id: 15,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 3,
    subjectName: 'General Mathematics',
    subjectCode: 'MAT-109',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 52,
    mcqMarks: 21,
    practicalMarks: 0,
    caMarks: 0,
    totalMarks: 73,
    isAbsent: false,
    gradeName: 'A',
    gradePoint: 4.0,
    isPassed: true,
    remarks: 'Good algebra calculations',
  },
  {
    id: 16,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 4,
    subjectName: 'Physics',
    subjectCode: 'PHY-136',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 32,
    mcqMarks: 16,
    practicalMarks: 19,
    caMarks: 0,
    totalMarks: 67,
    isAbsent: false,
    gradeName: 'A-',
    gradePoint: 3.5,
    isPassed: true,
    remarks: 'Understands basic principles',
  },
  {
    id: 17,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 5,
    subjectName: 'Chemistry',
    subjectCode: 'CHE-137',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 30,
    mcqMarks: 15,
    practicalMarks: 18,
    caMarks: 0,
    totalMarks: 63,
    isAbsent: false,
    gradeName: 'A-',
    gradePoint: 3.5,
    isPassed: true,
    remarks: 'Periodic table knowledge is good',
  },
  {
    id: 18,
    examTermId: 1,
    classId: 5,
    className: 'Class 10',
    subjectId: 6,
    subjectName: 'Information & Communication Tech',
    subjectCode: 'ICT-154',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    theoryMarks: 34,
    mcqMarks: 18,
    practicalMarks: 20,
    caMarks: 0,
    totalMarks: 72,
    isAbsent: false,
    gradeName: 'A',
    gradePoint: 4.0,
    isPassed: true,
    remarks: 'Active in computer lab classes',
  },
];

const DEFAULT_EXAM_RESULT_SUMMARIES: ExamResultSummaryInfo[] = [
  {
    id: 1,
    examTermId: 1,
    examTermName: '1st Term Examination 2026',
    studentId: 1,
    studentCode: 'STD-2025-001',
    studentName: 'Tanvir Ahmed',
    rollNumber: 1,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Padma',
    totalObtained: 549,
    totalFullMarks: 600,
    percentage: 91.5,
    gpa: 5.0,
    overallGrade: 'A+',
    classRank: 1,
    passedAll: true,
    failedSubjectCount: 0,
    remarks: 'Golden A+ (Outstanding)',
  },
  {
    id: 2,
    examTermId: 1,
    examTermName: '1st Term Examination 2026',
    studentId: 2,
    studentCode: 'STD-2025-002',
    studentName: 'Nusrat Jahan',
    rollNumber: 2,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Padma',
    totalObtained: 475,
    totalFullMarks: 600,
    percentage: 79.17,
    gpa: 4.67,
    overallGrade: 'A',
    classRank: 2,
    passedAll: true,
    failedSubjectCount: 0,
    remarks: 'Passed Successfully with Distinction',
  },
  {
    id: 3,
    examTermId: 1,
    examTermName: '1st Term Examination 2026',
    studentId: 3,
    studentCode: 'STD-2025-003',
    studentName: 'Farhan Kabir',
    rollNumber: 3,
    classId: 5,
    className: 'Class 10',
    sectionName: 'Meghna',
    totalObtained: 407,
    totalFullMarks: 600,
    percentage: 67.83,
    gpa: 3.67,
    overallGrade: 'A-',
    classRank: 3,
    passedAll: true,
    failedSubjectCount: 0,
    remarks: 'Passed Successfully',
  },
];

const DEFAULT_PERIOD_SLOTS: PeriodSlotInfo[] = [
  { id: 1, periodNumber: 0, name: 'Assembly & Homeroom', startTime: '08:30 AM', endTime: '08:45 AM', durationMinutes: 15, isBreak: true, shift: 'Morning' },
  { id: 2, periodNumber: 1, name: '1st Period', startTime: '08:45 AM', endTime: '09:30 AM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 3, periodNumber: 2, name: '2nd Period', startTime: '09:30 AM', endTime: '10:15 AM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 4, periodNumber: 3, name: '3rd Period', startTime: '10:15 AM', endTime: '11:00 AM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 5, periodNumber: 4, name: '4th Period', startTime: '11:00 AM', endTime: '11:45 AM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 6, periodNumber: 99, name: 'Tiffin & Refreshment', startTime: '11:45 AM', endTime: '12:30 PM', durationMinutes: 45, isBreak: true, shift: 'Morning' },
  { id: 7, periodNumber: 5, name: '5th Period', startTime: '12:30 PM', endTime: '01:15 PM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 8, periodNumber: 6, name: '6th Period', startTime: '01:15 PM', endTime: '02:00 PM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
  { id: 9, periodNumber: 7, name: '7th Period', startTime: '02:00 PM', endTime: '02:45 PM', durationMinutes: 45, isBreak: false, shift: 'Morning' },
];

const DEFAULT_TIMETABLE_ENTRIES: TimetableEntryInfo[] = [
  // Class 10 (id: 5, Section: Padma)
  // Sunday
  { id: 1, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 2, periodName: '1st Period', periodTime: '08:45 AM - 09:30 AM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },
  { id: 2, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 3, periodName: '2nd Period', periodTime: '09:30 AM - 10:15 AM', subjectId: 2, subjectName: 'English 1st Paper', subjectCode: 'ENG-107', teacherId: 2, teacherName: 'Nasreen Sultana', roomNumber: 'Room 301' },
  { id: 3, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 4, periodName: '3rd Period', periodTime: '10:15 AM - 11:00 AM', subjectId: 4, subjectName: 'Physics', subjectCode: 'PHY-136', teacherId: 3, teacherName: 'Shahidul Alam', roomNumber: 'Science Lab 1' },
  { id: 4, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 5, periodName: '4th Period', periodTime: '11:00 AM - 11:45 AM', subjectId: 1, subjectName: 'Bangla 1st Paper', subjectCode: 'BAN-101', teacherId: 4, teacherName: 'Farhana Yasmin', roomNumber: 'Room 301' },
  { id: 5, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 7, periodName: '5th Period', periodTime: '12:30 PM - 01:15 PM', subjectId: 5, subjectName: 'Chemistry', subjectCode: 'CHE-137', teacherId: 5, teacherName: 'Kamal Hossain', roomNumber: 'Science Lab 2' },
  { id: 6, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 8, periodName: '6th Period', periodTime: '01:15 PM - 02:00 PM', subjectId: 6, subjectName: 'Information & Communication Tech', subjectCode: 'ICT-154', teacherId: 6, teacherName: 'Anisur Rahman', roomNumber: 'Computer Lab 1' },
  { id: 7, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Sunday', periodSlotId: 9, periodName: '7th Period', periodTime: '02:00 PM - 02:45 PM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },

  // Monday
  { id: 8, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 2, periodName: '1st Period', periodTime: '08:45 AM - 09:30 AM', subjectId: 4, subjectName: 'Physics', subjectCode: 'PHY-136', teacherId: 3, teacherName: 'Shahidul Alam', roomNumber: 'Science Lab 1' },
  { id: 9, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 3, periodName: '2nd Period', periodTime: '09:30 AM - 10:15 AM', subjectId: 5, subjectName: 'Chemistry', subjectCode: 'CHE-137', teacherId: 5, teacherName: 'Kamal Hossain', roomNumber: 'Science Lab 2' },
  { id: 10, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 4, periodName: '3rd Period', periodTime: '10:15 AM - 11:00 AM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },
  { id: 11, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 5, periodName: '4th Period', periodTime: '11:00 AM - 11:45 AM', subjectId: 2, subjectName: 'English 1st Paper', subjectCode: 'ENG-107', teacherId: 2, teacherName: 'Nasreen Sultana', roomNumber: 'Room 301' },
  { id: 12, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 7, periodName: '5th Period', periodTime: '12:30 PM - 01:15 PM', subjectId: 1, subjectName: 'Bangla 1st Paper', subjectCode: 'BAN-101', teacherId: 4, teacherName: 'Farhana Yasmin', roomNumber: 'Room 301' },
  { id: 13, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Monday', periodSlotId: 8, periodName: '6th Period', periodTime: '01:15 PM - 02:00 PM', subjectId: 6, subjectName: 'Information & Communication Tech', subjectCode: 'ICT-154', teacherId: 6, teacherName: 'Anisur Rahman', roomNumber: 'Computer Lab 1' },

  // Tuesday
  { id: 14, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Tuesday', periodSlotId: 2, periodName: '1st Period', periodTime: '08:45 AM - 09:30 AM', subjectId: 2, subjectName: 'English 1st Paper', subjectCode: 'ENG-107', teacherId: 2, teacherName: 'Nasreen Sultana', roomNumber: 'Room 301' },
  { id: 15, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Tuesday', periodSlotId: 3, periodName: '2nd Period', periodTime: '09:30 AM - 10:15 AM', subjectId: 1, subjectName: 'Bangla 1st Paper', subjectCode: 'BAN-101', teacherId: 4, teacherName: 'Farhana Yasmin', roomNumber: 'Room 301' },
  { id: 16, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Tuesday', periodSlotId: 4, periodName: '3rd Period', periodTime: '10:15 AM - 11:00 AM', subjectId: 5, subjectName: 'Chemistry', subjectCode: 'CHE-137', teacherId: 5, teacherName: 'Kamal Hossain', roomNumber: 'Science Lab 2' },
  { id: 17, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Tuesday', periodSlotId: 5, periodName: '4th Period', periodTime: '11:00 AM - 11:45 AM', subjectId: 4, subjectName: 'Physics', subjectCode: 'PHY-136', teacherId: 3, teacherName: 'Shahidul Alam', roomNumber: 'Science Lab 1' },
  { id: 18, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Tuesday', periodSlotId: 7, periodName: '5th Period', periodTime: '12:30 PM - 01:15 PM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },

  // Wednesday
  { id: 19, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Wednesday', periodSlotId: 2, periodName: '1st Period', periodTime: '08:45 AM - 09:30 AM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },
  { id: 20, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Wednesday', periodSlotId: 3, periodName: '2nd Period', periodTime: '09:30 AM - 10:15 AM', subjectId: 6, subjectName: 'Information & Communication Tech', subjectCode: 'ICT-154', teacherId: 6, teacherName: 'Anisur Rahman', roomNumber: 'Computer Lab 1' },
  { id: 21, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Wednesday', periodSlotId: 4, periodName: '3rd Period', periodTime: '10:15 AM - 11:00 AM', subjectId: 2, subjectName: 'English 1st Paper', subjectCode: 'ENG-107', teacherId: 2, teacherName: 'Nasreen Sultana', roomNumber: 'Room 301' },
  { id: 22, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Wednesday', periodSlotId: 5, periodName: '4th Period', periodTime: '11:00 AM - 11:45 AM', subjectId: 1, subjectName: 'Bangla 1st Paper', subjectCode: 'BAN-101', teacherId: 4, teacherName: 'Farhana Yasmin', roomNumber: 'Room 301' },
  { id: 23, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Wednesday', periodSlotId: 7, periodName: '5th Period', periodTime: '12:30 PM - 01:15 PM', subjectId: 4, subjectName: 'Physics', subjectCode: 'PHY-136', teacherId: 3, teacherName: 'Shahidul Alam', roomNumber: 'Science Lab 1' },

  // Thursday
  { id: 24, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Thursday', periodSlotId: 2, periodName: '1st Period', periodTime: '08:45 AM - 09:30 AM', subjectId: 1, subjectName: 'Bangla 1st Paper', subjectCode: 'BAN-101', teacherId: 4, teacherName: 'Farhana Yasmin', roomNumber: 'Room 301' },
  { id: 25, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Thursday', periodSlotId: 3, periodName: '2nd Period', periodTime: '09:30 AM - 10:15 AM', subjectId: 3, subjectName: 'General Mathematics', subjectCode: 'MAT-109', teacherId: 1, teacherName: 'Dr. Mohammad Rafiqul Islam', roomNumber: 'Room 301' },
  { id: 26, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Thursday', periodSlotId: 4, periodName: '3rd Period', periodTime: '10:15 AM - 11:00 AM', subjectId: 5, subjectName: 'Chemistry', subjectCode: 'CHE-137', teacherId: 5, teacherName: 'Kamal Hossain', roomNumber: 'Science Lab 2' },
  { id: 27, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Thursday', periodSlotId: 5, periodName: '4th Period', periodTime: '11:00 AM - 11:45 AM', subjectId: 2, subjectName: 'English 1st Paper', subjectCode: 'ENG-107', teacherId: 2, teacherName: 'Nasreen Sultana', roomNumber: 'Room 301' },
  { id: 28, academicYearId: 1, classId: 5, className: 'Class 10', sectionId: 1, sectionName: 'Padma', dayOfWeek: 'Thursday', periodSlotId: 7, periodName: '5th Period', periodTime: '12:30 PM - 01:15 PM', subjectId: 6, subjectName: 'Information & Communication Tech', subjectCode: 'ICT-154', teacherId: 6, teacherName: 'Anisur Rahman', roomNumber: 'Computer Lab 1' },
];

// ==========================================
// Phase 10: Library Defaults
// ==========================================
const DEFAULT_BOOK_CATEGORIES: BookCategoryInfo[] = [
  { id: 1, name: 'Computer Science & ICT', code: 'CS-ICT', description: 'Programming, Algorithms, AI, Hardware and Networking' },
  { id: 2, name: 'Mathematics & Physics', code: 'MATH-PHY', description: 'Calculus, Linear Algebra, Mechanics, Electromagnetism' },
  { id: 3, name: 'General Science & Biology', code: 'SCI-BIO', description: 'Chemistry, Genetics, Ecology and General Science' },
  { id: 4, name: 'English Literature & Grammar', code: 'ENG-LIT', description: 'Classic Novels, Poetry, English Grammar and Composition' },
  { id: 5, name: 'Bangla Literature & Language', code: 'BAN-LIT', description: 'Nobel laureate works, prose, poetry and linguistics' },
  { id: 6, name: 'World History & Social Sciences', code: 'HIST-SOC', description: 'Ancient civilization, Modern history, Economics & Geography' },
  { id: 7, name: 'Reference & Encyclopedias', code: 'REF-ENC', description: 'Dictionaries, Atlases, Yearbooks and Research Handbooks' },
];

const DEFAULT_BOOKS: BookInfo[] = [
  {
    id: 1,
    accessionNo: 'ACC-2026-0001',
    title: 'Introduction to Algorithms (4th Edition)',
    author: 'Thomas H. Cormen, Charles E. Leiserson',
    publisher: 'MIT Press',
    isbn: '978-0262046305',
    edition: '4th Edition',
    publicationYear: 2022,
    categoryId: 1,
    categoryName: 'Computer Science & ICT',
    rackNumber: 'Rack 01',
    shelfNumber: 'Shelf A',
    totalCopies: 5,
    availableCopies: 4,
    issuedCopies: 1,
    price: 85.0,
    status: 'Available',
  },
  {
    id: 2,
    accessionNo: 'ACC-2026-0002',
    title: 'Clean Code: A Handbook of Agile Software Craftsmanship',
    author: 'Robert C. Martin',
    publisher: 'Prentice Hall',
    isbn: '978-0132350884',
    edition: '1st Edition',
    publicationYear: 2008,
    categoryId: 1,
    categoryName: 'Computer Science & ICT',
    rackNumber: 'Rack 01',
    shelfNumber: 'Shelf B',
    totalCopies: 4,
    availableCopies: 3,
    issuedCopies: 1,
    price: 42.5,
    status: 'Available',
  },
  {
    id: 3,
    accessionNo: 'ACC-2026-0003',
    title: 'University Physics with Modern Physics',
    author: 'Hugh D. Young, Roger A. Freedman',
    publisher: 'Pearson',
    isbn: '978-0135159552',
    edition: '15th Edition',
    publicationYear: 2019,
    categoryId: 2,
    categoryName: 'Mathematics & Physics',
    rackNumber: 'Rack 02',
    shelfNumber: 'Shelf A',
    totalCopies: 6,
    availableCopies: 6,
    issuedCopies: 0,
    price: 95.0,
    status: 'Available',
  },
  {
    id: 4,
    accessionNo: 'ACC-2026-0004',
    title: 'Calculus: Early Transcendentals',
    author: 'James Stewart',
    publisher: 'Cengage Learning',
    isbn: '978-1305272378',
    edition: '8th Edition',
    publicationYear: 2015,
    categoryId: 2,
    categoryName: 'Mathematics & Physics',
    rackNumber: 'Rack 02',
    shelfNumber: 'Shelf C',
    totalCopies: 8,
    availableCopies: 8,
    issuedCopies: 0,
    price: 78.0,
    status: 'Available',
  },
  {
    id: 5,
    accessionNo: 'ACC-2026-0005',
    title: 'Campbell Biology (12th Edition)',
    author: 'Lisa A. Urry, Michael L. Cain',
    publisher: 'Pearson',
    isbn: '978-0135188743',
    edition: '12th Edition',
    publicationYear: 2020,
    categoryId: 3,
    categoryName: 'General Science & Biology',
    rackNumber: 'Rack 03',
    shelfNumber: 'Shelf A',
    totalCopies: 5,
    availableCopies: 5,
    issuedCopies: 0,
    price: 110.0,
    status: 'Available',
  },
  {
    id: 6,
    accessionNo: 'ACC-2026-0006',
    title: 'To Kill a Mockingbird',
    author: 'Harper Lee',
    publisher: 'J. B. Lippincott & Co.',
    isbn: '978-0060935467',
    edition: '50th Anniversary Ed.',
    publicationYear: 1960,
    categoryId: 4,
    categoryName: 'English Literature & Grammar',
    rackNumber: 'Rack 04',
    shelfNumber: 'Shelf A',
    totalCopies: 7,
    availableCopies: 7,
    issuedCopies: 0,
    price: 18.0,
    status: 'Available',
  },
  {
    id: 7,
    accessionNo: 'ACC-2026-0007',
    title: '1984 & Animal Farm Special Collection',
    author: 'George Orwell',
    publisher: 'Secker & Warburg',
    isbn: '978-0451524935',
    edition: 'Classic Edition',
    publicationYear: 1949,
    categoryId: 4,
    categoryName: 'English Literature & Grammar',
    rackNumber: 'Rack 04',
    shelfNumber: 'Shelf B',
    totalCopies: 6,
    availableCopies: 6,
    issuedCopies: 0,
    price: 22.0,
    status: 'Available',
  },
  {
    id: 8,
    accessionNo: 'ACC-2026-0008',
    title: 'Shesher Kobita (The Last Poem)',
    author: 'Rabindranath Tagore',
    publisher: 'Visva-Bharati',
    isbn: '978-8172153578',
    edition: 'Centenary Edition',
    publicationYear: 1929,
    categoryId: 5,
    categoryName: 'Bangla Literature & Language',
    rackNumber: 'Rack 05',
    shelfNumber: 'Shelf A',
    totalCopies: 10,
    availableCopies: 10,
    issuedCopies: 0,
    price: 12.0,
    status: 'Available',
  },
  {
    id: 9,
    accessionNo: 'ACC-2026-0009',
    title: 'A Brief History of Humankind (Sapiens)',
    author: 'Yuval Noah Harari',
    publisher: 'Harper',
    isbn: '978-0062316097',
    edition: '1st Edition',
    publicationYear: 2015,
    categoryId: 6,
    categoryName: 'World History & Social Sciences',
    rackNumber: 'Rack 06',
    shelfNumber: 'Shelf A',
    totalCopies: 6,
    availableCopies: 6,
    issuedCopies: 0,
    price: 26.0,
    status: 'Available',
  },
  {
    id: 10,
    accessionNo: 'ACC-2026-0010',
    title: "Oxford Advanced Learner's Dictionary (10th Edition)",
    author: 'A. S. Hornby',
    publisher: 'Oxford University Press',
    isbn: '978-0194798488',
    edition: '10th Edition',
    publicationYear: 2020,
    categoryId: 7,
    categoryName: 'Reference & Encyclopedias',
    rackNumber: 'Rack 07',
    shelfNumber: 'Shelf A',
    totalCopies: 4,
    availableCopies: 4,
    issuedCopies: 0,
    price: 55.0,
    status: 'Available',
  },
];

const DEFAULT_LIBRARY_MEMBERS: LibraryMemberInfo[] = [
  {
    id: 1,
    memberId: 'LIB-STD-1001',
    memberType: 'Student',
    studentId: 1,
    patronName: 'Samiul Islam',
    rollOrDesignation: 'Class 10 (Roll 1)',
    cardIssueDate: '2026-01-10',
    maxAllowedBooks: 3,
    activeLoanCount: 1,
    status: 'Active',
  },
  {
    id: 2,
    memberId: 'LIB-STD-1002',
    memberType: 'Student',
    studentId: 2,
    patronName: 'Sadia Jahan',
    rollOrDesignation: 'Class 10 (Roll 2)',
    cardIssueDate: '2026-01-10',
    maxAllowedBooks: 3,
    activeLoanCount: 1,
    status: 'Active',
  },
  {
    id: 3,
    memberId: 'LIB-STD-1003',
    memberType: 'Student',
    studentId: 3,
    patronName: 'Tanvir Hasan',
    rollOrDesignation: 'Class 10 (Roll 3)',
    cardIssueDate: '2026-01-12',
    maxAllowedBooks: 3,
    activeLoanCount: 0,
    status: 'Active',
  },
  {
    id: 4,
    memberId: 'LIB-FAC-2001',
    memberType: 'Teacher',
    teacherId: 1,
    patronName: 'Dr. Mohammad Rafiqul Islam',
    rollOrDesignation: 'Principal & Senior Faculty',
    cardIssueDate: '2025-08-01',
    maxAllowedBooks: 5,
    activeLoanCount: 0,
    status: 'Active',
  },
  {
    id: 5,
    memberId: 'LIB-FAC-2002',
    memberType: 'Teacher',
    teacherId: 2,
    patronName: 'Nasreen Sultana',
    rollOrDesignation: 'Assistant Professor, English',
    cardIssueDate: '2025-08-01',
    maxAllowedBooks: 5,
    activeLoanCount: 0,
    status: 'Active',
  },
];

const DEFAULT_BOOK_CIRCULATIONS: BookCirculationRecord[] = [
  {
    id: 1,
    bookId: 1,
    accessionNo: 'ACC-2026-0001',
    bookTitle: 'Introduction to Algorithms (4th Edition)',
    memberId: 1,
    memberCode: 'LIB-STD-1001',
    patronName: 'Samiul Islam',
    memberType: 'Student',
    issueDate: '2026-02-01',
    dueDate: '2026-02-15',
    status: 'Issued',
    fineAmount: 0,
    finePaid: false,
    issuedBy: 'Chief Librarian',
    remarks: 'Active loan for programming contest preparation',
  },
  {
    id: 2,
    bookId: 2,
    accessionNo: 'ACC-2026-0002',
    bookTitle: 'Clean Code: A Handbook of Agile Software Craftsmanship',
    memberId: 2,
    memberCode: 'LIB-STD-1002',
    patronName: 'Sadia Jahan',
    memberType: 'Student',
    issueDate: '2026-01-10',
    dueDate: '2026-01-24',
    status: 'Overdue',
    fineAmount: 35.0,
    finePaid: false,
    issuedBy: 'Assistant Librarian',
    remarks: '7 days past deadline - overdue notice issued',
  },
  {
    id: 3,
    bookId: 3,
    accessionNo: 'ACC-2026-0003',
    bookTitle: 'University Physics with Modern Physics',
    memberId: 1,
    memberCode: 'LIB-STD-1001',
    patronName: 'Samiul Islam',
    memberType: 'Student',
    issueDate: '2026-01-05',
    dueDate: '2026-01-19',
    returnDate: '2026-01-18',
    status: 'Returned',
    fineAmount: 0,
    finePaid: true,
    issuedBy: 'Chief Librarian',
    remarks: 'Returned in good condition on time',
  },
];

// ==========================================
// Phase 11: Transport Defaults
// ==========================================
const DEFAULT_VEHICLES: VehicleInfo[] = [
  {
    id: 1,
    vehicleNumber: 'DHK-METRO-CHA-11-2041',
    vehicleModel: 'Tata Marcopolo CityBus 42-S',
    vehicleType: 'Bus',
    seatingCapacity: 42,
    driverName: 'Rafiqul Islam',
    driverPhone: '+880 1711-234567',
    driverLicense: 'DL-DHK-88412',
    helperName: 'Billal Hossain',
    helperPhone: '+880 1812-334455',
    insuranceExpiry: '2026-12-31',
    fitnessExpiry: '2026-10-15',
    status: 'Active',
  },
  {
    id: 2,
    vehicleNumber: 'DHK-METRO-CHA-11-2042',
    vehicleModel: 'Ashok Leyland Falcon 38-S',
    vehicleType: 'Bus',
    seatingCapacity: 38,
    driverName: 'Abdul Malek',
    driverPhone: '+880 1722-345678',
    driverLicense: 'DL-DHK-99231',
    helperName: 'Solaiman Miah',
    helperPhone: '+880 1913-445566',
    insuranceExpiry: '2026-11-30',
    fitnessExpiry: '2026-09-20',
    status: 'Active',
  },
  {
    id: 3,
    vehicleNumber: 'DHK-METRO-GA-14-3015',
    vehicleModel: 'Toyota Coaster Deluxe 28-S',
    vehicleType: 'Minibus',
    seatingCapacity: 28,
    driverName: 'Mizanur Rahman',
    driverPhone: '+880 1733-456789',
    driverLicense: 'DL-DHK-77124',
    helperName: 'Jahangir Alam',
    helperPhone: '+880 1814-556677',
    insuranceExpiry: '2027-01-15',
    fitnessExpiry: '2026-11-10',
    status: 'Active',
  },
  {
    id: 4,
    vehicleNumber: 'DHK-METRO-CHA-11-2044',
    vehicleModel: 'Hino Rainbow 32-S',
    vehicleType: 'Bus',
    seatingCapacity: 32,
    driverName: 'Kabir Hossain',
    driverPhone: '+880 1744-567890',
    driverLicense: 'DL-DHK-66541',
    helperName: 'Rokonuzzaman',
    helperPhone: '+880 1915-667788',
    insuranceExpiry: '2026-08-30',
    fitnessExpiry: '2026-06-25',
    status: 'Maintenance',
  },
];

const DEFAULT_ROUTES: TransportRouteInfo[] = [
  {
    id: 1,
    routeCode: 'RT-01',
    routeName: 'Route 01: Uttara - Airport - Campus',
    startPoint: 'Uttara Sector 14',
    endPoint: 'School Main Campus',
    distanceKm: 14.5,
    monthlyFee: 2500.0,
    vehicleId: 1,
    vehicleNumber: 'DHK-METRO-CHA-11-2041',
    pickupTime: '06:45 AM',
    dropTime: '02:30 PM',
    status: 'Active',
    stops: [
      { id: 1, routeId: 1, stopName: 'Uttara Sector 14 (Origin)', stopOrder: 1, pickupTime: '06:45 AM', dropTime: '02:30 PM', fare: 2500.0 },
      { id: 2, routeId: 1, stopName: 'House Building / Azampur', stopOrder: 2, pickupTime: '07:00 AM', dropTime: '02:45 PM', fare: 2400.0 },
      { id: 3, routeId: 1, stopName: 'Airport Intersection', stopOrder: 3, pickupTime: '07:15 AM', dropTime: '03:00 PM', fare: 2200.0 },
      { id: 4, routeId: 1, stopName: 'Khilkhet Overbridge', stopOrder: 4, pickupTime: '07:30 AM', dropTime: '03:15 PM', fare: 2000.0 },
      { id: 5, routeId: 1, stopName: 'School Campus Gate 1', stopOrder: 5, pickupTime: '07:45 AM', dropTime: '03:30 PM', fare: 0.0 },
    ],
  },
  {
    id: 2,
    routeCode: 'RT-02',
    routeName: 'Route 02: Mirpur - Agargaon - Campus',
    startPoint: 'Mirpur 10 Circle',
    endPoint: 'School Main Campus',
    distanceKm: 18.0,
    monthlyFee: 2800.0,
    vehicleId: 2,
    vehicleNumber: 'DHK-METRO-CHA-11-2042',
    pickupTime: '06:30 AM',
    dropTime: '02:30 PM',
    status: 'Active',
    stops: [
      { id: 6, routeId: 2, stopName: 'Mirpur 10 Circle (Origin)', stopOrder: 1, pickupTime: '06:30 AM', dropTime: '02:30 PM', fare: 2800.0 },
      { id: 7, routeId: 2, stopName: 'Mirpur 1 Bus Stand', stopOrder: 2, pickupTime: '06:45 AM', dropTime: '02:45 PM', fare: 2600.0 },
      { id: 8, routeId: 2, stopName: 'Agargaon Metro Station', stopOrder: 3, pickupTime: '07:05 AM', dropTime: '03:05 PM', fare: 2400.0 },
      { id: 9, routeId: 2, stopName: 'Bijoy Sarani Intersection', stopOrder: 4, pickupTime: '07:25 AM', dropTime: '03:25 PM', fare: 2200.0 },
      { id: 10, routeId: 2, stopName: 'School Campus Gate 2', stopOrder: 5, pickupTime: '07:50 AM', dropTime: '03:45 PM', fare: 0.0 },
    ],
  },
  {
    id: 3,
    routeCode: 'RT-03',
    routeName: 'Route 03: Dhanmondi - Mohakhali - Campus',
    startPoint: 'Dhanmondi Road 27',
    endPoint: 'School Main Campus',
    distanceKm: 16.5,
    monthlyFee: 3000.0,
    vehicleId: 3,
    vehicleNumber: 'DHK-METRO-GA-14-3015',
    pickupTime: '06:40 AM',
    dropTime: '02:30 PM',
    status: 'Active',
    stops: [
      { id: 11, routeId: 3, stopName: 'Dhanmondi 27 (Origin)', stopOrder: 1, pickupTime: '06:40 AM', dropTime: '02:30 PM', fare: 3000.0 },
      { id: 12, routeId: 3, stopName: 'Kalabagan Bus Stop', stopOrder: 2, pickupTime: '06:55 AM', dropTime: '02:45 PM', fare: 2800.0 },
      { id: 13, routeId: 3, stopName: 'Farmgate Ananda Cinema', stopOrder: 3, pickupTime: '07:15 AM', dropTime: '03:05 PM', fare: 2500.0 },
      { id: 14, routeId: 3, stopName: 'Mohakhali Flyover End', stopOrder: 4, pickupTime: '07:35 AM', dropTime: '03:25 PM', fare: 2200.0 },
      { id: 15, routeId: 3, stopName: 'School Campus Gate 1', stopOrder: 5, pickupTime: '07:50 AM', dropTime: '03:40 PM', fare: 0.0 },
    ],
  },
];

const DEFAULT_PASSENGERS: TransportPassengerInfo[] = [
  {
    id: 1,
    passengerType: 'Student',
    studentId: 1,
    patronName: 'Samiul Islam',
    rollOrDesignation: 'Class 10 (Roll 1)',
    phone: '+880 1718-123456',
    emergencyContact: '+880 1718-998877',
    routeId: 1,
    routeCode: 'RT-01',
    routeName: 'Route 01: Uttara - Airport - Campus',
    vehicleId: 1,
    vehicleNumber: 'DHK-METRO-CHA-11-2041',
    stopId: 2,
    stopName: 'House Building / Azampur',
    seatNumber: 'Seat 01A',
    allocationDate: '2026-01-10',
    monthlyFare: 2500.0,
    status: 'Active',
    remarks: 'Regular daily commuter',
  },
  {
    id: 2,
    passengerType: 'Student',
    studentId: 2,
    patronName: 'Sadia Jahan',
    rollOrDesignation: 'Class 10 (Roll 2)',
    phone: '+880 1819-112233',
    emergencyContact: '+880 1819-556677',
    routeId: 1,
    routeCode: 'RT-01',
    routeName: 'Route 01: Uttara - Airport - Campus',
    vehicleId: 1,
    vehicleNumber: 'DHK-METRO-CHA-11-2041',
    stopId: 2,
    stopName: 'House Building / Azampur',
    seatNumber: 'Seat 01B',
    allocationDate: '2026-01-10',
    monthlyFare: 2500.0,
    status: 'Active',
    remarks: 'Sibling discount verified',
  },
  {
    id: 3,
    passengerType: 'Student',
    studentId: 3,
    patronName: 'Tanvir Hasan',
    rollOrDesignation: 'Class 10 (Roll 3)',
    phone: '+880 1912-334455',
    emergencyContact: '+880 1912-887766',
    routeId: 2,
    routeCode: 'RT-02',
    routeName: 'Route 02: Mirpur - Agargaon - Campus',
    vehicleId: 2,
    vehicleNumber: 'DHK-METRO-CHA-11-2042',
    stopId: 8,
    stopName: 'Agargaon Metro Station',
    seatNumber: 'Seat 04A',
    allocationDate: '2026-01-12',
    monthlyFare: 2800.0,
    status: 'Active',
    remarks: 'Agargaon boarding stage',
  },
  {
    id: 4,
    passengerType: 'Teacher',
    teacherId: 1,
    patronName: 'Dr. Mohammad Rafiqul Islam',
    rollOrDesignation: 'Principal & Senior Faculty',
    phone: '+880 1711-889900',
    emergencyContact: '+880 1711-889900',
    routeId: 3,
    routeCode: 'RT-03',
    routeName: 'Route 03: Dhanmondi - Mohakhali - Campus',
    vehicleId: 3,
    vehicleNumber: 'DHK-METRO-GA-14-3015',
    stopId: 11,
    stopName: 'Dhanmondi 27 (Origin)',
    seatNumber: 'Seat 01F',
    allocationDate: '2025-08-01',
    monthlyFare: 0.0,
    status: 'Active',
    remarks: 'Complimentary faculty transport',
  },
];

// ==================== PHASE 12: DEFAULT HOSTEL DATA ====================
const DEFAULT_HOSTEL_BLOCKS: HostelBlockInfo[] = [
  {
    id: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    genderType: 'Boys',
    wardenName: 'Md. Rafiqul Islam',
    wardenPhone: '+880 1711-234567',
    address: 'North Campus, Gate 3',
    totalFloors: 3,
    status: 'Active',
  },
  {
    id: 2,
    blockName: 'Rokeya Hall (Girls Block B)',
    genderType: 'Girls',
    wardenName: 'Dr. Farida Begum',
    wardenPhone: '+880 1722-345678',
    address: 'South Campus, Residential Area',
    totalFloors: 3,
    status: 'Active',
  },
  {
    id: 3,
    blockName: 'Pioneer Hall (Junior Dormitory)',
    genderType: 'Boys',
    wardenName: 'Kamal Hossain',
    wardenPhone: '+880 1733-456789',
    address: 'East Campus, Building 5',
    totalFloors: 2,
    status: 'Active',
  },
];

const DEFAULT_HOSTEL_ROOMS: HostelRoomInfo[] = [
  {
    id: 1,
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    roomNumber: 'A-101',
    floorNumber: 1,
    roomType: 'Double',
    capacity: 2,
    monthlyFee: 3500.0,
    amenities: 'Attached Bath, Study Table, Balcony',
    status: 'Full',
    occupiedCount: 2,
  },
  {
    id: 2,
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    roomNumber: 'A-102',
    floorNumber: 1,
    roomType: 'Triple',
    capacity: 3,
    monthlyFee: 3000.0,
    amenities: 'Shared Bath, Study Desk, Ceiling Fan',
    status: 'Available',
    occupiedCount: 1,
  },
  {
    id: 3,
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    roomNumber: 'A-201',
    floorNumber: 2,
    roomType: 'Single',
    capacity: 1,
    monthlyFee: 5500.0,
    amenities: 'Attached Bath, Air Conditioning, Executive Desk',
    status: 'Available',
    occupiedCount: 0,
  },
  {
    id: 4,
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    roomNumber: 'A-202',
    floorNumber: 2,
    roomType: '4-Bed Dorm',
    capacity: 4,
    monthlyFee: 2500.0,
    amenities: 'Bunk Beds, Common Bath, Wi-Fi',
    status: 'Available',
    occupiedCount: 0,
  },
  {
    id: 5,
    blockId: 2,
    blockName: 'Rokeya Hall (Girls Block B)',
    roomNumber: 'B-101',
    floorNumber: 1,
    roomType: 'Double',
    capacity: 2,
    monthlyFee: 3500.0,
    amenities: 'Attached Bath, Built-in Wardrobe, Study Lamps',
    status: 'Available',
    occupiedCount: 1,
  },
  {
    id: 6,
    blockId: 2,
    blockName: 'Rokeya Hall (Girls Block B)',
    roomNumber: 'B-102',
    floorNumber: 1,
    roomType: 'Triple',
    capacity: 3,
    monthlyFee: 3000.0,
    amenities: 'Shared Bath, 3 Study Desks, High Security Intercom',
    status: 'Available',
    occupiedCount: 0,
  },
  {
    id: 7,
    blockId: 3,
    blockName: 'Pioneer Hall (Junior Dormitory)',
    roomNumber: 'J-101',
    floorNumber: 1,
    roomType: '4-Bed Dorm',
    capacity: 4,
    monthlyFee: 2400.0,
    amenities: 'Bunk Beds, Matron Supervision, Study Hall Access',
    status: 'Available',
    occupiedCount: 0,
  },
];

const DEFAULT_HOSTEL_ALLOCATIONS: HostelAllocationInfo[] = [
  {
    id: 1,
    roomId: 1,
    roomNumber: 'A-101',
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    studentId: 1,
    studentRegNo: 'STU-2026-0001',
    studentName: 'Samiul Islam',
    studentGender: 'Male',
    bedNumber: 'Bed-1',
    admissionDate: '2026-01-05',
    guardianContact: '+880 1819-112233',
    emergencyPhone: '+880 1819-112233',
    remarks: 'Hostel prefect & debater',
    status: 'Active',
  },
  {
    id: 2,
    roomId: 1,
    roomNumber: 'A-101',
    blockId: 1,
    blockName: 'Iqbal Hall (Boys Block A)',
    studentId: 3,
    studentRegNo: 'STU-2026-0003',
    studentName: 'Tanvir Hasan',
    studentGender: 'Male',
    bedNumber: 'Bed-2',
    admissionDate: '2026-01-05',
    guardianContact: '+880 1912-334455',
    emergencyPhone: '+880 1912-887766',
    remarks: 'Football team forward',
    status: 'Active',
  },
  {
    id: 3,
    roomId: 5,
    roomNumber: 'B-101',
    blockId: 2,
    blockName: 'Rokeya Hall (Girls Block B)',
    studentId: 2,
    studentRegNo: 'STU-2026-0002',
    studentName: 'Sadia Jahan',
    studentGender: 'Female',
    bedNumber: 'Bed-A',
    admissionDate: '2026-01-08',
    guardianContact: '+880 1711-445566',
    emergencyPhone: '+880 1711-445566',
    remarks: 'Science Olympiad competitor',
    status: 'Active',
  },
];

const DEFAULT_HOSTEL_GATE_PASSES: HostelGatePassInfo[] = [
  {
    id: 1,
    passNumber: 'GP-20260211-0001',
    allocationId: 1,
    studentName: 'Samiul Islam',
    studentRegNo: 'STU-2026-0001',
    roomNumber: 'A-101',
    blockName: 'Iqbal Hall (Boys Block A)',
    purpose: 'Home Visit (Weekend Leave)',
    leaveDate: '2026-02-13',
    expectedReturnDate: '2026-02-15',
    wardenApproval: 'Approved',
    status: 'Out',
    remarks: 'Guardian confirmed via phone',
  },
];

// ==================== PHASE 13: DEFAULT NOTICES & EVENTS ====================
const DEFAULT_NOTICES: SchoolNoticeInfo[] = [
  {
    id: 1,
    referenceNo: 'CIR-2026/001',
    title: 'Commencement of Academic Session 2026 & Orientation Protocol',
    category: 'Academic',
    targetAudience: 'All',
    priority: 'Important',
    isPinned: true,
    publishDate: '2026-01-02',
    expiryDate: '2026-04-30',
    content:
      'We are delighted to welcome all students, faculty, and guardians to Academic Session 2026.\n1. Regular classes for Classes 1 to 10 will begin promptly at 08:00 AM.\n2. Standard school uniform and student ID cards are mandatory for campus entry.\n3. School transport routes and bus passes will be activated from Monday.',
    attachmentName: 'Orientation_Guide_2026.pdf',
    status: 'Published',
    createdBy: 'Principal Office',
  },
  {
    id: 2,
    referenceNo: 'CIR-2026/002',
    title: 'URGENT: Half-Yearly Examination Routine & Admit Card Distribution',
    category: 'Exam',
    targetAudience: 'Students',
    priority: 'Urgent',
    isPinned: true,
    publishDate: '2026-02-05',
    expiryDate: '2026-03-30',
    content:
      'All Class Teachers and Subject Instructors are requested to submit final question papers by March 15.\nAdmit Cards with candidate examination roll numbers and seating allocations will be released on March 20.\nStudents with outstanding tuition fees are advised to clear accounts prior to admit card issuance.',
    attachmentName: 'Half_Yearly_Routine_2026.pdf',
    status: 'Published',
    createdBy: 'Exam Controller Board',
  },
  {
    id: 3,
    referenceNo: 'CIR-2026/003',
    title: 'Annual Inter-House Sports & Athletic Championship 2026',
    category: 'Sports',
    targetAudience: 'Students',
    priority: 'Normal',
    isPinned: false,
    publishDate: '2026-02-01',
    expiryDate: '2026-03-15',
    content:
      'The Annual Athletics Meet will be hosted at the main playground.\nHouse captains (Sher-e-Bangla, Fazlul Huq, Nazrul, and Begum Rokeya) must submit athlete rosters for track and field events (100m sprint, relay, long jump, badminton) to the Sports Coordinator.',
    attachmentName: 'Sports_Schedule.pdf',
    status: 'Published',
    createdBy: 'Physical Education Dept',
  },
  {
    id: 4,
    referenceNo: 'CIR-2026/004',
    title: 'Faculty Development Seminar on AI in K-12 STEM Curriculum',
    category: 'Administrative',
    targetAudience: 'Teachers',
    priority: 'Important',
    isPinned: false,
    publishDate: '2026-02-08',
    expiryDate: '2026-02-28',
    content:
      'A mandatory professional development seminar for all Senior Science and Mathematics teachers.\nKeynote address by Dr. Kazi M. Rahman on integrating practical coding and robotics labs.\nAttendance will be recorded in the biometric staff register.',
    status: 'Published',
    createdBy: 'Academic Vice Principal',
  },
  {
    id: 5,
    referenceNo: 'CIR-2026/005',
    title: 'School Closure Notice on Account of National Mourning & Public Holiday',
    category: 'Holiday',
    targetAudience: 'All',
    priority: 'Normal',
    isPinned: false,
    publishDate: '2026-01-20',
    expiryDate: '2026-03-01',
    content:
      'In observance of the official National Holiday, all academic lectures, library services, and administrative offices will remain closed. Regular classes resume the following working day.',
    status: 'Published',
    createdBy: 'General Administration',
  },
];

const DEFAULT_EVENTS: SchoolEventInfo[] = [
  {
    id: 1,
    eventTitle: 'Independence Day & National Cultural Exhibition',
    eventCategory: 'Holiday',
    startDate: '2026-03-26',
    endDate: '2026-03-26',
    startTime: '08:30 AM',
    endTime: '01:00 PM',
    venue: 'Campus Main Grounds',
    targetAudience: 'All',
    isHoliday: true,
    colorCode: '#DC2626',
    description: 'Flag hoisting ceremony followed by patriotic songs and student drama exhibition.',
    organizer: 'Cultural Affairs Committee',
  },
  {
    id: 2,
    eventTitle: 'Half-Yearly Examination Period (All Classes)',
    eventCategory: 'Exam',
    startDate: '2026-04-15',
    endDate: '2026-04-28',
    startTime: '09:00 AM',
    endTime: '12:00 PM',
    venue: 'Exam Halls A, B & C',
    targetAudience: 'Students',
    isHoliday: false,
    colorCode: '#D97706',
    description: 'Official term examinations covering first semester syllabus for Class 1 to 10.',
    organizer: 'Examination Board',
  },
  {
    id: 3,
    eventTitle: 'Annual Science & Robotics Tech Fair 2026',
    eventCategory: 'Academic',
    startDate: '2026-05-10',
    endDate: '2026-05-11',
    startTime: '10:00 AM',
    endTime: '04:30 PM',
    venue: 'Science Building Quadrangle',
    targetAudience: 'All',
    isHoliday: false,
    colorCode: '#059669',
    description: 'Inter-school science competition with 40+ innovative student project displays.',
    organizer: 'Young Scientists Club',
  },
  {
    id: 4,
    eventTitle: 'Eid-ul-Fitr Vacation (Institutional Recess)',
    eventCategory: 'Holiday',
    startDate: '2026-03-30',
    endDate: '2026-04-06',
    startTime: 'Full Day',
    endTime: 'Full Day',
    venue: 'School-wide',
    targetAudience: 'All',
    isHoliday: true,
    colorCode: '#DC2626',
    description: 'Annual religious festival recess. Hostel boarders may apply for home visit outpasses.',
    organizer: 'School Administration',
  },
  {
    id: 5,
    eventTitle: 'Parent-Teacher Conference & Progress Report Meeting (PTM)',
    eventCategory: 'PTM',
    startDate: '2026-05-20',
    endDate: '2026-05-20',
    startTime: '09:00 AM',
    endTime: '02:00 PM',
    venue: 'Respective Classrooms',
    targetAudience: 'Parents',
    isHoliday: false,
    colorCode: '#7C3AED',
    description: 'One-on-one progress review between guardians and Class Teachers regarding student GPA.',
    organizer: 'Academic Council',
  },
  {
    id: 6,
    eventTitle: 'Inter-School Football Championship Finals',
    eventCategory: 'Sports',
    startDate: '2026-06-05',
    endDate: '2026-06-05',
    startTime: '03:00 PM',
    endTime: '06:00 PM',
    venue: 'Outer Football Stadium',
    targetAudience: 'All',
    isHoliday: false,
    colorCode: '#2563EB',
    description: 'Final championship match between Ideal Model High School and St. Joseph College.',
    organizer: 'Sports Committee',
  },
];

const DEFAULT_CERTIFICATES: CertificateRecordInfo[] = [
  {
    id: 1,
    certificateNumber: 'CERT-BF-2026-0001',
    verificationCode: 'VER-8A41D9C2',
    certificateType: 'Bonafide Certificate',
    recipientType: 'Student',
    studentId: 1,
    recipientName: 'Samiul Islam',
    recipientCode: 'STU-2026-001',
    classOrDesignation: 'Class 10 (Section A, Roll 1)',
    fatherOrGuardian: 'Md. Abdul Karim',
    issueDate: '2026-02-10',
    conductGrade: 'Exemplary',
    reasonOrPurpose: 'National Olympiad & Student Visa Verification',
    remarks: 'Full-time regular student in good standing.',
    status: 'Issued',
    issuedBy: 'Prof. Dr. Mohammad Rafiqul Islam',
  },
  {
    id: 2,
    certificateNumber: 'CERT-MR-2026-0001',
    verificationCode: 'VER-5C92E7B1',
    certificateType: 'Merit Certificate',
    recipientType: 'Student',
    studentId: 2,
    recipientName: 'Sadia Jahan',
    recipientCode: 'STU-2026-002',
    classOrDesignation: 'Class 10 (Section A, Roll 2)',
    fatherOrGuardian: 'Md. Jahangir Alam',
    issueDate: '2026-02-18',
    conductGrade: 'Exemplary',
    reasonOrPurpose: '1st Position in Inter-School Science & Robotics Fair',
    remarks: 'Awarded Gold Distinction for Autonomous Water Quality Sensor.',
    status: 'Issued',
    issuedBy: 'Prof. Dr. Mohammad Rafiqul Islam',
  },
  {
    id: 3,
    certificateNumber: 'CERT-TM-2026-0001',
    verificationCode: 'VER-7F10B3A8',
    certificateType: 'Testimonial',
    recipientType: 'Student',
    studentId: 3,
    recipientName: 'Tanvir Hasan',
    recipientCode: 'STU-2026-003',
    classOrDesignation: 'Class 10 (Section A, Roll 3)',
    fatherOrGuardian: 'Kamrul Hasan',
    issueDate: '2026-03-02',
    conductGrade: 'Very Good',
    reasonOrPurpose: 'Higher Secondary College Admission & Scholarship',
    remarks: 'Demonstrated leadership as Debate Club Secretary.',
    status: 'Issued',
    issuedBy: 'Prof. Dr. Mohammad Rafiqul Islam',
  },
  {
    id: 4,
    certificateNumber: 'CERT-EX-2026-0001',
    verificationCode: 'VER-3D64F8E9',
    certificateType: 'Staff Experience Letter',
    recipientType: 'Teacher',
    staffOrTeacherId: 2,
    recipientName: 'Nasreen Sultana',
    recipientCode: 'TCH-2024-002',
    classOrDesignation: 'Assistant Professor, English',
    fatherOrGuardian: 'N/A',
    issueDate: '2026-03-08',
    leavingDate: '2026-03-08',
    conductGrade: 'Exemplary',
    reasonOrPurpose: 'Academic Tenure & Professional Reference',
    remarks: 'Recognized for 6 years of dedicated English curriculum mentorship.',
    status: 'Issued',
    issuedBy: 'Prof. Dr. Mohammad Rafiqul Islam',
  },
];

export const storage = StorageService;






