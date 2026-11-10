export type UserRole =
  | 'super_admin'
  | 'administrator'
  | 'teacher'
  | 'accountant'
  | 'receptionist'
  | 'librarian'
  | 'student_guardian';

export interface User {
  id: number;
  username: string;
  email: string;
  fullName: string;
  phone: string;
  role: UserRole;
  roleDisplayName: string;
  isActive: boolean;
  isDefaultPassword: boolean;
  failedLoginAttempts: number;
  lockedUntil: string | null;
  lastLoginAt: string | null;
}

export interface SchoolSetting {
  schoolName: string;
  schoolNameBn: string;
  motto: string;
  eiinNumber: string;
  registrationNo: string;
  address: string;
  city: string;
  district: string;
  country: string;
  phone: string;
  email: string;
  website: string;
  principalName: string;
  currencyCode: 'BDT' | 'USD';
  currencySymbol: '৳' | '$';
  language: 'en' | 'bn';
  isSetupCompleted: boolean;
}

export interface ActivityLogItem {
  id: number;
  timestamp: string;
  username: string;
  action: string;
  module: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'SECURITY';
}

export interface AcademicClass {
  id: number;
  name: string;
  code: string;
  sections: string[];
  studentCount: number;
}

export interface Guardian {
  id: number;
  fatherName?: string;
  motherName?: string;
  guardianName: string;
  relation: string;
  guardianPhone: string;
  guardianEmail?: string;
  guardianOccupation?: string;
  guardianAddress?: string;
}

export interface Student {
  id: number;
  studentId: string;
  admissionNumber: string;
  rollNumber: number;
  firstName: string;
  lastName: string;
  fullName: string;
  fullNameBn?: string;
  gender: 'Male' | 'Female' | 'Other';
  dateOfBirth: string;
  bloodGroup?: string;
  phone?: string;
  email?: string;
  address?: string;
  city?: string;
  district?: string;
  religion?: string;
  nationality?: string;
  admissionDate: string;
  className: string;
  sectionName: string;
  group?: string;
  shift?: string;
  academicYear: string;
  status: 'active' | 'inactive' | 'transferred' | 'graduated';
  guardian: Guardian;
  emergencyContact?: string;
  medicalNotes?: string;
  avatarUrl?: string;
}

export interface Teacher {
  id: number;
  teacherId: string;
  employeeId: string;
  fullName: string;
  fullNameBn?: string;
  gender: 'Male' | 'Female' | 'Other';
  dateOfBirth: string;
  bloodGroup?: string;
  phone: string;
  email: string;
  qualification: string;
  designation: string;
  department: string;
  primarySubject: string;
  joiningDate: string;
  salary: number;
  status: 'active' | 'on_leave' | 'resigned' | 'retired';
  attendanceToday?: 'present' | 'absent' | 'leave';
}

export interface Staff {
  id: number;
  staffId: string;
  employeeId: string;
  fullName: string;
  fullNameBn?: string;
  gender: 'Male' | 'Female' | 'Other';
  dateOfBirth: string;
  phone: string;
  email?: string;
  position: string;
  department: string;
  shift: string;
  joiningDate: string;
  salary: number;
  status: 'active' | 'on_leave' | 'resigned';
}

export interface AcademicYearInfo {
  id: number;
  name: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
  status: 'Active' | 'Upcoming' | 'Completed';
}

export interface SectionInfo {
  id: number;
  name: string;
  classId: number;
  className: string;
  roomNumber: string;
  capacity: number;
  shift: 'Morning' | 'Day' | 'Evening';
  group: string;
  classTeacherId?: number;
  classTeacherName?: string;
  studentCount: number;
}

export interface SchoolClassInfo {
  id: number;
  name: string;
  code: string;
  numericOrder: number;
  group: 'General' | 'Science' | 'Humanities' | 'Business Studies';
  shift: 'Morning' | 'Day' | 'Evening';
  academicYearId: number;
  academicYearName: string;
  sections: SectionInfo[];
  subjectCount: number;
  studentCount: number;
}

export interface SubjectInfo {
  id: number;
  subjectId: string;
  name: string;
  code: string;
  classId: number;
  className: string;
  fullMarks: number;
  passMarks: number;
  theoryMarks: number;
  practicalMarks: number;
  subjectType: 'Mandatory' | 'Optional';
  isOptional: boolean;
  teacherId?: number;
  teacherName?: string;
}

export type AttendanceStatus = 'Present' | 'Absent' | 'Late' | 'Leave';

export interface StudentAttendanceRecord {
  id: number;
  studentId: number;
  studentCode: string;
  studentName: string;
  rollNumber: number;
  classId: number;
  className: string;
  sectionId?: number;
  sectionName?: string;
  date: string;
  status: AttendanceStatus;
  checkInTime?: string;
  remarks?: string;
}

export interface TeacherAttendanceRecord {
  id: number;
  teacherId: number;
  employeeId: string;
  teacherName: string;
  department: string;
  subject: string;
  date: string;
  status: AttendanceStatus;
  checkInTime?: string;
  checkOutTime?: string;
  remarks?: string;
}

export interface FeeCategoryInfo {
  id: number;
  name: string;
  code: string;
  description?: string;
  isRecurring: boolean;
  frequency: 'Monthly' | 'Quarterly' | 'Yearly' | 'One-Time';
  isActive: boolean;
}

export interface FeeStructureInfo {
  id: number;
  categoryId: number;
  categoryName: string;
  classId: number;
  className: string;
  academicYearId: number;
  academicYearName: string;
  title: string;
  amount: number;
  dueDate: string;
  assignedCount: number;
  createdAt: string;
}

export interface FeePaymentRecord {
  id: number;
  studentFeeId: number;
  receiptNumber: string;
  amount: number;
  discountAmount: number;
  paymentMethod: 'Cash' | 'Bank Transfer' | 'bKash' | 'Nagad' | 'Rocket' | 'Card' | 'Cheque';
  transactionRef?: string;
  paymentDate: string;
  receivedBy: string;
  notes?: string;
}

export interface StudentFeeInvoice {
  id: number;
  studentId: number;
  studentCode: string;
  studentName: string;
  rollNumber: number;
  classId: number;
  className: string;
  sectionName?: string;
  feeStructureId: number;
  feeTitle: string;
  categoryName: string;
  totalAmount: number;
  discountAmount: number;
  netAmount: number;
  paidAmount: number;
  dueAmount: number;
  dueDate: string;
  status: 'Unpaid' | 'Partial' | 'Paid' | 'Overdue';
  createdAt: string;
  payments: FeePaymentRecord[];
}

export interface AccountCategoryInfo {
  id: number;
  name: string;
  code: string;
  type: 'Income' | 'Expense';
  description?: string;
  isSystem: boolean;
  isActive: boolean;
}

export interface AccountTransactionRecord {
  id: number;
  voucherNo: string;
  transactionDate: string;
  type: 'Income' | 'Expense';
  categoryId: number;
  categoryName: string;
  categoryCode: string;
  amount: number;
  paymentMethod: 'Cash' | 'Bank Transfer' | 'bKash' | 'Nagad' | 'Cheque' | 'Card';
  referenceNo?: string;
  paidToReceivedFrom: string;
  description?: string;
  recordedBy: string;
  status: 'Approved' | 'Pending' | 'Cancelled';
}

export interface FinancialSummary {
  totalIncome: number;
  totalExpense: number;
  netSurplus: number;
  cashInHand: number;
  isProfit: boolean;
}

export interface ExamTermInfo {
  id: number;
  name: string;
  examCode: string;
  academicYearId: number;
  academicYearName: string;
  startDate: string;
  endDate: string;
  status: 'Scheduled' | 'In Progress' | 'Completed' | 'Published';
  description?: string;
}

export interface GradingScaleInfo {
  id: number;
  gradeName: string;
  gradePoint: number;
  markFrom: number;
  markTo: number;
  remarks: string;
}

export interface ExamScheduleInfo {
  id: number;
  examTermId: number;
  classId: number;
  className: string;
  subjectId: number;
  subjectName: string;
  subjectCode: string;
  examDate: string;
  startTime: string;
  endTime: string;
  roomNumber: string;
  fullMarks: number;
  theoryFull: number;
  mcqFull: number;
  practicalFull: number;
}

export interface StudentMarkRecord {
  id: number;
  examTermId: number;
  classId: number;
  className: string;
  subjectId: number;
  subjectName: string;
  subjectCode: string;
  studentId: number;
  studentCode: string;
  studentName: string;
  rollNumber: number;
  theoryMarks: number;
  mcqMarks: number;
  practicalMarks: number;
  caMarks: number;
  totalMarks: number;
  isAbsent: boolean;
  gradeName: string;
  gradePoint: number;
  isPassed: boolean;
  remarks?: string;
}

export interface ExamResultSummaryInfo {
  id: number;
  examTermId: number;
  examTermName: string;
  studentId: number;
  studentCode: string;
  studentName: string;
  rollNumber: number;
  classId: number;
  className: string;
  sectionName?: string;
  totalObtained: number;
  totalFullMarks: number;
  percentage: number;
  gpa: number;
  overallGrade: string;
  classRank: number | null;
  passedAll: boolean;
  failedSubjectCount: number;
  remarks?: string;
}

export interface PeriodSlotInfo {
  id: number;
  periodNumber: number;
  name: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  isBreak: boolean;
  shift: 'Morning' | 'Day';
  academicYearId?: number;
}

export interface TimetableEntryInfo {
  id: number;
  academicYearId: number;
  classId: number;
  className: string;
  sectionId?: number;
  sectionName?: string;
  dayOfWeek: 'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Saturday';
  periodSlotId: number;
  periodName: string;
  periodTime: string;
  subjectId: number;
  subjectName: string;
  subjectCode: string;
  teacherId: number;
  teacherName: string;
  roomNumber: string;
  notes?: string;
}

export interface TimetableConflict {
  conflictType: 'teacher' | 'room';
  message: string;
  dayOfWeek: string;
  periodName: string;
  conflictingClass?: string;
}






