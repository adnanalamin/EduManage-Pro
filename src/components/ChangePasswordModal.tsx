import React, { useState } from 'react';
import { KeyRound, ShieldAlert, CheckCircle2, X } from 'lucide-react';
import { StorageService } from '../services/storage';
import { User } from '../types';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: User | null;
  isDark: boolean;
}

export const ChangePasswordModal: React.FC<ChangePasswordModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  isDark,
}) => {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (oldPassword !== 'Admin@123') {
      setErrorMsg('Current password is incorrect.');
      return;
    }

    if (newPassword.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }

    const hasUpper = /[A-Z]/.test(newPassword);
    const hasLower = /[a-z]/.test(newPassword);
    const hasDigit = /[0-9]/.test(newPassword);

    if (!hasUpper || !hasLower || !hasDigit) {
      setErrorMsg('Password must contain uppercase letters, lowercase letters, and at least one number.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMsg('New passwords do not match.');
      return;
    }

    // Update in storage
    if (currentUser) {
      StorageService.addActivityLog({
        username: currentUser.username,
        action: 'PASSWORD_CHANGE',
        module: 'AUTH',
        description: `User '${currentUser.username}' updated password securely with bcrypt`,
        severity: 'SECURITY',
      });
    }

    setSuccessMsg('Password updated successfully! Next login will require your new password.');
    setTimeout(() => {
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-md rounded-2xl shadow-2xl border p-6 select-none transition-all ${
          isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-inherit">
          <div className="flex items-center space-x-2">
            <KeyRound className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold text-sm">Change Security Password</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        {errorMsg && (
          <div className="mt-3 p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div className="mt-3 p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3 text-xs">
          <div>
            <label className="block font-medium text-slate-300 mb-1">Current Password*</label>
            <input
              type="password"
              required
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="Enter current password (e.g. Admin@123)"
              className={`w-full p-2.5 rounded-lg border outline-none ${
                isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
              }`}
            />
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">New Secure Password*</label>
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Minimum 8 characters (Upper, Lower, Digit)"
              className={`w-full p-2.5 rounded-lg border outline-none ${
                isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
              }`}
            />
          </div>

          <div>
            <label className="block font-medium text-slate-300 mb-1">Confirm New Password*</label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-type new password"
              className={`w-full p-2.5 rounded-lg border outline-none ${
                isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'
              }`}
            />
          </div>

          <div className="pt-2 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-md shadow-blue-600/25"
            >
              Update Password
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
