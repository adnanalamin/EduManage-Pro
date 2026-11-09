import React, { useState } from 'react';
import { School, ShieldCheck, Calendar, BookOpen, CheckCircle2, ChevronRight, ChevronLeft } from 'lucide-react';
import { SchoolSetting } from '../types';
import { StorageService } from '../services/storage';

interface SetupWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (settings: SchoolSetting) => void;
  isDark: boolean;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ isOpen, onClose, onComplete, isDark }) => {
  const [step, setStep] = useState(1);
  const currentSettings = StorageService.getSchoolSettings();

  const [formData, setFormData] = useState<SchoolSetting>({ ...currentSettings });
  const [adminName, setAdminName] = useState('Super Administrator');
  const [adminEmail, setAdminEmail] = useState('admin@school.local');
  const [adminPass, setAdminPass] = useState('');
  const [adminPassConfirm, setAdminPassConfirm] = useState('');
  const [sessionName, setSessionName] = useState('2024–2025');

  if (!isOpen) return null;

  const handleNext = () => {
    if (step === 2) {
      if (adminPass || adminPassConfirm) {
        if (adminPass !== adminPassConfirm) {
          alert('Passwords do not match!');
          return;
        }
        if (adminPass.length < 8) {
          alert('Password must be at least 8 characters long.');
          return;
        }
      }
    }
    setStep((s) => Math.min(s + 1, 5));
  };

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 1));
  };

  const handleFinish = () => {
    const updated: SchoolSetting = {
      ...formData,
      isSetupCompleted: true,
    };
    StorageService.saveSchoolSettings(updated);
    StorageService.addActivityLog({
      username: 'admin',
      action: 'SETUP_WIZARD_COMPLETED',
      module: 'SETTINGS',
      description: 'First-Run Setup Wizard completed with updated school parameters and curriculum',
      severity: 'INFO',
    });
    onComplete(updated);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-2xl rounded-2xl shadow-2xl border p-6 select-none transition-all flex flex-col max-h-[90vh] ${
          isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        {/* Wizard Header */}
        <div className="border-b border-inherit pb-4 mb-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600 flex items-center justify-center text-white font-bold text-lg">
              ✨
            </div>
            <div>
              <h2 className="text-base font-bold text-purple-400">First-Run Setup Wizard</h2>
              <p className="text-xs text-slate-400">Configure your institution offline database parameters</p>
            </div>
          </div>
          <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-400">
            <span>Step {step} of 5</span>
          </div>
        </div>

        {/* Progress Tracker */}
        <div className="grid grid-cols-5 gap-2 mb-6">
          {['School Info', 'Admin Account', 'Session', 'Classes', 'Finish'].map((name, idx) => (
            <div key={name} className="text-center">
              <div
                className={`h-1.5 rounded-full mb-1 transition-all ${
                  idx + 1 <= step ? 'bg-purple-500' : isDark ? 'bg-slate-800' : 'bg-slate-200'
                }`}
              />
              <span className={`text-[10px] ${idx + 1 === step ? 'font-bold text-purple-400' : 'text-slate-500'}`}>
                {name}
              </span>
            </div>
          ))}
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto px-1 space-y-4 text-xs">
          {step === 1 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-200">1. Institution Identity & Regional Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">School Name (English)*</label>
                  <input
                    type="text"
                    value={formData.schoolName}
                    onChange={(e) => setFormData({ ...formData, schoolName: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">School Name (বাংলা)</label>
                  <input
                    type="text"
                    value={formData.schoolNameBn}
                    onChange={(e) => setFormData({ ...formData, schoolNameBn: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">EIIN / Registration No</label>
                  <input
                    type="text"
                    value={formData.eiinNumber}
                    onChange={(e) => setFormData({ ...formData, eiinNumber: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Primary Currency</label>
                  <select
                    value={formData.currencyCode}
                    onChange={(e) => {
                      const code = e.target.value as 'BDT' | 'USD';
                      setFormData({
                        ...formData,
                        currencyCode: code,
                        currencySymbol: code === 'BDT' ? '৳' : '$',
                      });
                    }}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  >
                    <option value="BDT">BDT (৳ - Bangladeshi Taka)</option>
                    <option value="USD">USD ($ - US Dollar)</option>
                  </select>
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Official Phone</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Official Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block font-medium text-slate-300 mb-1">Campus Address</label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-200">2. Super Administrator Credentials</h3>
              <p className="text-slate-400">Configure your primary administrator account for secure local access.</p>
              <div className="space-y-3 max-w-md">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Admin Full Name*</label>
                  <input
                    type="text"
                    value={adminName}
                    onChange={(e) => setAdminName(e.target.value)}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Admin Email Address*</label>
                  <input
                    type="email"
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Change Default Password</label>
                  <input
                    type="password"
                    placeholder="Leave blank to keep default 'Admin@123'"
                    value={adminPass}
                    onChange={(e) => setAdminPass(e.target.value)}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                {adminPass && (
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Confirm New Password</label>
                    <input
                      type="password"
                      placeholder="Retype password"
                      value={adminPassConfirm}
                      onChange={(e) => setAdminPassConfirm(e.target.value)}
                      className={`w-full p-2 rounded-lg border outline-none ${
                        isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                      }`}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-200">3. Active Academic Calendar & Session</h3>
              <div className="max-w-md space-y-3">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Academic Session Name</label>
                  <input
                    type="text"
                    value={sessionName}
                    onChange={(e) => setSessionName(e.target.value)}
                    className={`w-full p-2 rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                    }`}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Start Date</label>
                    <input
                      type="date"
                      defaultValue="2024-01-01"
                      className={`w-full p-2 rounded-lg border outline-none ${
                        isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                      }`}
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-300 mb-1">End Date</label>
                    <input
                      type="date"
                      defaultValue="2024-12-31"
                      className={`w-full p-2 rounded-lg border outline-none ${
                        isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
                      }`}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-200">4. Starter Grade Curriculum</h3>
              <p className="text-slate-400">The following standard grades and sections will be enabled:</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {[
                  'Class 6 (Sec A, B, Padma)',
                  'Class 7 (Sec A, B, Meghna)',
                  'Class 8 (Sec A, B, Jamuna)',
                  'Class 9 (Science, Arts, Business)',
                  'Class 10 (Science, Arts, Business)',
                  'College Class 11 (HSC)',
                ].map((grade) => (
                  <div key={grade} className="p-2.5 rounded-lg border border-slate-700 bg-slate-800 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="font-medium text-slate-200">{grade}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4 text-center py-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto text-3xl">
                ✓
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">Ready to Initialize EduManage Pro</h3>
                <p className="text-slate-400 max-w-md mx-auto mt-1">
                  All institution settings, role security policies, and local SQLite tables are configured and ready.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 text-left max-w-md mx-auto space-y-1 font-mono text-[11px] text-slate-300">
                <p>• Institution: {formData.schoolName}</p>
                <p>• EIIN: {formData.eiinNumber} | Currency: {formData.currencySymbol} ({formData.currencyCode})</p>
                <p>• Session: {sessionName}</p>
                <p>• Offline Database: sqlite:///data/edumanage.db (WAL Enabled)</p>
              </div>
            </div>
          )}
        </div>

        {/* Wizard Footer Controls */}
        <div className="border-t border-inherit pt-4 mt-4 flex items-center justify-between">
          <button
            type="button"
            disabled={step === 1}
            onClick={handleBack}
            className={`px-4 py-2 rounded-lg border font-semibold flex items-center space-x-1 ${
              step === 1
                ? 'opacity-40 cursor-not-allowed border-transparent'
                : isDark
                ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                : 'border-slate-300 hover:bg-slate-100 text-slate-700'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Back</span>
          </button>

          <div className="flex space-x-2">
            <button
              type="button"
              onClick={onClose}
              className={`px-4 py-2 rounded-lg font-semibold ${
                isDark ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-600'
              }`}
            >
              Skip / Cancel
            </button>

            {step < 5 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2 rounded-lg font-semibold bg-purple-600 hover:bg-purple-500 text-white flex items-center space-x-1 shadow-lg shadow-purple-600/20"
              >
                <span>Continue</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                className="px-6 py-2 rounded-lg font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center space-x-1 shadow-lg shadow-emerald-600/20"
              >
                <span>Save & Finish Setup</span>
                <CheckCircle2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
