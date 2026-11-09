import React, { useState, useMemo } from 'react';
import {
  Briefcase,
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
  Shield,
  Clock,
} from 'lucide-react';
import { Staff, SchoolSetting, User } from '../types';
import { StorageService } from '../services/storage';

interface StaffManagementProps {
  isDark: boolean;
  schoolSetting: SchoolSetting;
  currentUser: User | null;
}

export const StaffManagement: React.FC<StaffManagementProps> = ({
  isDark,
  schoolSetting,
}) => {
  const [staffList, setStaffList] = useState<Staff[]>(() => StorageService.getStaff());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPosition, setSelectedPosition] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const perPage = 8;

  // Modals
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null);
  const [selectedStaffForID, setSelectedStaffForID] = useState<Staff | null>(null);

  const [formData, setFormData] = useState<Partial<Staff>>({
    fullName: '',
    fullNameBn: '',
    gender: 'Male',
    dateOfBirth: '1990-01-01',
    phone: '',
    email: '',
    position: 'Accountant',
    department: 'Administration & Accounts',
    shift: 'Day',
    joiningDate: '2022-01-01',
    salary: 25000,
    status: 'active',
  });

  const stats = useMemo(() => {
    const total = staffList.length;
    const active = staffList.filter((s) => s.status === 'active').length;
    const adminOffice = staffList.filter((s) => s.department.includes('Admin') || s.position.includes('Account')).length;
    const payroll = staffList.reduce((acc, s) => acc + (s.salary || 0), 0);
    return { total, active, adminOffice, payroll };
  }, [staffList]);

  const filteredStaff = useMemo(() => {
    return staffList.filter((s) => {
      const matchSearch =
        searchQuery.trim() === '' ||
        s.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.staffId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.position.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.phone.includes(searchQuery);

      const matchPos = selectedPosition === 'all' || s.position === selectedPosition;
      return matchSearch && matchPos;
    });
  }, [staffList, searchQuery, selectedPosition]);

  const totalPages = Math.ceil(filteredStaff.length / perPage) || 1;
  const paginatedStaff = useMemo(() => {
    const start = (currentPage - 1) * perPage;
    return filteredStaff.slice(start, start + perPage);
  }, [filteredStaff, currentPage]);

  const handleOpenAdd = () => {
    setEditingStaff(null);
    setFormData({
      fullName: '',
      fullNameBn: '',
      gender: 'Male',
      dateOfBirth: '1990-01-01',
      phone: '',
      email: '',
      position: 'Accountant',
      department: 'Administration & Accounts',
      shift: 'Day',
      joiningDate: new Date().toISOString().split('T')[0],
      salary: 25000,
      status: 'active',
    });
    setIsFormOpen(true);
  };

  const handleOpenEdit = (s: Staff) => {
    setEditingStaff(s);
    setFormData({ ...s });
    setIsFormOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.fullName || !formData.phone || !formData.position) {
      alert('Please fill in required fields.');
      return;
    }

    if (editingStaff) {
      StorageService.updateStaff(editingStaff.id, formData);
    } else {
      StorageService.addStaff(formData as any);
    }
    setStaffList(StorageService.getStaff());
    setIsFormOpen(false);
  };

  const handleExportCSV = () => {
    const headers = ['Staff ID', 'Employee ID', 'Full Name', 'Position', 'Department', 'Shift', 'Phone', 'Salary (BDT)', 'Status'];
    const rows = filteredStaff.map((s) => [
      s.staffId,
      s.employeeId,
      `"${s.fullName}"`,
      `"${s.position}"`,
      s.department,
      s.shift,
      s.phone,
      s.salary,
      s.status,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', `Staff_Directory_${new Date().toISOString().slice(0, 10)}.csv`);
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
          <div className="w-12 h-12 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center text-2xl font-bold">
            💼
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-100">Staff & Employee Directory</h1>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                Phase 3 Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Support personnel: Accountants, Librarians, Receptionists, Security, Office, and IT staff
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleOpenAdd}
            className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-indigo-600/20"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Register Staff</span>
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
          { label: 'Total Personnel', value: stats.total, color: 'text-indigo-400', border: 'border-indigo-500/30' },
          { label: 'Active Staff', value: stats.active, color: 'text-emerald-400', border: 'border-emerald-500/30' },
          { label: 'Administration & Office', value: stats.adminOffice, color: 'text-blue-400', border: 'border-blue-500/30' },
          { label: 'Staff Payroll', value: `৳ ${stats.payroll.toLocaleString()}`, color: 'text-cyan-400', border: 'border-cyan-500/30' },
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

      {/* Search & Filter Bar */}
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
            placeholder="Search staff by name, employee ID, position, or phone..."
            className={`w-full pl-9 pr-3 py-2 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-950 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
            }`}
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={selectedPosition}
            onChange={(e) => setSelectedPosition(e.target.value)}
            className={`py-2 px-3 rounded-lg text-xs border outline-none ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-300 text-slate-700'
            }`}
          >
            <option value="all">All Roles</option>
            <option value="Chief Accountant">Chief Accountant</option>
            <option value="Librarian">Librarian</option>
            <option value="Front Desk Receptionist">Front Desk Receptionist</option>
            <option value="Security Supervisor">Security Supervisor</option>
          </select>
        </div>
      </div>

      {/* Staff Table */}
      <div
        className={`rounded-2xl border overflow-hidden ${
          isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold text-[11px] bg-slate-950/40">
                <th className="py-3 px-4">Staff ID</th>
                <th className="py-3 px-4">Employee Name</th>
                <th className="py-3 px-3">Role / Position</th>
                <th className="py-3 px-3">Department</th>
                <th className="py-3 px-3">Shift</th>
                <th className="py-3 px-3">Phone</th>
                <th className="py-3 px-3">Salary</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {paginatedStaff.map((s) => (
                <tr key={s.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-indigo-400">{s.staffId}</td>
                  <td className="py-3 px-4 font-semibold text-slate-100">{s.fullName}</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-semibold">
                      {s.position}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-300">{s.department}</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
                      {s.shift} Shift
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">{s.phone}</td>
                  <td className="py-3 px-3 font-semibold text-cyan-400">৳ {s.salary.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1">
                      <button
                        onClick={() => setSelectedStaffForID(s)}
                        title="Print Staff ID Badge"
                        className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20"
                      >
                        <CreditCard className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleOpenEdit(s)}
                        title="Edit Staff Member"
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
            className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">
                {editingStaff ? `Edit Staff: ${editingStaff.fullName}` : 'Register New Staff Member'}
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
                  <label className="block text-slate-300 mb-1 font-semibold">Role / Position*</label>
                  <input
                    required
                    type="text"
                    value={formData.position || ''}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    placeholder="e.g. Accountant, Librarian"
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Department*</label>
                  <select
                    value={formData.department || 'Administration & Accounts'}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Administration & Accounts">Administration & Accounts</option>
                    <option value="Library & Support">Library & Support</option>
                    <option value="Security & Facilities">Security & Facilities</option>
                    <option value="IT & Technical">IT & Technical</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Shift</label>
                  <select
                    value={formData.shift || 'Day'}
                    onChange={(e) => setFormData({ ...formData, shift: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  >
                    <option value="Day">Day Shift</option>
                    <option value="Morning">Morning Shift</option>
                    <option value="Night">Night Shift</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Phone*</label>
                  <input
                    required
                    type="text"
                    value={formData.phone || ''}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-semibold">Monthly Salary (BDT ৳)</label>
                  <input
                    type="number"
                    value={formData.salary || 22000}
                    onChange={(e) => setFormData({ ...formData, salary: parseInt(e.target.value) || 22000 })}
                    className="w-full p-2 rounded-lg border bg-slate-800 border-slate-700 text-white outline-none"
                  />
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
                  className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow"
                >
                  {editingStaff ? 'Save Changes' : 'Register Staff Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Staff ID Badge */}
      {selectedStaffForID && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div
            className={`w-full max-w-lg rounded-2xl shadow-2xl border p-6 select-none transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <h3 className="font-bold text-sm">Staff Identity Badge (CR80 Format)</h3>
              <button onClick={() => setSelectedStaffForID(null)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="my-6 flex justify-center">
              <div className="w-[340px] h-[214px] rounded-xl overflow-hidden shadow-2xl border border-slate-300 bg-white text-slate-900 flex flex-col justify-between">
                <div className="bg-indigo-900 text-white py-2 px-3 text-center">
                  <h4 className="font-bold text-[11px] leading-tight tracking-wide uppercase">
                    {schoolSetting.schoolName}
                  </h4>
                  <p className="text-[9px] text-indigo-200 font-medium">STAFF IDENTITY BADGE</p>
                </div>

                <div className="p-3 flex space-x-3 items-center">
                  <div className="w-16 h-20 rounded-md bg-slate-100 border border-slate-300 flex flex-col items-center justify-center text-slate-400 shrink-0">
                    <span className="text-xl">💼</span>
                    <span className="text-[8px] font-bold mt-1 text-indigo-800">STAFF</span>
                  </div>

                  <div className="text-[10px] space-y-0.5 leading-tight flex-1">
                    <p className="font-black text-xs text-indigo-950">{selectedStaffForID.fullName}</p>
                    <p className="text-slate-600 font-mono">ID: {selectedStaffForID.staffId}</p>
                    <p className="text-slate-700 font-semibold">{selectedStaffForID.position}</p>
                    <p className="text-slate-700">Department: {selectedStaffForID.department}</p>
                    <p className="text-slate-700">Shift: {selectedStaffForID.shift} Shift</p>
                    <p className="text-slate-600 text-[9px]">Phone: {selectedStaffForID.phone}</p>
                  </div>
                </div>

                <div className="bg-slate-950 text-white py-1 px-3 flex items-center justify-between text-[8px]">
                  <span>Institutional Staff Credential</span>
                  <span className="font-semibold text-slate-300">Principal Signature</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-inherit">
              <button
                onClick={() => setSelectedStaffForID(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Printer className="w-4 h-4" />
                <span>Print Staff Badge</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
