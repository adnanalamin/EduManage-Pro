import React from 'react';
import {
  LayoutDashboard,
  GraduationCap,
  Users,
  Briefcase,
  BookOpen,
  CalendarCheck,
  CreditCard,
  TrendingUp,
  FileSpreadsheet,
  Award,
  Clock,
  Library,
  Bus,
  Building2,
  Bell,
  CalendarDays,
  FileBarChart,
  BadgeCheck,
  Settings,
  FileCode2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SidebarProps {
  currentModule: string;
  onSelectModule: (module: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isDark: boolean;
  schoolName: string;
}

export const MODULE_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: 'Live', phase: 1 },
  { id: 'students', label: 'Students', icon: GraduationCap, badge: 'Live', phase: 2 },
  { id: 'teachers', label: 'Teachers', icon: Users, badge: 'Live', phase: 3 },
  { id: 'staff', label: 'Staff Management', icon: Briefcase, badge: 'Live', phase: 3 },
  { id: 'academics', label: 'Academics', icon: BookOpen, badge: 'Live', phase: 4 },
  { id: 'attendance', label: 'Attendance', icon: CalendarCheck, badge: 'Live', phase: 5 },
  { id: 'fees', label: 'Fees & Billing', icon: CreditCard, badge: 'Live', phase: 6 },
  { id: 'accounting', label: 'Accounting', icon: TrendingUp, badge: 'Live', phase: 7 },
  { id: 'exams', label: 'Exams', icon: FileSpreadsheet, badge: 'Live', phase: 8 },
  { id: 'results', label: 'Results & GPA', icon: Award, badge: 'Live', phase: 8 },
  { id: 'timetable', label: 'Timetable', icon: Clock, badge: 'Live', phase: 9 },
  { id: 'library', label: 'Library', icon: Library, badge: 'Phase 10', phase: 10 },
  { id: 'transport', label: 'Transport', icon: Bus, badge: 'Phase 11', phase: 11 },
  { id: 'hostel', label: 'Hostel', icon: Building2, badge: 'Phase 12', phase: 12 },
  { id: 'notices', label: 'Notices', icon: Bell, badge: 'Phase 13', phase: 13 },
  { id: 'events', label: 'Events Calendar', icon: CalendarDays, badge: 'Phase 13', phase: 13 },
  { id: 'reports', label: 'Reports & Export', icon: FileBarChart, badge: 'Phase 14', phase: 14 },
  { id: 'certificates', label: 'Certificates & IDs', icon: BadgeCheck, badge: 'Phase 15', phase: 15 },
  { id: 'settings', label: 'School Settings', icon: Settings, badge: 'Active', phase: 1 },
  { id: 'python_explorer', label: 'Python Source & EXE', icon: FileCode2, badge: 'Phases 1-9 Files', phase: 1, highlight: true },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentModule,
  onSelectModule,
  isCollapsed,
  onToggleCollapse,
  isDark,
}) => {
  return (
    <aside
      className={`h-[calc(100vh-36px)] flex flex-col border-r transition-all duration-300 select-none ${
        isCollapsed ? 'w-16' : 'w-64'
      } ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}
    >
      {/* Sidebar Header */}
      <div className="p-3 border-b border-inherit flex items-center justify-between">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow font-bold text-sm">
              🎓
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight text-blue-500">EduManage Pro</h2>
              <p className="text-[10px] text-slate-400">Desktop School Suite</p>
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className={`p-1.5 rounded-md hover:bg-slate-800 text-slate-400 ${isCollapsed ? 'mx-auto' : ''}`}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {MODULE_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = currentModule === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectModule(item.id)}
              className={`w-full flex items-center px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : isDark
                  ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              } ${item.highlight && !isActive ? 'border border-blue-500/30 text-blue-400' : ''}`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : item.highlight ? 'text-blue-400' : 'text-slate-400'}`} />
              
              {!isCollapsed && (
                <div className="ml-3 flex-1 flex items-center justify-between">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : item.highlight
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer */}
      {!isCollapsed && (
        <div className={`p-3 border-t text-[11px] border-inherit text-slate-400 ${
          isDark ? 'bg-slate-950/40' : 'bg-slate-50'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-slate-300">Phase 1 Foundation</span>
            <span className="text-emerald-400 font-mono text-[10px]">v1.0.0</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-tight">
            PySide6 + SQLite + Bcrypt + SQLAlchemy Core
          </p>
        </div>
      )}
    </aside>
  );
};
