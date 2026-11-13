import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart3,
  FileSpreadsheet,
  FileText,
  Download,
  Printer,
  RefreshCw,
  Users,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  GraduationCap,
  Search,
  Filter,
  Building2,
  Bus,
  BookOpen,
  CalendarCheck,
  ShieldCheck,
} from 'lucide-react';
import { StorageService } from '../services/storage';
import {
  ComprehensiveReportAnalytics,
  SchoolClassInfo,
  SchoolSetting,
  Student,
  AccountTransactionRecord,
} from '../types';

interface ReportsManagementProps {
  isDark?: boolean;
}

export const ReportsManagement: React.FC<ReportsManagementProps> = ({ isDark = true }) => {
  const [activeTab, setActiveTab] = useState<'analytics' | 'generator' | 'briefing' | 'export'>('analytics');
  const [selectedClassId, setSelectedClassId] = useState<number | undefined>(undefined);
  const [reportType, setReportType] = useState<'defaulters' | 'demographics' | 'attendance' | 'financial'>('defaulters');
  const [searchTerm, setSearchTerm] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [exportHistory, setExportHistory] = useState<{ id: number; filename: string; format: string; timestamp: string }[]>([]);

  const [classes, setClasses] = useState<SchoolClassInfo[]>([]);
  const [schoolSetting, setSchoolSetting] = useState<SchoolSetting>(() => StorageService.getSchoolSettings());
  const [analytics, setAnalytics] = useState<ComprehensiveReportAnalytics>(() =>
    StorageService.getComprehensiveReportAnalytics()
  );
  const [students, setStudents] = useState<Student[]>([]);
  const [transactions, setTransactions] = useState<AccountTransactionRecord[]>([]);

  const loadAllData = () => {
    setClasses(StorageService.getDetailedClasses());
    setSchoolSetting(StorageService.getSchoolSettings());
    setAnalytics(StorageService.getComprehensiveReportAnalytics(selectedClassId));
    setStudents(StorageService.getStudents());
    setTransactions(StorageService.getAccountTransactions());
  };

  useEffect(() => {
    loadAllData();
  }, [selectedClassId]);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 4000);
  };

  const triggerDownload = (filename: string, content: string, mimeType: string, formatLabel: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportHistory((prev) => [
      {
        id: Date.now(),
        filename,
        format: formatLabel,
        timestamp: new Date().toLocaleTimeString(),
      },
      ...prev.slice(0, 9),
    ]);
    showToast(`Exported ${filename} (${formatLabel})`);
  };

  const handleExportCsv = (type: 'defaulters' | 'demographics' | 'attendance' | 'financial') => {
    const { filename, csvContent } = StorageService.generateCsvExport(type, selectedClassId);
    triggerDownload(filename, '\uFEFF' + csvContent, 'text/csv;charset=utf-8;', 'CSV');
  };

  const handleExportMasterWorkbook = () => {
    const dateStamp = new Date().toISOString().split('T')[0];
    // Generate SpreadsheetML 2003 XML (opens natively in Microsoft Excel with multi-sheet support)
    const escapeXml = (s: unknown) =>
      String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');

    const makeRow = (cells: (string | number)[], styleId = 'Default') =>
      `<Row>${cells
        .map((c) => {
          const isNum = typeof c === 'number' && !Number.isNaN(c);
          return `<Cell ss:StyleID="${styleId}"><Data ss:Type="${isNum ? 'Number' : 'String'}">${escapeXml(c)}</Data></Cell>`;
        })
        .join('')}</Row>`;

    const summaryRows = [
      makeRow(['Category', 'Indicator', 'Value', 'Status'], 'Header'),
      makeRow(['Demographics', 'Total Enrolled Students', analytics.totalStudents, 'Active']),
      makeRow(['Demographics', 'Male / Female Split', `${analytics.maleStudents} M / ${analytics.femaleStudents} F`, 'Balanced']),
      makeRow(['Staffing', 'Total Faculty & Staff', analytics.totalStaff, 'Optimal']),
      makeRow(['Finance', 'Total Fee Billed', analytics.totalInvoiced, 'Audited']),
      makeRow(['Finance', 'Total Fee Collected', analytics.totalCollected, `${analytics.collectionEfficiency}%`]),
      makeRow(['Finance', 'Total Fee Dues', analytics.totalDues, `${analytics.defaultersCount} Overdue`]),
      makeRow(['Finance', 'Net Operating Surplus', analytics.netSurplus, analytics.netSurplus >= 0 ? 'Surplus' : 'Deficit']),
      makeRow(['Academics', 'Overall Attendance Rate', `${analytics.attendanceRate}%`, 'Compliant']),
      makeRow(['Academics', 'Exam Pass Rate', `${analytics.passRate}%`, 'Exceeding']),
      makeRow(['Academics', 'Institutional Avg GPA', analytics.avgGpa, 'Distinction']),
      makeRow(['Facilities', 'Library Active Loans', `${analytics.activeLoans} / ${analytics.totalBooks}`, 'Active']),
      makeRow(['Facilities', 'Transport Passengers', analytics.transportPassengers, `${analytics.totalRoutes} Routes`]),
      makeRow(['Facilities', 'Hostel Occupancy', `${analytics.hostelOccupancy}/${analytics.hostelCapacity}`, `${analytics.hostelOccupancyRate}%`]),
    ].join('\n');

    const defaulterRows = [
      makeRow(['Invoice No', 'Admission No', 'Student Name', 'Class & Section', 'Billed', 'Paid', 'Due', 'Due Date', 'Days Overdue', 'Phone'], 'Header'),
      ...analytics.defaultersList.map((d) =>
        makeRow([
          d.invoiceNumber,
          d.admissionNumber,
          d.studentName,
          d.classSection,
          d.totalAmount,
          d.paidAmount,
          d.dueAmount,
          d.dueDate,
          d.daysOverdue,
          d.guardianPhone,
        ])
      ),
    ].join('\n');

    const studentRows = [
      makeRow(['Student ID', 'Admission No', 'Full Name', 'Class', 'Section', 'Roll', 'Gender', 'Guardian Phone', 'Status'], 'Header'),
      ...students.map((s) =>
        makeRow([
          s.studentId,
          s.admissionNumber,
          s.fullName,
          s.className,
          s.sectionName || '',
          s.rollNumber,
          s.gender,
          s.guardian?.guardianPhone || '',
          s.status,
        ])
      ),
    ].join('\n');

    const workbookXml = `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal"><Font ss:FontName="Calibri" ss:Size="11"/></Style>
  <Style ss:ID="Header"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1E3A8A" ss:Pattern="Solid"/></Style>
 </Styles>
 <Worksheet ss:Name="Executive Summary"><Table>${summaryRows}</Table></Worksheet>
 <Worksheet ss:Name="Fee Defaulters"><Table>${defaulterRows}</Table></Worksheet>
 <Worksheet ss:Name="Student Demographics"><Table>${studentRows}</Table></Worksheet>
</Workbook>`;

    triggerDownload(
      `EduManage_Master_Workbook_${dateStamp}.xls`,
      workbookXml,
      'application/vnd.ms-excel;charset=utf-8;',
      'Excel (.xls)'
    );
  };

  const selectedClassName = useMemo(() => {
    if (!selectedClassId) return undefined;
    return classes.find((c) => c.id === selectedClassId)?.name;
  }, [classes, selectedClassId]);

  const filteredDefaulters = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return analytics.defaultersList.filter(
      (d) =>
        !q ||
        d.studentName.toLowerCase().includes(q) ||
        d.admissionNumber.toLowerCase().includes(q) ||
        d.invoiceNumber.toLowerCase().includes(q) ||
        d.classSection.toLowerCase().includes(q)
    );
  }, [analytics.defaultersList, searchTerm]);

  const filteredStudents = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return students.filter((s) => {
      if (selectedClassName && s.className !== selectedClassName) return false;
      return (
        !q ||
        s.fullName.toLowerCase().includes(q) ||
        s.admissionNumber.toLowerCase().includes(q) ||
        s.className.toLowerCase().includes(q)
      );
    });
  }, [students, selectedClassName, searchTerm]);

  const filteredTransactions = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return transactions.filter(
      (t) =>
        !q ||
        (t.description || t.paidToReceivedFrom || '').toLowerCase().includes(q) ||
        t.voucherNo.toLowerCase().includes(q) ||
        t.categoryName.toLowerCase().includes(q)
    );
  }, [transactions, searchTerm]);

  const cardBg = isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200';
  const subCardBg = isDark ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200';
  const textPrimary = isDark ? 'text-white' : 'text-slate-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-slate-500';
  const currency = schoolSetting.currencySymbol || '৳';

  const malePct =
    analytics.totalStudents > 0 ? Math.round((analytics.maleStudents / analytics.totalStudents) * 100) : 50;
  const femalePct = 100 - malePct;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-xl border border-emerald-500 text-sm font-medium">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/15 text-blue-500">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <h1 className={`text-2xl font-bold tracking-tight ${textPrimary}`}>
                Comprehensive Reports, Analytics & Data Export
              </h1>
              <p className={`text-sm ${textMuted}`}>
                Cross-module performance audits, arrears intelligence, attendance compliance & Excel/CSV/PDF exports
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setActiveTab('briefing')}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium transition-colors"
          >
            <FileText className="w-4 h-4" />
            Executive PDF Briefing
          </button>
          <button
            onClick={handleExportMasterWorkbook}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Export Master Workbook (.xls)
          </button>
          <button
            onClick={loadAllData}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
              isDark
                ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* 5 Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-blue-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Student Strength</span>
            <Users className="w-4 h-4 text-blue-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{analytics.activeStudents} Active</div>
          <div className={`text-xs mt-1 ${textMuted}`}>
            {analytics.maleStudents} Male / {analytics.femaleStudents} Female ({analytics.totalStudents} Total)
          </div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-emerald-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Attendance Rate</span>
            <CalendarCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{analytics.attendanceRate}%</div>
          <div className="text-xs mt-1 text-emerald-500 font-medium">Target Benchmark: 90.0%</div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-amber-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Fee Realization</span>
            <DollarSign className="w-4 h-4 text-amber-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{analytics.collectionEfficiency}%</div>
          <div className={`text-xs mt-1 ${textMuted}`}>
            {analytics.defaultersCount} overdue invoice{analytics.defaultersCount === 1 ? '' : 's'}
          </div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-violet-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Academic GPA</span>
            <GraduationCap className="w-4 h-4 text-violet-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{analytics.avgGpa} / 5.00</div>
          <div className="text-xs mt-1 text-violet-400 font-medium">Pass Rate: {analytics.passRate}%</div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-cyan-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Net Cash Surplus</span>
            <TrendingUp className="w-4 h-4 text-cyan-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${analytics.netSurplus >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
            {currency} {analytics.netSurplus.toLocaleString()}
          </div>
          <div className={`text-xs mt-1 ${textMuted}`}>
            Income {currency}{analytics.totalIncome.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className={`flex flex-wrap gap-2 border-b pb-3 ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        {[
          { id: 'analytics', label: 'Institutional Health & Analytics', icon: BarChart3 },
          { id: 'generator', label: 'Report Generator & Live Preview', icon: Filter },
          { id: 'briefing', label: 'Executive Summary PDF Preview', icon: FileText },
          { id: 'export', label: 'Data Export Center', icon: Download },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                active
                  ? 'bg-blue-600 text-white shadow-sm'
                  : isDark
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: ANALYTICS & INSTITUTIONAL HEALTH */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Financial & Fee Realization Panel */}
            <div className={`p-5 rounded-xl border ${cardBg} space-y-4`}>
              <div className="flex items-center justify-between">
                <h2 className={`text-base font-bold flex items-center gap-2 ${textPrimary}`}>
                  <DollarSign className="w-5 h-5 text-emerald-500" />
                  Financial & Fee Collection Audit
                </h2>
                <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-500/15 text-emerald-400 font-semibold">
                  {analytics.collectionEfficiency}% Realized
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className={textMuted}>Fee Collection Progress ({currency}{analytics.totalCollected.toLocaleString()} / {currency}{analytics.totalInvoiced.toLocaleString()})</span>
                    <span className={textPrimary}>{analytics.collectionEfficiency}%</span>
                  </div>
                  <div className={`w-full h-2.5 rounded-full overflow-hidden ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`}>
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, analytics.collectionEfficiency)}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className={`p-3 rounded-lg border ${subCardBg}`}>
                    <div className={`text-xs ${textMuted}`}>Gross Fee Billed</div>
                    <div className={`text-lg font-bold mt-0.5 ${textPrimary}`}>
                      {currency} {analytics.totalInvoiced.toLocaleString()}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg border ${subCardBg}`}>
                    <div className={`text-xs ${textMuted}`}>Outstanding Arrears</div>
                    <div className="text-lg font-bold mt-0.5 text-rose-500">
                      {currency} {analytics.totalDues.toLocaleString()}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg border ${subCardBg}`}>
                    <div className={`text-xs ${textMuted}`}>Operating Income</div>
                    <div className="text-lg font-bold mt-0.5 text-emerald-500">
                      {currency} {analytics.totalIncome.toLocaleString()}
                    </div>
                  </div>
                  <div className={`p-3 rounded-lg border ${subCardBg}`}>
                    <div className={`text-xs ${textMuted}`}>Operating Expenses</div>
                    <div className="text-lg font-bold mt-0.5 text-amber-500">
                      {currency} {analytics.totalExpenses.toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Demography & Campus Facilities Panel */}
            <div className={`p-5 rounded-xl border ${cardBg} space-y-4`}>
              <div className="flex items-center justify-between">
                <h2 className={`text-base font-bold flex items-center gap-2 ${textPrimary}`}>
                  <Building2 className="w-5 h-5 text-blue-500" />
                  Student Demography & Campus Facilities
                </h2>
                <span className="text-xs px-2.5 py-1 rounded-md bg-blue-500/15 text-blue-400 font-semibold">
                  {analytics.totalStaff} Faculty & Staff
                </span>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1.5">
                  <span className="text-blue-400">Male: {analytics.maleStudents} ({malePct}%)</span>
                  <span className="text-pink-400">Female: {analytics.femaleStudents} ({femalePct}%)</span>
                </div>
                <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-800">
                  <div className="bg-blue-500 h-full" style={{ width: `${malePct}%` }} />
                  <div className="bg-pink-500 h-full" style={{ width: `${femalePct}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className={`p-3 rounded-lg border ${subCardBg}`}>
                  <div className="flex items-center gap-1.5 text-xs text-amber-400 font-semibold">
                    <BookOpen className="w-3.5 h-3.5" />
                    Library
                  </div>
                  <div className={`text-lg font-bold mt-1 ${textPrimary}`}>{analytics.totalBooks} Titles</div>
                  <div className={`text-xs ${textMuted}`}>{analytics.activeLoans} Active Loans</div>
                </div>

                <div className={`p-3 rounded-lg border ${subCardBg}`}>
                  <div className="flex items-center gap-1.5 text-xs text-blue-400 font-semibold">
                    <Bus className="w-3.5 h-3.5" />
                    Transport
                  </div>
                  <div className={`text-lg font-bold mt-1 ${textPrimary}`}>{analytics.transportPassengers} Riders</div>
                  <div className={`text-xs ${textMuted}`}>{analytics.totalRoutes} Active Routes</div>
                </div>

                <div className={`p-3 rounded-lg border ${subCardBg}`}>
                  <div className="flex items-center gap-1.5 text-xs text-teal-400 font-semibold">
                    <Building2 className="w-3.5 h-3.5" />
                    Hostel
                  </div>
                  <div className={`text-lg font-bold mt-1 ${textPrimary}`}>{analytics.hostelOccupancyRate}%</div>
                  <div className={`text-xs ${textMuted}`}>
                    {analytics.hostelOccupancy}/{analytics.hostelCapacity} Beds
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Class Attendance Compliance Table */}
          <div className={`rounded-xl border overflow-hidden ${cardBg}`}>
            <div className={`p-4 border-b flex items-center justify-between ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
              <div>
                <h3 className={`text-base font-bold ${textPrimary}`}>Class-by-Class Attendance Compliance Audit</h3>
                <p className={`text-xs ${textMuted}`}>Evaluated from real recorded attendance registers</p>
              </div>
              <button
                onClick={() => handleExportCsv('attendance')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className={isDark ? 'bg-slate-800/80 text-slate-300' : 'bg-slate-50 text-slate-600'}>
                  <tr>
                    <th className="px-4 py-3 font-semibold">Class / Grade</th>
                    <th className="px-4 py-3 font-semibold text-center">Recorded Sessions</th>
                    <th className="px-4 py-3 font-semibold text-center">Present</th>
                    <th className="px-4 py-3 font-semibold text-center">Absent</th>
                    <th className="px-4 py-3 font-semibold text-center">Late</th>
                    <th className="px-4 py-3 font-semibold">Attendance Rate</th>
                    <th className="px-4 py-3 font-semibold">Compliance Status</th>
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                  {analytics.classAttendanceList.map((row) => (
                    <tr key={row.className} className={isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                      <td className={`px-4 py-3 font-semibold ${textPrimary}`}>{row.className}</td>
                      <td className={`px-4 py-3 text-center ${textMuted}`}>{row.totalRecords}</td>
                      <td className="px-4 py-3 text-center text-emerald-500 font-medium">{row.presentCount}</td>
                      <td className="px-4 py-3 text-center text-rose-500 font-medium">{row.absentCount}</td>
                      <td className="px-4 py-3 text-center text-amber-500 font-medium">{row.lateCount}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className={`w-24 h-2 rounded-full overflow-hidden ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`}>
                            <div
                              className={`h-full rounded-full ${
                                row.attendancePercentage >= 90
                                  ? 'bg-emerald-500'
                                  : row.attendancePercentage >= 75
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.min(100, row.attendancePercentage)}%` }}
                            />
                          </div>
                          <span className={`font-semibold text-xs ${textPrimary}`}>{row.attendancePercentage}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                            row.attendancePercentage >= 90
                              ? 'bg-emerald-500/15 text-emerald-400'
                              : row.attendancePercentage >= 75
                              ? 'bg-amber-500/15 text-amber-400'
                              : 'bg-rose-500/15 text-rose-400'
                          }`}
                        >
                          {row.attendancePercentage >= 90
                            ? 'Optimal (>=90%)'
                            : row.attendancePercentage >= 75
                            ? 'Satisfactory'
                            : 'Needs Review'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: REPORT GENERATOR & LIVE PREVIEW */}
      {activeTab === 'generator' && (
        <div className="space-y-4">
          <div className={`p-4 rounded-xl border flex flex-col md:flex-row md:items-center gap-4 ${cardBg}`}>
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Report Dataset</label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value as typeof reportType)}
                  className={`w-full px-3 py-2 rounded-lg border text-sm ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="defaulters">Fee Defaulters & Arrears Audit</option>
                  <option value="demographics">Student Demographic Roster</option>
                  <option value="attendance">Attendance Compliance Summary</option>
                  <option value="financial">Accounting General Ledger</option>
                </select>
              </div>

              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Class Filter</label>
                <select
                  value={selectedClassId ?? ''}
                  onChange={(e) => setSelectedClassId(e.target.value ? Number(e.target.value) : undefined)}
                  className={`w-full px-3 py-2 rounded-lg border text-sm ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  <option value="">All Classes</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Search Records</label>
                <div className="relative">
                  <Search className={`w-4 h-4 absolute left-3 top-2.5 ${textMuted}`} />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Filter by name, ID, invoice..."
                    className={`w-full pl-9 pr-3 py-2 rounded-lg border text-sm ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
                    }`}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-end gap-2 shrink-0">
              <button
                onClick={() => handleExportCsv(reportType)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold"
              >
                <Download className="w-4 h-4" />
                Download CSV
              </button>
            </div>
          </div>

          {/* Preview Table */}
          <div className={`rounded-xl border overflow-hidden ${cardBg}`}>
            <div className="overflow-x-auto">
              {reportType === 'defaulters' && (
                <table className="w-full text-sm text-left">
                  <thead className={isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Invoice No</th>
                      <th className="px-4 py-3 font-semibold">Student</th>
                      <th className="px-4 py-3 font-semibold">Class & Section</th>
                      <th className="px-4 py-3 font-semibold">Description</th>
                      <th className="px-4 py-3 font-semibold text-right">Billed</th>
                      <th className="px-4 py-3 font-semibold text-right">Paid</th>
                      <th className="px-4 py-3 font-semibold text-right">Due Balance</th>
                      <th className="px-4 py-3 font-semibold">Guardian Phone</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                    {filteredDefaulters.length === 0 ? (
                      <tr>
                        <td colSpan={9} className={`px-4 py-8 text-center ${textMuted}`}>
                          No outstanding fee defaulters match the current filter.
                        </td>
                      </tr>
                    ) : (
                      filteredDefaulters.map((d) => (
                        <tr key={d.invoiceId} className={isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                          <td className="px-4 py-3 font-mono text-xs text-blue-400">{d.invoiceNumber}</td>
                          <td className="px-4 py-3">
                            <div className={`font-semibold ${textPrimary}`}>{d.studentName}</div>
                            <div className={`text-xs ${textMuted}`}>{d.admissionNumber}</div>
                          </td>
                          <td className={`px-4 py-3 ${textMuted}`}>{d.classSection}</td>
                          <td className={`px-4 py-3 ${textPrimary}`}>{d.title}</td>
                          <td className={`px-4 py-3 text-right ${textMuted}`}>
                            {currency}{d.totalAmount.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right text-emerald-500">
                            {currency}{d.paidAmount.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-rose-500">
                            {currency}{d.dueAmount.toLocaleString()}
                          </td>
                          <td className={`px-4 py-3 font-mono text-xs ${textMuted}`}>{d.guardianPhone}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/15 text-rose-400">
                              {d.status} ({d.daysOverdue}d)
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}

              {reportType === 'demographics' && (
                <table className="w-full text-sm text-left">
                  <thead className={isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Admission No</th>
                      <th className="px-4 py-3 font-semibold">Full Name</th>
                      <th className="px-4 py-3 font-semibold">Class & Section</th>
                      <th className="px-4 py-3 font-semibold text-center">Roll</th>
                      <th className="px-4 py-3 font-semibold">Gender</th>
                      <th className="px-4 py-3 font-semibold">Guardian</th>
                      <th className="px-4 py-3 font-semibold">Phone</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                    {filteredStudents.map((s) => (
                      <tr key={s.id} className={isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                        <td className="px-4 py-3 font-mono text-xs text-blue-400">{s.admissionNumber}</td>
                        <td className={`px-4 py-3 font-semibold ${textPrimary}`}>{s.fullName}</td>
                        <td className={`px-4 py-3 ${textMuted}`}>
                          {s.className} {s.sectionName ? `- ${s.sectionName}` : ''}
                        </td>
                        <td className={`px-4 py-3 text-center ${textPrimary}`}>{s.rollNumber}</td>
                        <td className={`px-4 py-3 ${textMuted}`}>{s.gender}</td>
                        <td className={`px-4 py-3 ${textPrimary}`}>{s.guardian?.guardianName || 'N/A'}</td>
                        <td className={`px-4 py-3 font-mono text-xs ${textMuted}`}>{s.guardian?.guardianPhone || 'N/A'}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/15 text-emerald-400">
                            {s.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {reportType === 'attendance' && (
                <table className="w-full text-sm text-left">
                  <thead className={isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Class / Grade</th>
                      <th className="px-4 py-3 font-semibold text-center">Sessions</th>
                      <th className="px-4 py-3 font-semibold text-center">Present</th>
                      <th className="px-4 py-3 font-semibold text-center">Absent</th>
                      <th className="px-4 py-3 font-semibold text-center">Late</th>
                      <th className="px-4 py-3 font-semibold text-right">Attendance %</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                    {analytics.classAttendanceList.map((row) => (
                      <tr key={row.className}>
                        <td className={`px-4 py-3 font-semibold ${textPrimary}`}>{row.className}</td>
                        <td className={`px-4 py-3 text-center ${textMuted}`}>{row.totalRecords}</td>
                        <td className="px-4 py-3 text-center text-emerald-500">{row.presentCount}</td>
                        <td className="px-4 py-3 text-center text-rose-500">{row.absentCount}</td>
                        <td className="px-4 py-3 text-center text-amber-500">{row.lateCount}</td>
                        <td className={`px-4 py-3 text-right font-bold ${textPrimary}`}>{row.attendancePercentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {reportType === 'financial' && (
                <table className="w-full text-sm text-left">
                  <thead className={isDark ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                    <tr>
                      <th className="px-4 py-3 font-semibold">Voucher No</th>
                      <th className="px-4 py-3 font-semibold">Date</th>
                      <th className="px-4 py-3 font-semibold">Type</th>
                      <th className="px-4 py-3 font-semibold">Category</th>
                      <th className="px-4 py-3 font-semibold">Description</th>
                      <th className="px-4 py-3 font-semibold text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                    {filteredTransactions.map((tx) => (
                      <tr key={tx.id}>
                        <td className="px-4 py-3 font-mono text-xs text-blue-400">{tx.voucherNo}</td>
                        <td className={`px-4 py-3 text-xs ${textMuted}`}>{tx.transactionDate}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${
                              tx.type === 'Income'
                                ? 'bg-emerald-500/15 text-emerald-400'
                                : 'bg-rose-500/15 text-rose-400'
                            }`}
                          >
                            {tx.type}
                          </span>
                        </td>
                        <td className={`px-4 py-3 ${textMuted}`}>{tx.categoryName}</td>
                        <td className={`px-4 py-3 ${textPrimary}`}>{tx.description || tx.paidToReceivedFrom}</td>
                        <td
                          className={`px-4 py-3 text-right font-bold ${
                            tx.type === 'Income' ? 'text-emerald-500' : 'text-rose-500'
                          }`}
                        >
                          {currency}{tx.amount.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: EXECUTIVE BRIEFING A4 PDF PREVIEW */}
      {activeTab === 'briefing' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className={`text-sm ${textMuted}`}>
              Portrait A4 Executive Performance Briefing — mirrors Python ReportLab <code className="text-blue-400">ExecutiveSummaryPdf</code>
            </p>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold"
            >
              <Printer className="w-4 h-4" />
              Print / Save as PDF
            </button>
          </div>

          <div className="bg-white text-slate-900 rounded-xl shadow-2xl border border-slate-300 max-w-4xl mx-auto p-8 md:p-10 space-y-6">
            {/* Institutional Header */}
            <div className="text-center border-b-2 border-blue-900 pb-4">
              <h2 className="text-2xl font-extrabold text-blue-950 uppercase tracking-wide">
                {schoolSetting.schoolName}
              </h2>
              <p className="text-xs italic text-slate-600 mt-1">{schoolSetting.motto}</p>
              <p className="text-xs text-slate-500 mt-1">
                {schoolSetting.address} | Phone: {schoolSetting.phone} | Email: {schoolSetting.email} | EIIN: {schoolSetting.eiinNumber}
              </p>
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold uppercase tracking-wider text-slate-900">
                EXECUTIVE PERFORMANCE BRIEFING & AUDIT SUMMARY
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Generated on {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} • Official Governance Audit
              </p>
            </div>

            {/* Section 1 */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-2">
                1. Institutional Scorecard & Core Benchmarks
              </h4>
              <table className="w-full text-xs border border-slate-300">
                <thead className="bg-blue-900 text-white">
                  <tr>
                    <th className="p-2 text-left">Metric Indicator</th>
                    <th className="p-2 text-left">Audited Value</th>
                    <th className="p-2 text-left">Benchmark</th>
                    <th className="p-2 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  <tr>
                    <td className="p-2 font-medium">Total Enrolled Students</td>
                    <td className="p-2 font-bold">{analytics.activeStudents} Active ({analytics.totalStudents} Total)</td>
                    <td className="p-2">500 Target</td>
                    <td className="p-2 font-semibold text-emerald-700">Optimal</td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="p-2 font-medium">Faculty & Staff Strength</td>
                    <td className="p-2 font-bold">{analytics.totalStaff} ({analytics.teachingStaff} Teaching)</td>
                    <td className="p-2">1:15 Ratio</td>
                    <td className="p-2 font-semibold text-emerald-700">Compliant</td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium">Attendance Compliance Rate</td>
                    <td className="p-2 font-bold">{analytics.attendanceRate}%</td>
                    <td className="p-2">90.0% Minimum</td>
                    <td className="p-2 font-semibold text-emerald-700">Healthy</td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="p-2 font-medium">Fee Collection Efficiency</td>
                    <td className="p-2 font-bold">{analytics.collectionEfficiency}%</td>
                    <td className="p-2">85.0% Target</td>
                    <td className="p-2 font-semibold text-blue-700">
                      {analytics.collectionEfficiency >= 80 ? 'On Track' : 'Follow-Up'}
                    </td>
                  </tr>
                  <tr>
                    <td className="p-2 font-medium">Institutional Average GPA</td>
                    <td className="p-2 font-bold">{analytics.avgGpa} / 5.00</td>
                    <td className="p-2">3.50 Standard</td>
                    <td className="p-2 font-semibold text-emerald-700">Distinction ({analytics.passRate}% Pass)</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Section 2 */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-2">
                2. Financial Health & Fee Realization Summary
              </h4>
              <table className="w-full text-xs border border-slate-300">
                <thead className="bg-blue-600 text-white">
                  <tr>
                    <th className="p-2 text-left">Revenue & Accounts Stream</th>
                    <th className="p-2 text-right">Amount ({currency})</th>
                    <th className="p-2 text-left">Audit Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  <tr>
                    <td className="p-2">Gross Student Fee Billing</td>
                    <td className="p-2 text-right font-semibold">{currency} {analytics.totalInvoiced.toLocaleString()}</td>
                    <td className="p-2 text-slate-600">Academic Fee Invoices</td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="p-2">Realized Collections (Paid)</td>
                    <td className="p-2 text-right font-semibold text-emerald-700">{currency} {analytics.totalCollected.toLocaleString()}</td>
                    <td className="p-2 text-slate-600">{analytics.collectionEfficiency}% Realized</td>
                  </tr>
                  <tr>
                    <td className="p-2">Outstanding Dues / Arrears</td>
                    <td className="p-2 text-right font-semibold text-rose-700">{currency} {analytics.totalDues.toLocaleString()}</td>
                    <td className="p-2 text-slate-600">{analytics.defaultersCount} Overdue Accounts</td>
                  </tr>
                  <tr className="bg-slate-50">
                    <td className="p-2">General Operating Income / Expenditure</td>
                    <td className="p-2 text-right font-semibold">
                      +{currency}{analytics.totalIncome.toLocaleString()} / -{currency}{analytics.totalExpenses.toLocaleString()}
                    </td>
                    <td className="p-2 text-slate-600">Chart of Accounts Ledger</td>
                  </tr>
                  <tr className="bg-sky-50 font-bold">
                    <td className="p-2">Net Operating Surplus</td>
                    <td className="p-2 text-right text-blue-950">{currency} {analytics.netSurplus.toLocaleString()}</td>
                    <td className="p-2 text-blue-900">{analytics.netSurplus >= 0 ? 'Positive Cashflow' : 'Deficit'}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Section 3 Signatures */}
            <div className="grid grid-cols-3 gap-6 pt-10 text-center text-xs">
              <div>
                <div className="border-t border-slate-400 pt-2 font-bold">Prepared By</div>
                <div className="text-slate-600">Lead Data Analyst</div>
              </div>
              <div>
                <div className="border-t border-slate-400 pt-2 font-bold">Audited By</div>
                <div className="text-slate-600">Bursar / Financial Controller</div>
              </div>
              <div>
                <div className="border-t border-slate-400 pt-2 font-bold">Approved By</div>
                <div className="text-slate-600">{schoolSetting.principalName}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DATA EXPORT CENTER */}
      {activeTab === 'export' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div className={`p-5 rounded-xl border border-t-4 border-t-emerald-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <FileSpreadsheet className="w-6 h-6 text-emerald-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Master Institutional Workbook</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Multi-sheet Excel workbook containing Executive Summary, Fee Defaulters, and Student Demographics generated directly from active records.
                </p>
              </div>
              <button
                onClick={handleExportMasterWorkbook}
                className="mt-5 w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Master Excel (.xls)
              </button>
            </div>

            <div className={`p-5 rounded-xl border border-t-4 border-t-rose-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <AlertTriangle className="w-6 h-6 text-rose-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Fee Defaulters & Arrears CSV</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Complete roster of overdue fee invoices, pending balances, days overdue, and guardian contact numbers for fee recovery follow-up.
                </p>
              </div>
              <button
                onClick={() => handleExportCsv('defaulters')}
                className="mt-5 w-full py-2.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Defaulters CSV
              </button>
            </div>

            <div className={`p-5 rounded-xl border border-t-4 border-t-blue-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <Users className="w-6 h-6 text-blue-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Master Student Roster CSV</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Full student registry with admission numbers, class, section, roll numbers, birth dates, blood group, and guardian details.
                </p>
              </div>
              <button
                onClick={() => handleExportCsv('demographics')}
                className="mt-5 w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Student CSV
              </button>
            </div>

            <div className={`p-5 rounded-xl border border-t-4 border-t-amber-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <CalendarCheck className="w-6 h-6 text-amber-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Attendance Compliance CSV</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Class-wise attendance audit summary showing total sessions, present, absent, late counts, and compliance percentages.
                </p>
              </div>
              <button
                onClick={() => handleExportCsv('attendance')}
                className="mt-5 w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Attendance CSV
              </button>
            </div>

            <div className={`p-5 rounded-xl border border-t-4 border-t-cyan-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <DollarSign className="w-6 h-6 text-cyan-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Accounting Ledger CSV</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Full double-entry income and expenditure voucher dataset for external financial reconciliation and annual tax audit.
                </p>
              </div>
              <button
                onClick={() => handleExportCsv('financial')}
                className="mt-5 w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Ledger CSV
              </button>
            </div>

            <div className={`p-5 rounded-xl border border-t-4 border-t-indigo-500 flex flex-col justify-between ${cardBg}`}>
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <ShieldCheck className="w-6 h-6 text-indigo-500" />
                  <h3 className={`font-bold text-base ${textPrimary}`}>Executive Audit PDF</h3>
                </div>
                <p className={`text-xs leading-relaxed ${textMuted}`}>
                  Opens the Portrait A4 Institutional Scorecard & Financial Summary ready for direct printing or PDF archival.
                </p>
              </div>
              <button
                onClick={() => setActiveTab('briefing')}
                className="mt-5 w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold flex items-center justify-center gap-2"
              >
                <Printer className="w-4 h-4" />
                Open Printable Briefing
              </button>
            </div>
          </div>

          {/* Session Export Activity */}
          <div className={`p-4 rounded-xl border ${cardBg}`}>
            <h4 className={`text-sm font-bold mb-2 ${textPrimary}`}>Recent Export History (This Session)</h4>
            {exportHistory.length === 0 ? (
              <p className={`text-xs ${textMuted}`}>No exports triggered in this session yet. Click any export button above.</p>
            ) : (
              <div className="space-y-1.5">
                {exportHistory.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center justify-between text-xs px-3 py-2 rounded-lg border ${subCardBg}`}
                  >
                    <span className={`font-mono ${textPrimary}`}>{item.filename}</span>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-semibold">
                        {item.format}
                      </span>
                      <span className={textMuted}>{item.timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
