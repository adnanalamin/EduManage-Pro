import React from 'react';
import { Minus, Square, X, Database, ShieldCheck } from 'lucide-react';

interface TitleBarProps {
  schoolName: string;
  isDark: boolean;
  onClose: () => void;
}

export const TitleBar: React.FC<TitleBarProps> = ({ schoolName, isDark, onClose }) => {
  return (
    <header className={`h-9 select-none flex items-center justify-between px-3 border-b text-xs transition-colors duration-200 ${
      isDark ? 'bg-slate-900 border-slate-800 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
    }`}>
      {/* Left: App Icon & Title */}
      <div className="flex items-center space-x-2">
        <div className="w-5 h-5 rounded bg-blue-600 flex items-center justify-center text-white font-bold text-[10px] shadow-sm">
          EM
        </div>
        <span className="font-semibold text-blue-500">EduManage Pro</span>
        <span className="text-slate-400">|</span>
        <span className="truncate max-w-[280px] text-slate-400 font-medium">{schoolName}</span>
      </div>

      {/* Center: System Status */}
      <div className="hidden md:flex items-center space-x-3 text-[11px] text-slate-400">
        <span className="flex items-center space-x-1 bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">
          <Database className="w-3 h-3 text-emerald-400" />
          <span>SQLite 3.42 (WAL Mode)</span>
        </span>
        <span className="flex items-center space-x-1 bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/20">
          <ShieldCheck className="w-3 h-3 text-blue-400" />
          <span>Bcrypt Auth & RBAC Active</span>
        </span>
      </div>

      {/* Right: Window Controls */}
      <div className="flex items-center space-x-1">
        <button 
          title="Minimize to Taskbar"
          className={`p-1.5 rounded hover:bg-slate-700/40 text-slate-400 transition-colors`}
          onClick={() => alert('Application minimized to Windows taskbar tray.')}
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button 
          title="Toggle Maximize"
          className={`p-1.5 rounded hover:bg-slate-700/40 text-slate-400 transition-colors`}
          onClick={() => alert('Windows Desktop Fullscreen / Windowed toggle.')}
        >
          <Square className="w-3.5 h-3.5" />
        </button>
        <button 
          title="Exit Application"
          className="p-1.5 rounded hover:bg-red-600 hover:text-white text-slate-400 transition-colors"
          onClick={onClose}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
