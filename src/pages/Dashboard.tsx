import React from 'react';
import {
  Users,
  GraduationCap,
  Briefcase,
  CalendarCheck,
  CreditCard,
  AlertTriangle,
  TrendingUp,
  School,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Sparkles,
  FileSpreadsheet,
  PlusCircle,
  Printer,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { SchoolSetting, ActivityLogItem, User } from '../types';

interface DashboardProps {
  schoolSetting: SchoolSetting;
  activityLogs: ActivityLogItem[];
  currentUser: User | null;
  isDark: boolean;
  onNavigateModule: (module: string) => void;
  onOpenQuickAction: (action: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  schoolSetting,
  activityLogs,
  currentUser,
  isDark,
  onNavigateModule,
  onOpenQuickAction,
}) => {
  const isBn = schoolSetting.language === 'bn';
  const currency = schoolSetting.currencySymbol;

  // KPI Metrics Data
  const kpiMetrics = [
    {
      title: isBn ? 'মোট শিক্ষার্থী' : 'Total Students',
      value: '1,420',
      subtext: isBn ? 'সক্রিয়: ১,৩৮৫ | নতুন ভর্তি: ৩৫' : 'Active: 1,385  |  Admitted: 35',
      trend: '+4.2%',
      isPositive: true,
      icon: GraduationCap,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10 border-blue-500/20',
    },
    {
      title: isBn ? 'শিক্ষক ও অনুষদ' : 'Teachers & Faculty',
      value: '68',
      subtext: isBn ? 'আজ উপস্থিত: ৬৪ জন (৪ জন ছুটিতে)' : 'Present: 64  |  On Leave: 4',
      trend: '94.1%',
      isPositive: true,
      icon: Users,
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      title: isBn ? 'আজকের উপস্থিতি' : "Today's Attendance",
      value: '94.2%',
      subtext: isBn ? 'উপস্থিত: ১,৩০৪ | অনুপস্থিত: ৮১' : 'Present: 1,304  |  Absent: 81',
      trend: '+1.5%',
      isPositive: true,
      icon: CalendarCheck,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10 border-purple-500/20',
    },
    {
      title: isBn ? 'আজকের ফি আদায়' : "Today's Fees Collection",
      value: `${currency} 85,400`,
      subtext: isBn ? 'চলতি মাস: ৳ ১৪,২০,০০০' : 'This Month: ৳ 1,420,000',
      trend: '+12.4%',
      isPositive: true,
      icon: CreditCard,
      color: 'text-cyan-500',
      bg: 'bg-cyan-500/10 border-cyan-500/20',
    },
    {
      title: isBn ? 'বকেয়া ফি' : 'Outstanding Due Fees',
      value: `${currency} 124,500`,
      subtext: isBn ? '৪২ জন শিক্ষার্থীর বকেয়া বিল' : '42 Pending Invoices (Class 9 & 10)',
      trend: '-8.1%',
      isPositive: false,
      icon: AlertTriangle,
      color: 'text-amber-500',
      bg: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      title: isBn ? 'কর্মকর্তা ও কর্মচারী' : 'Total Staff & Admin',
      value: '24',
      subtext: isBn ? 'হিসাব, লাইব্রেরি, নিরাপত্তা ও অফিস' : 'Finance, Library, Security, Support',
      trend: 'Active',
      isPositive: true,
      icon: Briefcase,
      color: 'text-indigo-500',
      bg: 'bg-indigo-500/10 border-indigo-500/20',
    },
  ];

  // Class Distribution Data
  const classDist = [
    { name: 'Class 6', count: 280, pct: 93, color: 'bg-blue-500' },
    { name: 'Class 7', count: 295, pct: 98, color: 'bg-emerald-500' },
    { name: 'Class 8', count: 310, pct: 100, color: 'bg-purple-500' },
    { name: 'Class 9', count: 265, pct: 88, color: 'bg-amber-500' },
    { name: 'Class 10', count: 270, pct: 90, color: 'bg-cyan-500' },
  ];

  // Monthly Fees Data (6 months in thousands BDT)
  const monthlyFees = [
    { month: 'Jun', amount: 1150, height: '65%' },
    { month: 'Jul', amount: 1320, height: '75%' },
    { month: 'Aug', amount: 1280, height: '72%' },
    { month: 'Sep', amount: 1450, height: '85%' },
    { month: 'Oct', amount: 1390, height: '80%' },
    { month: 'Nov', amount: 1620, height: '95%' },
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto select-none">
      {/* Welcome Banner */}
      <div
        className={`p-6 rounded-2xl border transition-all ${
          isDark
            ? 'bg-gradient-to-r from-slate-900 via-slate-900 to-blue-950/40 border-slate-800'
            : 'bg-gradient-to-r from-blue-50 via-white to-slate-50 border-blue-100'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl">🏛️</span>
              <h1 className="text-xl font-bold tracking-tight text-slate-100">
                {isBn ? schoolSetting.schoolNameBn || schoolSetting.schoolName : schoolSetting.schoolName}
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                EIIN: {schoolSetting.eiinNumber}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              {isBn
                ? `স্বাগতম, ${currentUser?.fullName || 'সুপার অ্যাডমিন'}। EduManage Pro অফলাইন স্কুল ব্যবস্থাপনা সফটওয়্যারে আপনার স্বাগত।`
                : `Welcome back, ${currentUser?.fullName || 'Super Admin'}. EduManage Pro desktop database is synchronized and operational.`}
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => onOpenQuickAction('admit_student')}
              className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-blue-600/20"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>{isBn ? 'নতুন শিক্ষার্থী ভর্তি' : 'Admit Student'}</span>
            </button>
            <button
              onClick={() => onOpenQuickAction('collect_fee')}
              className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg shadow-emerald-600/20"
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>{isBn ? 'ফি গ্রহণ' : 'Collect Fee'}</span>
            </button>
            <button
              onClick={() => window.print()}
              title="Print Executive Summary"
              className={`p-2 rounded-xl border ${
                isDark ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-white border-slate-200 text-slate-700'
              }`}
            >
              <Printer className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpiMetrics.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              className={`p-5 rounded-2xl border transition-all ${
                isDark ? 'bg-slate-900/90 border-slate-800 hover:border-slate-700' : 'bg-white border-slate-200 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{kpi.title}</span>
                <div className={`p-2 rounded-xl border ${kpi.bg}`}>
                  <Icon className={`w-4 h-4 ${kpi.color}`} />
                </div>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-black tracking-tight">{kpi.value}</span>
                <span
                  className={`text-[11px] font-semibold flex items-center ${
                    kpi.isPositive ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {kpi.isPositive ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
                  {kpi.trend}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 font-medium">{kpi.subtext}</p>
            </div>
          );
        })}
      </div>

      {/* Secondary Row: Attendance Breakdown & Fee Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Attendance Breakdown (5 cols) */}
        <div
          className={`lg:col-span-5 p-5 rounded-2xl border flex flex-col justify-between ${
            isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div>
                <h3 className="text-sm font-bold">{isBn ? 'দৈনিক উপস্থিতির পরিসংখ্যান' : "Today's Attendance Overview"}</h3>
                <p className="text-[11px] text-slate-400">Class 6 to Class 10 (1,420 Enrolled)</p>
              </div>
              <button
                onClick={() => onNavigateModule('attendance')}
                className="text-xs font-semibold text-blue-400 hover:underline flex items-center"
              >
                <span>View</span>
                <ChevronRight className="w-3 h-3 ml-0.5" />
              </button>
            </div>

            {/* Attendance Progress Ring Simulation */}
            <div className="mt-5 flex items-center justify-around py-2">
              <div className="text-center">
                <div className="w-20 h-20 rounded-full border-4 border-emerald-500 flex items-center justify-center mx-auto mb-1 bg-emerald-500/10">
                  <span className="text-lg font-bold text-emerald-400">91.8%</span>
                </div>
                <p className="text-xs font-bold text-slate-200">1,304</p>
                <p className="text-[10px] text-slate-400">Present Today</p>
              </div>
              <div className="text-center">
                <div className="w-20 h-20 rounded-full border-4 border-red-500 flex items-center justify-center mx-auto mb-1 bg-red-500/10">
                  <span className="text-lg font-bold text-red-400">5.7%</span>
                </div>
                <p className="text-xs font-bold text-slate-200">81</p>
                <p className="text-[10px] text-slate-400">Absent</p>
              </div>
              <div className="text-center">
                <div className="w-20 h-20 rounded-full border-4 border-amber-500 flex items-center justify-center mx-auto mb-1 bg-amber-500/10">
                  <span className="text-lg font-bold text-amber-400">2.5%</span>
                </div>
                <p className="text-xs font-bold text-slate-200">35</p>
                <p className="text-[10px] text-slate-400">Authorized Leave</p>
              </div>
            </div>

            {/* Attendance bars by class */}
            <div className="mt-4 space-y-2.5">
              {classDist.map((c) => (
                <div key={c.name} className="text-xs">
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="font-semibold">{c.name}</span>
                    <span className="text-slate-400">{c.count} students ({c.pct}% present)</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Monthly Fee Collection Progression (7 cols) */}
        <div
          className={`lg:col-span-7 p-5 rounded-2xl border flex flex-col justify-between ${
            isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
          }`}
        >
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-inherit">
              <div>
                <h3 className="text-sm font-bold">{isBn ? 'মাসিক ফি আদায় পর্যালোচনা' : 'Monthly Fee Collections (BDT)'}</h3>
                <p className="text-[11px] text-slate-400">Past 6 months revenue performance vs targets</p>
              </div>
              <button
                onClick={() => onNavigateModule('fees')}
                className="text-xs font-semibold text-blue-400 hover:underline flex items-center"
              >
                <span>Ledgers</span>
                <ChevronRight className="w-3 h-3 ml-0.5" />
              </button>
            </div>

            {/* Bar chart columns */}
            <div className="mt-8 flex items-end justify-between h-44 px-4 pt-4 border-b border-slate-800">
              {monthlyFees.map((mf) => (
                <div key={mf.month} className="flex flex-col items-center flex-1">
                  <span className="text-[10px] font-mono text-slate-400 mb-1">৳{(mf.amount / 100).toFixed(1)}L</span>
                  <div className="w-10 rounded-t-lg bg-gradient-to-t from-blue-600 to-cyan-400 transition-all hover:opacity-90" style={{ height: mf.height }} />
                  <span className="text-[11px] font-bold text-slate-300 mt-2">{mf.month}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-800">
                <span className="text-[10px] text-slate-400">Total Collected YTD</span>
                <p className="font-bold text-blue-400 text-sm mt-0.5">৳ 82.10 Lakh</p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-800">
                <span className="text-[10px] text-slate-400">Scholarships Granted</span>
                <p className="font-bold text-purple-400 text-sm mt-0.5">৳ 4.60 Lakh</p>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-800">
                <span className="text-[10px] text-slate-400">Recovery Rate</span>
                <p className="font-bold text-emerald-400 text-sm mt-0.5">96.8%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tertiary Section: Recent System Activity & Security Log Feed */}
      <div
        className={`p-5 rounded-2xl border ${
          isDark ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-inherit">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold">{isBn ? 'সিস্টেম অডিট ট্রেইল ও নিরাপত্তা লগ' : 'System Activity & Security Audit Trail'}</h3>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">SQLite WAL Log • Auto-Recorded</span>
        </div>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold text-[11px]">
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">User</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Module</th>
                <th className="py-2.5 px-3">Details</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {activityLogs.slice(0, 6).map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">{log.timestamp}</td>
                  <td className="py-2.5 px-3 font-semibold text-slate-200">{log.username}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-blue-400 font-semibold">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">{log.module}</td>
                  <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate">{log.description}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                        log.severity === 'SECURITY'
                          ? 'bg-amber-500/20 text-amber-400'
                          : log.severity === 'WARNING'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-emerald-500/20 text-emerald-400'
                      }`}
                    >
                      {log.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
