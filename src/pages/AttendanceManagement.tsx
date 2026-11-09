import React, { useState, useMemo } from 'react';
import {
  CalendarCheck,
  CheckCircle2,
  XCircle,
  Clock,
  CalendarDays,
  FileSpreadsheet,
  Printer,
  Search,
  Filter,
  Save,
  Users,
  Award,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import {
  Student,
  Teacher,
  SchoolClassInfo,
  SectionInfo,
  StudentAttendanceRecord,
  TeacherAttendanceRecord,
  AttendanceStatus,
  SchoolSetting,
  User,
} from '../types';
import { StorageService } from '../services/storage';

interface AttendanceManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const AttendanceManagement: React.FC<AttendanceManagementProps> = ({
  isDark,
  schoolSetting,
}) => {
  const [activeTab, setActiveTab] = useState<'students' | 'teachers' | 'monthly'>('students');

  // Core Data
  const [students] = useState<Student[]>(() => StorageService.getStudents());
  const [teachers] = useState<Teacher[]>(() => StorageService.getTeachers());
  const [classes] = useState<SchoolClassInfo[]>(() => StorageService.getDetailedClasses());
  const [sections] = useState<SectionInfo[]>(() => StorageService.getSections());

  // Date selections
  const [selectedDate, setSelectedDate] = useState<string>('2026-11-09');
  const [selectedClassId, setSelectedClassId] = useState<number>(() => classes[4]?.id || 5); // default Class 10
  const [selectedSectionId, setSelectedSectionId] = useState<string>('all');

  // Student Attendance Working Buffer
  const [savedStudentRecords, setSavedStudentRecords] = useState<StudentAttendanceRecord[]>(() =>
    StorageService.getStudentAttendances()
  );
  const [studentWorkingMap, setStudentWorkingMap] = useState<
    Record<number, { status: AttendanceStatus; checkIn: string; remarks: string }>
  >({});

  // Teacher Attendance Working Buffer
  const [savedTeacherRecords, setSavedTeacherRecords] = useState<TeacherAttendanceRecord[]>(() =>
    StorageService.getTeacherAttendances()
  );
  const [teacherWorkingMap, setTeacherWorkingMap] = useState<
    Record<number, { status: AttendanceStatus; checkIn: string; checkOut: string; remarks: string }>
  >({});

  // Monthly Register Controls
  const [regClassId, setRegClassId] = useState<number>(() => classes[4]?.id || 5);
  const [regMonth, setRegMonth] = useState<number>(11);
  const [regYear, setRegYear] = useState<number>(2026);

  // Success Notification Banner
  const [saveBanner, setSaveBanner] = useState<string | null>(null);

  // Selected Class Object
  const currentClass = useMemo(() => classes.find((c) => c.id === selectedClassId), [classes, selectedClassId]);

  // Sections of Selected Class
  const classSections = useMemo(
    () => sections.filter((s) => s.classId === selectedClassId),
    [sections, selectedClassId]
  );

  // Filter students for the selected class/section
  const classStudents = useMemo(() => {
    return students.filter((s) => {
      const matchClass = s.className === currentClass?.name || s.className.includes(String(currentClass?.numericOrder));
      const matchSection =
        selectedSectionId === 'all' ||
        s.sectionName.toLowerCase().includes(selectedSectionId.toLowerCase());
      return matchClass && matchSection;
    });
  }, [students, currentClass, selectedSectionId]);

  // Sync working buffer when class/date changes
  React.useEffect(() => {
    const existing = savedStudentRecords.filter((r) => r.date === selectedDate);
    const map: Record<number, { status: AttendanceStatus; checkIn: string; remarks: string }> = {};

    classStudents.forEach((stu) => {
      const found = existing.find((r) => r.studentId === stu.id);
      if (found) {
        map[stu.id] = {
          status: found.status,
          checkIn: found.checkInTime || '08:15 AM',
          remarks: found.remarks || '',
        };
      } else {
        map[stu.id] = {
          status: 'Present',
          checkIn: '08:15 AM',
          remarks: '',
        };
      }
    });
    setStudentWorkingMap(map);
  }, [selectedDate, selectedClassId, selectedSectionId, classStudents, savedStudentRecords]);

  // Sync teacher working buffer when date changes
  React.useEffect(() => {
    const existing = savedTeacherRecords.filter((r) => r.date === selectedDate);
    const map: Record<number, { status: AttendanceStatus; checkIn: string; checkOut: string; remarks: string }> = {};

    teachers.forEach((t) => {
      const found = existing.find((r) => r.teacherId === t.id);
      if (found) {
        map[t.id] = {
          status: found.status,
          checkIn: found.checkInTime || '07:50 AM',
          checkOut: found.checkOutTime || '03:15 PM',
          remarks: found.remarks || '',
        };
      } else {
        map[t.id] = {
          status: 'Present',
          checkIn: '07:50 AM',
          checkOut: '03:15 PM',
          remarks: '',
        };
      }
    });
    setTeacherWorkingMap(map);
  }, [selectedDate, teachers, savedTeacherRecords]);

  // Live KPI for student attendance
  const studentStats = useMemo(() => {
    const values = Object.values(studentWorkingMap);
    const total = values.length;
    const present = values.filter((v) => v.status === 'Present').length;
    const absent = values.filter((v) => v.status === 'Absent').length;
    const late = values.filter((v) => v.status === 'Late').length;
    const leave = values.filter((v) => v.status === 'Leave').length;
    const rate = total > 0 ? Math.round((present / total) * 100) : 0;
    return { total, present, absent, late, leave, rate };
  }, [studentWorkingMap]);

  // Live KPI for teacher attendance
  const teacherStats = useMemo(() => {
    const values = Object.values(teacherWorkingMap);
    const total = values.length;
    const present = values.filter((v) => v.status === 'Present').length;
    const absent = values.filter((v) => v.status === 'Absent').length;
    const late = values.filter((v) => v.status === 'Late').length;
    const leave = values.filter((v) => v.status === 'Leave').length;
    const rate = total > 0 ? Math.round((present / total) * 100) : 0;
    return { total, present, absent, late, leave, rate };
  }, [teacherWorkingMap]);

  // ==================== ACTIONS: STUDENT ====================
  const handleSetStudentStatus = (studentId: number, status: AttendanceStatus) => {
    setStudentWorkingMap((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        status,
      },
    }));
  };

  const handleSetAllStudents = (status: AttendanceStatus) => {
    setStudentWorkingMap((prev) => {
      const next: typeof prev = {};
      Object.keys(prev).forEach((k) => {
        const id = Number(k);
        next[id] = { ...prev[id], status };
      });
      return next;
    });
  };

  const handleSaveStudentAttendance = () => {
    const recordsToSave: StudentAttendanceRecord[] = classStudents.map((stu) => {
      const buf = studentWorkingMap[stu.id] || { status: 'Present', checkIn: '08:15 AM', remarks: '' };
      return {
        id: Date.now() + stu.id,
        studentId: stu.id,
        studentCode: stu.studentId,
        studentName: stu.fullName,
        rollNumber: stu.rollNumber,
        classId: selectedClassId,
        className: currentClass?.name || 'Class',
        sectionName: stu.sectionName,
        date: selectedDate,
        status: buf.status,
        checkInTime: buf.checkIn,
        remarks: buf.remarks,
      };
    });

    StorageService.recordStudentAttendance(recordsToSave);
    setSavedStudentRecords(StorageService.getStudentAttendances());
    setSaveBanner(
      `Attendance saved for ${currentClass?.name} on ${selectedDate} (${studentStats.present} Present, ${studentStats.absent} Absent)`
    );
    setTimeout(() => setSaveBanner(null), 4000);
  };

  // ==================== ACTIONS: TEACHER ====================
  const handleSetTeacherStatus = (teacherId: number, status: AttendanceStatus) => {
    setTeacherWorkingMap((prev) => ({
      ...prev,
      [teacherId]: {
        ...prev[teacherId],
        status,
      },
    }));
  };

  const handleSetAllTeachers = (status: AttendanceStatus) => {
    setTeacherWorkingMap((prev) => {
      const next: typeof prev = {};
      Object.keys(prev).forEach((k) => {
        const id = Number(k);
        next[id] = { ...prev[id], status };
      });
      return next;
    });
  };

  const handleSaveTeacherAttendance = () => {
    const recordsToSave: TeacherAttendanceRecord[] = teachers.map((t) => {
      const buf = teacherWorkingMap[t.id] || {
        status: 'Present',
        checkIn: '07:50 AM',
        checkOut: '03:15 PM',
        remarks: '',
      };
      return {
        id: Date.now() + t.id,
        teacherId: t.id,
        employeeId: t.employeeId,
        teacherName: t.fullName,
        department: t.department,
        subject: t.primarySubject,
        date: selectedDate,
        status: buf.status,
        checkInTime: buf.checkIn,
        checkOutTime: buf.checkOut,
        remarks: buf.remarks,
      };
    });

    StorageService.recordTeacherAttendance(recordsToSave);
    setSavedTeacherRecords(StorageService.getTeacherAttendances());
    setSaveBanner(`Faculty attendance saved for ${selectedDate} (${teacherStats.present} Present)`);
    setTimeout(() => setSaveBanner(null), 4000);
  };

  // ==================== MONTHLY REGISTER DATA ====================
  const daysInMonth = useMemo(() => new Date(regYear, regMonth, 0).getDate(), [regYear, regMonth]);

  const monthlyMatrix = useMemo(() => {
    const targetClass = classes.find((c) => c.id === regClassId);
    const enrolled = students.filter(
      (s) => s.className === targetClass?.name || s.className.includes(String(targetClass?.numericOrder))
    );

    return enrolled.map((stu) => {
      const daysRecord: Record<number, AttendanceStatus | '-'> = {};
      let pCount = 0;
      let aCount = 0;
      let lCount = 0;
      let lvCount = 0;

      for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${regYear}-${String(regMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const match = savedStudentRecords.find((r) => r.studentId === stu.id && r.date === dateStr);
        if (match) {
          daysRecord[day] = match.status;
          if (match.status === 'Present') pCount++;
          else if (match.status === 'Absent') aCount++;
          else if (match.status === 'Late') lCount++;
          else if (match.status === 'Leave') lvCount++;
        } else {
          // Deterministic demo seed so heatmap looks realistic for previous days
          const dayOfWeek = new Date(regYear, regMonth - 1, day).getDay();
          if (dayOfWeek === 5) {
            // Friday weekend in Bangladesh
            daysRecord[day] = '-';
          } else if (day <= 9) {
            const isAbsent = (stu.rollNumber + day) % 7 === 0;
            const isLate = (stu.rollNumber + day) % 9 === 0;
            if (isAbsent) {
              daysRecord[day] = 'Absent';
              aCount++;
            } else if (isLate) {
              daysRecord[day] = 'Late';
              lCount++;
            } else {
              daysRecord[day] = 'Present';
              pCount++;
            }
          } else {
            daysRecord[day] = '-';
          }
        }
      }

      const totalRecorded = pCount + aCount + lCount + lvCount;
      const pct = totalRecorded > 0 ? Math.round((pCount / totalRecorded) * 100) : 0;

      return {
        student: stu,
        days: daysRecord,
        pCount,
        aCount,
        lCount,
        lvCount,
        percentage: pct,
      };
    });
  }, [students, classes, regClassId, regYear, regMonth, daysInMonth, savedStudentRecords]);

  // Export CSV / Excel simulation
  const handleExportCSV = () => {
    const targetClass = classes.find((c) => c.id === regClassId);
    let csv = `MONTHLY ATTENDANCE REGISTER - ${targetClass?.name?.toUpperCase()} (${regMonth}/${regYear})\n`;
    csv += 'Roll,Student ID,Student Name,' + Array.from({ length: daysInMonth }, (_, i) => i + 1).join(',') + ',P,A,L,%\n';

    monthlyMatrix.forEach((m) => {
      const dayValues = Array.from({ length: daysInMonth }, (_, i) => m.days[i + 1] || '-').join(',');
      csv += `${m.student.rollNumber},${m.student.studentId},"${m.student.fullName}",${dayValues},${m.pCount},${m.aCount},${m.lCount},${m.percentage}%\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Attendance_Register_${targetClass?.name}_${regYear}_${regMonth}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`p-6 space-y-6 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <CalendarCheck className="w-5 h-5 text-emerald-500" />
              Attendance & Register Management
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
              Live Register
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time daily marking, biometric check-in sync, punctuality ratios, and visual monthly registers
          </p>
        </div>

        {/* Action Tabs */}
        <div className={`p-1 rounded-xl border flex space-x-1 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-slate-100 border-slate-200'}`}>
          <button
            onClick={() => setActiveTab('students')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'students'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Student Daily</span>
          </button>
          <button
            onClick={() => setActiveTab('teachers')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'teachers'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Award className="w-3.5 h-3.5" />
            <span>Faculty & Staff</span>
          </button>
          <button
            onClick={() => setActiveTab('monthly')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'monthly'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Monthly Register</span>
          </button>
        </div>
      </div>

      {/* Confirmation Banner */}
      {saveBanner && (
        <div className="p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{saveBanner}</span>
          </div>
          <button onClick={() => setSaveBanner(null)} className="text-emerald-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* ==================== TAB 1: STUDENT ATTENDANCE ==================== */}
      {activeTab === 'students' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div
            className={`p-3.5 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-3 ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              {/* Date */}
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Date:</span>
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                />
              </div>

              {/* Class */}
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Class:</span>
                <select
                  value={selectedClassId}
                  onChange={(e) => setSelectedClassId(Number(e.target.value))}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.group})
                    </option>
                  ))}
                </select>
              </div>

              {/* Section */}
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Section:</span>
                <select
                  value={selectedSectionId}
                  onChange={(e) => setSelectedSectionId(e.target.value)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                >
                  <option value="all">All Sections</option>
                  {classSections.map((sec) => (
                    <option key={sec.id} value={sec.name}>
                      {sec.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Quick Bulk Actions */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleSetAllStudents('Present')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/90 hover:bg-emerald-500 text-white shadow-sm transition-all"
              >
                Mark All Present
              </button>
              <button
                onClick={() => handleSetAllStudents('Absent')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600/90 hover:bg-red-500 text-white shadow-sm transition-all"
              >
                Mark All Absent
              </button>
              <button
                onClick={handleSaveStudentAttendance}
                className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition-all"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Register</span>
              </button>
            </div>
          </div>

          {/* Metric KPI Strip */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <Users className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Enrolled</p>
                <p className="text-sm font-bold text-slate-100">{studentStats.total}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Present</p>
                <p className="text-sm font-bold text-emerald-400">{studentStats.present}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                <XCircle className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Absent</p>
                <p className="text-sm font-bold text-red-400">{studentStats.absent}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Late</p>
                <p className="text-sm font-bold text-amber-400">{studentStats.late}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <CalendarDays className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Leave</p>
                <p className="text-sm font-bold text-indigo-400">{studentStats.leave}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                <Award className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium uppercase">Rate %</p>
                <p className="text-sm font-bold text-purple-400">{studentStats.rate}%</p>
              </div>
            </div>
          </div>

          {/* Student Roster Table */}
          <div
            className={`rounded-xl border overflow-hidden ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <table className="w-full text-left text-xs">
              <thead
                className={`border-b font-semibold uppercase tracking-wider text-[11px] ${
                  isDark ? 'bg-slate-950/80 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                <tr>
                  <th className="py-3 px-4 w-16">Roll</th>
                  <th className="py-3 px-4">Student ID</th>
                  <th className="py-3 px-4">Student Full Name</th>
                  <th className="py-3 px-4">Section</th>
                  <th className="py-3 px-4 text-center">Attendance State</th>
                  <th className="py-3 px-4">Check-in Time</th>
                  <th className="py-3 px-4">Remarks / Excuse</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-inherit">
                {classStudents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No active students found in this class section.
                    </td>
                  </tr>
                ) : (
                  classStudents.map((stu) => {
                    const rowData = studentWorkingMap[stu.id] || {
                      status: 'Present',
                      checkIn: '08:15 AM',
                      remarks: '',
                    };
                    return (
                      <tr key={stu.id} className="hover:bg-slate-800/20 transition-colors">
                        <td className="py-3 px-4 font-bold font-mono text-slate-300">
                          #{String(stu.rollNumber).padStart(2, '0')}
                        </td>
                        <td className="py-3 px-4 font-mono text-blue-400">{stu.studentId}</td>
                        <td className="py-3 px-4 font-bold text-slate-100">{stu.fullName}</td>
                        <td className="py-3 px-4 text-slate-300">{stu.sectionName}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center space-x-1">
                            {(['Present', 'Absent', 'Late', 'Leave'] as AttendanceStatus[]).map((st) => {
                              const isSelected = rowData.status === st;
                              const btnColor =
                                st === 'Present'
                                  ? isSelected
                                    ? 'bg-emerald-600 text-white font-bold'
                                    : 'text-emerald-400 hover:bg-emerald-500/20'
                                  : st === 'Absent'
                                  ? isSelected
                                    ? 'bg-red-600 text-white font-bold'
                                    : 'text-red-400 hover:bg-red-500/20'
                                  : st === 'Late'
                                  ? isSelected
                                    ? 'bg-amber-600 text-white font-bold'
                                    : 'text-amber-400 hover:bg-amber-500/20'
                                  : isSelected
                                  ? 'bg-indigo-600 text-white font-bold'
                                  : 'text-indigo-400 hover:bg-indigo-500/20';

                              return (
                                <button
                                  key={st}
                                  type="button"
                                  onClick={() => handleSetStudentStatus(stu.id, st)}
                                  className={`px-2.5 py-1 rounded-md text-[10px] transition-all border border-transparent ${btnColor}`}
                                >
                                  {st === 'Present'
                                    ? 'P'
                                    : st === 'Absent'
                                    ? 'A'
                                    : st === 'Late'
                                    ? 'L'
                                    : 'Leave'}
                                </button>
                              );
                            })}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <input
                            type="text"
                            value={rowData.checkIn}
                            onChange={(e) =>
                              setStudentWorkingMap((prev) => ({
                                ...prev,
                                [stu.id]: { ...prev[stu.id], checkIn: e.target.value },
                              }))
                            }
                            className={`w-28 px-2 py-1 rounded text-xs border outline-none font-mono ${
                              isDark ? 'bg-slate-950 border-slate-800 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                            }`}
                          />
                        </td>
                        <td className="py-3 px-4">
                          <input
                            type="text"
                            placeholder="Optional notes..."
                            value={rowData.remarks}
                            onChange={(e) =>
                              setStudentWorkingMap((prev) => ({
                                ...prev,
                                [stu.id]: { ...prev[stu.id], remarks: e.target.value },
                              }))
                            }
                            className={`w-full max-w-xs px-2 py-1 rounded text-xs border outline-none ${
                              isDark ? 'bg-slate-950 border-slate-800 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                            }`}
                          />
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==================== TAB 2: FACULTY ATTENDANCE ==================== */}
      {activeTab === 'teachers' && (
        <div className="space-y-4">
          <div
            className={`p-3.5 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-3 ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="flex items-center space-x-3">
              <span className="text-xs font-semibold text-slate-400">Faculty Date:</span>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                  isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                }`}
              />
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleSetAllTeachers('Present')}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/90 hover:bg-emerald-500 text-white"
              >
                Mark All Present
              </button>
              <button
                onClick={handleSaveTeacherAttendance}
                className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Faculty Register</span>
              </button>
            </div>
          </div>

          {/* Teacher Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <Users className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium">TOTAL FACULTY</p>
                <p className="text-sm font-bold text-slate-100">{teacherStats.total}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium">PRESENT</p>
                <p className="text-sm font-bold text-emerald-400">{teacherStats.present}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
                <XCircle className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium">ABSENT</p>
                <p className="text-sm font-bold text-red-400">{teacherStats.absent}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <CalendarDays className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium">ON LEAVE</p>
                <p className="text-sm font-bold text-indigo-400">{teacherStats.leave}</p>
              </div>
            </div>

            <div
              className={`p-3 rounded-xl border flex items-center space-x-3 ${
                isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
              }`}
            >
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                <Award className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-medium">RATE %</p>
                <p className="text-sm font-bold text-purple-400">{teacherStats.rate}%</p>
              </div>
            </div>
          </div>

          {/* Teacher Table */}
          <div
            className={`rounded-xl border overflow-hidden ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <table className="w-full text-left text-xs">
              <thead
                className={`border-b font-semibold uppercase tracking-wider text-[11px] ${
                  isDark ? 'bg-slate-950/80 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                }`}
              >
                <tr>
                  <th className="py-3 px-4">Employee ID</th>
                  <th className="py-3 px-4">Teacher Name</th>
                  <th className="py-3 px-4">Department & Subject</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4">In / Out Time</th>
                  <th className="py-3 px-4">Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-inherit">
                {teachers.map((t) => {
                  const rowData = teacherWorkingMap[t.id] || {
                    status: 'Present',
                    checkIn: '07:50 AM',
                    checkOut: '03:15 PM',
                    remarks: '',
                  };
                  return (
                    <tr key={t.id} className="hover:bg-slate-800/20">
                      <td className="py-3 px-4 font-mono text-emerald-400 font-semibold">{t.employeeId}</td>
                      <td className="py-3 px-4 font-bold text-slate-100">{t.fullName}</td>
                      <td className="py-3 px-4 text-slate-300">
                        {t.department} • <span className="text-slate-400">{t.primarySubject}</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          {(['Present', 'Absent', 'Late', 'Leave'] as AttendanceStatus[]).map((st) => {
                            const isSelected = rowData.status === st;
                            return (
                              <button
                                key={st}
                                type="button"
                                onClick={() => handleSetTeacherStatus(t.id, st)}
                                className={`px-2.5 py-1 rounded text-[10px] font-semibold transition-all ${
                                  isSelected
                                    ? st === 'Present'
                                      ? 'bg-emerald-600 text-white'
                                      : st === 'Absent'
                                      ? 'bg-red-600 text-white'
                                      : st === 'Late'
                                      ? 'bg-amber-600 text-white'
                                      : 'bg-indigo-600 text-white'
                                    : 'text-slate-400 hover:bg-slate-800'
                                }`}
                              >
                                {st}
                              </button>
                            );
                          })}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {rowData.checkIn} — {rowData.checkOut}
                      </td>
                      <td className="py-3 px-4">
                        <input
                          type="text"
                          placeholder="Duty note..."
                          value={rowData.remarks}
                          onChange={(e) =>
                            setTeacherWorkingMap((prev) => ({
                              ...prev,
                              [t.id]: { ...prev[t.id], remarks: e.target.value },
                            }))
                          }
                          className={`w-full max-w-xs px-2 py-1 rounded text-xs border outline-none ${
                            isDark ? 'bg-slate-950 border-slate-800 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                          }`}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==================== TAB 3: MONTHLY REGISTER HEATMAP ==================== */}
      {activeTab === 'monthly' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div
            className={`p-3.5 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-3 ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Class:</span>
                <select
                  value={regClassId}
                  onChange={(e) => setRegClassId(Number(e.target.value))}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.group})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Month:</span>
                <select
                  value={regMonth}
                  onChange={(e) => setRegMonth(Number(e.target.value))}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                >
                  <option value={1}>January</option>
                  <option value={2}>February</option>
                  <option value={3}>March</option>
                  <option value={4}>April</option>
                  <option value={5}>May</option>
                  <option value={6}>June</option>
                  <option value={7}>July</option>
                  <option value={8}>August</option>
                  <option value={9}>September</option>
                  <option value={10}>October</option>
                  <option value={11}>November</option>
                  <option value={12}>December</option>
                </select>
              </div>

              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-slate-400">Year:</span>
                <select
                  value={regYear}
                  onChange={(e) => setRegYear(Number(e.target.value))}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-100' : 'bg-slate-50 border-slate-200 text-slate-900'
                  }`}
                >
                  <option value={2025}>2025</option>
                  <option value={2026}>2026</option>
                  <option value={2027}>2027</option>
                </select>
              </div>
            </div>

            {/* Export & Print */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleExportCSV}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>Export CSV / Excel</span>
              </button>
              <button
                onClick={() => window.print()}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-700 hover:bg-slate-600 text-white shadow-sm"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Register</span>
              </button>
            </div>
          </div>

          {/* Color Legend */}
          <div className="flex items-center flex-wrap gap-4 text-xs text-slate-400 px-1">
            <span className="font-semibold text-slate-300">Legend:</span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-emerald-500 inline-block" />
              <span>Present (P)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-red-500 inline-block" />
              <span>Absent (A)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-amber-500 inline-block" />
              <span>Late (L)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-indigo-500 inline-block" />
              <span>Leave (Lv)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-slate-700 inline-block" />
              <span>Weekend / Future (-)</span>
            </span>
          </div>

          {/* Monthly Heatmap Matrix Table */}
          <div
            className={`rounded-xl border overflow-x-auto ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead
                className={`border-b font-semibold uppercase text-[10px] ${
                  isDark ? 'bg-slate-950/80 border-slate-800 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-600'
                }`}
              >
                <tr>
                  <th className="py-2.5 px-3 sticky left-0 z-10 bg-inherit min-w-[50px]">Roll</th>
                  <th className="py-2.5 px-3 sticky left-12 z-10 bg-inherit min-w-[150px]">Student Name</th>
                  {Array.from({ length: daysInMonth }, (_, i) => (
                    <th key={i + 1} className="py-2 px-1 text-center font-mono w-7">
                      {i + 1}
                    </th>
                  ))}
                  <th className="py-2.5 px-2 text-center text-emerald-400">P</th>
                  <th className="py-2.5 px-2 text-center text-red-400">A</th>
                  <th className="py-2.5 px-2 text-center text-amber-400">L</th>
                  <th className="py-2.5 px-3 text-right">Attendance %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-inherit">
                {monthlyMatrix.map((item) => (
                  <tr key={item.student.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2 px-3 font-mono font-bold sticky left-0 z-10 bg-inherit">
                      #{item.student.rollNumber}
                    </td>
                    <td className="py-2 px-3 font-bold text-slate-100 truncate sticky left-12 z-10 bg-inherit">
                      {item.student.fullName}
                    </td>

                    {/* 31 days cells */}
                    {Array.from({ length: daysInMonth }, (_, i) => {
                      const day = i + 1;
                      const st = item.days[day];
                      const cellColor =
                        st === 'Present'
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : st === 'Absent'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : st === 'Late'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : st === 'Leave'
                          ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                          : 'text-slate-600';

                      return (
                        <td key={day} className="py-1 px-0.5 text-center">
                          <span
                            className={`inline-block w-5 h-5 leading-5 text-[9px] font-bold rounded ${cellColor}`}
                          >
                            {st === 'Present'
                              ? 'P'
                              : st === 'Absent'
                              ? 'A'
                              : st === 'Late'
                              ? 'L'
                              : st === 'Leave'
                              ? 'Lv'
                              : '·'}
                          </span>
                        </td>
                      );
                    })}

                    <td className="py-2 px-2 text-center font-bold text-emerald-400">{item.pCount}</td>
                    <td className="py-2 px-2 text-center font-bold text-red-400">{item.aCount}</td>
                    <td className="py-2 px-2 text-center font-bold text-amber-400">{item.lCount}</td>
                    <td className="py-2 px-3 text-right">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          item.percentage >= 90
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : item.percentage >= 75
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-red-500/20 text-red-400 flex items-center justify-end gap-1'
                        }`}
                      >
                        {item.percentage < 75 && <AlertTriangle className="w-3 h-3 shrink-0" />}
                        {item.percentage}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
