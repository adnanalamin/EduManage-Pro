import React from 'react';
import { Bell, AlertTriangle, Calendar, CreditCard, X, CheckCheck } from 'lucide-react';

interface NotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
}

const NOTIFICATIONS = [
  {
    id: 1,
    title: 'Outstanding Fee Alert',
    message: '42 students in Class 9 (Science) have tuition fees due for this month.',
    time: '25 mins ago',
    type: 'fee',
    icon: CreditCard,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  },
  {
    id: 2,
    title: 'Upcoming Half-Yearly Exam Schedule',
    message: 'Final exam routine has been approved and published to the student notice board.',
    time: '1 hour ago',
    type: 'exam',
    icon: Calendar,
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  },
  {
    id: 3,
    title: 'Automated Database Safety Backup',
    message: 'Daily SQLite WAL checkpoint and backup to backups/edumanage_daily.db verified successfully.',
    time: '3 hours ago',
    type: 'system',
    icon: CheckCheck,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  },
];

export const NotificationsModal: React.FC<NotificationsModalProps> = ({ isOpen, onClose, isDark }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div
        className={`w-full max-w-md rounded-2xl shadow-2xl border p-5 select-none transition-all ${
          isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        <div className="flex items-center justify-between pb-3 border-b border-inherit">
          <div className="flex items-center space-x-2">
            <Bell className="w-5 h-5 text-blue-400" />
            <h3 className="font-bold text-sm">System Notifications</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="py-3 space-y-2.5 max-h-96 overflow-y-auto">
          {NOTIFICATIONS.map((n) => {
            const Icon = n.icon;
            return (
              <div key={n.id} className={`p-3 rounded-xl border ${n.color} flex space-x-3`}>
                <Icon className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-xs text-slate-200">{n.title}</h4>
                    <span className="text-[10px] text-slate-400">{n.time}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{n.message}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-2 border-t border-inherit text-center">
          <button
            onClick={onClose}
            className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
          >
            Mark All as Read
          </button>
        </div>
      </div>
    </div>
  );
};
