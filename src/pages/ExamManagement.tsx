import React, { useState, useMemo } from 'react';
import {
  GraduationCap,
  Award,
  CheckCircle2,
  Calendar,
  FileSpreadsheet,
  Printer,
  Search,
  Filter,
  Save,
  Plus,
  BookOpen,
  TrendingUp,
  Percent,
  Download,
  Eye,
  X,
  FileText,
  UserCheck,
  Building,
  School,
  Clock,
  MapPin,
} from 'lucide-react';
import {
  SchoolSetting,
  User,
  ExamTermInfo,
  GradingScaleInfo,
  ExamScheduleInfo,
  StudentMarkRecord,
  ExamResultSummaryInfo,
  SchoolClassInfo,
  SubjectInfo,
  Student,
} from '../types';
import { StorageService } from '../services/storage';

interface ExamManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const ExamManagement: React.FC<ExamManagementProps> = ({
  isDark,
  schoolSetting,
  currentUser,
}) => {
  // Tabs: tabulation, marks_entry, routines, grading_scale
  const [activeTab, setActiveTab] = useState<'tabulation' | 'marks_entry' | 'routines' | 'grading_scale'>('tabulation');

  // Master Data
  const [terms, setTerms] = useState<ExamTermInfo[]>(() => StorageService.getExamTerms());
  const [selectedTermId, setSelectedTermId] = useState<number>(() => terms[0]?.id || 1);
  const [classes] = useState<SchoolClassInfo[]>(() => StorageService.getDetailedClasses());
  const [selectedClassId, setSelectedClassId] = useState<number>(() => classes[4]?.id || 5); // Class 10 default
  const [subjects] = useState<SubjectInfo[]>(() => StorageService.getSubjects());
  const [selectedSubjectId, setSelectedSubjectId] = useState<number>(() => subjects[0]?.id || 1);
  const [students] = useState<Student[]>(() => StorageService.getStudents());
  const [gradingScales] = useState<GradingScaleInfo[]>(() => StorageService.getGradingScales());

  // Marks and Summaries state
  const [marks, setMarks] = useState<StudentMarkRecord[]>(() => StorageService.getStudentMarks());
  const [summaries, setSummaries] = useState<ExamResultSummaryInfo[]>(() => StorageService.getExamResultSummaries());
  const [schedules, setSchedules] = useState<ExamScheduleInfo[]>(() => StorageService.getExamSchedules());

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [sectionFilter, setSectionFilter] = useState('all');

  // Modals
  const [showReportCardModal, setShowReportCardModal] = useState(false);
  const [selectedReportStudent, setSelectedReportStudent] = useState<ExamResultSummaryInfo | null>(null);

  const [showAdmitCardModal, setShowAdmitCardModal] = useState(false);
  const [selectedAdmitStudent, setSelectedAdmitStudent] = useState<Student | null>(null);

  const [showNewScheduleModal, setShowNewScheduleModal] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    subjectId: subjects[0]?.id || 1,
    examDate: '2026-04-26',
    startTime: '10:00 AM',
    endTime: '01:00 PM',
    roomNumber: 'Room 303',
    fullMarks: 100,
    theoryFull: 70,
    mcqFull: 30,
    practicalFull: 0,
  });

  const [showNewTermModal, setShowNewTermModal] = useState(false);
  const [newTerm, setNewTerm] = useState({
    name: '',
    examCode: '',
    startDate: '',
    endDate: '',
    status: 'Scheduled' as const,
    description: '',
  });

  const currentClass = classes.find((c) => c.id === selectedClassId);
  const classStudents = useMemo(() => {
    return students.filter(
      (s) =>
        (s.className === currentClass?.name ||
          s.className.toLowerCase().includes((currentClass?.name || '').toLowerCase())) &&
        s.status === 'active'
    );
  }, [students, currentClass]);

  const [marksBuffer, setMarksBuffer] = useState<Record<number, {
    theoryMarks: number;
    mcqMarks: number;
    practicalMarks: number;
    caMarks: number;
    isAbsent: boolean;
    remarks: string;
  }>>({});

  // Synchronize marksBuffer when term, class or subject changes
  React.useEffect(() => {
    const existingMarks = StorageService.getStudentMarks(selectedTermId, selectedClassId, selectedSubjectId);
    const buf: Record<number, {
      theoryMarks: number;
      mcqMarks: number;
      practicalMarks: number;
      caMarks: number;
      isAbsent: boolean;
      remarks: string;
    }> = {};

    classStudents.forEach((student) => {
      const rec = existingMarks.find((m) => m.studentId === student.id);
      if (rec) {
        buf[student.id] = {
          theoryMarks: rec.theoryMarks,
          mcqMarks: rec.mcqMarks,
          practicalMarks: rec.practicalMarks,
          caMarks: rec.caMarks,
          isAbsent: rec.isAbsent,
          remarks: rec.remarks || '',
        };
      } else {
        buf[student.id] = {
          theoryMarks: 0,
          mcqMarks: 0,
          practicalMarks: 0,
          caMarks: 0,
          isAbsent: false,
          remarks: '',
        };
      }
    });
    setMarksBuffer(buf);
  }, [selectedTermId, selectedClassId, selectedSubjectId, classStudents]);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // KPI Calculations
  const stats = useMemo(() => {
    const termSummaries = summaries.filter((s) => s.examTermId === selectedTermId && s.classId === selectedClassId);
    const totalExaminees = termSummaries.length;
    const passed = termSummaries.filter((s) => s.passedAll).length;
    const passRate = totalExaminees > 0 ? ((passed / totalExaminees) * 100).toFixed(1) : '0';
    const gpa5Count = termSummaries.filter((s) => s.gpa === 5.0).length;
    const classSchedules = schedules.filter((s) => s.examTermId === selectedTermId && s.classId === selectedClassId);

    return {
      totalExaminees,
      passed,
      passRate,
      gpa5Count,
      scheduledExams: classSchedules.length,
    };
  }, [summaries, schedules, selectedTermId, selectedClassId]);

  // Tabulation Filtered Summaries
  const filteredSummaries = useMemo(() => {
    return summaries
      .filter((s) => s.examTermId === selectedTermId && s.classId === selectedClassId)
      .filter((s) => {
        if (sectionFilter !== 'all' && s.sectionName?.toLowerCase() !== sectionFilter.toLowerCase()) {
          return false;
        }
        if (searchQuery) {
          const q = searchQuery.toLowerCase();
          return (
            s.studentName.toLowerCase().includes(q) ||
            s.studentCode.toLowerCase().includes(q) ||
            s.rollNumber.toString().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => (a.classRank || 999) - (b.classRank || 999));
  }, [summaries, selectedTermId, selectedClassId, sectionFilter, searchQuery]);

  // Handle Save Marks
  const handleSaveMarks = () => {
    const marksList = Object.entries(marksBuffer).map(([stdIdStr, data]) => ({
      studentId: Number(stdIdStr),
      ...data,
    }));

    const updated = StorageService.upsertStudentMarks(
      selectedTermId,
      selectedClassId,
      selectedSubjectId,
      marksList
    );

    setMarks(StorageService.getStudentMarks());
    setSummaries(StorageService.getExamResultSummaries());
    showToast(`Successfully saved marks for ${updated.length} students & recomputed class GPA!`);
  };

  // Handle Mark Buffer Change
  const handleMarkChange = (
    studentId: number,
    field: 'theoryMarks' | 'mcqMarks' | 'practicalMarks' | 'caMarks' | 'isAbsent' | 'remarks',
    value: any
  ) => {
    setMarksBuffer((prev) => ({
      ...prev,
      [studentId]: {
        ...prev[studentId],
        [field]: value,
      },
    }));
  };

  // Handle Recompile
  const handleRecompile = () => {
    const recompiled = StorageService.compileClassResults(selectedTermId, selectedClassId);
    setSummaries(StorageService.getExamResultSummaries());
    showToast(`Recompiled merit rankings for ${recompiled.length} students in ${selectedClass?.name || 'Class'}!`);
  };

  // Handle Add Schedule
  const handleAddSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    const sub = subjects.find((s) => s.id === Number(newSchedule.subjectId));
    if (!sub) return;

    StorageService.createExamSchedule({
      examTermId: selectedTermId,
      classId: selectedClassId,
      className: selectedClass?.name || 'Class',
      subjectId: sub.id,
      subjectName: sub.name,
      subjectCode: sub.code,
      examDate: newSchedule.examDate,
      startTime: newSchedule.startTime,
      endTime: newSchedule.endTime,
      roomNumber: newSchedule.roomNumber,
      fullMarks: Number(newSchedule.fullMarks),
      theoryFull: Number(newSchedule.theoryFull),
      mcqFull: Number(newSchedule.mcqFull),
      practicalFull: Number(newSchedule.practicalFull),
    });

    setSchedules(StorageService.getExamSchedules());
    setShowNewScheduleModal(false);
    showToast(`Exam timetable slot added for ${sub.name}!`);
  };

  // Handle Create Term
  const handleCreateTerm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTerm.name || !newTerm.examCode) return;
    const term = StorageService.createExamTerm({
      name: newTerm.name,
      examCode: newTerm.examCode,
      academicYearId: 1,
      academicYearName: '2025-2026',
      startDate: newTerm.startDate || '2026-05-01',
      endDate: newTerm.endDate || '2026-05-15',
      status: newTerm.status,
      description: newTerm.description,
    });
    setTerms(StorageService.getExamTerms());
    setSelectedTermId(term.id);
    setShowNewTermModal(false);
    showToast(`New Exam Term "${term.name}" created!`);
  };

  // Export Tabulation CSV
  const handleExportCSV = () => {
    const header = [
      'Rank',
      'Roll',
      'Student ID',
      'Student Name',
      'Class',
      'Section',
      'Total Marks',
      'Percentage',
      'GPA (5.0)',
      'Overall Grade',
      'Status',
      'Remarks',
    ];

    const rows = filteredSummaries.map((s) => [
      s.classRank || '-',
      s.rollNumber,
      s.studentCode,
      `"${s.studentName}"`,
      s.className,
      s.sectionName || '',
      s.totalObtained,
      `${s.percentage}%`,
      s.gpa.toFixed(2),
      s.overallGrade,
      s.passedAll ? 'PASSED' : 'FAILED',
      `"${s.remarks || ''}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [header.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Tabulation_Sheet_${selectedClass?.name || 'Class'}_${selectedTerm?.name || 'Exam'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Tabulation sheet CSV exported successfully!');
  };

  const selectedClass = classes.find((c) => c.id === selectedClassId);
  const selectedTerm = terms.find((t) => t.id === selectedTermId);
  const selectedSubject = subjects.find((s) => s.id === selectedSubjectId);

  // Helper for GPA color
  const getGpaBadgeClass = (gpa: number, passed: boolean) => {
    if (!passed) return 'bg-red-500/15 text-red-500 border border-red-500/30';
    if (gpa === 5.0) return 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30';
    if (gpa >= 4.0) return 'bg-blue-500/15 text-blue-500 border border-blue-500/30';
    if (gpa >= 3.5) return 'bg-cyan-500/15 text-cyan-500 border border-cyan-500/30';
    if (gpa >= 3.0) return 'bg-amber-500/15 text-amber-500 border border-amber-500/30';
    return 'bg-purple-500/15 text-purple-500 border border-purple-500/30';
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

      {/* Top Header & Context Controls */}
      <div className={`p-6 rounded-2xl border transition-colors ${
        isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-500">
                <GraduationCap className="w-6 h-6" />
              </div>
              <h1 className={`text-2xl font-bold tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
                Examinations, Grading & Result Publication
              </h1>
            </div>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Manage examination terms, routines, theory/MCQ/practical marks distribution, GPA 5.0 grading, tabulations, and academic transcripts.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Term Selector */}
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Term:
              </span>
              <select
                value={selectedTermId}
                onChange={(e) => setSelectedTermId(Number(e.target.value))}
                className={`text-sm font-medium px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-white'
                    : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                {terms.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.status})
                  </option>
                ))}
              </select>
            </div>

            {/* Class Selector */}
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Class:
              </span>
              <select
                value={selectedClassId}
                onChange={(e) => setSelectedClassId(Number(e.target.value))}
                className={`text-sm font-medium px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-white'
                    : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.group})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setShowNewTermModal(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>New Term</span>
            </button>
          </div>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Class Examinees</span>
              <Award className="w-4 h-4 text-blue-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.totalExaminees}
            </div>
            <span className="text-[11px] text-slate-400">{selectedClass?.name || 'Class'} candidates</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Passed All</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="text-2xl font-bold text-emerald-500">
              {stats.passed}
            </div>
            <span className="text-[11px] text-slate-400">Zero failing subjects</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Pass Rate</span>
              <Percent className="w-4 h-4 text-cyan-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.passRate}%
            </div>
            <span className="text-[11px] text-slate-400">Class success index</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>GPA 5.0 (Golden)</span>
              <TrendingUp className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-bold text-amber-500">
              {stats.gpa5Count}
            </div>
            <span className="text-[11px] text-slate-400">Top honors distinction</span>
          </div>

          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
              <span>Routines Scheduled</span>
              <Calendar className="w-4 h-4 text-purple-500" />
            </div>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              {stats.scheduledExams}
            </div>
            <span className="text-[11px] text-slate-400">Subject exam slots</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('tabulation')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'tabulation'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Award className="w-4 h-4" />
          <span>Tabulation Sheet & Merit Rankings</span>
        </button>

        <button
          onClick={() => setActiveTab('marks_entry')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'marks_entry'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Marks Entry Register</span>
        </button>

        <button
          onClick={() => setActiveTab('routines')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'routines'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Exam Routines & Timetable</span>
        </button>

        <button
          onClick={() => setActiveTab('grading_scale')}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'grading_scale'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Grading System Scale (GPA 5.0)</span>
        </button>
      </div>

      {/* TAB 1: TABULATION SHEET & MERIT RANKINGS */}
      {activeTab === 'tabulation' && (
        <div className="space-y-4">
          {/* Action and Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search student or roll..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full text-sm pl-9 pr-4 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    isDark
                      ? 'bg-slate-900 border-slate-800 text-white placeholder-slate-500'
                      : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
                  }`}
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={sectionFilter}
                  onChange={(e) => setSectionFilter(e.target.value)}
                  className={`text-sm px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    isDark
                      ? 'bg-slate-900 border-slate-800 text-white'
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="all">All Sections</option>
                  <option value="Padma">Padma</option>
                  <option value="Meghna">Meghna</option>
                  <option value="Jamuna">Jamuna</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
              <button
                onClick={handleRecompile}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold border border-indigo-500/30 text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                title="Re-run pass/fail rules, merit rankings, and GPA aggregations"
              >
                <TrendingUp className="w-4 h-4" />
                <span>Recompile Merit</span>
              </button>

              <button
                onClick={handleExportCSV}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
              >
                <FileSpreadsheet className="w-4 h-4" />
                <span>Export Tabulation</span>
              </button>
            </div>
          </div>

          {/* Tabulation Table */}
          <div className={`overflow-x-auto rounded-2xl border ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className={`border-b text-xs font-semibold uppercase tracking-wider ${
                  isDark ? 'border-slate-800 text-slate-400 bg-slate-800/30' : 'border-slate-200 text-slate-600 bg-slate-50'
                }`}>
                  <th className="py-3.5 px-4 text-center">Rank</th>
                  <th className="py-3.5 px-4">Student</th>
                  <th className="py-3.5 px-3">Roll</th>
                  <th className="py-3.5 px-3">Section</th>
                  <th className="py-3.5 px-4 text-right">Total Marks</th>
                  <th className="py-3.5 px-4 text-center">Percentage</th>
                  <th className="py-3.5 px-4 text-center">GPA (5.0)</th>
                  <th className="py-3.5 px-4 text-center">Grade</th>
                  <th className="py-3.5 px-4 text-center">Result Status</th>
                  <th className="py-3.5 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {filteredSummaries.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="py-8 text-center text-slate-400">
                      No results compiled yet for this term and class. Enter marks or click "Recompile Merit".
                    </td>
                  </tr>
                ) : (
                  filteredSummaries.map((s) => (
                    <tr
                      key={s.id}
                      className={`hover:bg-slate-500/5 transition-colors ${
                        !s.passedAll ? (isDark ? 'bg-red-950/10' : 'bg-red-50/50') : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 text-center font-bold">
                        {s.classRank ? (
                          <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-extrabold ${
                            s.classRank === 1
                              ? 'bg-amber-400/20 text-amber-500 border border-amber-400/40'
                              : s.classRank === 2
                              ? 'bg-slate-300/20 text-slate-400 border border-slate-300/40'
                              : s.classRank === 3
                              ? 'bg-amber-600/20 text-amber-600 border border-amber-600/40'
                              : isDark
                              ? 'text-slate-400'
                              : 'text-slate-600'
                          }`}>
                            {s.classRank}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {s.studentName}
                        </div>
                        <div className="text-xs text-slate-400 font-mono">
                          {s.studentCode}
                        </div>
                      </td>
                      <td className="py-3.5 px-3 font-semibold text-slate-800 dark:text-slate-200">
                        {s.rollNumber}
                      </td>
                      <td className="py-3.5 px-3 text-slate-600 dark:text-slate-400">
                        {s.sectionName || 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-slate-900 dark:text-white">
                        {s.totalObtained} <span className="text-xs text-slate-400 font-normal">/ {s.totalFullMarks}</span>
                      </td>
                      <td className="py-3.5 px-4 text-center font-medium text-slate-700 dark:text-slate-300">
                        {s.percentage.toFixed(1)}%
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${getGpaBadgeClass(s.gpa, s.passedAll)}`}>
                          {s.gpa.toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className={`font-extrabold text-sm ${
                          s.overallGrade === 'A+' ? 'text-emerald-500' :
                          s.overallGrade === 'A' ? 'text-blue-500' :
                          s.overallGrade === 'F' ? 'text-red-500' :
                          isDark ? 'text-slate-200' : 'text-slate-800'
                        }`}>
                          {s.overallGrade}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {s.passedAll ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Passed</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/20" title={`Failed in ${s.failedSubjectCount} subject(s)`}>
                            <span>Failed ({s.failedSubjectCount})</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => {
                              setSelectedReportStudent(s);
                              setShowReportCardModal(true);
                            }}
                            className="p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                            title="Generate & Print Academic Transcript / Report Card"
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: MARKS ENTRY REGISTER */}
      {activeTab === 'marks_entry' && (
        <div className="space-y-4">
          {/* Controls */}
          <div className={`p-4 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Subject:
                </span>
                <select
                  value={selectedSubjectId}
                  onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
                  className={`text-sm font-semibold px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    isDark
                      ? 'bg-slate-800 border-slate-700 text-white'
                      : 'bg-slate-50 border-slate-300 text-slate-800'
                  }`}
                >
                  {subjects.map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.name} ({sub.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="text-xs text-slate-400">
                Full Marks: <strong className="text-slate-700 dark:text-slate-200">100</strong> (Theory: 70, MCQ: 30) | Pass: <strong className="text-slate-700 dark:text-slate-200">33</strong>
              </div>
            </div>

            <button
              onClick={handleSaveMarks}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-colors"
            >
              <Save className="w-4 h-4" />
              <span>Save & Compile Marks</span>
            </button>
          </div>

          {/* Marks Entry Grid */}
          <div className={`overflow-x-auto rounded-2xl border ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className={`border-b text-xs font-semibold uppercase tracking-wider ${
                  isDark ? 'border-slate-800 text-slate-400 bg-slate-800/30' : 'border-slate-200 text-slate-600 bg-slate-50'
                }`}>
                  <th className="py-3 px-4 w-12 text-center">Roll</th>
                  <th className="py-3 px-4">Student Name</th>
                  <th className="py-3 px-3 text-center w-28">Theory (70)</th>
                  <th className="py-3 px-3 text-center w-28">MCQ (30)</th>
                  <th className="py-3 px-3 text-center w-28">Practical (25)</th>
                  <th className="py-3 px-3 text-center w-28">CA (20)</th>
                  <th className="py-3 px-3 text-center w-24">Total</th>
                  <th className="py-3 px-3 text-center w-24">Absent</th>
                  <th className="py-3 px-3 text-center w-20">Grade</th>
                  <th className="py-3 px-4">Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {classStudents.map((std) => {
                  const entry = marksBuffer[std.id] || {
                    theoryMarks: 0,
                    mcqMarks: 0,
                    practicalMarks: 0,
                    caMarks: 0,
                    isAbsent: false,
                    remarks: '',
                  };

                  const currentTotal = entry.isAbsent
                    ? 0
                    : Number(entry.theoryMarks || 0) +
                      Number(entry.mcqMarks || 0) +
                      Number(entry.practicalMarks || 0) +
                      Number(entry.caMarks || 0);

                  const grade = entry.isAbsent
                    ? { gradeName: 'F', gradePoint: 0.0, isPassed: false }
                    : StorageService.getGradeForScore(currentTotal);

                  return (
                    <tr
                      key={std.id}
                      className={`hover:bg-slate-500/5 transition-colors ${
                        entry.isAbsent ? (isDark ? 'bg-red-950/20' : 'bg-red-50') : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center font-bold text-slate-900 dark:text-white">
                        {std.rollNumber}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {std.firstName} {std.lastName}
                        </div>
                        <div className="text-xs text-slate-400 font-mono">
                          {std.studentId}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          disabled={entry.isAbsent}
                          value={entry.theoryMarks}
                          onChange={(e) => handleMarkChange(std.id, 'theoryMarks', Math.max(0, Number(e.target.value)))}
                          className={`w-20 text-center font-semibold py-1.5 rounded-lg border focus:ring-2 focus:ring-indigo-500 ${
                            isDark
                              ? 'bg-slate-800 border-slate-700 text-white disabled:opacity-30'
                              : 'bg-white border-slate-300 text-slate-900 disabled:opacity-30'
                          }`}
                        />
                      </td>
                      <td className="py-2 px-3 text-center">
                        <input
                          type="number"
                          min="0"
                          max="50"
                          disabled={entry.isAbsent}
                          value={entry.mcqMarks}
                          onChange={(e) => handleMarkChange(std.id, 'mcqMarks', Math.max(0, Number(e.target.value)))}
                          className={`w-20 text-center font-semibold py-1.5 rounded-lg border focus:ring-2 focus:ring-indigo-500 ${
                            isDark
                              ? 'bg-slate-800 border-slate-700 text-white disabled:opacity-30'
                              : 'bg-white border-slate-300 text-slate-900 disabled:opacity-30'
                          }`}
                        />
                      </td>
                      <td className="py-2 px-3 text-center">
                        <input
                          type="number"
                          min="0"
                          max="50"
                          disabled={entry.isAbsent}
                          value={entry.practicalMarks}
                          onChange={(e) => handleMarkChange(std.id, 'practicalMarks', Math.max(0, Number(e.target.value)))}
                          className={`w-20 text-center font-semibold py-1.5 rounded-lg border focus:ring-2 focus:ring-indigo-500 ${
                            isDark
                              ? 'bg-slate-800 border-slate-700 text-white disabled:opacity-30'
                              : 'bg-white border-slate-300 text-slate-900 disabled:opacity-30'
                          }`}
                        />
                      </td>
                      <td className="py-2 px-3 text-center">
                        <input
                          type="number"
                          min="0"
                          max="30"
                          disabled={entry.isAbsent}
                          value={entry.caMarks}
                          onChange={(e) => handleMarkChange(std.id, 'caMarks', Math.max(0, Number(e.target.value)))}
                          className={`w-20 text-center font-semibold py-1.5 rounded-lg border focus:ring-2 focus:ring-indigo-500 ${
                            isDark
                              ? 'bg-slate-800 border-slate-700 text-white disabled:opacity-30'
                              : 'bg-white border-slate-300 text-slate-900 disabled:opacity-30'
                          }`}
                        />
                      </td>
                      <td className="py-3 px-3 text-center font-extrabold text-base text-slate-900 dark:text-white">
                        {currentTotal}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <label className="inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={entry.isAbsent}
                            onChange={(e) => handleMarkChange(std.id, 'isAbsent', e.target.checked)}
                            className="rounded border-slate-300 text-red-600 focus:ring-red-500 h-4 w-4"
                          />
                        </label>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          grade.gradeName === 'A+' ? 'bg-emerald-500/20 text-emerald-500' :
                          grade.gradeName === 'F' ? 'bg-red-500/20 text-red-500' :
                          'bg-indigo-500/20 text-indigo-500'
                        }`}>
                          {grade.gradeName}
                        </span>
                      </td>
                      <td className="py-2 px-4">
                        <input
                          type="text"
                          placeholder="Optional feedback..."
                          value={entry.remarks}
                          onChange={(e) => handleMarkChange(std.id, 'remarks', e.target.value)}
                          className={`w-full text-xs py-1.5 px-3 rounded-lg border focus:ring-2 focus:ring-indigo-500 ${
                            isDark
                              ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500'
                              : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
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

      {/* TAB 3: EXAM ROUTINES & TIMETABLES */}
      {activeTab === 'routines' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
              Exam Timetable & Schedule ({selectedTerm?.name} — {selectedClass?.name})
            </h2>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowNewScheduleModal(true)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>Add Exam Slot</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {schedules
              .filter((s) => s.examTermId === selectedTermId && s.classId === selectedClassId)
              .map((sch) => (
                <div
                  key={sch.id}
                  className={`p-5 rounded-2xl border transition-all ${
                    isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="text-xs font-bold text-indigo-500 bg-indigo-500/10 px-2.5 py-1 rounded-full uppercase">
                        {sch.subjectCode}
                      </span>
                      <h3 className={`text-base font-bold mt-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                        {sch.subjectName}
                      </h3>
                    </div>
                    <div className="p-2 rounded-xl bg-slate-500/10 text-slate-400">
                      <Clock className="w-5 h-5" />
                    </div>
                  </div>

                  <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-800 pt-3">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-indigo-400" />
                      <span className="font-semibold text-slate-700 dark:text-slate-200">{sch.examDate}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-amber-400" />
                      <span>{sch.startTime} - {sch.endTime}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-emerald-400" />
                      <span>Hall / Room: <strong className="text-slate-700 dark:text-slate-200">{sch.roomNumber}</strong></span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-400">Total Marks: {sch.fullMarks}</span>
                    <span className="text-slate-500">
                      TH: {sch.theoryFull} | MCQ: {sch.mcqFull} | PR: {sch.practicalFull}
                    </span>
                  </div>
                </div>
              ))}
          </div>

          {/* Admit Cards Section */}
          <div className={`mt-8 p-6 rounded-2xl border ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className={`text-base font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  Candidate Exam Admit Cards ({selectedClass?.name})
                </h3>
                <p className="text-xs text-slate-400">
                  Generate and print official examination hall admission cards with subject routines and instructions.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {classStudents.map((std) => (
                <div
                  key={std.id}
                  className={`p-3 rounded-xl border flex items-center justify-between ${
                    isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div>
                    <div className="text-xs font-bold text-slate-900 dark:text-white">
                      Roll {std.rollNumber} - {std.firstName} {std.lastName}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {std.studentId} | Sec: {std.sectionName}
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedAdmitStudent(std);
                      setShowAdmitCardModal(true);
                    }}
                    className="p-1.5 rounded-lg text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                    title="Print Admit Card"
                  >
                    <Printer className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GRADING SYSTEM SCALE (GPA 5.0) */}
      {activeTab === 'grading_scale' && (
        <div className="space-y-6">
          <div className={`p-6 rounded-2xl border ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <h2 className={`text-lg font-bold mb-1 ${isDark ? 'text-white' : 'text-slate-900'}`}>
              Standard National Grading System (GPA 5.0 Scale)
            </h2>
            <p className="text-xs text-slate-400 mb-6">
              Official grading conversion scale used for all terminal, mid-term, model, and final promotional evaluations.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className={`border-b text-xs font-semibold uppercase tracking-wider ${
                    isDark ? 'border-slate-800 text-slate-400 bg-slate-800/30' : 'border-slate-200 text-slate-600 bg-slate-50'
                  }`}>
                    <th className="py-3 px-4">Numeric Score Range</th>
                    <th className="py-3 px-4 text-center">Letter Grade</th>
                    <th className="py-3 px-4 text-center">Grade Point (GP)</th>
                    <th className="py-3 px-4">Performance Assessment</th>
                    <th className="py-3 px-4 text-center">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {gradingScales.map((scale) => (
                    <tr key={scale.id} className="hover:bg-slate-500/5 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-800 dark:text-slate-200">
                        {scale.markFrom}% — {scale.markTo}%
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-base text-indigo-500">
                        {scale.gradeName}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-slate-900 dark:text-white">
                        {scale.gradePoint.toFixed(1)}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 dark:text-slate-300">
                        {scale.remarks}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {scale.gradePoint > 0 ? (
                          <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                            Passed
                          </span>
                        ) : (
                          <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/20">
                            Failed
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Crucial Grading Rules */}
            <div className={`mt-8 p-5 rounded-xl border ${
              isDark ? 'bg-amber-950/20 border-amber-900/40 text-amber-200' : 'bg-amber-50 border-amber-200 text-amber-900'
            }`}>
              <div className="flex items-center gap-2 font-bold text-sm mb-2">
                <CheckCircle2 className="w-4 h-4 text-amber-500" />
                <span>System Policy: Mandatory Fail-Lock Enforcement</span>
              </div>
              <ul className="text-xs space-y-1.5 list-disc list-inside opacity-90">
                <li>
                  <strong>Subject Minimum:</strong> A candidate must obtain at least 33% marks (or grade 'D') in each individual subject to be considered passed.
                </li>
                <li>
                  <strong>Fail-Lock Rule:</strong> If a student fails (mark &lt; 33) or is marked absent in ANY single subject, their overall terminal GPA is rigidly computed as <strong>0.00</strong> with a letter grade of <strong>'F'</strong>, regardless of outstanding marks in other subjects.
                </li>
                <li>
                  <strong>Merit Ranking Priority:</strong> Students who pass in all subjects are ranked first according to highest GPA descending, followed by highest total obtained marks. Failed candidates are ranked subsequently.
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: STUDENT REPORT CARD / ACADEMIC TRANSCRIPT */}
      {showReportCardModal && selectedReportStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className={`w-full max-w-3xl rounded-2xl shadow-2xl border p-6 my-8 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2 font-bold text-indigo-500">
                <FileText className="w-5 h-5" />
                <span>Official Academic Transcript & Report Card</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Report Card</span>
                </button>
                <button
                  onClick={() => setShowReportCardModal(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Printable Transcript Layout */}
            <div className="py-6 space-y-6 printable-area">
              {/* Institution Header */}
              <div className="text-center pb-4 border-b border-slate-200 dark:border-slate-800">
                <div className="text-xl font-extrabold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
                  {schoolSetting.schoolName}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">
                  EIIN: {schoolSetting.eiinNumber} | Reg: {schoolSetting.registrationNo}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {schoolSetting.address}, {schoolSetting.city}, {schoolSetting.country}
                </div>
                <div className="inline-block mt-3 px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                  {selectedReportStudent.examTermName} — Progress Report
                </div>
              </div>

              {/* Student Profile Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-500/5 p-4 rounded-xl">
                <div>
                  <span className="text-slate-400 block">Student Name:</span>
                  <strong className="text-sm">{selectedReportStudent.studentName}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block">Student ID:</span>
                  <strong className="font-mono">{selectedReportStudent.studentCode}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block">Class & Section:</span>
                  <strong>{selectedReportStudent.className} ({selectedReportStudent.sectionName || 'Padma'})</strong>
                </div>
                <div>
                  <span className="text-slate-400 block">Roll Number:</span>
                  <strong className="text-base text-indigo-500">{selectedReportStudent.rollNumber}</strong>
                </div>
              </div>

              {/* Subject Marks Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-800">
                  <thead>
                    <tr className="bg-slate-500/10 font-bold border-b border-slate-200 dark:border-slate-800">
                      <th className="p-2.5">Subject</th>
                      <th className="p-2.5 text-center">Full</th>
                      <th className="p-2.5 text-center">Theory</th>
                      <th className="p-2.5 text-center">MCQ</th>
                      <th className="p-2.5 text-center">Practical</th>
                      <th className="p-2.5 text-center">Obtained</th>
                      <th className="p-2.5 text-center">Grade</th>
                      <th className="p-2.5 text-center">Point</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {marks
                      .filter((m) => m.examTermId === selectedReportStudent.examTermId && m.studentId === selectedReportStudent.studentId)
                      .map((m) => (
                        <tr key={m.id}>
                          <td className="p-2.5 font-medium">
                            {m.subjectName} <span className="text-[10px] text-slate-400 font-mono">({m.subjectCode})</span>
                          </td>
                          <td className="p-2.5 text-center text-slate-400">100</td>
                          <td className="p-2.5 text-center">{m.theoryMarks}</td>
                          <td className="p-2.5 text-center">{m.mcqMarks}</td>
                          <td className="p-2.5 text-center">{m.practicalMarks}</td>
                          <td className="p-2.5 text-center font-bold">{m.totalMarks}</td>
                          <td className="p-2.5 text-center font-bold text-indigo-500">{m.gradeName}</td>
                          <td className="p-2.5 text-center font-bold">{m.gradePoint.toFixed(1)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>

              {/* Result Summary Box */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-center">
                <div>
                  <span className="text-slate-400 block text-xs">Total Marks:</span>
                  <span className="text-base font-extrabold">{selectedReportStudent.totalObtained} / {selectedReportStudent.totalFullMarks}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-xs">Percentage:</span>
                  <span className="text-base font-extrabold">{selectedReportStudent.percentage.toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-xs">Grade Point Average:</span>
                  <span className="text-xl font-extrabold text-indigo-600 dark:text-indigo-400">
                    {selectedReportStudent.gpa.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-xs">Overall Result:</span>
                  <span className={`text-sm font-extrabold ${selectedReportStudent.passedAll ? 'text-emerald-500' : 'text-red-500'}`}>
                    {selectedReportStudent.passedAll ? `PASSED (${selectedReportStudent.overallGrade})` : 'FAILED (F)'}
                  </span>
                  <span className="block text-[10px] text-slate-400">Rank #{selectedReportStudent.classRank}</span>
                </div>
              </div>

              {/* Signatures */}
              <div className="pt-12 grid grid-cols-3 gap-6 text-center text-xs text-slate-500">
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Class Teacher
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2">
                  Head of Examinations
                </div>
                <div className="border-t border-slate-300 dark:border-slate-700 pt-2 font-bold text-slate-700 dark:text-slate-300">
                  Principal Signature
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: CANDIDATE ADMIT CARD */}
      {showAdmitCardModal && selectedAdmitStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className={`w-full max-w-2xl rounded-2xl shadow-2xl border p-6 my-8 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-sm text-indigo-500">Candidate Admit Card</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Admit</span>
                </button>
                <button onClick={() => setShowAdmitCardModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="py-4 space-y-4 printable-area">
              <div className="text-center pb-2 border-b border-slate-200 dark:border-slate-800">
                <div className="font-bold text-base uppercase text-indigo-500">{schoolSetting.schoolName}</div>
                <div className="text-xs text-slate-400">EXAMINATION ADMIT CARD — {selectedTerm?.name}</div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-slate-500/5 p-3 rounded-xl">
                <div>
                  <span className="text-slate-400 block text-[10px]">CANDIDATE:</span>
                  <strong>{selectedAdmitStudent.firstName} {selectedAdmitStudent.lastName}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">STUDENT ID:</span>
                  <strong className="font-mono">{selectedAdmitStudent.studentId}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">CLASS / SEC:</span>
                  <strong>{selectedClass?.name} - {selectedAdmitStudent.sectionName}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">ROLL NO:</span>
                  <strong className="text-base text-indigo-500">{selectedAdmitStudent.rollNumber}</strong>
                </div>
              </div>

              {/* Routine Schedule on Admit */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-800">
                  <thead>
                    <tr className="bg-slate-500/10 font-bold border-b border-slate-200 dark:border-slate-800">
                      <th className="p-2">Date</th>
                      <th className="p-2">Time</th>
                      <th className="p-2">Subject</th>
                      <th className="p-2 text-center">Room</th>
                      <th className="p-2 text-center">Invigilator Sign</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {schedules
                      .filter((s) => s.examTermId === selectedTermId && s.classId === selectedClassId)
                      .map((sch) => (
                        <tr key={sch.id}>
                          <td className="p-2 font-mono">{sch.examDate}</td>
                          <td className="p-2">{sch.startTime} - {sch.endTime}</td>
                          <td className="p-2 font-medium">{sch.subjectName}</td>
                          <td className="p-2 text-center font-bold">{sch.roomNumber}</td>
                          <td className="p-2 text-center text-slate-300">___________</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>

              <div className="p-3 bg-slate-500/5 rounded-lg text-[10px] text-slate-400 space-y-1">
                <div className="font-bold text-slate-600 dark:text-slate-300">Examination Instructions:</div>
                <div>1. Candidates must arrive at the examination hall at least 15 minutes prior to commencement.</div>
                <div>2. Mobile phones, electronic smartwatches, and programmable devices are strictly prohibited.</div>
                <div>3. Admit Card and Student ID badge must be placed on the desk throughout the test.</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: ADD SCHEDULE SLOT */}
      {showNewScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl border p-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-base">Add Exam Timetable Slot</span>
              <button onClick={() => setShowNewScheduleModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddSchedule} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Subject</label>
                <select
                  value={newSchedule.subjectId}
                  onChange={(e) => setNewSchedule({ ...newSchedule, subjectId: Number(e.target.value) })}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Exam Date</label>
                  <input
                    type="date"
                    required
                    value={newSchedule.examDate}
                    onChange={(e) => setNewSchedule({ ...newSchedule, examDate: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Room Number</label>
                  <input
                    type="text"
                    required
                    value={newSchedule.roomNumber}
                    onChange={(e) => setNewSchedule({ ...newSchedule, roomNumber: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Start Time</label>
                  <input
                    type="text"
                    value={newSchedule.startTime}
                    onChange={(e) => setNewSchedule({ ...newSchedule, startTime: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">End Time</label>
                  <input
                    type="text"
                    value={newSchedule.endTime}
                    onChange={(e) => setNewSchedule({ ...newSchedule, endTime: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewScheduleModal(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold border border-slate-600 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  Add Slot
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: CREATE EXAM TERM */}
      {showNewTermModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl border p-6 ${
            isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-base">Create New Exam Term</span>
              <button onClick={() => setShowNewTermModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateTerm} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Term Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2nd Terminal Examination 2026"
                  value={newTerm.name}
                  onChange={(e) => setNewTerm({ ...newTerm, name: e.target.value })}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-400">Exam Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. EXM-2026-T2"
                  value={newTerm.examCode}
                  onChange={(e) => setNewTerm({ ...newTerm, examCode: e.target.value })}
                  className={`w-full text-sm p-2.5 rounded-xl border ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">Start Date</label>
                  <input
                    type="date"
                    required
                    value={newTerm.startDate}
                    onChange={(e) => setNewTerm({ ...newTerm, startDate: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold mb-1 text-slate-400">End Date</label>
                  <input
                    type="date"
                    required
                    value={newTerm.endDate}
                    onChange={(e) => setNewTerm({ ...newTerm, endDate: e.target.value })}
                    className={`w-full text-sm p-2.5 rounded-xl border ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewTermModal(false)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold border border-slate-600 text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  Create Term
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
