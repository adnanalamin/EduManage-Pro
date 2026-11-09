import React, { useState, useEffect } from 'react';
import { Lock, User, Eye, EyeOff, ShieldAlert, CheckCircle, School, AlertTriangle } from 'lucide-react';
import { StorageService } from '../services/storage';
import { User as UserType } from '../types';

interface LoginModalProps {
  isOpen: boolean;
  onSuccess: (user: UserType) => void;
  isDark: boolean;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onSuccess, isDark }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('Admin@123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [isLocked, setIsLocked] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown > 0) {
      timer = setTimeout(() => {
        setCountdown((c) => c - 1);
      }, 1000);
    } else if (countdown === 0 && isLocked) {
      setIsLocked(false);
      setErrorMsg('');
      setAttempts(0);
    }
    return () => clearTimeout(timer);
  }, [countdown, isLocked]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLocked) return;

    const trimmedUser = username.trim();
    const users = StorageService.getUsers();
    const foundUser = users.find(
      (u) => u.username.toLowerCase() === trimmedUser.toLowerCase() || u.email.toLowerCase() === trimmedUser.toLowerCase()
    );

    // Default password test: 'Admin@123'
    if (foundUser && password === 'Admin@123') {
      setErrorMsg('');
      setAttempts(0);
      StorageService.addActivityLog({
        username: foundUser.username,
        action: 'LOGIN_SUCCESS',
        module: 'AUTH',
        description: `User '${foundUser.username}' logged in successfully (${foundUser.roleDisplayName})`,
        severity: 'INFO',
      });
      StorageService.setCurrentUser(foundUser);
      onSuccess(foundUser);
    } else {
      const nextAttempts = attempts + 1;
      setAttempts(nextAttempts);

      StorageService.addActivityLog({
        username: trimmedUser || 'unknown',
        action: 'LOGIN_FAILED',
        module: 'AUTH',
        description: `Failed login attempt ${nextAttempts}/5 for '${trimmedUser}'`,
        severity: 'SECURITY',
      });

      if (nextAttempts >= 5) {
        setIsLocked(true);
        setCountdown(60);
        setErrorMsg('Account locked for 60 seconds due to 5 consecutive failed attempts.');
      } else {
        const remaining = 5 - nextAttempts;
        setErrorMsg(`Invalid credentials. ${remaining} attempts remaining before temporary account lockout.`);
      }
    }
  };

  const handleQuickPreset = (presetUser: string) => {
    setUsername(presetUser);
    setPassword('Admin@123');
    setErrorMsg('');
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-md rounded-2xl shadow-2xl border p-8 select-none transition-all ${
          isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        {/* Header Branding */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/25 mb-3 text-white text-2xl font-bold">
            🎓
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-blue-500">EduManage Pro</h2>
          <p className="text-xs text-slate-400 mt-1">Complete School Management Desktop System</p>
        </div>

        {/* Security Alert / Error Notice */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">{errorMsg}</p>
              {isLocked && <p className="mt-1 font-mono">Unlocking in: {countdown}s</p>}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Username or Email
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                required
                disabled={isLocked}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin or admin@school.local"
                className={`w-full pl-9 pr-3 py-2.5 rounded-lg text-xs border outline-none transition-all ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-white focus:border-blue-500'
                    : 'bg-slate-50 border-slate-300 text-slate-900 focus:border-blue-600'
                }`}
              />
            </div>
          </div>

          {/* Password Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                disabled={isLocked}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className={`w-full pl-9 pr-10 py-2.5 rounded-lg text-xs border outline-none transition-all ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-white focus:border-blue-500'
                    : 'bg-slate-50 border-slate-300 text-slate-900 focus:border-blue-600'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Remember me & Forgot Password */}
          <div className="flex items-center justify-between text-xs">
            <label className="flex items-center space-x-2 cursor-pointer text-slate-400">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded border-slate-700 text-blue-600 focus:ring-0"
              />
              <span>Remember username</span>
            </label>
            <button
              type="button"
              onClick={() => alert("Offline Recovery: Use '--reset-admin' flag or contact Super Administrator at contact@idealmodel.edu.bd")}
              className="text-blue-400 hover:underline"
            >
              Forgot password?
            </button>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLocked}
            className={`w-full py-3 rounded-xl font-bold text-xs tracking-wide shadow-lg transition-all ${
              isLocked
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/25 active:scale-[0.98]'
            }`}
          >
            {isLocked ? `Locked (${countdown}s)` : 'Sign In to EduManage Pro'}
          </button>
        </form>

        {/* Preset demo shortcuts */}
        <div className="mt-6 pt-5 border-t border-slate-800 text-center">
          <p className="text-[11px] text-slate-400 mb-2 font-medium">Quick Credentials (Click to Fill):</p>
          <div className="flex flex-wrap gap-1.5 justify-center">
            <button
              onClick={() => handleQuickPreset('admin')}
              className="px-2.5 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-blue-400 font-mono border border-slate-700"
            >
              admin (Super Admin)
            </button>
            <button
              onClick={() => handleQuickPreset('teacher.kamal')}
              className="px-2.5 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 font-mono border border-slate-700"
            >
              teacher.kamal (Teacher)
            </button>
            <button
              onClick={() => handleQuickPreset('accountant.shafiq')}
              className="px-2.5 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-amber-400 font-mono border border-slate-700"
            >
              accountant (Finance)
            </button>
          </div>
          <p className="text-[10px] text-slate-500 mt-2">Password for all seed accounts: <b>Admin@123</b></p>
        </div>
      </div>
    </div>
  );
};
