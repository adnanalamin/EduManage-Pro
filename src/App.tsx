import React, { useState, useEffect } from 'react';
import { TitleBar } from './components/TitleBar';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { Dashboard } from './pages/Dashboard';
import { StudentManagement } from './pages/StudentManagement';
import { TeacherManagement } from './pages/TeacherManagement';
import { StaffManagement } from './pages/StaffManagement';
import { AcademicManagement } from './pages/AcademicManagement';
import { AttendanceManagement } from './pages/AttendanceManagement';
import { FeesManagement } from './pages/FeesManagement';
import { AccountingManagement } from './pages/AccountingManagement';
import { ExamManagement } from './pages/ExamManagement';
import { TimetableManagement } from './pages/TimetableManagement';
import { ModulePlaceholder } from './pages/ModulePlaceholder';
import { PythonProjectExplorer } from './components/PythonProjectExplorer';
import { LoginModal } from './components/LoginModal';
import { SetupWizard } from './components/SetupWizard';
import { GlobalSearchModal } from './components/GlobalSearchModal';
import { NotificationsModal } from './components/NotificationsModal';
import { ChangePasswordModal } from './components/ChangePasswordModal';
import { StorageService } from './services/storage';
import { User, SchoolSetting, ActivityLogItem, UserRole } from './types';

export default function App() {
  const [isDark, setIsDark] = useState<boolean>(() => StorageService.getTheme() === 'dark');
  const [currentUser, setCurrentUser] = useState<User | null>(() => StorageService.getCurrentUser());
  const [schoolSetting, setSchoolSetting] = useState<SchoolSetting>(() => StorageService.getSchoolSettings());
  const [activityLogs, setActivityLogs] = useState<ActivityLogItem[]>(() => StorageService.getActivityLogs());
  const [currentModule, setCurrentModule] = useState<string>('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);

  // Modals
  const [showLoginModal, setShowLoginModal] = useState<boolean>(() => !StorageService.getCurrentUser());
  const [showSetupWizard, setShowSetupWizard] = useState<boolean>(false);
  const [showSearchModal, setShowSearchModal] = useState<boolean>(false);
  const [showNotificationsModal, setShowNotificationsModal] = useState<boolean>(false);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState<boolean>(false);

  // Sync theme changes
  useEffect(() => {
    StorageService.setTheme(isDark ? 'dark' : 'light');
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  // Global Ctrl+K shortcut for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setShowSearchModal(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleToggleTheme = () => {
    setIsDark((prev) => !prev);
  };

  const handleToggleLanguage = () => {
    const nextLang = schoolSetting.language === 'en' ? 'bn' : 'en';
    const updated = { ...schoolSetting, language: nextLang as 'en' | 'bn' };
    setSchoolSetting(updated);
    StorageService.saveSchoolSettings(updated);
    StorageService.addActivityLog({
      username: currentUser?.username || 'admin',
      action: 'LOCALE_CHANGED',
      module: 'SETTINGS',
      description: `Language switched to ${nextLang === 'bn' ? 'Bangla (বাংলা)' : 'English'}`,
      severity: 'INFO',
    });
    setActivityLogs(StorageService.getActivityLogs());
  };

  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    setShowLoginModal(false);
    setActivityLogs(StorageService.getActivityLogs());
  };

  const handleLogout = () => {
    if (currentUser) {
      StorageService.addActivityLog({
        username: currentUser.username,
        action: 'LOGOUT',
        module: 'AUTH',
        description: `User '${currentUser.username}' logged out of desktop session`,
        severity: 'INFO',
      });
    }
    StorageService.setCurrentUser(null);
    setCurrentUser(null);
    setShowLoginModal(true);
    setActivityLogs(StorageService.getActivityLogs());
  };

  const handleSwitchRole = (role: UserRole) => {
    const users = StorageService.getUsers();
    let target = users.find((u) => u.role === role);
    if (!target && currentUser) {
      target = {
        ...currentUser,
        role,
        roleDisplayName: role.replace('_', ' ').toUpperCase(),
      };
    }
    if (target) {
      setCurrentUser(target);
      StorageService.setCurrentUser(target);
      StorageService.addActivityLog({
        username: target.username,
        action: 'ROLE_SWITCH',
        module: 'AUTH',
        description: `Active desktop session switched to role: ${target.roleDisplayName}`,
        severity: 'INFO',
      });
      setActivityLogs(StorageService.getActivityLogs());
    }
  };

  const handleQuickAction = (action: string) => {
    if (action === 'admit_student') {
      setCurrentModule('students');
      StorageService.addActivityLog({
        username: currentUser?.username || 'admin',
        action: 'NAVIGATE_ADMISSION',
        module: 'STUDENTS',
        description: 'Initiated student admission form workflow',
        severity: 'INFO',
      });
      setActivityLogs(StorageService.getActivityLogs());
    } else if (action === 'collect_fee') {
      setCurrentModule('fees');
      StorageService.addActivityLog({
        username: currentUser?.username || 'admin',
        action: 'NAVIGATE_FEES',
        module: 'FEES',
        description: 'Initiated student fee collection workflow',
        severity: 'INFO',
      });
      setActivityLogs(StorageService.getActivityLogs());
    }
  };

  return (
    <div
      className={`min-h-screen flex flex-col font-sans transition-colors duration-200 overflow-hidden ${
        isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-100 text-slate-900'
      }`}
    >
      {/* 1. Desktop Window Title Bar (Windows 11 Frame) */}
      <TitleBar
        schoolName={schoolSetting.schoolName}
        isDark={isDark}
        onClose={() => {
          if (confirm('Exit EduManage Pro Desktop application?')) {
            alert('Desktop application session ended.');
          }
        }}
      />

      {/* 2. Main Workspace Layout: Sidebar + (TopBar + Content) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          currentModule={currentModule}
          onSelectModule={(mod) => setCurrentModule(mod)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
          isDark={isDark}
          schoolName={schoolSetting.schoolName}
        />

        {/* Right Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar */}
          <TopBar
            currentUser={currentUser}
            schoolSetting={schoolSetting}
            isDark={isDark}
            onToggleTheme={handleToggleTheme}
            onOpenSearch={() => setShowSearchModal(true)}
            onOpenNotifications={() => setShowNotificationsModal(true)}
            onOpenChangePassword={() => setShowChangePasswordModal(true)}
            onOpenSetupWizard={() => setShowSetupWizard(true)}
            onSwitchRole={handleSwitchRole}
            onLogout={handleLogout}
            onToggleLanguage={handleToggleLanguage}
          />

            {/* Dynamic Content Views */}
          <main className="flex-1 overflow-y-auto">
            {currentModule === 'dashboard' ? (
              <Dashboard
                schoolSetting={schoolSetting}
                activityLogs={activityLogs}
                currentUser={currentUser}
                isDark={isDark}
                onNavigateModule={(mod) => setCurrentModule(mod)}
                onOpenQuickAction={handleQuickAction}
              />
            ) : currentModule === 'students' ? (
              <StudentManagement
                isDark={isDark}
                schoolSetting={schoolSetting}
                currentUser={currentUser}
              />
            ) : currentModule === 'teachers' ? (
              <TeacherManagement
                isDark={isDark}
                schoolSetting={schoolSetting}
                currentUser={currentUser}
              />
            ) : currentModule === 'staff' ? (
              <StaffManagement
                isDark={isDark}
                schoolSetting={schoolSetting}
                currentUser={currentUser}
              />
            ) : currentModule === 'academics' ? (
              <AcademicManagement
                isDark={isDark}
                schoolSetting={schoolSetting}
                currentUser={currentUser}
              />
            ) : currentModule === 'attendance' ? (
              <AttendanceManagement
                isDark={isDark}
                schoolSetting={schoolSetting}
                currentUser={currentUser}
              />
            ) : currentModule === 'fees' ? (
              <div className="p-6">
                <FeesManagement currentUserRole={currentUser?.role} />
              </div>
            ) : currentModule === 'accounting' ? (
              <div className="p-6">
                <AccountingManagement currentUserRole={currentUser?.role} />
              </div>
            ) : currentModule === 'exams' || currentModule === 'results' ? (
              <div className="p-6">
                <ExamManagement
                  isDark={isDark}
                  schoolSetting={schoolSetting}
                  currentUser={currentUser}
                />
              </div>
            ) : currentModule === 'timetable' ? (
              <div className="p-6">
                <TimetableManagement
                  isDark={isDark}
                  schoolSetting={schoolSetting}
                  currentUser={currentUser}
                />
              </div>
            ) : currentModule === 'python_explorer' ? (
              <PythonProjectExplorer isDark={isDark} />
            ) : (
              <ModulePlaceholder
                moduleId={currentModule}
                isDark={isDark}
                onAdmitStudent={() => handleQuickAction('admit_student')}
              />
            )}
          </main>
        </div>
      </div>

      {/* Modals & Dialogs */}
      <LoginModal
        isOpen={showLoginModal}
        onSuccess={handleLoginSuccess}
        isDark={isDark}
      />

      <SetupWizard
        isOpen={showSetupWizard}
        onClose={() => setShowSetupWizard(false)}
        onComplete={(settings) => {
          setSchoolSetting(settings);
          setActivityLogs(StorageService.getActivityLogs());
        }}
        isDark={isDark}
      />

      <GlobalSearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
        isDark={isDark}
        onSelectResult={(cat) => setCurrentModule(cat)}
      />

      <NotificationsModal
        isOpen={showNotificationsModal}
        onClose={() => setShowNotificationsModal(false)}
        isDark={isDark}
      />

      <ChangePasswordModal
        isOpen={showChangePasswordModal}
        onClose={() => setShowChangePasswordModal(false)}
        currentUser={currentUser}
        isDark={isDark}
      />
    </div>
  );
}
