import React, { useState, useMemo } from 'react';
import {
  Users,
  GraduationCap,
  PlusCircle,
  Download,
  Upload,
  Search,
  Filter,
  Eye,
  Edit,
  Trash2,
  Printer,
  ChevronLeft,
  ChevronRight,
  BadgeCheck,
  CheckCircle2,
  FileSpreadsheet,
  AlertCircle,
  X,
  CreditCard,
  QrCode,
  Sparkles,
} from 'lucide-react';
import { Student, SchoolSetting, User } from '../types';
import { StorageService } from '../services/storage';

interface StudentManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const StudentManagement: React.FC<StudentManagementProps> = ({
  isDark,
  schoolSetting,
  currentUser,
}) => {
  const [students, setStudents] = useState<Student[]>(() => StorageService.getStudents());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState('all');
  const [selectedGender, setSelectedGender] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const perPage = 8;

  // Modals state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [selectedStudentForID, setSelectedStudentForID] = useState<Student | null>(null);
  const [selectedStudentForDossier, setSelectedStudentForDossier] = useState<Student | null>(null);
  const [isPromoteOpen, setIsPromoteOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);

  // Form State
  const [formTab, setFormTab] = useState(1);
  const [formData, setFormData] = useState<Partial<Student>>({
    firstName: '',
    lastName: '',
    fullNameBn: '',
    gender: 'Male',
    dateOfBirth: '2010-01-01',
    bloodGroup: 'A+',
    phone: '',
    email: '',
    className: 'Class 10',
    sectionName: 'Science',
    rollNumber: 1,
    group: 'Science',
    shift: 'Day',
    academicYear: '2024-2025',
    status: 'active',
    address: '',
    city: 'Dhaka',
    district: 'Dhaka',
    guardian: {
      id: 0,
      guardianName: '',
      relation: 'Father',
      guardianPhone: '',
      guardianEmail: '',
      guardianOccupation: '',
      fatherName: '',
      motherName: '',
    },
    emergencyContact: '',
    medicalNotes: '',
  });

  // KPI Calculations
  const stats = useMemo(() => {
    const total = students.length;
    const active = students.filter((s) => s.status === 'active').length;
    const male = students.filter((s) => s.gender === 'Male').length;
    const female = students.filter((s) => s.gender === 'Female').length;
    return { total, active, male, female };
  }, [students]);

  // Filtering & Search
  const filteredStudents = useMemo(() => {
    return students.filter((stu) => {
      const matchSearch =
        searchQuery.trim() === '' ||
        stu.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        stu.studentId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        stu.admissionNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (stu.phone && stu.phone.includes(searchQuery)) ||
        stu.rollNumber.toString() === searchQuery.trim();

      const matchClass = selectedClass === 'all' || stu.className === selectedClass;
      const matchGender = selectedGender === 'all' || stu.gender === selectedGender;
      const matchStatus = selectedStatus === 'all' || stu.status === selectedStatus;

      return matchSearch && matchClass && matchGender && matchStatus;
    });
  }, [students, searchQuery, selectedClass, selectedGender, selectedStatus]);

  // Pagination
  const totalPages = Math.ceil(filteredStudents.length / perPage) || 1;
  const paginatedStudents = useMemo(() => {
    const start = (currentPage - 1) * perPage;
    return filteredStudents.slice(start, start + perPage);
  }, [filteredStudents, currentPage]);

  const handleOpenAddForm = () => {
    setEditingStudent(null);
    setFormTab(1);
    setFormData({
      firstName: '',
      lastName: '',
      fullNameBn: '',
      gender: 'Male',
      dateOfBirth: '2010-01-01',
      bloodGroup: 'A+',
      phone: '',
      email: '',
      className: 'Class 10',
      sectionName: 'Science',
      rollNumber: students.length + 1,
      group: 'Science',
      shift: 'Day',
      academicYear: '2024-2025',
      status: 'active',
      address: '',
      city: 'Dhaka',
      district: 'Dhaka',
      guardian: {
        id: 0,
        guardianName: '',
        relation: 'Father',
        guardianPhone: '',
        guardianEmail: '',
        guardianOccupation: '',
        fatherName: '',
        motherName: '',
      },
      emergencyContact: '',
      medicalNotes: '',
    });
    setIsFormOpen(true);
  };

  const handleOpenEditForm = (stu: Student) => {
    setEditingStudent(stu);
    setFormTab(1);
    setFormData({ ...stu });
    setIsFormOpen(true);
  };

  const handleSaveStudent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.firstName || !formData.lastName) {
      alert('First Name and Last Name are required.');
      return;
    }
    if (!formData.guardian?.guardianName || !formData.guardian?.guardianPhone) {
      alert('Guardian Name and Phone number are required.');
      return;
    }

    const fullName = `${formData.firstName.trim()} ${formData.lastName.trim()}`;

    if (editingStudent) {
      // Update
      const updated = StorageService.updateStudent(editingStudent.id, {
        ...formData,
        fullName,
      });
      if (updated) {
        setStudents(StorageService.getStudents());
      }
    } else {
      // Create new
      StorageService.addStudent({
        ...formData,
        fullName,
        admissionDate: new Date().toISOString().split('T')[0],
      } as any);
      setStudents(StorageService.getStudents());
    }

    setIsFormOpen(false);
  };

  const handleDeleteStudent = (stu: Student) => {
    if (confirm(`Archive student record for '${stu.fullName}' (${stu.studentId})?`)) {
      StorageService.deleteStudent(stu.id, true);
      setStudents(StorageService.getStudents());
    }
  };

  // Export to CSV / Excel
  const handleExportCSV = () => {
    const headers = [
      'Student ID',
      'Admission No',
      'Roll',
      'Full Name',
      'Gender',
      'Class',
      'Section',
      'Blood Group',
      'Guardian Name',
      'Guardian Phone',
      'Status',
    ];
    const rows = filteredStudents.map((s) => [
      s.studentId,
      s.admissionNumber,
      s.rollNumber,
      `"${s.fullName}"`,
      s.gender,
      s.className,
      s.sectionName,
      s.bloodGroup || '',
      `"${s.guardian.guardianName}"`,
      s.guardian.guardianPhone,
      s.status,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Students_Roster_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto select-none">
      {/* 1. Page Header with Title and Primary Actions */}
      <div
        className={`p-6 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center text-2xl font-bold">
            🎓
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-100">Student Management & Admissions</h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Phase 2 Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Manage complete student profiles, roll numbers, guardian contacts, ID cards, and academic promotions
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleOpenAddForm}
            className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-blue-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Admit Student</span>
          </button>

          <button
            onClick={() => setIsImportOpen(true)}
            className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Excel</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="px-3 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={() => setIsPromoteOpen(true)}
            className="px-3 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Batch Promotion</span>
          </button>
        </div>
      </div>

      {/* 2. KPI Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Enrolled', value: stats.total, color: 'text-blue-400', border: 'border-blue-500/30' },
          { label: 'Active Students', value: stats.active, color: 'text-emerald-400', border: 'border-emerald-500/30' },
          { label: 'Male Students', value: stats.male, color: 'text-purple-400', border: 'border-purple-500/30' },
          { label: 'Female Students', value: stats.female, color: 'text-pink-400', border: 'border-pink-500/30' },
        ].map((kpi, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-xl border ${kpi.border} ${
              isDark ? 'bg-slate-900/80' : 'bg-white'
            }`}
          >
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{kpi.label}</span>
            <p className={`text-2xl font-black mt-1 ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* 3. Search and Multi-column Filter Bar */}
      <div
        className={`p-4 rounded-2xl border flex flex-col md:flex-row items-center gap-3 ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search students by name, roll, student ID, admission no, or phone..."
            className={`w-full pl-9 pr-3 py-2 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
            }`}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Class Filter */}
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Classes</option>
            <option value="Class 6">Class 6</option>
            <option value="Class 7">Class 7</option>
            <option value="Class 8">Class 8</option>
            <option value="Class 9">Class 9</option>
            <option value="Class 10">Class 10</option>
          </select>

          {/* Gender Filter */}
          <select
            value={selectedGender}
            onChange={(e) => setSelectedGender(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Genders</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="transferred">Transferred</option>
          </select>

          {(searchQuery || selectedClass !== 'all' || selectedGender !== 'all' || selectedStatus !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedClass('all');
                setSelectedGender('all');
                setSelectedStatus('all');
              }}
              className="px-2.5 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* 4. Student Roster Table */}
      <div
        className={`rounded-2xl border overflow-hidden ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold text-[11px] bg-slate-950/40">
                <th className="py-3 px-4">Student ID</th>
                <th className="py-3 px-3">Roll</th>
                <th className="py-3 px-4">Full Name</th>
                <th className="py-3 px-3">Class & Section</th>
                <th className="py-3 px-3">Gender</th>
                <th className="py-3 px-3">Blood</th>
                <th className="py-3 px-4">Guardian & Phone</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {paginatedStudents.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-slate-500">
                    No students found matching your criteria.
                  </td>
                </tr>
              ) : (
                paginatedStudents.map((stu) => (
                  <tr key={stu.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-blue-400">{stu.studentId}</td>
                    <td className="py-3 px-3 font-bold text-slate-200">{stu.rollNumber}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2.5">
                        <div className="w-7 h-7 rounded-full bg-blue-600/20 text-blue-400 font-bold flex items-center justify-center text-xs shrink-0">
                          {stu.firstName.charAt(0)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-100">{stu.fullName}</p>
                          {stu.fullNameBn && <p className="text-[10px] text-slate-400 font-bengali">{stu.fullNameBn}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      <span className="font-medium">{stu.className}</span>{' '}
                      <span className="text-slate-400">({stu.sectionName})</span>
                    </td>
                    <td className="py-3 px-3 text-slate-300">{stu.gender}</td>
                    <td className="py-3 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">
                        {stu.bloodGroup || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-medium text-slate-200">{stu.guardian.guardianName}</p>
                      <p className="text-[11px] text-slate-400 font-mono">{stu.guardian.guardianPhone}</p>
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          stu.status === 'active'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {stu.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        {/* ID Card Button */}
                        <button
                          onClick={() => setSelectedStudentForID(stu)}
                          title="Generate & Print Student ID Card"
                          className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                        >
                          <CreditCard className="w-3.5 h-3.5" />
                        </button>

                        {/* Dossier PDF Button */}
                        <button
                          onClick={() => setSelectedStudentForDossier(stu)}
                          title="Print Official Student Dossier"
                          className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        {/* Edit Button */}
                        <button
                          onClick={() => handleOpenEditForm(stu)}
                          title="Edit Student Details"
                          className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 hover:bg-purple-500/20"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>

                        {/* Archive Button */}
                        <button
                          onClick={() => handleDeleteStudent(stu)}
                          title="Archive Student"
                          className="p-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20"
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

        {/* Pagination Bar */}
        <div className="p-3 bg-slate-950/40 border-t border-inherit flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing {(currentPage - 1) * perPage + 1} to{' '}
            {Math.min(currentPage * perPage, filteredStudents.length)} of {filteredStudents.length} students
          </span>
          <div className="flex items-center space-x-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
              className={`px-3 py-1.5 rounded-lg border flex items-center space-x-1 ${
                currentPage === 1 ? 'opacity-40 cursor-not-allowed border-transparent' : 'border-slate-700 hover:bg-slate-800'
              }`}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <span className="font-semibold px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
              className={`px-3 py-1.5 rounded-lg border flex items-center space-x-1 ${
                currentPage === totalPages ? 'opacity-40 cursor-not-allowed border-transparent' : 'border-slate-700 hover:bg-slate-800'
              }`}
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* MODAL 1: Admission & Edit Form */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-2xl rounded-2xl shadow-2xl border p-6 select-none transition-all flex flex-col max-h-[92vh] ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div className="flex items-center space-x-2">
                <GraduationCap className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-sm">
                  {editingStudent ? `Edit Student: ${editingStudent.fullName}` : 'New Student Admission Form'}
                </h3>
              </div>
              <button onClick={() => setIsFormOpen(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tab navigation */}
            <div className="flex border-b border-inherit my-3 gap-4 text-xs font-semibold">
              {[
                { id: 1, label: '1. Personal' },
                { id: 2, label: '2. Academic' },
                { id: 3, label: '3. Guardian' },
                { id: 4, label: '4. Address & Medical' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFormTab(tab.id)}
                  className={`pb-2 transition-colors border-b-2 ${
                    formTab === tab.id
                      ? 'border-blue-500 text-blue-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Form Fields */}
            <form onSubmit={handleSaveStudent} className="flex-1 overflow-y-auto space-y-4 px-1 text-xs">
              {formTab === 1 && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">First Name*</label>
                    <input
                      required
                      type="text"
                      value={formData.firstName || ''}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      placeholder="e.g. Tahsin"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Last Name*</label>
                    <input
                      required
                      type="text"
                      value={formData.lastName || ''}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      placeholder="e.g. Rahman"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Bangla Name (ঐচ্ছিক)</label>
                    <input
                      type="text"
                      value={formData.fullNameBn || ''}
                      onChange={(e) => setFormData({ ...formData, fullNameBn: e.target.value })}
                      placeholder="e.g. তাহসিন রহমান"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white font-bengali"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Gender*</label>
                    <select
                      value={formData.gender || 'Male'}
                      onChange={(e) => setFormData({ ...formData, gender: e.target.value as any })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Date of Birth*</label>
                    <input
                      required
                      type="date"
                      value={formData.dateOfBirth || '2010-01-01'}
                      onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Blood Group</label>
                    <select
                      value={formData.bloodGroup || 'A+'}
                      onChange={(e) => setFormData({ ...formData, bloodGroup: e.target.value })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Student Phone</label>
                    <input
                      type="text"
                      value={formData.phone || ''}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="+880 1700-000000"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Student Email</label>
                    <input
                      type="email"
                      value={formData.email || ''}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="student@school.local"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                </div>
              )}

              {formTab === 2 && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Class*</label>
                    <select
                      value={formData.className || 'Class 10'}
                      onChange={(e) => setFormData({ ...formData, className: e.target.value })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="Class 6">Class 6</option>
                      <option value="Class 7">Class 7</option>
                      <option value="Class 8">Class 8</option>
                      <option value="Class 9">Class 9</option>
                      <option value="Class 10">Class 10</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Section*</label>
                    <input
                      type="text"
                      value={formData.sectionName || 'A'}
                      onChange={(e) => setFormData({ ...formData, sectionName: e.target.value })}
                      placeholder="A, B, Science, Padma"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Roll Number*</label>
                    <input
                      required
                      type="number"
                      min={1}
                      value={formData.rollNumber || 1}
                      onChange={(e) => setFormData({ ...formData, rollNumber: parseInt(e.target.value) || 1 })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Academic Session*</label>
                    <input
                      type="text"
                      value={formData.academicYear || '2024-2025'}
                      onChange={(e) => setFormData({ ...formData, academicYear: e.target.value })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Study Group</label>
                    <select
                      value={formData.group || 'Science'}
                      onChange={(e) => setFormData({ ...formData, group: e.target.value })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="General">General</option>
                      <option value="Science">Science</option>
                      <option value="Business Studies">Business Studies / Commerce</option>
                      <option value="Humanities">Humanities / Arts</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Status</label>
                    <select
                      value={formData.status || 'active'}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="transferred">Transferred</option>
                      <option value="graduated">Graduated</option>
                    </select>
                  </div>
                </div>
              )}

              {formTab === 3 && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Primary Guardian Name*</label>
                    <input
                      required
                      type="text"
                      value={formData.guardian?.guardianName || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, guardianName: e.target.value },
                        })
                      }
                      placeholder="e.g. Dr. Lutfor Rahman"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Relationship*</label>
                    <select
                      value={formData.guardian?.relation || 'Father'}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, relation: e.target.value },
                        })
                      }
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    >
                      <option value="Father">Father</option>
                      <option value="Mother">Mother</option>
                      <option value="Uncle">Uncle</option>
                      <option value="Legal Guardian">Legal Guardian</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Father's Name</label>
                    <input
                      type="text"
                      value={formData.guardian?.fatherName || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, fatherName: e.target.value },
                        })
                      }
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Mother's Name</label>
                    <input
                      type="text"
                      value={formData.guardian?.motherName || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, motherName: e.target.value },
                        })
                      }
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Guardian Phone*</label>
                    <input
                      required
                      type="text"
                      value={formData.guardian?.guardianPhone || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, guardianPhone: e.target.value },
                        })
                      }
                      placeholder="+880 1711-000000"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Guardian Occupation</label>
                    <input
                      type="text"
                      value={formData.guardian?.guardianOccupation || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          guardian: { ...formData.guardian!, guardianOccupation: e.target.value },
                        })
                      }
                      placeholder="Doctor, Govt Officer, Businessman"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                </div>
              )}

              {formTab === 4 && (
                <div className="space-y-3">
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Campus Residential Address</label>
                    <textarea
                      rows={2}
                      value={formData.address || ''}
                      onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                      placeholder="House, Road, Area details"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-medium text-slate-300 mb-1">City / Division</label>
                      <input
                        type="text"
                        value={formData.city || 'Dhaka'}
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                        className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                      />
                    </div>
                    <div>
                      <label className="block font-medium text-slate-300 mb-1">Emergency Contact Phone</label>
                      <input
                        type="text"
                        value={formData.emergencyContact || ''}
                        onChange={(e) => setFormData({ ...formData, emergencyContact: e.target.value })}
                        placeholder="+880 1711-223344"
                        className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Medical Notes & Allergies</label>
                    <input
                      type="text"
                      value={formData.medicalNotes || ''}
                      onChange={(e) => setFormData({ ...formData, medicalNotes: e.target.value })}
                      placeholder="e.g. Asthma, Peanut Allergy, Normal Eyesight"
                      className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 outline-none text-white"
                    />
                  </div>
                </div>
              )}

              {/* Form Navigation / Submit */}
              <div className="pt-3 border-t border-inherit flex items-center justify-between">
                <button
                  type="button"
                  disabled={formTab === 1}
                  onClick={() => setFormTab((t) => t - 1)}
                  className={`px-3 py-1.5 rounded-lg border ${
                    formTab === 1 ? 'opacity-30 cursor-not-allowed border-transparent' : 'border-slate-700 hover:bg-slate-800'
                  }`}
                >
                  Previous
                </button>

                <div className="flex space-x-2">
                  {formTab < 4 ? (
                    <button
                      type="button"
                      onClick={() => setFormTab((t) => t + 1)}
                      className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold"
                    >
                      Next Step
                    </button>
                  ) : (
                    <button
                      type="submit"
                      className="px-5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow"
                    >
                      {editingStudent ? 'Save Changes' : 'Confirm Admission'}
                    </button>
                  )}
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Student ID Card Preview & Printable Layout */}
      {selectedStudentForID && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div className="flex items-center space-x-2">
                <CreditCard className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-sm">Student Identity Card (CR80 PVC Format)</h3>
              </div>
              <button onClick={() => setSelectedStudentForID(null)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Visual ID Card Preview */}
            <div className="my-6 flex justify-center">
              <div className="w-[340px] h-[214px] rounded-xl overflow-hidden shadow-2xl border border-slate-300 bg-white text-slate-900 flex flex-col justify-between">
                {/* Header */}
                <div className="bg-blue-900 text-white py-2 px-3 text-center">
                  <h4 className="font-bold text-[11px] leading-tight tracking-wide uppercase">
                    {schoolSetting.schoolName}
                  </h4>
                  <p className="text-[9px] text-blue-200 font-medium">STUDENT IDENTITY CARD</p>
                </div>

                {/* Body Row */}
                <div className="p-3 flex space-x-3 items-center">
                  {/* Photo Frame */}
                  <div className="w-16 h-20 rounded-md bg-slate-100 border border-slate-300 flex flex-col items-center justify-center text-slate-400 shrink-0">
                    <span className="text-xl">🎓</span>
                    <span className="text-[8px] font-bold mt-1 text-slate-500">PHOTO</span>
                  </div>

                  {/* Student Details */}
                  <div className="text-[10px] space-y-0.5 leading-tight flex-1">
                    <p className="font-black text-xs text-blue-950">{selectedStudentForID.fullName}</p>
                    <p className="text-slate-600 font-mono">ID: {selectedStudentForID.studentId}</p>
                    <p className="text-slate-700">
                      Class: <b>{selectedStudentForID.className}</b> ({selectedStudentForID.sectionName})
                    </p>
                    <p className="text-slate-700">Roll: <b>{selectedStudentForID.rollNumber}</b></p>
                    <p className="text-red-700 font-bold">Blood: {selectedStudentForID.bloodGroup || 'N/A'}</p>
                    <p className="text-slate-600 text-[9px] truncate">
                      Parent: {selectedStudentForID.guardian.guardianName}
                    </p>
                  </div>
                </div>

                {/* Footer Strip */}
                <div className="bg-slate-950 text-white py-1 px-3 flex items-center justify-between text-[8px]">
                  <span>Emergency: {selectedStudentForID.guardian.guardianPhone}</span>
                  <span className="font-semibold text-slate-300">Principal Signature</span>
                </div>
              </div>
            </div>

            {/* Print action buttons */}
            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setSelectedStudentForID(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => {
                  window.print();
                }}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Printer className="w-4 h-4" />
                <span>Print Student Card</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Printable Official Student Dossier */}
      {selectedStudentForDossier && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-2xl rounded-2xl shadow-2xl border p-6 select-none transition-all flex flex-col max-h-[90vh] ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">Official Student Admission Dossier</h3>
              <button onClick={() => setSelectedStudentForDossier(null)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 my-2 border rounded-xl bg-white text-slate-900 text-xs space-y-4">
              {/* Letterhead */}
              <div className="text-center border-b pb-3 border-slate-200">
                <h2 className="text-base font-bold text-blue-900">{schoolSetting.schoolName}</h2>
                <p className="text-[11px] text-slate-600">{schoolSetting.schoolNameBn}</p>
                <p className="text-[10px] text-slate-500">
                  EIIN: {schoolSetting.eiinNumber} | Phone: {schoolSetting.phone} | Email: {schoolSetting.email}
                </p>
                <p className="text-[10px] text-slate-500">{schoolSetting.address}</p>
                <div className="mt-2 inline-block px-3 py-0.5 rounded bg-blue-50 text-blue-900 font-bold text-[11px]">
                  STUDENT ADMISSION DOSSIER
                </div>
              </div>

              {/* Student info grid */}
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Student ID:</p>
                  <p className="font-bold font-mono text-blue-900">{selectedStudentForDossier.studentId}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Admission Number:</p>
                  <p className="font-bold font-mono text-blue-900">{selectedStudentForDossier.admissionNumber}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Full Name:</p>
                  <p className="font-bold text-slate-900">{selectedStudentForDossier.fullName}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Roll Number:</p>
                  <p className="font-bold text-slate-900">{selectedStudentForDossier.rollNumber}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Class & Section:</p>
                  <p className="font-bold text-slate-900">
                    {selectedStudentForDossier.className} ({selectedStudentForDossier.sectionName})
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Academic Session:</p>
                  <p className="font-bold text-slate-900">{selectedStudentForDossier.academicYear}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Gender & DOB:</p>
                  <p className="font-bold text-slate-900">
                    {selectedStudentForDossier.gender} | {selectedStudentForDossier.dateOfBirth}
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Blood Group:</p>
                  <p className="font-bold text-red-600">{selectedStudentForDossier.bloodGroup || 'N/A'}</p>
                </div>
              </div>

              {/* Guardian Section */}
              <div className="border-t pt-3 border-slate-200">
                <h4 className="font-bold text-xs text-slate-900 mb-2">Guardian & Family Information</h4>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <p>
                    <span className="text-slate-500">Primary Guardian:</span>{' '}
                    <b>{selectedStudentForDossier.guardian.guardianName}</b> ({selectedStudentForDossier.guardian.relation})
                  </p>
                  <p>
                    <span className="text-slate-500">Guardian Phone:</span>{' '}
                    <b>{selectedStudentForDossier.guardian.guardianPhone}</b>
                  </p>
                  <p>
                    <span className="text-slate-500">Father's Name:</span>{' '}
                    {selectedStudentForDossier.guardian.fatherName || 'N/A'}
                  </p>
                  <p>
                    <span className="text-slate-500">Mother's Name:</span>{' '}
                    {selectedStudentForDossier.guardian.motherName || 'N/A'}
                  </p>
                  <p className="col-span-2">
                    <span className="text-slate-500">Residential Address:</span>{' '}
                    {selectedStudentForDossier.address || 'Same as campus'}
                  </p>
                </div>
              </div>

              {/* Signatures */}
              <div className="pt-8 flex justify-between text-center text-[10px] text-slate-600">
                <div>
                  <div className="w-36 border-b border-slate-400 mb-1" />
                  <span>Student / Guardian Signature</span>
                </div>
                <div>
                  <div className="w-36 border-b border-slate-400 mb-1" />
                  <span>Admissions Officer</span>
                </div>
                <div>
                  <div className="w-36 border-b border-slate-400 mb-1" />
                  <span>Principal & Official Seal</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setSelectedStudentForDossier(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Printer className="w-4 h-4" />
                <span>Print Official Dossier</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: Batch Academic Promotion */}
      {isPromoteOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h3 className="font-bold text-sm">Batch Academic Promotion</h3>
              </div>
              <button onClick={() => setIsPromoteOpen(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3 text-xs">
              <p className="text-slate-400">
                Promote students enrolled in a class to the next academic level.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">From Class</label>
                  <select
                    id="promote-from"
                    defaultValue="Class 9"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Class 6">Class 6</option>
                    <option value="Class 7">Class 7</option>
                    <option value="Class 8">Class 8</option>
                    <option value="Class 9">Class 9</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Promote To</label>
                  <select
                    id="promote-to"
                    defaultValue="Class 10"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Class 7">Class 7</option>
                    <option value="Class 8">Class 8</option>
                    <option value="Class 9">Class 9</option>
                    <option value="Class 10">Class 10</option>
                    <option value="Class 11 (College)">Class 11 (College)</option>
                  </select>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 text-[11px]">
                <p className="font-semibold">Automated Year-End Action</p>
                <p className="mt-0.5">
                  Roll numbers will be carried over and academic session will update to 2025–2026.
                </p>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setIsPromoteOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const fromEl = document.getElementById('promote-from') as HTMLSelectElement;
                  const toEl = document.getElementById('promote-to') as HTMLSelectElement;
                  const fromVal = fromEl.value;
                  const toVal = toEl.value;
                  const targetIds = students.filter((s) => s.className === fromVal).map((s) => s.id);
                  if (targetIds.length === 0) {
                    alert(`No active students found in ${fromVal}.`);
                    return;
                  }
                  StorageService.bulkPromote(targetIds, toVal, '2025-2026');
                  setStudents(StorageService.getStudents());
                  alert(`Successfully promoted ${targetIds.length} students to ${toVal}!`);
                  setIsPromoteOpen(false);
                }}
                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow"
              >
                Execute Promotion
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: Excel Batch Import */}
      {isImportOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-md rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div className="flex items-center space-x-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm">Import Students from Excel</h3>
              </div>
              <button onClick={() => setIsImportOpen(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-3 text-xs">
              <p className="text-slate-400">
                Quickly populate student rosters from standardized spreadsheets.
              </p>

              <div className="p-3 rounded-lg border-2 border-dashed border-slate-700 text-center py-6 bg-slate-950/40">
                <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                <p className="font-semibold text-slate-300">Drop your student_roster.xlsx here</p>
                <p className="text-[10px] text-slate-500 mt-1">Supports Excel .xlsx and .csv files</p>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 text-[11px] text-slate-400">
                <p className="font-semibold text-slate-300">Expected Column Headers:</p>
                <p className="font-mono text-[10px] mt-0.5 text-blue-400">
                  Roll, First Name, Last Name, Gender, DOB, Phone, Guardian Name, Guardian Phone
                </p>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setIsImportOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  // Simulate batch import of sample students
                  const sampleNewStudent = {
                    firstName: 'Kamrul',
                    lastName: 'Islam',
                    fullNameBn: 'কামরুল ইসলাম',
                    gender: 'Male' as const,
                    dateOfBirth: '2010-03-15',
                    bloodGroup: 'B+',
                    phone: '+880 1715-998877',
                    className: 'Class 9',
                    sectionName: 'Science',
                    rollNumber: 15,
                    group: 'Science',
                    shift: 'Day',
                    academicYear: '2024-2025',
                    status: 'active' as const,
                    guardian: {
                      id: 0,
                      guardianName: 'Nazrul Islam',
                      relation: 'Father',
                      guardianPhone: '+880 1715-112233',
                    },
                  };
                  StorageService.addStudent(sampleNewStudent as any);
                  setStudents(StorageService.getStudents());
                  alert('Excel import simulated: 1 new student successfully added to database!');
                  setIsImportOpen(false);
                }}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow"
              >
                Simulate Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
