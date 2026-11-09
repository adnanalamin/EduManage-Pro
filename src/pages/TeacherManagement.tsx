import React, { useState, useMemo } from 'react';
import {
  Users,
  PlusCircle,
  Download,
  Search,
  Filter,
  Eye,
  Edit,
  Printer,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  X,
  Sparkles,
  BookOpen,
} from 'lucide-react';
import { Teacher, SchoolSetting, User } from '../types';
import { StorageService } from '../services/storage';

interface TeacherManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const TeacherManagement: React.FC<TeacherManagementProps> = ({
  isDark,
  schoolSetting,
}) => {
  const [teachers, setTeachers] = useState<Teacher[]>(() => StorageService.getTeachers());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const perPage = 8;

  // Modals
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null);
  const [selectedTeacherForID, setSelectedTeacherForID] = useState<Teacher | null>(null);
  const [selectedTeacherForDossier, setSelectedTeacherForDossier] = useState<Teacher | null>(null);

  // Form State
  const [formData, setFormData] = useState<Partial<Teacher>>({
    fullName: '',
    fullNameBn: '',
    gender: 'Male',
    dateOfBirth: '1988-01-01',
    bloodGroup: 'A+',
    phone: '',
    email: '',
    qualification: 'M.Sc. in Physics, B.Ed',
    designation: 'Assistant Teacher',
    department: 'Science',
    primarySubject: 'Physics',
    joiningDate: '2020-01-01',
    salary: 38000,
    status: 'active',
  });

  const stats = useMemo(() => {
    const total = teachers.length;
    const active = teachers.filter((t) => t.status === 'active').length;
    const present = teachers.filter((t) => t.attendanceToday === 'present').length;
    const payroll = teachers.reduce((acc, t) => acc + (t.salary || 0), 0);
    return { total, active, present, payroll };
  }, [teachers]);

  const filteredTeachers = useMemo(() => {
    return teachers.filter((t) => {
      const matchSearch =
        searchQuery.trim() === '' ||
        t.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.teacherId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.primarySubject.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.phone.includes(searchQuery);

      const matchDept = selectedDept === 'all' || t.department === selectedDept;
      const matchStatus = selectedStatus === 'all' || t.status === selectedStatus;

      return matchSearch && matchDept && matchStatus;
    });
  }, [teachers, searchQuery, selectedDept, selectedStatus]);

  const totalPages = Math.ceil(filteredTeachers.length / perPage) || 1;
  const paginatedTeachers = useMemo(() => {
    const start = (currentPage - 1) * perPage;
    return filteredTeachers.slice(start, start + perPage);
  }, [filteredTeachers, currentPage]);

  const handleOpenAdd = () => {
    setEditingTeacher(null);
    setFormData({
      fullName: '',
      fullNameBn: '',
      gender: 'Male',
      dateOfBirth: '1988-01-01',
      bloodGroup: 'A+',
      phone: '',
      email: '',
      qualification: 'M.Sc. in Physics, B.Ed',
      designation: 'Assistant Teacher',
      department: 'Science',
      primarySubject: 'Physics',
      joiningDate: new Date().toISOString().split('T')[0],
      salary: 38000,
      status: 'active',
    });
    setIsFormOpen(true);
  };

  const handleOpenEdit = (t: Teacher) => {
    setEditingTeacher(t);
    setFormData({ ...t });
    setIsFormOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.fullName || !formData.phone || !formData.email || !formData.primarySubject) {
      alert('Please fill in all mandatory fields.');
      return;
    }

    if (editingTeacher) {
      StorageService.updateTeacher(editingTeacher.id, formData);
    } else {
      StorageService.addTeacher(formData as any);
    }
    setTeachers(StorageService.getTeachers());
    setIsFormOpen(false);
  };

  const handleExportCSV = () => {
    const headers = ['Teacher ID', 'Employee ID', 'Full Name', 'Department', 'Primary Subject', 'Designation', 'Phone', 'Email', 'Salary (BDT)', 'Status'];
    const rows = filteredTeachers.map((t) => [
      t.teacherId,
      t.employeeId,
      `"${t.fullName}"`,
      t.department,
      t.primarySubject,
      `"${t.designation}"`,
      t.phone,
      t.email,
      t.salary,
      t.status,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `Faculty_Directory_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto select-none">
      {/* Header */}
      <div
        className={`p-6 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center text-2xl font-bold">
            👨‍🏫
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-100">Teacher & Faculty Management</h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Phase 3 Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Faculty roster, department assignments, academic qualifications, ID badges, and payroll
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleOpenAdd}
            className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-emerald-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Register Teacher</span>
          </button>
          <button
            onClick={handleExportCSV}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs flex items-center space-x-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Faculty', value: stats.total, color: 'text-emerald-400', border: 'border-emerald-500/30' },
          { label: 'Active Teachers', value: stats.active, color: 'text-blue-400', border: 'border-blue-500/30' },
          { label: 'Present Today', value: stats.present, color: 'text-purple-400', border: 'border-purple-500/30' },
          { label: 'Monthly Payroll', value: `৳ ${stats.payroll.toLocaleString()}`, color: 'text-cyan-400', border: 'border-cyan-500/30' },
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

      {/* Filter and Search Bar */}
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
            placeholder="Search faculty by name, teacher ID, phone, or subject..."
            className={`w-full pl-9 pr-3 py-2 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
            }`}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Departments</option>
            <option value="Science">Science</option>
            <option value="Mathematics">Mathematics</option>
            <option value="Languages">Languages</option>
            <option value="ICT & Computer Science">ICT & Computer Science</option>
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="on_leave">On Leave</option>
            <option value="resigned">Resigned</option>
          </select>
        </div>
      </div>

      {/* Faculty Table */}
      <div
        className={`rounded-2xl border overflow-hidden ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold text-[11px] bg-slate-950/40">
                <th className="py-3 px-4">Teacher ID</th>
                <th className="py-3 px-4">Faculty Name</th>
                <th className="py-3 px-3">Department</th>
                <th className="py-3 px-3">Primary Subject</th>
                <th className="py-3 px-3">Designation</th>
                <th className="py-3 px-3">Contact</th>
                <th className="py-3 px-3">Salary</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {paginatedTeachers.map((t) => (
                <tr key={t.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-emerald-400">{t.teacherId}</td>
                  <td className="py-3 px-4">
                    <p className="font-semibold text-slate-100">{t.fullName}</p>
                    <p className="text-[10px] text-slate-400">{t.qualification}</p>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-purple-300 font-medium">
                      {t.department}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-200 font-medium">{t.primarySubject}</td>
                  <td className="py-3 px-3 text-slate-300">{t.designation}</td>
                  <td className="py-3 px-3">
                    <p className="font-mono text-slate-300">{t.phone}</p>
                    <p className="text-[10px] text-slate-500 truncate max-w-[120px]">{t.email}</p>
                  </td>
                  <td className="py-3 px-3 font-semibold text-cyan-400">৳ {t.salary.toLocaleString()}</td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        t.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1">
                      <button
                        onClick={() => setSelectedTeacherForID(t)}
                        title="Print Faculty ID Badge"
                        className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                      >
                        <CreditCard className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setSelectedTeacherForDossier(t)}
                        title="View Profile Dossier"
                        className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleOpenEdit(t)}
                        title="Edit Profile"
                        className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 hover:bg-purple-500/20"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: Form Dialog */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-xl rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">
                {editingTeacher ? `Edit Faculty: ${editingTeacher.fullName}` : 'Register New Faculty Member'}
              </h3>
              <button onClick={() => setIsFormOpen(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSave} className="py-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Full Name*</label>
                  <input
                    required
                    type="text"
                    value={formData.fullName || ''}
                    onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Gender</label>
                  <select
                    value={formData.gender || 'Male'}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value as any })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Department*</label>
                  <select
                    value={formData.department || 'Science'}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Science">Science</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Languages">Languages</option>
                    <option value="ICT & Computer Science">ICT & Computer Science</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Primary Subject*</label>
                  <input
                    required
                    type="text"
                    value={formData.primarySubject || ''}
                    onChange={(e) => setFormData({ ...formData, primarySubject: e.target.value })}
                    placeholder="e.g. Physics"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Qualification*</label>
                  <input
                    required
                    type="text"
                    value={formData.qualification || ''}
                    onChange={(e) => setFormData({ ...formData, qualification: e.target.value })}
                    placeholder="e.g. M.Sc. in Physics, B.Ed"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Designation*</label>
                  <input
                    required
                    type="text"
                    value={formData.designation || 'Assistant Teacher'}
                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Phone*</label>
                  <input
                    required
                    type="text"
                    value={formData.phone || ''}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+880 1700-000000"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Email*</label>
                  <input
                    required
                    type="email"
                    value={formData.email || ''}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="teacher@school.local"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Monthly Basic Salary (BDT ৳)</label>
                  <input
                    type="number"
                    value={formData.salary || 35000}
                    onChange={(e) => setFormData({ ...formData, salary: parseInt(e.target.value) || 35000 })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Status</label>
                  <select
                    value={formData.status || 'active'}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="active">Active</option>
                    <option value="on_leave">On Leave</option>
                    <option value="resigned">Resigned</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-inherit flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow"
                >
                  {editingTeacher ? 'Save Changes' : 'Register Faculty'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Teacher ID Badge */}
      {selectedTeacherForID && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">Faculty Identity Badge (CR80 Standard)</h3>
              <button onClick={() => setSelectedTeacherForID(null)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="my-6 flex justify-center">
              <div className="w-[340px] h-[214px] rounded-xl overflow-hidden shadow-2xl border border-slate-300 bg-white text-slate-900 flex flex-col justify-between">
                <div className="bg-emerald-800 text-white py-2 px-3 text-center">
                  <h4 className="font-bold text-[11px] leading-tight tracking-wide uppercase">
                    {schoolSetting.schoolName}
                  </h4>
                  <p className="text-[9px] text-emerald-200 font-medium">FACULTY IDENTITY BADGE</p>
                </div>

                <div className="p-3 flex space-x-3 items-center">
                  <div className="w-16 h-20 rounded-md bg-slate-100 border border-slate-300 flex flex-col items-center justify-center text-slate-400 shrink-0">
                    <span className="text-xl">👨‍🏫</span>
                    <span className="text-[8px] font-bold mt-1 text-emerald-800">FACULTY</span>
                  </div>

                  <div className="text-[10px] space-y-0.5 leading-tight flex-1">
                    <p className="font-black text-xs text-emerald-950">{selectedTeacherForID.fullName}</p>
                    <p className="text-slate-600 font-mono">ID: {selectedTeacherForID.teacherId}</p>
                    <p className="text-slate-700 font-semibold">{selectedTeacherForID.designation}</p>
                    <p className="text-slate-700">Subject: <b>{selectedTeacherForID.primarySubject}</b></p>
                    <p className="text-slate-700">Department: {selectedTeacherForID.department}</p>
                    <p className="text-slate-600 text-[9px]">Phone: {selectedTeacherForID.phone}</p>
                  </div>
                </div>

                <div className="bg-slate-950 text-white py-1 px-3 flex items-center justify-between text-[8px]">
                  <span>Authorized Faculty Credential</span>
                  <span className="font-semibold text-slate-300">Principal Signature</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setSelectedTeacherForID(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Printer className="w-4 h-4" />
                <span>Print Faculty Badge</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Teacher Profile Dossier */}
      {selectedTeacherForDossier && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-xl rounded-2xl shadow-2xl border p-6 select-none transition-all flex flex-col max-h-[90vh] ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">Faculty Service Record Dossier</h3>
              <button onClick={() => setSelectedTeacherForDossier(null)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 my-2 border rounded-xl bg-white text-slate-900 text-xs space-y-4">
              <div className="text-center border-b pb-3 border-slate-200">
                <h2 className="text-base font-bold text-emerald-900">{schoolSetting.schoolName}</h2>
                <p className="text-[10px] text-slate-500">EIIN: {schoolSetting.eiinNumber} | Phone: {schoolSetting.phone}</p>
                <div className="mt-2 inline-block px-3 py-0.5 rounded bg-emerald-50 text-emerald-900 font-bold text-[11px]">
                  TEACHER SERVICE DOSSIER
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Teacher ID:</p>
                  <p className="font-bold font-mono text-emerald-900">{selectedTeacherForDossier.teacherId}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Employee ID:</p>
                  <p className="font-bold font-mono text-emerald-900">{selectedTeacherForDossier.employeeId}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Faculty Full Name:</p>
                  <p className="font-bold text-slate-900">{selectedTeacherForDossier.fullName}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Designation:</p>
                  <p className="font-bold text-slate-900">{selectedTeacherForDossier.designation}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Department & Subject:</p>
                  <p className="font-bold text-slate-900">
                    {selectedTeacherForDossier.department} ({selectedTeacherForDossier.primarySubject})
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Qualification:</p>
                  <p className="font-bold text-slate-900">{selectedTeacherForDossier.qualification}</p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Phone & Email:</p>
                  <p className="font-bold text-slate-900">
                    {selectedTeacherForDossier.phone} | {selectedTeacherForDossier.email}
                  </p>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-200">
                  <p className="text-slate-500">Monthly Compensation:</p>
                  <p className="font-bold text-emerald-700">৳ {selectedTeacherForDossier.salary.toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setSelectedTeacherForDossier(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Printer className="w-4 h-4" />
                <span>Print Record</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
