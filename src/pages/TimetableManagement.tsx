import React, { useState, useMemo } from 'react';
import {
  Clock,
  Calendar,
  Users,
  Building,
  Plus,
  Printer,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  X,
  Edit2,
  Trash2,
  BookOpen,
  Coffee,
  Sparkles,
  Search,
  Filter,
} from 'lucide-react';
import {
  SchoolSetting,
  User,
  PeriodSlotInfo,
  TimetableEntryInfo,
  TimetableConflict,
  SchoolClassInfo,
  Teacher,
  SubjectInfo,
} from '../types';
import { StorageService } from '../services/storage';

const STANDARD_DAYS: Array<'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday'> = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
];

interface TimetableManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const TimetableManagement: React.FC<TimetableManagementProps> = ({
  isDark,
  schoolSetting,
}) => {
  // Mode: 'class' (Class Timetable) or 'teacher' (Teacher Routine)
  const [viewMode, setViewMode] = useState<'class' | 'teacher'>('class');

  // Master Data
  const [classes] = useState<SchoolClassInfo[]>(() => StorageService.getDetailedClasses());
  const [selectedClassId, setSelectedClassId] = useState<number>(() => classes[4]?.id || 5); // Class 10 default
  const [teachers] = useState<Teacher[]>(() => StorageService.getTeachers());
  const [selectedTeacherId, setSelectedTeacherId] = useState<number>(() => teachers[0]?.id || 1);
  const [subjects] = useState<SubjectInfo[]>(() => StorageService.getSubjects());

  // Timetable & Periods State
  const [periods, setPeriods] = useState<PeriodSlotInfo[]>(() => StorageService.getPeriodSlots());
  const [entries, setEntries] = useState<TimetableEntryInfo[]>(() => StorageService.getTimetableEntries());

  // Filters
  const [selectedSection, setSelectedSection] = useState<string>('all');

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Modals
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimetableEntryInfo | null>(null);
  const [slotForm, setSlotForm] = useState({
    dayOfWeek: 'Sunday' as 'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday',
    periodSlotId: periods[1]?.id || 2,
    subjectId: subjects[0]?.id || 1,
    teacherId: teachers[0]?.id || 1,
    roomNumber: 'Room 301',
    notes: '',
  });
  const [activeConflicts, setActiveConflicts] = useState<TimetableConflict[]>([]);

  const [showPeriodModal, setShowPeriodModal] = useState(false);
  const [periodForm, setPeriodForm] = useState({
    periodNumber: 1,
    name: '',
    startTime: '08:45 AM',
    endTime: '09:30 AM',
    durationMinutes: 45,
    isBreak: false,
  });

  const [showClassPrintModal, setShowClassPrintModal] = useState(false);
  const [showTeacherPrintModal, setShowTeacherPrintModal] = useState(false);

  // Selected Class & Teacher Objects
  const currentClass = classes.find((c) => c.id === selectedClassId);
  const currentTeacher = teachers.find((t) => t.id === selectedTeacherId);

  // Teaching periods (excluding assembly or keeping tiffin)
  const displayPeriods = useMemo(() => {
    return periods.filter((p) => p.periodNumber !== 0).sort((a, b) => a.periodNumber - b.periodNumber);
  }, [periods]);

  // Class Matrix
  const classMatrix = useMemo(() => {
    const secId = selectedSection !== 'all' ? Number(selectedSection) : undefined;
    return StorageService.getClassTimetableMatrix(selectedClassId, secId);
  }, [selectedClassId, selectedSection, entries]);

  // Teacher Matrix
  const teacherMatrix = useMemo(() => {
    return StorageService.getTeacherRoutineMatrix(selectedTeacherId);
  }, [selectedTeacherId, entries]);

  // Statistics
  const stats = useMemo(() => {
    return StorageService.getTimetableStats();
  }, [periods, entries]);

  // Conflict Checker on Slot Form Change
  const runFormConflictCheck = (
    day: string,
    periodId: number,
    tId: number,
    room: string,
    excludeId?: number
  ) => {
    const clashes = StorageService.checkTimetableConflict(day, periodId, tId, room, excludeId);
    setActiveConflicts(clashes);
  };

  // Open Assign Slot Modal
  const handleOpenAssignModal = (day: 'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday', periodId: number, existing?: TimetableEntryInfo) => {
    if (existing) {
      setEditingEntry(existing);
      setSlotForm({
        dayOfWeek: existing.dayOfWeek as any,
        periodSlotId: existing.periodSlotId,
        subjectId: existing.subjectId,
        teacherId: existing.teacherId,
        roomNumber: existing.roomNumber,
        notes: existing.notes || '',
      });
      runFormConflictCheck(existing.dayOfWeek, existing.periodSlotId, existing.teacherId, existing.roomNumber, existing.id);
    } else {
      setEditingEntry(null);
      const defaultSub = subjects.find((s) => s.classId === selectedClassId) || subjects[0];
      setSlotForm({
        dayOfWeek: day,
        periodSlotId: periodId,
        subjectId: defaultSub ? defaultSub.id : 1,
        teacherId: teachers[0]?.id || 1,
        roomNumber: currentClass?.sections[0]?.roomNumber || 'Room 301',
        notes: '',
      });
      runFormConflictCheck(day, periodId, teachers[0]?.id || 1, 'Room 301');
    }
    setShowAssignModal(true);
  };

  // Handle Save Slot Assignment
  const handleSaveSlot = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeConflicts.length > 0) {
      alert(`Cannot schedule: ${activeConflicts[0].message}`);
      return;
    }

    const res = StorageService.assignTimetableEntry({
      id: editingEntry ? editingEntry.id : undefined,
      academicYearId: 1,
      classId: selectedClassId,
      sectionId: selectedSection !== 'all' ? Number(selectedSection) : currentClass?.sections[0]?.id,
      dayOfWeek: slotForm.dayOfWeek,
      periodSlotId: Number(slotForm.periodSlotId),
      subjectId: Number(slotForm.subjectId),
      teacherId: Number(slotForm.teacherId),
      roomNumber: slotForm.roomNumber.trim(),
      notes: slotForm.notes,
    });

    if (res.conflicts.length > 0) {
      setActiveConflicts(res.conflicts);
      return;
    }

    setEntries(StorageService.getTimetableEntries());
    setShowAssignModal(false);
    showToast('Teaching period assigned successfully!');
  };

  // Handle Delete Slot
  const handleDeleteSlot = (id: number) => {
    if (confirm('Remove this teaching assignment from the timetable?')) {
      StorageService.deleteTimetableEntry(id);
      setEntries(StorageService.getTimetableEntries());
      setShowAssignModal(false);
      showToast('Timetable slot cleared.');
    }
  };

  // Handle Save Period
  const handleSavePeriod = (e: React.FormEvent) => {
    e.preventDefault();
    if (!periodForm.name || !periodForm.startTime || !periodForm.endTime) return;

    StorageService.createPeriodSlot({
      periodNumber: Number(periodForm.periodNumber),
      name: periodForm.name,
      startTime: periodForm.startTime,
      endTime: periodForm.endTime,
      durationMinutes: Number(periodForm.durationMinutes),
      isBreak: periodForm.isBreak,
      shift: 'Morning',
      academicYearId: 1,
    });

    setPeriods(StorageService.getPeriodSlots());
    setShowPeriodModal(false);
    showToast(`Period "${periodForm.name}" created!`);
  };

  // Export Timetable CSV
  const handleExportCSV = () => {
    const teaching = displayPeriods;
    const header = ['Day', ...teaching.map((p) => `${p.name} (${p.startTime}-${p.endTime})`)];
    const rows = STANDARD_DAYS.map((day) => {
      const row: string[] = [day];
      teaching.forEach((p) => {
        if (p.isBreak) {
          row.push('TIFFIN BREAK');
        } else {
          const entry = classMatrix[day]?.[p.id];
          if (entry) {
            row.push(`"${entry.subjectName} (${entry.teacherName} - ${entry.roomNumber})"`);
          } else {
            row.push('"—"');
          }
        }
      });
      return row.join(',');
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + [header.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Class_Timetable_${currentClass?.name || 'Class'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Class Timetable exported to CSV successfully!');
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-emerald-600 text-white px-5 py-3 rounded-xl shadow-2xl animate-bounce">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* Top Banner & Context Header */}
      <div className={`p-6 rounded-2xl border transition-colors ${
        isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500">
                <Clock className="w-6 h-6" />
              </div>
              <h1 className={`text-2xl font-bold tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
                Class Timetable & Teacher Routine Management
              </h1>
            </div>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Weekly master schedule, teaching allocations, room utilization, and automated clash/double-booking detection.
            </p>
          </div>

          {/* View Mode Switcher & Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <div className={`flex rounded-xl p-1 border ${
              isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-100 border-slate-200'
            }`}>
              <button
                onClick={() => setViewMode('class')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  viewMode === 'class'
                    ? 'bg-blue-600 text-white shadow'
                    : isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Class Timetable</span>
              </button>

              <button
                onClick={() => setViewMode('teacher')}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  viewMode === 'teacher'
                    ? 'bg-emerald-600 text-white shadow'
                    : isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Teacher Routine</span>
              </button>
            </div>

            <button
              onClick={() => setShowPeriodModal(true)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition-colors ${
                isDark
                  ? 'border-slate-700 text-slate-300 hover:bg-slate-800'
                  : 'border-slate-300 text-slate-700 hover:bg-slate-100'
              }`}
            >
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              <span>Bell Timings</span>
            </button>

            {viewMode === 'class' ? (
              <>
                <button
                  onClick={handleExportCSV}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Export Excel</span>
                </button>
                <button
                  onClick={() => setShowClassPrintModal(true)}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-colors"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Class Routine</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => setShowTeacherPrintModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Teacher Routine</span>
              </button>
            )}
          </div>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Teaching Periods / Day</span>
              <Clock className="w-4 h-4 text-blue-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.teachingPeriodsCount} <span className="text-xs text-slate-400 font-normal">slots</span>
            </div>
            <span className="text-[11px] text-slate-400">45-min duration bells</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Total Weekly Slots</span>
              <Calendar className="w-4 h-4 text-indigo-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.totalAssignedSlots}
            </div>
            <span className="text-[11px] text-slate-400">Sun — Thu master matrix</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Active Faculty Deployed</span>
              <Users className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-500">
              {stats.activeTeachingFaculty}
            </div>
            <span className="text-[11px] text-slate-400">Conflict-free verified</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Classrooms / Labs</span>
              <Building className="w-4 h-4 text-amber-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.allocatedRooms}
            </div>
            <span className="text-[11px] text-slate-400">Unique rooms allocated</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Collision Status</span>
              <CheckCircle2 className="w-4 h-4 text-cyan-500" />
            </div>
            <div className="text-2xl font-bold text-cyan-500">
              100% OK
            </div>
            <span className="text-[11px] text-slate-400">Zero double-bookings</span>
          </div>
        </div>
      </div>

      {/* FILTER & SELECTOR BAR */}
      <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
        isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        {viewMode === 'class' ? (
          <div className="flex flex-wrap items-center gap-4 w-full sm:w-auto">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Class:
              </span>
              <select
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(Number(e.target.value))}
                className={`text-sm font-semibold px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.group})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Section:
              </span>
              <select
                value={selectedSection}
                onChange={(e) => setSelectedSection(e.target.value)}
                className={`text-sm font-semibold px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                <option value="all">All Sections (Padma)</option>
                {currentClass?.sections.map((s) => (
                  <option key={s.id} value={s.id}>
                    Section {s.name} ({s.roomNumber})
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-4 w-full sm:w-auto">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Faculty Member:
              </span>
              <select
                value={selectedTeacherId}
                onChange={(e) => setSelectedTeacherId(Number(e.target.value))}
                className={`text-sm font-semibold px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                {teachers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.fullName} ({t.designation} - {t.department})
                  </option>
                ))}
              </select>
            </div>

            <div className="text-xs text-emerald-500 font-bold bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
              Department: {currentTeacher?.department || 'General'} | Primary: {currentTeacher?.primarySubject || 'Teaching'}
            </div>
          </div>
        )}

        <div className="text-xs text-slate-400 flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span>Click on any time slot below to assign or reschedule a subject</span>
        </div>
      </div>

      {/* =========================================================================
          INTERACTIVE WEEKLY TIMETABLE MATRIX GRID
      ========================================================================== */}
      <div className={`overflow-x-auto rounded-2xl border ${
        isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <table className="w-full text-left text-sm border-collapse min-w-[900px]">
          <thead>
            <tr className={`border-b text-xs font-semibold uppercase tracking-wider ${
              isDark ? 'border-slate-800 text-slate-400 bg-slate-800/40' : 'border-slate-200 text-slate-600 bg-slate-50'
            }`}>
              <th className="py-4 px-4 w-28 text-center border-r border-inherit">
                Day \ Period
              </th>
              {displayPeriods.map((p) => (
                <th
                  key={p.id}
                  className={`py-3.5 px-3 text-center border-r border-inherit last:border-r-0 ${
                    p.isBreak ? (isDark ? 'bg-amber-950/20 text-amber-400' : 'bg-amber-50 text-amber-700') : ''
                  }`}
                >
                  <div className="font-bold text-xs">{p.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5 font-normal">
                    {p.startTime} - {p.endTime}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {STANDARD_DAYS.map((day) => (
              <tr key={day} className="hover:bg-slate-500/5 transition-colors">
                {/* Day Header */}
                <td className={`py-4 px-3 text-center font-bold text-xs border-r border-slate-200 dark:border-slate-800 ${
                  isDark ? 'bg-slate-800/20 text-slate-200' : 'bg-slate-50 text-slate-800'
                }`}>
                  {day}
                </td>

                {/* Period Columns */}
                {displayPeriods.map((p) => {
                  if (p.isBreak) {
                    return (
                      <td
                        key={p.id}
                        className={`p-3 text-center border-r border-slate-200 dark:border-slate-800 select-none ${
                          isDark ? 'bg-amber-950/10' : 'bg-amber-50/60'
                        }`}
                      >
                        <div className="flex flex-col items-center justify-center gap-1 text-amber-500 opacity-80">
                          <Coffee className="w-4 h-4" />
                          <span className="text-[10px] font-bold tracking-wider uppercase">Tiffin Break</span>
                        </div>
                      </td>
                    );
                  }

                  // Class view or Teacher view slot
                  const entry = viewMode === 'class' ? classMatrix[day]?.[p.id] : teacherMatrix[day]?.[p.id];

                  return (
                    <td
                      key={p.id}
                      onClick={() => handleOpenAssignModal(day, p.id, entry)}
                      className="p-2 border-r border-slate-200 dark:border-slate-800 last:border-r-0 cursor-pointer group hover:bg-blue-500/10 transition-colors"
                    >
                      {entry ? (
                        <div className={`p-2.5 rounded-xl border transition-all ${
                          isDark
                            ? 'bg-slate-800/70 border-slate-700/80 group-hover:border-blue-500/60'
                            : 'bg-blue-50/60 border-blue-200 group-hover:border-blue-400'
                        }`}>
                          <div className="flex items-center justify-between gap-1 mb-1">
                            <span className="text-[11px] font-extrabold text-blue-600 dark:text-blue-400 truncate">
                              {viewMode === 'class' ? entry.subjectName : `${entry.className} (${entry.sectionName || 'A'})`}
                            </span>
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-500/10 text-slate-500 dark:text-slate-400 shrink-0">
                              {entry.roomNumber}
                            </span>
                          </div>

                          <div className="text-[10px] text-slate-600 dark:text-slate-300 font-medium truncate flex items-center gap-1">
                            {viewMode === 'class' ? entry.teacherName : entry.subjectName}
                          </div>
                        </div>
                      ) : (
                        <div className="h-16 flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 dark:border-slate-800 opacity-30 group-hover:opacity-100 group-hover:border-blue-400 group-hover:text-blue-500 transition-all">
                          <Plus className="w-4 h-4 mb-0.5" />
                          <span className="text-[9px] font-semibold">Assign</span>
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* =========================================================================
          MODAL 1: ASSIGN / EDIT TIMETABLE SLOT
      ========================================================================== */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-500" />
                <span className="font-bold text-base">
                  {editingEntry ? 'Edit Teaching Slot' : 'Assign Teaching Period Slot'}
                </span>
              </div>
              <button
                onClick={() => setShowAssignModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Live Conflict Alert Banner */}
            {activeConflicts.length > 0 && (
              <div className="mt-4 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-500 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Scheduling Conflict Detected!</span>
                </div>
                {activeConflicts.map((c, i) => (
                  <div key={i} className="pl-5 text-[11px] leading-tight">
                    • {c.message}
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleSaveSlot} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Day of Week</label>
                  <select
                    value={slotForm.dayOfWeek}
                    onChange={(e) => {
                      const day = e.target.value as any;
                      setSlotForm({ ...slotForm, dayOfWeek: day });
                      runFormConflictCheck(day, slotForm.periodSlotId, slotForm.teacherId, slotForm.roomNumber, editingEntry?.id);
                    }}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  >
                    {STANDARD_DAYS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Period Bell Slot</label>
                  <select
                    value={slotForm.periodSlotId}
                    onChange={(e) => {
                      const pid = Number(e.target.value);
                      setSlotForm({ ...slotForm, periodSlotId: pid });
                      runFormConflictCheck(slotForm.dayOfWeek, pid, slotForm.teacherId, slotForm.roomNumber, editingEntry?.id);
                    }}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  >
                    {displayPeriods.filter((p) => !p.isBreak).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.startTime} - {p.endTime})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Subject</label>
                <select
                  value={slotForm.subjectId}
                  onChange={(e) => setSlotForm({ ...slotForm, subjectId: Number(e.target.value) })}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code} - {s.className})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Assigned Teacher</label>
                <select
                  value={slotForm.teacherId}
                  onChange={(e) => {
                    const tid = Number(e.target.value);
                    setSlotForm({ ...slotForm, teacherId: tid });
                    runFormConflictCheck(slotForm.dayOfWeek, slotForm.periodSlotId, tid, slotForm.roomNumber, editingEntry?.id);
                  }}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                >
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.fullName} ({t.designation} - {t.department})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Room / Laboratory</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Room 301, Science Lab 1"
                    value={slotForm.roomNumber}
                    onChange={(e) => {
                      const room = e.target.value;
                      setSlotForm({ ...slotForm, roomNumber: room });
                      runFormConflictCheck(slotForm.dayOfWeek, slotForm.periodSlotId, slotForm.teacherId, room, editingEntry?.id);
                    }}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Optional Remarks</label>
                  <input
                    type="text"
                    placeholder="e.g. Practical experiment"
                    value={slotForm.notes}
                    onChange={(e) => setSlotForm({ ...slotForm, notes: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
                {editingEntry ? (
                  <button
                    type="button"
                    onClick={() => handleDeleteSlot(editingEntry.id)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-red-600/10 text-red-500 hover:bg-red-600/20"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Clear Slot</span>
                  </button>
                ) : <div></div>}

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAssignModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-600 text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={activeConflicts.length > 0}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white shadow"
                  >
                    {editingEntry ? 'Update Slot' : 'Confirm Assignment'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 2: PERIOD CONFIGURATION
      ========================================================================== */}
      {showPeriodModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl border p-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-base">Add School Bell Period</span>
              <button onClick={() => setShowPeriodModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSavePeriod} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Period Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 8th Period, Recess, Assembly"
                  value={periodForm.name}
                  onChange={(e) => setPeriodForm({ ...periodForm, name: e.target.value })}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Start Time</label>
                  <input
                    type="text"
                    required
                    value={periodForm.startTime}
                    onChange={(e) => setPeriodForm({ ...periodForm, startTime: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">End Time</label>
                  <input
                    type="text"
                    required
                    value={periodForm.endTime}
                    onChange={(e) => setPeriodForm({ ...periodForm, endTime: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="isBreak"
                  checked={periodForm.isBreak}
                  onChange={(e) => setPeriodForm({ ...periodForm, isBreak: e.target.checked })}
                  className="rounded border-slate-400 text-blue-600 focus:ring-blue-500 h-4 w-4"
                />
                <label htmlFor="isBreak" className="text-xs text-slate-300">
                  This is a Break / Non-Teaching Interval (Assembly, Tiffin)
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPeriodModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-600 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white"
                >
                  Save Period Slot
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 3: PRINTABLE CLASS TIMETABLE (LANDSCAPE A4)
      ========================================================================== */}
      {showClassPrintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className={`w-full max-w-4xl rounded-2xl shadow-2xl border p-6 my-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-sm text-blue-500">Official Class Routine Sheet</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Document</span>
                </button>
                <button onClick={() => setShowClassPrintModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="py-6 space-y-6 printable-area">
              <div className="text-center pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="text-xl font-extrabold uppercase tracking-wide text-blue-600 dark:text-blue-400">
                  {schoolSetting.schoolName}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  EIIN: {schoolSetting.eiinNumber} | Address: {schoolSetting.address}, {schoolSetting.city}
                </div>
                <div className="inline-block mt-3 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-500/10 text-blue-500 border border-blue-500/20">
                  WEEKLY CLASS TIMETABLE — {currentClass?.name.toUpperCase()} ({currentClass?.group.toUpperCase()})
                </div>
              </div>

              {/* Grid Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-slate-300 dark:border-slate-700">
                  <thead>
                    <tr className="bg-slate-800 text-white font-bold">
                      <th className="p-2.5 text-center border-r border-slate-700 w-24">Day</th>
                      {displayPeriods.map((p) => (
                        <th key={p.id} className="p-2 text-center border-r border-slate-700 last:border-r-0">
                          <div>{p.name}</div>
                          <div className="text-[9px] font-normal opacity-80">{p.startTime} - {p.endTime}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-300 dark:divide-slate-700">
                    {STANDARD_DAYS.map((day) => (
                      <tr key={day}>
                        <td className="p-2.5 text-center font-bold bg-slate-100 dark:bg-slate-800/40 border-r border-slate-300 dark:border-slate-700">
                          {day}
                        </td>
                        {displayPeriods.map((p) => {
                          if (p.isBreak) {
                            return (
                              <td key={p.id} className="p-2 text-center text-amber-600 font-bold bg-amber-50 dark:bg-amber-950/20 border-r border-slate-300 dark:border-slate-700 text-[10px]">
                                TIFFIN BREAK
                              </td>
                            );
                          }
                          const entry = classMatrix[day]?.[p.id];
                          return (
                            <td key={p.id} className="p-2 text-center border-r border-slate-300 dark:border-slate-700 last:border-r-0 text-[11px]">
                              {entry ? (
                                <div>
                                  <strong className="block text-blue-600 dark:text-blue-400 font-bold">{entry.subjectName}</strong>
                                  <span className="text-[10px] text-slate-500">{entry.teacherName}</span>
                                  <span className="block text-[9px] text-slate-400">{entry.roomNumber}</span>
                                </div>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Signatures */}
              <div className="pt-12 grid grid-cols-3 gap-6 text-center text-xs text-slate-500">
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Class Teacher Signature
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Routine Committee In-Charge
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2 font-bold text-slate-700 dark:text-slate-300">
                  Principal Signature & Official Seal
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 4: PRINTABLE TEACHER ROUTINE (LANDSCAPE A4)
      ========================================================================== */}
      {showTeacherPrintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className={`w-full max-w-4xl rounded-2xl shadow-2xl border p-6 my-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-sm text-emerald-500">Faculty Weekly Routine Schedule</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Routine</span>
                </button>
                <button onClick={() => setShowTeacherPrintModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="py-6 space-y-6 printable-area">
              <div className="text-center pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="text-xl font-extrabold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
                  {schoolSetting.schoolName}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  FACULTY INDIVIDUAL TEACHING WORKLOAD & ROUTINE
                </div>
              </div>

              {/* Teacher Info Header */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-emerald-500/10 rounded-xl text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px]">NAME:</span>
                  <strong>{currentTeacher?.fullName}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">EMPLOYEE ID:</span>
                  <strong className="font-mono">{currentTeacher?.employeeId}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">DEPARTMENT:</span>
                  <strong>{currentTeacher?.department}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">DESIGNATION:</span>
                  <strong>{currentTeacher?.designation}</strong>
                </div>
              </div>

              {/* Grid Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-slate-300 dark:border-slate-700">
                  <thead>
                    <tr className="bg-slate-800 text-white font-bold">
                      <th className="p-2.5 text-center border-r border-slate-700 w-24">Day</th>
                      {displayPeriods.map((p) => (
                        <th key={p.id} className="p-2 text-center border-r border-slate-700 last:border-r-0">
                          <div>{p.name}</div>
                          <div className="text-[9px] font-normal opacity-80">{p.startTime} - {p.endTime}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-300 dark:divide-slate-700">
                    {STANDARD_DAYS.map((day) => (
                      <tr key={day}>
                        <td className="p-2.5 text-center font-bold bg-slate-100 dark:bg-slate-800/40 border-r border-slate-300 dark:border-slate-700">
                          {day}
                        </td>
                        {displayPeriods.map((p) => {
                          if (p.isBreak) {
                            return (
                              <td key={p.id} className="p-2 text-center text-amber-600 font-bold bg-amber-50 dark:bg-amber-950/20 border-r border-slate-300 dark:border-slate-700 text-[10px]">
                                TIFFIN BREAK
                              </td>
                            );
                          }
                          const entry = teacherMatrix[day]?.[p.id];
                          return (
                            <td key={p.id} className="p-2 text-center border-r border-slate-300 dark:border-slate-700 last:border-r-0 text-[11px]">
                              {entry ? (
                                <div>
                                  <strong className="block text-emerald-600 dark:text-emerald-400 font-bold">{entry.className} ({entry.sectionName || 'Padma'})</strong>
                                  <span className="text-[10px] text-slate-500">{entry.subjectName}</span>
                                  <span className="block text-[9px] text-slate-400">{entry.roomNumber}</span>
                                </div>
                              ) : (
                                <span className="text-slate-300">Off</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Signatures */}
              <div className="pt-12 grid grid-cols-3 gap-6 text-center text-xs text-slate-500">
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Teacher Signature
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Academic In-Charge
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2 font-bold text-slate-700 dark:text-slate-300">
                  Principal Signature & Stamp
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
