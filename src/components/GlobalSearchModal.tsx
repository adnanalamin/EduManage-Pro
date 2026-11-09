import React, { useState, useEffect } from 'react';
import { Search, GraduationCap, Users, CreditCard, Bell, ArrowRight, X } from 'lucide-react';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  isDark: boolean;
  onSelectResult: (category: string) => void;
}

interface SearchItem {
  id: string;
  title: string;
  category: 'students' | 'teachers' | 'fees' | 'notices' | 'academics';
  subtitle: string;
  tag: string;
}

const SAMPLE_DATABASE_RECORDS: SearchItem[] = [
  { id: '1', title: 'Adnan Sami (Roll 101, Class 10)', category: 'students', subtitle: 'Science Group • Section A • ID: STU-2024-001', tag: 'Student' },
  { id: '2', title: 'Sadia Jahan (Roll 102, Class 10)', category: 'students', subtitle: 'Science Group • Section A • ID: STU-2024-002', tag: 'Student' },
  { id: '3', title: 'Kamal Hossain (Senior Science Teacher)', category: 'teachers', subtitle: 'Physics Department • ID: TCH-042', tag: 'Faculty' },
  { id: '4', title: 'Nazmul Islam (Math Department Head)', category: 'teachers', subtitle: 'Mathematics • ID: TCH-015', tag: 'Faculty' },
  { id: '5', title: 'Receipt #REC-2024-0899 (৳ 4,500)', category: 'fees', subtitle: 'Monthly Tuition & Lab Fee • Paid via Bkash', tag: 'Fee' },
  { id: '6', title: 'Receipt #REC-2024-0904 (৳ 3,200)', category: 'fees', subtitle: 'Library & Exam Fee • Paid Cash', tag: 'Fee' },
  { id: '7', title: 'Notice: First Term Examination Schedule', category: 'notices', subtitle: 'Published by Exam Controller • All Classes', tag: 'Notice' },
  { id: '8', title: 'Class 9 - Section Padma (Science)', category: 'academics', subtitle: 'Room 304 • Class Teacher: Kamal Hossain', tag: 'Class' },
];

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({ isOpen, onClose, isDark, onSelectResult }) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;

  const filtered = query.trim() === ''
    ? SAMPLE_DATABASE_RECORDS.slice(0, 5)
    : SAMPLE_DATABASE_RECORDS.filter(
        (item) =>
          item.title.toLowerCase().includes(query.toLowerCase()) ||
          item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
          item.tag.toLowerCase().includes(query.toLowerCase())
      );

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-start justify-center pt-20 p-4">
      <div
        className={`w-full max-w-xl rounded-2xl shadow-2xl border select-none transition-all overflow-hidden ${
          isDark ? 'bg-slate-900 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-800'
        }`}
      >
        {/* Search Input Bar */}
        <div className="p-3 border-b border-inherit flex items-center space-x-3">
          <Search className="w-5 h-5 text-blue-400 shrink-0" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search students, teachers, receipts, notices (e.g. Adnan, Receipt, Class 10)..."
            className="flex-1 bg-transparent border-none outline-none text-sm placeholder-slate-400"
          />
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-400">
              No matching records found in offline SQLite database for "{query}".
            </div>
          ) : (
            filtered.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  onSelectResult(item.category);
                  onClose();
                }}
                className={`w-full text-left p-2.5 rounded-xl flex items-center justify-between text-xs transition-all ${
                  isDark ? 'hover:bg-slate-800' : 'hover:bg-slate-100'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold text-xs shrink-0">
                    {item.tag.charAt(0)}
                  </div>
                  <div>
                    <p className="font-semibold">{item.title}</p>
                    <p className="text-[11px] text-slate-400">{item.subtitle}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 font-mono text-slate-300">
                    {item.tag}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </button>
            ))
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="p-2.5 bg-slate-950/40 border-t border-inherit text-[11px] text-slate-400 flex items-center justify-between px-4">
          <span>Search SQLite Database (Instant Indexed Queries)</span>
          <div className="flex items-center space-x-2">
            <span>Esc to exit</span>
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-[9px]">ESC</kbd>
          </div>
        </div>
      </div>
    </div>
  );
};
