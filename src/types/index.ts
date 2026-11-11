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

// ----------------- Phase 10: Library Circulation & Catalog -----------------
export interface BookCategoryInfo {
  id: number;
  name: string;
  code: string;
  description?: string;
}

export interface BookInfo {
  id: number;
  accessionNo: string;
  title: string;
  author: string;
  publisher?: string;
  isbn?: string;
  edition?: string;
  publicationYear?: number;
  categoryId: number;
  categoryName: string;
  rackNumber?: string;
  shelfNumber?: string;
  totalCopies: number;
  availableCopies: number;
  issuedCopies: number;
  price: number;
  status: 'Available' | 'Out of Stock' | 'Discontinued';
}

export interface LibraryMemberInfo {
  id: number;
  memberId: string;
  memberType: 'Student' | 'Teacher' | 'Staff';
  studentId?: number;
  teacherId?: number;
  staffId?: number;
  patronName: string;
  rollOrDesignation?: string;
  cardIssueDate: string;
  maxAllowedBooks: number;
  activeLoanCount: number;
  status: 'Active' | 'Suspended' | 'Expired';
}

export interface BookCirculationRecord {
  id: number;
  bookId: number;
  accessionNo: string;
  bookTitle: string;
  memberId: number;
  memberCode: string;
  patronName: string;
  memberType: 'Student' | 'Teacher' | 'Staff';
  issueDate: string;
  dueDate: string;
  returnDate?: string;
  status: 'Issued' | 'Returned' | 'Overdue';
  fineAmount: number;
  finePaid: boolean;
  issuedBy?: string;
  remarks?: string;
}

export interface LibraryStatsInfo {
  totalTitles: number;
  totalInventoryCopies: number;
  availableCopies: number;
  currentlyIssued: number;
  overdueCount: number;
  activeMembers: number;
  totalFineCollected: number;
}

// ----------------- Phase 11: Transport & Fleet Management -----------------
export interface VehicleInfo {
  id: number;
  vehicleNumber: string;
  vehicleModel: string;
  vehicleType: 'Bus' | 'Minibus' | 'Van' | 'Coaster';
  seatingCapacity: number;
  driverName: string;
  driverPhone: string;
  driverLicense?: string;
  helperName?: string;
  helperPhone?: string;
  insuranceExpiry?: string;
  fitnessExpiry?: string;
  status: 'Active' | 'Maintenance' | 'Out of Service';
}

export interface TransportStopInfo {
  id: number;
  routeId: number;
  stopName: string;
  stopOrder: number;
  pickupTime?: string;
  dropTime?: string;
  fare?: number;
}

export interface TransportRouteInfo {
  id: number;
  routeCode: string;
  routeName: string;
  startPoint: string;
  endPoint: string;
  distanceKm: number;
  monthlyFee: number;
  vehicleId?: number;
  vehicleNumber?: string;
  pickupTime?: string;
  dropTime?: string;
  stops: TransportStopInfo[];
  status: 'Active' | 'Inactive';
}

export interface TransportPassengerInfo {
  id: number;
  passengerType: 'Student' | 'Teacher' | 'Staff';
  studentId?: number;
  teacherId?: number;
  patronName: string;
  rollOrDesignation?: string;
  phone?: string;
  emergencyContact?: string;
  routeId: number;
  routeCode: string;
  routeName: string;
  vehicleId?: number;
  vehicleNumber?: string;
  stopId?: number;
  stopName?: string;
  seatNumber?: string;
  allocationDate: string;
  monthlyFare: number;
  status: 'Active' | 'Suspended' | 'Cancelled';
  remarks?: string;
}

export interface TransportStatsInfo {
  totalVehicles: number;
  activeVehicles: number;
  totalRoutes: number;
  totalCapacity: number;
  allocatedPassengers: number;
  availableSeats: number;
  monthlyRevenue: number;
}

// ----------------- Phase 12: Hostel & Dormitory Management -----------------
export interface HostelBlockInfo {
  id: number;
  blockName: string;
  genderType: 'Boys' | 'Girls' | 'Co-ed';
  wardenName: string;
  wardenPhone: string;
  address?: string;
  totalFloors: number;
  status: 'Active' | 'Maintenance';
}

export interface HostelRoomInfo {
  id: number;
  blockId: number;
  blockName: string;
  roomNumber: string;
  floorNumber: number;
  roomType: 'Single' | 'Double' | 'Triple' | '4-Bed Dorm' | '6-Bed Dorm';
  capacity: number;
  monthlyFee: number;
  amenities: string;
  status: 'Available' | 'Full' | 'Maintenance';
  occupiedCount?: number;
}

export interface HostelAllocationInfo {
  id: number;
  roomId: number;
  roomNumber: string;
  blockId?: number;
  blockName: string;
  studentId: number;
  studentRegNo: string;
  studentName: string;
  studentGender?: string;
  bedNumber: string;
  admissionDate: string;
  vacateDate?: string;
  guardianContact?: string;
  emergencyPhone?: string;
  remarks?: string;
  status: 'Active' | 'Vacated' | 'Suspended';
}

export interface HostelGatePassInfo {
  id: number;
  passNumber: string;
  allocationId: number;
  studentName: string;
  studentRegNo?: string;
  roomNumber: string;
  blockName: string;
  purpose: string;
  leaveDate: string;
  expectedReturnDate: string;
  actualReturnDate?: string;
  wardenApproval: 'Approved' | 'Pending' | 'Rejected';
  status: 'Out' | 'Returned' | 'Overstayed' | 'Cancelled';
  remarks?: string;
}

export interface HostelStatsInfo {
  totalBlocks: number;
  totalRooms: number;
  totalCapacity: number;
  occupiedBeds: number;
  availableBeds: number;
  occupancyRate: number;
  boardersOut: number;
  presentInHostel: number;
}

// ----------------- Phase 13: Notice Board, Circulars & Events Calendar -----------------
export interface SchoolNoticeInfo {
  id: number;
  referenceNo: string;
  title: string;
  category: 'Academic' | 'Exam' | 'Holiday' | 'Administrative' | 'Sports' | 'Fee' | 'Emergency';
  targetAudience: 'All' | 'Students' | 'Teachers' | 'Parents' | 'Staff';
  targetClassId?: number;
  priority: 'Normal' | 'Important' | 'Urgent';
  isPinned: boolean;
  publishDate: string;
  expiryDate?: string;
  content: string;
  attachmentName?: string;
  status: 'Published' | 'Draft' | 'Archived';
  createdBy: string;
}

export interface SchoolEventInfo {
  id: number;
  eventTitle: string;
  eventCategory: 'Academic' | 'Holiday' | 'Exam' | 'Sports' | 'Cultural' | 'PTM' | 'Meeting' | 'Tour';
  startDate: string;
  endDate: string;
  startTime?: string;
  endTime?: string;
  venue: string;
  targetAudience: string;
  isHoliday: boolean;
  colorCode: string;
  description?: string;
  organizer: string;
}

export interface NoticeStatsInfo {
  totalNotices: number;
  publishedNotices: number;
  urgentAlerts: number;
  upcomingEvents: number;
  totalHolidays: number;
}

export interface FeeDefaulterRecord {
  invoiceId: number;
  invoiceNumber: string;
  studentId: number;
  studentName: string;
  admissionNumber: string;
  classSection: string;
  guardianPhone: string;
  title: string;
  totalAmount: number;
  paidAmount: number;
  dueAmount: number;
  dueDate: string;
  daysOverdue: number;
  status: string;
}

export interface ClassAttendanceAuditItem {
  className: string;
  totalRecords: number;
  presentCount: number;
  absentCount: number;
  lateCount: number;
  attendancePercentage: number;
}

export interface ComprehensiveReportAnalytics {
  totalStudents: number;
  activeStudents: number;
  maleStudents: number;
  femaleStudents: number;
  totalStaff: number;
  activeStaff: number;
  teachingStaff: number;
  totalInvoiced: number;
  totalCollected: number;
  totalDues: number;
  collectionEfficiency: number;
  defaultersCount: number;
  totalIncome: number;
  totalExpenses: number;
  netSurplus: number;
  attendanceRate: number;
  examTermsCount: number;
  totalAssessed: number;
  passRate: number;
  avgGpa: number;
  totalBooks: number;
  activeLoans: number;
  totalRoutes: number;
  transportPassengers: number;
  hostelCapacity: number;
  hostelOccupancy: number;
  hostelOccupancyRate: number;
  classAttendanceList: ClassAttendanceAuditItem[];
  defaultersList: FeeDefaulterRecord[];
}

export interface ReportFilterConfig {
  reportType: 'executive' | 'defaulters' | 'demographics' | 'attendance' | 'financial';
  classId?: number;
  startDate?: string;
  endDate?: string;
  format: 'preview' | 'pdf' | 'csv' | 'xlsx';
}




