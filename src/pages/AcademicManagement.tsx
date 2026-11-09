import React, { useState, useMemo } from 'react';
import {
  BookOpen,
  PlusCircle,
  Search,
  Filter,
  Edit,
  Trash2,
  Users,
  DoorOpen,
  CalendarDays,
  CheckCircle2,
  GraduationCap,
  Sparkles,
  Layers,
  X,
  AlertCircle,
} from 'lucide-react';
import {
  SchoolClassInfo,
  SectionInfo,
  SubjectInfo,
  AcademicYearInfo,
  Teacher,
  SchoolSetting,
  User,
} from '../types';
import { StorageService } from '../services/storage';

interface AcademicManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const AcademicManagement: React.FC<AcademicManagementProps> = ({
  isDark,
  schoolSetting,
}) => {
  const [activeTab, setActiveTab] = useState<'classes' | 'subjects' | 'sessions'>('classes');
  
  // Data states
  const [classes, setClasses] = useState<SchoolClassInfo[]>(() => StorageService.getDetailedClasses());
  const [sections, setSections] = useState<SectionInfo[]>(() => StorageService.getSections());
  const [subjects, setSubjects] = useState<SubjectInfo[]>(() => StorageService.getSubjects());
  const [academicYears, setAcademicYears] = useState<AcademicYearInfo[]>(() => StorageService.getAcademicYears());
  const [teachers] = useState<Teacher[]>(() => StorageService.getTeachers());

  // Filters
  const [classSearch, setClassSearch] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('all');
  const [subjectSearch, setSubjectSearch] = useState('');
  const [selectedClassForSub, setSelectedClassForSub] = useState<string>('all');

  // Modals
  const [isClassModalOpen, setIsClassModalOpen] = useState(false);
  const [editingClass, setEditingClass] = useState<SchoolClassInfo | null>(null);
  const [classFormData, setClassFormData] = useState({
    name: '',
    code: '',
    numericOrder: 9,
    group: 'General' as SchoolClassInfo['group'],
    shift: 'Morning' as SchoolClassInfo['shift'],
    academicYearId: 1,
  });

  const [isSectionModalOpen, setIsSectionModalOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<SectionInfo | null>(null);
  const [sectionFormData, setSectionFormData] = useState({
    name: '',
    classId: 1,
    roomNumber: '',
    capacity: 50,
    shift: 'Morning' as SectionInfo['shift'],
    group: 'General',
    classTeacherId: undefined as number | undefined,
  });

  const [isSubjectModalOpen, setIsSubjectModalOpen] = useState(false);
  const [editingSubject, setEditingSubject] = useState<SubjectInfo | null>(null);
  const [subjectFormData, setSubjectFormData] = useState({
    name: '',
    code: '',
    classId: 1,
    fullMarks: 100,
    passMarks: 33,
    theoryMarks: 75,
    practicalMarks: 25,
    subjectType: 'Mandatory' as SubjectInfo['subjectType'],
    teacherId: undefined as number | undefined,
  });

  const [isYearModalOpen, setIsYearModalOpen] = useState(false);
  const [yearFormData, setYearFormData] = useState({
    name: '2026-2027',
    startDate: '2026-01-01',
    endDate: '2026-12-31',
    isCurrent: false,
    status: 'Upcoming' as AcademicYearInfo['status'],
  });

  const refreshAll = () => {
    setClasses(StorageService.getDetailedClasses());
    setSections(StorageService.getSections());
    setSubjects(StorageService.getSubjects());
    setAcademicYears(StorageService.getAcademicYears());
  };

  // KPI calculations
  const activeYear = useMemo(() => academicYears.find((y) => y.isCurrent) || academicYears[0], [academicYears]);
  const totalStudents = useMemo(() => sections.reduce((acc, s) => acc + (s.studentCount || 0), 0), [sections]);

  // Filtered classes
  const filteredClasses = useMemo(() => {
    return classes.filter((c) => {
      const matchSearch =
        c.name.toLowerCase().includes(classSearch.toLowerCase()) ||
        c.code.toLowerCase().includes(classSearch.toLowerCase());
      const matchGroup = selectedGroup === 'all' || c.group === selectedGroup;
      return matchSearch && matchGroup;
    });
  }, [classes, classSearch, selectedGroup]);

  // Filtered subjects
  const filteredSubjects = useMemo(() => {
    return subjects.filter((s) => {
      const matchSearch =
        s.name.toLowerCase().includes(subjectSearch.toLowerCase()) ||
        s.code.toLowerCase().includes(subjectSearch.toLowerCase()) ||
        s.subjectId.toLowerCase().includes(subjectSearch.toLowerCase());
      const matchClass = selectedClassForSub === 'all' || s.classId === Number(selectedClassForSub);
      return matchSearch && matchClass;
    });
  }, [subjects, subjectSearch, selectedClassForSub]);

  // ==================== HANDLERS: CLASS ====================
  const handleOpenAddClass = () => {
    setEditingClass(null);
    setClassFormData({
      name: '',
      code: '',
      numericOrder: classes.length + 1,
      group: 'General',
      shift: 'Morning',
      academicYearId: activeYear ? activeYear.id : 1,
    });
    setIsClassModalOpen(true);
  };

  const handleOpenEditClass = (c: SchoolClassInfo) => {
    setEditingClass(c);
    setClassFormData({
      name: c.name,
      code: c.code,
      numericOrder: c.numericOrder,
      group: c.group,
      shift: c.shift,
      academicYearId: c.academicYearId,
    });
    setIsClassModalOpen(true);
  };

  const handleSaveClass = (e: React.FormEvent) => {
    e.preventDefault();
    if (!classFormData.name.trim()) return;

    const academicYearName = academicYears.find((y) => y.id === classFormData.academicYearId)?.name || '2025-2026';

    if (editingClass) {
      StorageService.updateClass(editingClass.id, {
        ...classFormData,
        academicYearName,
      });
    } else {
      StorageService.addClass({
        ...classFormData,
        academicYearName,
      });
    }
    setIsClassModalOpen(false);
    refreshAll();
  };

  const handleDeleteClass = (id: number, name: string) => {
    if (confirm(`Are you sure you want to delete '${name}'? This will remove all associated sections and subjects.`)) {
      StorageService.deleteClass(id);
      refreshAll();
    }
  };

  // ==================== HANDLERS: SECTION ====================
  const handleOpenAddSection = (defaultClassId?: number) => {
    setEditingSection(null);
    const targetClassId = defaultClassId || classes[0]?.id || 1;
    const targetClass = classes.find((c) => c.id === targetClassId);
    setSectionFormData({
      name: '',
      classId: targetClassId,
      roomNumber: '',
      capacity: 50,
      shift: targetClass?.shift || 'Morning',
      group: targetClass?.group || 'General',
      classTeacherId: undefined,
    });
    setIsSectionModalOpen(true);
  };

  const handleOpenEditSection = (s: SectionInfo) => {
    setEditingSection(s);
    setSectionFormData({
      name: s.name,
      classId: s.classId,
      roomNumber: s.roomNumber,
      capacity: s.capacity,
      shift: s.shift,
      group: s.group,
      classTeacherId: s.classTeacherId,
    });
    setIsSectionModalOpen(true);
  };

  const handleSaveSection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sectionFormData.name.trim()) return;

    const targetClass = classes.find((c) => c.id === Number(sectionFormData.classId));
    const targetTeacher = teachers.find((t) => t.id === Number(sectionFormData.classTeacherId));

    const payload = {
      name: sectionFormData.name,
      classId: Number(sectionFormData.classId),
      className: targetClass?.name || 'Unknown Class',
      roomNumber: sectionFormData.roomNumber,
      capacity: Number(sectionFormData.capacity),
      shift: sectionFormData.shift,
      group: sectionFormData.group,
      classTeacherId: targetTeacher?.id,
      classTeacherName: targetTeacher?.fullName,
    };

    if (editingSection) {
      StorageService.updateSection(editingSection.id, payload);
    } else {
      StorageService.addSection(payload);
    }
    setIsSectionModalOpen(false);
    refreshAll();
  };

  const handleDeleteSection = (id: number, name: string) => {
    if (confirm(`Remove section '${name}'?`)) {
      StorageService.deleteSection(id);
      refreshAll();
    }
  };

  // ==================== HANDLERS: SUBJECT ====================
  const handleOpenAddSubject = (defaultClassId?: number) => {
    setEditingSubject(null);
    setSubjectFormData({
      name: '',
      code: '',
      classId: defaultClassId || classes[0]?.id || 1,
      fullMarks: 100,
      passMarks: 33,
      theoryMarks: 75,
      practicalMarks: 25,
      subjectType: 'Mandatory',
      teacherId: undefined,
    });
    setIsSubjectModalOpen(true);
  };

  const handleOpenEditSubject = (s: SubjectInfo) => {
    setEditingSubject(s);
    setSubjectFormData({
      name: s.name,
      code: s.code,
      classId: s.classId,
      fullMarks: s.fullMarks,
      passMarks: s.passMarks,
      theoryMarks: s.theoryMarks,
      practicalMarks: s.practicalMarks,
      subjectType: s.subjectType,
      teacherId: s.teacherId,
    });
    setIsSubjectModalOpen(true);
  };

  const handleSaveSubject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subjectFormData.name.trim() || !subjectFormData.code.trim()) return;

    const targetClass = classes.find((c) => c.id === Number(subjectFormData.classId));
    const targetTeacher = teachers.find((t) => t.id === Number(subjectFormData.teacherId));

    const full = Number(subjectFormData.fullMarks);
    let theory = Number(subjectFormData.theoryMarks);
    const practical = Number(subjectFormData.practicalMarks);

    if (theory + practical !== full) {
      theory = full - practical;
    }

    const payload = {
      name: subjectFormData.name,
      code: subjectFormData.code,
      classId: Number(subjectFormData.classId),
      className: targetClass?.name || 'Class',
      fullMarks: full,
      passMarks: Number(subjectFormData.passMarks),
      theoryMarks: theory,
      practicalMarks: practical,
      subjectType: subjectFormData.subjectType,
      isOptional: subjectFormData.subjectType === 'Optional',
      teacherId: targetTeacher?.id,
      teacherName: targetTeacher?.fullName,
    };

    if (editingSubject) {
      StorageService.updateSubject(editingSubject.id, payload);
    } else {
      StorageService.addSubject(payload);
    }
    setIsSubjectModalOpen(false);
    refreshAll();
  };

  const handleDeleteSubject = (id: number, name: string) => {
    if (confirm(`Delete subject '${name}'?`)) {
      StorageService.deleteSubject(id);
      refreshAll();
    }
  };

  // ==================== HANDLERS: ACADEMIC YEAR ====================
  const handleSaveYear = (e: React.FormEvent) => {
    e.preventDefault();
    if (!yearFormData.name.trim()) return;
    StorageService.addAcademicYear(yearFormData);
    setIsYearModalOpen(false);
    refreshAll();
  };

  const handleSwitchActiveYear = (id: number) => {
    StorageService.setActiveAcademicYear(id);
    refreshAll();
  };

  return (
    <div className={`p-6 space-y-6 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
      {/* 1. Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-blue-500" />
              Academic & Curriculum Management
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold">
              Session: {activeYear?.name || '2025-2026'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Configure School Classes, Section Allocations, Class Teachers, and Subject Marks Breakdown
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center flex-wrap gap-2">
          <button
            onClick={handleOpenAddClass}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition-all"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Add Class</span>
          </button>
          <button
            onClick={() => handleOpenAddSection()}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all"
          >
            <DoorOpen className="w-3.5 h-3.5" />
            <span>Add Section</span>
          </button>
          <button
            onClick={() => handleOpenAddSubject()}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white shadow-sm transition-all"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Add Subject</span>
          </button>
        </div>
      </div>

      {/* 2. KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-3 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-500">
            <CalendarDays className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] text-slate-400 font-medium">Active Session</p>
            <p className="text-sm font-bold text-blue-400 truncate">{activeYear?.name}</p>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-3 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-500">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] text-slate-400 font-medium">Total Classes</p>
            <p className="text-sm font-bold text-indigo-400">{classes.length}</p>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-3 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-500">
            <DoorOpen className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] text-slate-400 font-medium">Active Sections</p>
            <p className="text-sm font-bold text-emerald-400">{sections.length}</p>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-3 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-500">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] text-slate-400 font-medium">Total Subjects</p>
            <p className="text-sm font-bold text-purple-400">{subjects.length}</p>
          </div>
        </div>

        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-3 ${
            isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-500">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[11px] text-slate-400 font-medium">Enrolled Students</p>
            <p className="text-sm font-bold text-amber-400">{totalStudents}</p>
          </div>
        </div>
      </div>

      {/* 3. Navigation Tabs */}
      <div className={`border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('classes')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'classes'
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>Classes & Section Roster ({classes.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('subjects')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'subjects'
                ? 'border-purple-500 text-purple-500'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Curriculum & Subjects ({subjects.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'sessions'
                ? 'border-emerald-500 text-emerald-500'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CalendarDays className="w-4 h-4" />
            <span>Academic Sessions & Years</span>
          </button>
        </div>
      </div>

      {/* 4. Tab 1 Content: Classes & Sections */}
      {activeTab === 'classes' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div
            className={`p-3 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-3 ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search class or code..."
                  value={classSearch}
                  onChange={(e) => setClassSearch(e.target.value)}
                  className={`w-full pl-9 pr-3 py-1.5 rounded-lg text-xs outline-none border transition-colors ${
                    isDark
                      ? 'bg-slate-950 border-slate-800 text-slate-100 focus:border-blue-500'
                      : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-blue-500'
                  }`}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={selectedGroup}
                  onChange={(e) => setSelectedGroup(e.target.value)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
                >
                  <option value="all">All Groups</option>
                  <option value="General">General</option>
                  <option value="Science">Science</option>
                  <option value="Humanities">Humanities</option>
                  <option value="Business Studies">Business Studies</option>
                </select>
              </div>
            </div>

            <span className="text-xs text-slate-400">
              Showing {filteredClasses.length} of {classes.length} Classes
            </span>
          </div>

          {/* Classes Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredClasses.map((cls) => {
              const classSections = sections.filter((s) => s.classId === cls.id);
              const classSubs = subjects.filter((s) => s.classId === cls.id);
              return (
                <div
                  key={cls.id}
                  className={`rounded-xl border transition-all hover:shadow-md flex flex-col justify-between ${
                    isDark ? 'bg-slate-900/80 border-slate-800' : 'bg-white border-slate-200'
                  }`}
                >
                  {/* Card Header */}
                  <div className="p-4 border-b border-inherit">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="font-bold text-base text-slate-100">{cls.name}</h3>
                          <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-blue-500/20 text-blue-400">
                            {cls.code}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Stream: <span className="font-semibold text-slate-300">{cls.group}</span> • Shift:{' '}
                          <span className="font-semibold text-slate-300">{cls.shift}</span>
                        </p>
                      </div>

                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleOpenEditClass(cls)}
                          title="Edit Class Details"
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-blue-400"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteClass(cls.id, cls.name)}
                          title="Delete Class"
                          className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 mt-3 text-xs">
                      <span className="flex items-center gap-1 text-slate-400">
                        <Users className="w-3.5 h-3.5 text-amber-400" />
                        <strong className="text-slate-200">{cls.studentCount}</strong> Students
                      </span>
                      <span className="flex items-center gap-1 text-slate-400">
                        <BookOpen className="w-3.5 h-3.5 text-purple-400" />
                        <strong className="text-slate-200">{classSubs.length}</strong> Subjects
                      </span>
                    </div>
                  </div>

                  {/* Sections List */}
                  <div className="p-4 flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                        Assigned Sections ({classSections.length})
                      </span>
                      <button
                        onClick={() => handleOpenAddSection(cls.id)}
                        className="text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                      >
                        <PlusCircle className="w-3 h-3" />
                        <span>Add Section</span>
                      </button>
                    </div>

                    {classSections.length === 0 ? (
                      <div className="p-3 text-center rounded-lg border border-dashed border-slate-800 text-slate-500 text-xs">
                        No sections allocated yet
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {classSections.map((sec) => (
                          <div
                            key={sec.id}
                            className={`p-2.5 rounded-lg border flex items-center justify-between text-xs ${
                              isDark ? 'bg-slate-950/60 border-slate-800/80' : 'bg-slate-50 border-slate-200'
                            }`}
                          >
                            <div className="space-y-0.5">
                              <div className="flex items-center space-x-2">
                                <span className="font-bold text-slate-200">{sec.name}</span>
                                {sec.roomNumber && (
                                  <span className="text-[10px] text-slate-400 font-mono">[{sec.roomNumber}]</span>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-400">
                                Teacher:{' '}
                                <span className="text-blue-400 font-medium">
                                  {sec.classTeacherName || 'Unassigned'}
                                </span>
                              </p>
                            </div>

                            <div className="flex items-center space-x-2">
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                                Cap: {sec.capacity}
                              </span>
                              <button
                                onClick={() => handleOpenEditSection(sec)}
                                className="p-1 rounded text-slate-400 hover:text-blue-400"
                                title="Edit Section"
                              >
                                <Edit className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => handleDeleteSection(sec.id, sec.name)}
                                className="p-1 rounded text-slate-400 hover:text-red-400"
                                title="Delete Section"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Card Footer */}
                  <div
                    className={`p-3 border-t text-[11px] flex items-center justify-between ${
                      isDark ? 'bg-slate-950/40 border-slate-800 text-slate-500' : 'bg-slate-50 border-slate-200 text-slate-600'
                    }`}
                  >
                    <span>Order: #{cls.numericOrder}</span>
                    <button
                      onClick={() => handleOpenAddSubject(cls.id)}
                      className="text-purple-400 hover:underline font-medium"
                    >
                      + Add Subject to Syllabus
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Tab 2 Content: Subject Curriculum */}
      {activeTab === 'subjects' && (
        <div className="space-y-4">
          {/* Subject Filter Bar */}
          <div
            className={`p-3 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-3 ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search subject by name or code..."
                  value={subjectSearch}
                  onChange={(e) => setSubjectSearch(e.target.value)}
                  className={`w-full pl-9 pr-3 py-1.5 rounded-lg text-xs outline-none border transition-colors ${
                    isDark
                      ? 'bg-slate-950 border-slate-800 text-slate-100 focus:border-purple-500'
                      : 'bg-slate-50 border-slate-200 text-slate-900 focus:border-purple-500'
                  }`}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={selectedClassForSub}
                  onChange={(e) => setSelectedClassForSub(e.target.value)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
                >
                  <option value="all">All School Classes</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.group})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={() => handleOpenAddSubject()}
              className="flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-purple-600 hover:bg-purple-500 text-white"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Add Subject</span>
            </button>
          </div>

          {/* Subjects Table */}
          <div
            className={`rounded-xl border overflow-hidden ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead
                  className={`border-b font-semibold uppercase tracking-wider text-[11px] ${
                    isDark ? 'bg-slate-950/80 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}
                >
                  <tr>
                    <th className="py-3 px-4">Subject ID</th>
                    <th className="py-3 px-4">Subject Name</th>
                    <th className="py-3 px-4">Code</th>
                    <th className="py-3 px-4">Class</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Marks (Full / Pass)</th>
                    <th className="py-3 px-4">Theory / Practical</th>
                    <th className="py-3 px-4">Assigned Teacher</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-inherit">
                  {filteredSubjects.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400">
                        No subjects match the selected filters.
                      </td>
                    </tr>
                  ) : (
                    filteredSubjects.map((sub) => (
                      <tr
                        key={sub.id}
                        className={`hover:bg-slate-800/30 transition-colors ${
                          isDark ? 'text-slate-300' : 'text-slate-700'
                        }`}
                      >
                        <td className="py-3 px-4 font-mono text-purple-400 font-semibold">{sub.subjectId}</td>
                        <td className="py-3 px-4 font-bold text-slate-100">{sub.name}</td>
                        <td className="py-3 px-4 font-mono font-medium">{sub.code}</td>
                        <td className="py-3 px-4">
                          <span className="font-semibold">{sub.className}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              sub.subjectType === 'Mandatory'
                                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            }`}
                          >
                            {sub.subjectType}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-slate-200">{sub.fullMarks}</span> /{' '}
                          <span className="text-slate-400">{sub.passMarks}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          Th: <strong className="text-slate-200">{sub.theoryMarks}</strong> | Pr:{' '}
                          <strong className="text-slate-200">{sub.practicalMarks}</strong>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {sub.teacherName ? (
                            <span className="font-medium text-emerald-400">{sub.teacherName}</span>
                          ) : (
                            <span className="text-slate-500 italic">Unassigned</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end space-x-1">
                            <button
                              onClick={() => handleOpenEditSubject(sub)}
                              className="p-1 rounded text-slate-400 hover:text-blue-400 hover:bg-slate-800"
                              title="Edit Subject"
                            >
                              <Edit className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteSubject(sub.id, sub.name)}
                              className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-slate-800"
                              title="Delete Subject"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
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
        </div>
      )}

      {/* 6. Tab 3 Content: Academic Sessions & Years */}
      {activeTab === 'sessions' && (
        <div className="space-y-4">
          <div
            className={`p-4 rounded-xl border flex items-center justify-between ${
              isDark ? 'bg-slate-900/60 border-slate-800' : 'bg-white border-slate-200'
            }`}
          >
            <div>
              <h3 className="font-bold text-sm">Academic Year Sessions</h3>
              <p className="text-xs text-slate-400">
                Only one academic session can be active at a time for enrollments and grading.
              </p>
            </div>
            <button
              onClick={() => setIsYearModalOpen(true)}
              className="flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Add New Academic Session</span>
            </button>
          </div>

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
                  <th className="py-3 px-4">Academic Year</th>
                  <th className="py-3 px-4">Start Date</th>
                  <th className="py-3 px-4">End Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Active State</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-inherit">
                {academicYears.map((ay) => (
                  <tr key={ay.id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-4 font-bold text-slate-100">{ay.name}</td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{ay.startDate}</td>
                    <td className="py-3 px-4 text-slate-300 font-mono">{ay.endDate}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          ay.status === 'Active'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : ay.status === 'Upcoming'
                            ? 'bg-blue-500/20 text-blue-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {ay.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {ay.isCurrent ? (
                        <span className="flex items-center gap-1 text-emerald-400 font-semibold text-xs">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Current Active</span>
                        </span>
                      ) : (
                        <span className="text-slate-500">Inactive</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {!ay.isCurrent && (
                        <button
                          onClick={() => handleSwitchActiveYear(ay.id)}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-blue-600 hover:bg-blue-500 text-white"
                        >
                          Make Active
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ADD / EDIT CLASS ==================== */}
      {isClassModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-md rounded-2xl border shadow-2xl p-6 ${
              isDark ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h2 className="text-base font-bold">
                {editingClass ? 'Edit Class Details' : 'Add New School Class'}
              </h2>
              <button onClick={() => setIsClassModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveClass} className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Academic Year</label>
                <select
                  value={classFormData.academicYearId}
                  onChange={(e) => setClassFormData({ ...classFormData, academicYearId: Number(e.target.value) })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  {academicYears.map((y) => (
                    <option key={y.id} value={y.id}>
                      {y.name} {y.isCurrent ? '(Current)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1">Class Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Class 9, Grade 10, Nursery"
                  value={classFormData.name}
                  onChange={(e) => setClassFormData({ ...classFormData, name: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Class Code</label>
                  <input
                    type="text"
                    placeholder="e.g. C09"
                    value={classFormData.code}
                    onChange={(e) => setClassFormData({ ...classFormData, code: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Numeric Order</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={classFormData.numericOrder}
                    onChange={(e) => setClassFormData({ ...classFormData, numericOrder: Number(e.target.value) })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Academic Group</label>
                  <select
                    value={classFormData.group}
                    onChange={(e) =>
                      setClassFormData({ ...classFormData, group: e.target.value as SchoolClassInfo['group'] })
                    }
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <option value="General">General</option>
                    <option value="Science">Science</option>
                    <option value="Humanities">Humanities</option>
                    <option value="Business Studies">Business Studies</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Default Shift</label>
                  <select
                    value={classFormData.shift}
                    onChange={(e) =>
                      setClassFormData({ ...classFormData, shift: e.target.value as SchoolClassInfo['shift'] })
                    }
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <option value="Morning">Morning</option>
                    <option value="Day">Day</option>
                    <option value="Evening">Evening</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-inherit">
                <button
                  type="button"
                  onClick={() => setIsClassModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button type="submit" className="px-5 py-2 rounded-lg font-bold bg-blue-600 hover:bg-blue-500 text-white">
                  Save Class
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ADD / EDIT SECTION ==================== */}
      {isSectionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-md rounded-2xl border shadow-2xl p-6 ${
              isDark ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h2 className="text-base font-bold">
                {editingSection ? 'Edit Section Details' : 'Add New Class Section'}
              </h2>
              <button onClick={() => setIsSectionModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSection} className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Assign to Class *</label>
                <select
                  value={sectionFormData.classId}
                  onChange={(e) => setSectionFormData({ ...sectionFormData, classId: Number(e.target.value) })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.group})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1">Section Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Section A, Padma, Meghna, Rose"
                  value={sectionFormData.name}
                  onChange={(e) => setSectionFormData({ ...sectionFormData, name: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Room / Hall</label>
                  <input
                    type="text"
                    placeholder="e.g. Room 204"
                    value={sectionFormData.roomNumber}
                    onChange={(e) => setSectionFormData({ ...sectionFormData, roomNumber: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Student Capacity</label>
                  <input
                    type="number"
                    min={10}
                    max={120}
                    value={sectionFormData.capacity}
                    onChange={(e) => setSectionFormData({ ...sectionFormData, capacity: Number(e.target.value) })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Shift</label>
                  <select
                    value={sectionFormData.shift}
                    onChange={(e) =>
                      setSectionFormData({ ...sectionFormData, shift: e.target.value as SectionInfo['shift'] })
                    }
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <option value="Morning">Morning</option>
                    <option value="Day">Day</option>
                    <option value="Evening">Evening</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Stream / Group</label>
                  <select
                    value={sectionFormData.group}
                    onChange={(e) => setSectionFormData({ ...sectionFormData, group: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <option value="General">General</option>
                    <option value="Science">Science</option>
                    <option value="Humanities">Humanities</option>
                    <option value="Business Studies">Business Studies</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-1">Class Teacher</label>
                <select
                  value={sectionFormData.classTeacherId || ''}
                  onChange={(e) =>
                    setSectionFormData({
                      ...sectionFormData,
                      classTeacherId: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <option value="">-- None (Unassigned) --</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.fullName} ({t.primarySubject})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-inherit">
                <button
                  type="button"
                  onClick={() => setIsSectionModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button type="submit" className="px-5 py-2 rounded-lg font-bold bg-emerald-600 hover:bg-emerald-500 text-white">
                  Save Section
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ADD / EDIT SUBJECT ==================== */}
      {isSubjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-lg rounded-2xl border shadow-2xl p-6 ${
              isDark ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h2 className="text-base font-bold">
                {editingSubject ? 'Edit Subject Syllabus' : 'Add Subject to Curriculum'}
              </h2>
              <button onClick={() => setIsSubjectModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSubject} className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Target School Class *</label>
                <select
                  value={subjectFormData.classId}
                  onChange={(e) => setSubjectFormData({ ...subjectFormData, classId: Number(e.target.value) })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.group})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1">Subject Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Higher Mathematics, Physics 1st Paper"
                  value={subjectFormData.name}
                  onChange={(e) => setSubjectFormData({ ...subjectFormData, name: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Subject Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 174, 126"
                    value={subjectFormData.code}
                    onChange={(e) => setSubjectFormData({ ...subjectFormData, code: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Subject Type</label>
                  <select
                    value={subjectFormData.subjectType}
                    onChange={(e) =>
                      setSubjectFormData({
                        ...subjectFormData,
                        subjectType: e.target.value as SubjectInfo['subjectType'],
                      })
                    }
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <option value="Mandatory">Mandatory</option>
                    <option value="Optional">Optional</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2">
                <div>
                  <label className="block font-semibold mb-1">Full Marks</label>
                  <input
                    type="number"
                    min={25}
                    max={200}
                    value={subjectFormData.fullMarks}
                    onChange={(e) =>
                      setSubjectFormData({ ...subjectFormData, fullMarks: Number(e.target.value) })
                    }
                    className={`w-full px-2.5 py-1.5 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Pass Marks</label>
                  <input
                    type="number"
                    min={10}
                    max={100}
                    value={subjectFormData.passMarks}
                    onChange={(e) =>
                      setSubjectFormData({ ...subjectFormData, passMarks: Number(e.target.value) })
                    }
                    className={`w-full px-2.5 py-1.5 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Theory</label>
                  <input
                    type="number"
                    min={0}
                    max={200}
                    value={subjectFormData.theoryMarks}
                    onChange={(e) =>
                      setSubjectFormData({ ...subjectFormData, theoryMarks: Number(e.target.value) })
                    }
                    className={`w-full px-2.5 py-1.5 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Practical</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={subjectFormData.practicalMarks}
                    onChange={(e) =>
                      setSubjectFormData({ ...subjectFormData, practicalMarks: Number(e.target.value) })
                    }
                    className={`w-full px-2.5 py-1.5 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-1">Assigned Subject Teacher</label>
                <select
                  value={subjectFormData.teacherId || ''}
                  onChange={(e) =>
                    setSubjectFormData({
                      ...subjectFormData,
                      teacherId: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <option value="">-- None (Unassigned) --</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.fullName} ({t.primarySubject})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-inherit">
                <button
                  type="button"
                  onClick={() => setIsSubjectModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button type="submit" className="px-5 py-2 rounded-lg font-bold bg-purple-600 hover:bg-purple-500 text-white">
                  Save Subject
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== MODAL: ADD ACADEMIC SESSION ==================== */}
      {isYearModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className={`w-full max-w-sm rounded-2xl border shadow-2xl p-6 ${
              isDark ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h2 className="text-base font-bold">New Academic Session</h2>
              <button onClick={() => setIsYearModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveYear} className="mt-4 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold mb-1">Session Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026-2027"
                  value={yearFormData.name}
                  onChange={(e) => setYearFormData({ ...yearFormData, name: e.target.value })}
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Start Date</label>
                  <input
                    type="date"
                    value={yearFormData.startDate}
                    onChange={(e) => setYearFormData({ ...yearFormData, startDate: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">End Date</label>
                  <input
                    type="date"
                    value={yearFormData.endDate}
                    onChange={(e) => setYearFormData({ ...yearFormData, endDate: e.target.value })}
                    className={`w-full px-3 py-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                    }`}
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-1">Status</label>
                <select
                  value={yearFormData.status}
                  onChange={(e) =>
                    setYearFormData({ ...yearFormData, status: e.target.value as AcademicYearInfo['status'] })
                  }
                  className={`w-full px-3 py-2 rounded-lg border outline-none ${
                    isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <option value="Upcoming">Upcoming</option>
                  <option value="Active">Active</option>
                  <option value="Completed">Completed</option>
                </select>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="setAsCurrent"
                  checked={yearFormData.isCurrent}
                  onChange={(e) =>
                    setYearFormData({
                      ...yearFormData,
                      isCurrent: e.target.checked,
                      status: e.target.checked ? 'Active' : yearFormData.status,
                    })
                  }
                  className="rounded text-blue-600"
                />
                <label htmlFor="setAsCurrent" className="font-semibold text-slate-300">
                  Set as immediate Active Session
                </label>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-inherit">
                <button
                  type="button"
                  onClick={() => setIsYearModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-700 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button type="submit" className="px-5 py-2 rounded-lg font-bold bg-emerald-600 hover:bg-emerald-500 text-white">
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
