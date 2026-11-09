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

export const storage = StorageService;


