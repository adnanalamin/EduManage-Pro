import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  Moon,
  Sun,
  Bell,
  Languages,
  UserCheck,
  LogOut,
  KeyRound,
  ShieldAlert,
  Sparkles,
  ChevronDown,
} from 'lucide-react';
import { User, UserRole, SchoolSetting } from '../types';

interface TopBarProps {
  currentUser: User | null;
  schoolSetting: SchoolSetting;
  isDark: boolean;
  onToggleTheme: () => void;
  onOpenSearch: () => void;
  onOpenNotifications: () => void;
  onOpenChangePassword: () => void;
  onOpenSetupWizard: () => void;
  onSwitchRole: (role: UserRole) => void;
  onLogout: () => void;
  onToggleLanguage: () => void;
}

const ROLES_LIST: { id: UserRole; label: string; icon: string }[] = [
  { id: 'super_admin', label: 'Super Admin (All Access)', icon: '👑' },
  { id: 'administrator', label: 'Administrator', icon: '🏛️' },
  { id: 'teacher', label: 'Teacher', icon: '👨‍🏫' },
  { id: 'accountant', label: 'Accountant', icon: '💰' },
  { id: 'receptionist', label: 'Receptionist', icon: '📋' },
  { id: 'librarian', label: 'Librarian', icon: '📚' },
  { id: 'student_guardian', label: 'Student / Guardian', icon: '🎓' },
];

export const TopBar: React.FC<TopBarProps> = ({
  currentUser,
  schoolSetting,
  isDark,
  onToggleTheme,
  onOpenSearch,
  onOpenNotifications,
  onOpenChangePassword,
  onOpenSetupWizard,
  onSwitchRole,
  onLogout,
  onToggleLanguage,
}) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const roleMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
      if (roleMenuRef.current && !roleMenuRef.current.contains(event.target as Node)) {
        setShowRoleMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className={`h-14 border-b px-4 flex items-center justify-between transition-colors select-none ${
      isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      {/* Search trigger */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onOpenSearch}
          className={`flex items-center space-x-3 px-3 py-1.5 rounded-lg border text-xs w-64 md:w-80 transition-all ${
            isDark
              ? 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
              : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300'
          }`}
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span className="flex-1 text-left truncate">Search students, staff, receipts...</span>
          <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
            Ctrl+K
          </kbd>
        </button>

        <div className="hidden lg:flex items-center space-x-2 text-xs">
          <span className="px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 font-semibold border border-blue-500/20">
            Session: 2024–2025
          </span>
          <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 font-mono text-[11px]">
            EIIN: {schoolSetting.eiinNumber}
          </span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-2">
        {/* Bangladesh Language Toggle */}
        <button
          onClick={onToggleLanguage}
          title="Toggle English / বাংলা Language Mode"
          className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 border transition-all ${
            isDark
              ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
              : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
          }`}
        >
          <Languages className="w-3.5 h-3.5 text-emerald-400" />
          <span>{schoolSetting.language === 'bn' ? 'বাংলা (BD)' : 'English'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={onToggleTheme}
          title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          className={`p-2 rounded-lg border transition-all ${
            isDark
              ? 'bg-slate-800 border-slate-700 text-amber-300 hover:bg-slate-700'
              : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
          }`}
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Notification Button */}
        <button
          onClick={onOpenNotifications}
          title="Notifications"
          className={`p-2 rounded-lg border relative transition-all ${
            isDark
              ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
              : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
          }`}
        >
          <Bell className="w-4 h-4" />
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
            3
          </span>
        </button>

        {/* Role Switcher Dropdown (Demo Helper for testing RBAC) */}
        <div className="relative" ref={roleMenuRef}>
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 border transition-all ${
              isDark
                ? 'bg-blue-900/30 border-blue-700/50 text-blue-300 hover:bg-blue-900/50'
                : 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100'
            }`}
            title="Switch User Role to test RBAC"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Role:</span>
            <span className="font-bold">{currentUser?.roleDisplayName || 'Super Admin'}</span>
            <ChevronDown className="w-3 h-3 ml-0.5 opacity-60" />
          </button>

          {showRoleMenu && (
            <div className={`absolute right-0 mt-2 w-56 rounded-xl shadow-xl border py-1.5 z-50 text-xs ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="px-3 py-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-inherit">
                Switch Test Role
              </div>
              {ROLES_LIST.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    onSwitchRole(r.id);
                    setShowRoleMenu(false);
                  }}
                  className={`w-full text-left px-3 py-2 flex items-center space-x-2 transition-colors ${
                    currentUser?.role === r.id
                      ? 'bg-blue-600 text-white font-semibold'
                      : isDark
                      ? 'hover:bg-slate-800'
                      : 'hover:bg-slate-100'
                  }`}
                >
                  <span>{r.icon}</span>
                  <span className="truncate">{r.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* User Profile Menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={`flex items-center space-x-2 p-1.5 pr-2.5 rounded-lg border transition-all ${
              isDark
                ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-slate-200'
                : 'bg-slate-100 border-slate-200 hover:bg-slate-200 text-slate-800'
            }`}
          >
            <div className="w-7 h-7 rounded-md bg-blue-600 text-white font-bold text-xs flex items-center justify-center">
              {currentUser?.fullName?.charAt(0) || 'A'}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-xs font-semibold leading-none truncate max-w-[120px]">
                {currentUser?.fullName || 'Super Administrator'}
              </p>
              <p className="text-[10px] text-slate-400 leading-tight">
                {currentUser?.roleDisplayName || 'Super Admin'}
              </p>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showUserMenu && (
            <div className={`absolute right-0 mt-2 w-64 rounded-xl shadow-2xl border py-2 z-50 text-xs ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
            }`}>
              <div className="px-4 py-2 border-b border-inherit">
                <p className="font-semibold text-sm">{currentUser?.fullName}</p>
                <p className="text-slate-400 text-[11px]">{currentUser?.email}</p>
                <div className="mt-1 flex items-center space-x-1.5">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    {currentUser?.roleDisplayName}
                  </span>
                  <span className="text-[10px] text-slate-400">Offline SQLite</span>
                </div>
              </div>

              <div className="py-1">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    onOpenChangePassword();
                  }}
                  className={`w-full text-left px-4 py-2 flex items-center space-x-2.5 ${
                    isDark ? 'hover:bg-slate-800' : 'hover:bg-slate-100'
                  }`}
                >
                  <KeyRound className="w-4 h-4 text-amber-400" />
                  <span>Change Password (Bcrypt)</span>
                </button>

                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    onOpenSetupWizard();
                  }}
                  className={`w-full text-left px-4 py-2 flex items-center space-x-2.5 ${
                    isDark ? 'hover:bg-slate-800' : 'hover:bg-slate-100'
                  }`}
                >
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Rerun First-Run Setup Wizard</span>
                </button>
              </div>

              <div className="border-t border-inherit pt-1">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    onLogout();
                  }}
                  className="w-full text-left px-4 py-2 flex items-center space-x-2.5 text-red-500 hover:bg-red-500/10 font-semibold"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out of EduManage Pro</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
