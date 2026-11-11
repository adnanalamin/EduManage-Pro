import React, { useState, useEffect } from 'react';
import {
  Bell,
  CalendarDays,
  FileText,
  AlertTriangle,
  Pin,
  Plus,
  Search,
  Filter,
  CheckCircle,
  Download,
  Printer,
  Calendar,
  Clock,
  MapPin,
  Users,
  ShieldAlert,
  Building,
  RefreshCw,
} from 'lucide-react';
import { StorageService } from '../services/storage';
import {
  SchoolNoticeInfo,
  SchoolEventInfo,
  NoticeStatsInfo,
} from '../types';

export const NoticeManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'notices' | 'events' | 'letterhead'>('notices');

  // Datasets
  const [notices, setNotices] = useState<SchoolNoticeInfo[]>([]);
  const [events, setEvents] = useState<SchoolEventInfo[]>([]);
  const [stats, setStats] = useState<NoticeStatsInfo>({
    totalNotices: 0,
    publishedNotices: 0,
    urgentAlerts: 0,
    upcomingEvents: 0,
    totalHolidays: 0,
  });

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAudienceFilter, setSelectedAudienceFilter] = useState('All');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('All');
  const [selectedEventCategory, setSelectedEventCategory] = useState('All');

  // Modals
  const [showNoticeModal, setShowNoticeModal] = useState(false);
  const [showEventModal, setShowEventModal] = useState(false);

  // Selected Notice for Letterhead
  const [selectedNoticeForPrint, setSelectedNoticeForPrint] = useState<SchoolNoticeInfo | null>(null);

  // Forms
  const [noticeForm, setNoticeForm] = useState({
    title: '',
    category: 'Academic' as SchoolNoticeInfo['category'],
    targetAudience: 'All' as SchoolNoticeInfo['targetAudience'],
    priority: 'Normal' as SchoolNoticeInfo['priority'],
    isPinned: false,
    publishDate: new Date().toISOString().split('T')[0],
    expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    content: '',
    attachmentName: '',
    createdBy: 'Principal Office',
  });

  const [eventForm, setEventForm] = useState({
    eventTitle: '',
    eventCategory: 'Academic' as SchoolEventInfo['eventCategory'],
    startDate: new Date().toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    startTime: '09:00 AM',
    endTime: '01:00 PM',
    venue: 'Campus Main Auditorium',
    targetAudience: 'All',
    isHoliday: false,
    description: '',
    organizer: 'School Administration',
  });

  // Alerts
  const [alertMessage, setAlertMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showAlert = (type: 'success' | 'error', text: string) => {
    setAlertMessage({ type, text });
    setTimeout(() => setAlertMessage(null), 4000);
  };

  const loadData = () => {
    const n = StorageService.getNotices();
    const e = StorageService.getEvents();
    const s = StorageService.getNoticeStats();
    setNotices(n);
    setEvents(e);
    setStats(s);

    if (n.length > 0 && !selectedNoticeForPrint) {
      setSelectedNoticeForPrint(n[0]);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Save Notice
  const handleSaveNotice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!noticeForm.title.trim() || !noticeForm.content.trim()) {
      showAlert('error', 'Title and Content are required.');
      return;
    }

    StorageService.saveNotice(noticeForm);
    showAlert('success', `Notice '${noticeForm.title}' published successfully!`);
    setShowNoticeModal(false);
    setNoticeForm({
      title: '',
      category: 'Academic',
      targetAudience: 'All',
      priority: 'Normal',
      isPinned: false,
      publishDate: new Date().toISOString().split('T')[0],
      expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      content: '',
      attachmentName: '',
      createdBy: 'Principal Office',
    });
    loadData();
  };

  // Delete Notice
  const handleDeleteNotice = (id: number) => {
    if (confirm('Are you sure you want to delete this circular notice?')) {
      StorageService.deleteNotice(id);
      showAlert('success', 'Notice deleted successfully.');
      loadData();
    }
  };

  // Save Event
  const handleSaveEvent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventForm.eventTitle.trim()) {
      showAlert('error', 'Event Title is required.');
      return;
    }

    StorageService.saveEvent(eventForm);
    showAlert('success', `Event '${eventForm.eventTitle}' added to academic calendar!`);
    setShowEventModal(false);
    setEventForm({
      eventTitle: '',
      eventCategory: 'Academic',
      startDate: new Date().toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
      startTime: '09:00 AM',
      endTime: '01:00 PM',
      venue: 'Campus Main Auditorium',
      targetAudience: 'All',
      isHoliday: false,
      description: '',
      organizer: 'School Administration',
    });
    loadData();
  };

  // Delete Event
  const handleDeleteEvent = (id: number) => {
    if (confirm('Are you sure you want to remove this academic event?')) {
      StorageService.deleteEvent(id);
      showAlert('success', 'Event removed.');
      loadData();
    }
  };

  // Filtered Notices
  const filteredNotices = notices.filter((n) => {
    const matchesSearch =
      n.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.referenceNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.content.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesAudience = selectedAudienceFilter === 'All' || n.targetAudience === selectedAudienceFilter || n.targetAudience === 'All';
    const matchesCategory = selectedCategoryFilter === 'All' || n.category === selectedCategoryFilter;
    return matchesSearch && matchesAudience && matchesCategory;
  });

  // Filtered Events
  const filteredEvents = events.filter((e) => {
    const matchesSearch =
      e.eventTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.venue.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = selectedEventCategory === 'All' || e.eventCategory === selectedEventCategory;
    return matchesSearch && matchesCat;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-600/10 text-blue-600 dark:text-blue-400 rounded-xl">
            <Bell className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">Notice Board & Academic Calendar</h1>
              <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 rounded-full border border-blue-200 dark:border-blue-800">
                Phase 13 Live
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Official circular memos, urgent bulletins, academic events timeline & holiday planners
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => {
              StorageService.getNotices();
              loadData();
              showAlert('success', 'Defaults reloaded successfully.');
            }}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Defaults</span>
          </button>
          <button
            onClick={() => setShowNoticeModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Publish Circular</span>
          </button>
          <button
            onClick={() => setShowEventModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-sm"
          >
            <CalendarDays className="w-3.5 h-3.5" />
            <span>Schedule Event</span>
          </button>
        </div>
      </div>

      {/* Alert Notice */}
      {alertMessage && (
        <div
          className={`p-3.5 rounded-xl text-xs font-semibold flex items-center justify-between border ${
            alertMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
              : 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {alertMessage.type === 'success' ? (
              <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
            )}
            <span>{alertMessage.text}</span>
          </div>
          <button onClick={() => setAlertMessage(null)} className="text-slate-400 hover:text-slate-600">
            &times;
          </button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-blue-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Notices</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{stats.totalNotices}</h3>
            <span className="text-[11px] font-medium text-blue-600">Circulars</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Official memos on record</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-emerald-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Bulletins</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{stats.publishedNotices}</h3>
            <span className="text-[11px] font-medium text-emerald-600">Published</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Visible to campus patrons</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-rose-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Urgent Alerts</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-rose-600 dark:text-rose-400">{stats.urgentAlerts}</h3>
            <span className="text-[11px] font-bold text-rose-600">Pinned Top</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Critical high-priority notices</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-teal-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Upcoming Events</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-teal-600 dark:text-teal-400">{stats.upcomingEvents}</h3>
            <span className="text-[11px] font-medium text-teal-600">Active</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Scheduled on calendar</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-amber-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">School Holidays</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-amber-600 dark:text-amber-400">{stats.totalHolidays}</h3>
            <span className="text-[11px] font-medium text-amber-600">Official</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Attendance auto-recess</p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('notices')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'notices'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Notice Board & Circulars</span>
          <span className="px-1.5 py-0.2 bg-white/20 text-white rounded-full text-[10px]">{notices.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('events')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'events'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CalendarDays className="w-4 h-4" />
          <span>Academic Calendar & Holidays</span>
          <span className="px-1.5 py-0.2 bg-white/20 text-white rounded-full text-[10px]">{events.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('letterhead')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'letterhead'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Official Circular Letterhead (PDF)</span>
        </button>
      </div>

      {/* TAB 1: NOTICES & CIRCULARS */}
      {activeTab === 'notices' && (
        <div className="space-y-4">
          {/* Pinned Urgent Bulletins */}
          {notices.some((n) => n.isPinned) && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-rose-600 uppercase tracking-wider">
                <Pin className="w-3.5 h-3.5" />
                <span>Pinned Urgent Circulars</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {notices
                  .filter((n) => n.isPinned)
                  .map((n) => (
                    <div
                      key={n.id}
                      className="p-4 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 shadow-sm space-y-2"
                    >
                      <div className="flex items-start justify-between">
                        <span className="text-[10px] font-mono font-bold bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300 px-2 py-0.5 rounded">
                          {n.referenceNo}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-rose-600 text-white rounded-full">
                          URGENT ALERT
                        </span>
                      </div>
                      <h4 className="font-bold text-sm text-slate-900 dark:text-white leading-tight">{n.title}</h4>
                      <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2">{n.content}</p>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-rose-100 dark:border-rose-900/40">
                        <span>Audience: <strong>{n.targetAudience}</strong></span>
                        <button
                          onClick={() => {
                            setSelectedNoticeForPrint(n);
                            setActiveTab('letterhead');
                          }}
                          className="font-semibold text-blue-600 hover:text-blue-700 underline"
                        >
                          View Memo
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Search & Filters Bar */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search circulars by title, reference, or content..."
                  className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white w-64 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <select
                  value={selectedAudienceFilter}
                  onChange={(e) => setSelectedAudienceFilter(e.target.value)}
                  className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                >
                  <option value="All">All Audiences</option>
                  <option value="Students">Students Only</option>
                  <option value="Teachers">Teachers Only</option>
                  <option value="Parents">Parents Only</option>
                  <option value="Staff">Staff Only</option>
                </select>

                <select
                  value={selectedCategoryFilter}
                  onChange={(e) => setSelectedCategoryFilter(e.target.value)}
                  className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                >
                  <option value="All">All Categories</option>
                  <option value="Academic">Academic</option>
                  <option value="Exam">Exam</option>
                  <option value="Holiday">Holiday</option>
                  <option value="Administrative">Administrative</option>
                  <option value="Sports">Sports</option>
                  <option value="Fee">Fee</option>
                </select>
              </div>
            </div>

            <div className="text-xs font-semibold text-slate-500">Showing {filteredNotices.length} circulars</div>
          </div>

          {/* Notices Table */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 uppercase font-semibold text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Ref No</th>
                    <th className="py-3 px-4">Circular Title & Subject</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Audience</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">Publish Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
                  {filteredNotices.map((n) => (
                    <tr key={n.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-mono font-bold text-blue-600 dark:text-blue-400">
                        {n.isPinned ? `📌 ${n.referenceNo}` : n.referenceNo}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white max-w-sm truncate">
                        {n.title}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {n.category}
                        </span>
                      </td>
                      <td className="py-3 px-4">{n.targetAudience}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            n.priority === 'Urgent'
                              ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400'
                              : n.priority === 'Important'
                              ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400'
                              : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {n.priority}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">{n.publishDate}</td>
                      <td className="py-3 px-4 text-right space-x-1">
                        <button
                          onClick={() => {
                            setSelectedNoticeForPrint(n);
                            setActiveTab('letterhead');
                          }}
                          className="px-2.5 py-1 text-[11px] font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/50 dark:hover:bg-blue-900/60 rounded transition"
                        >
                          Memo Letterhead
                        </button>
                        <button
                          onClick={() => handleDeleteNotice(n.id)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 dark:hover:bg-rose-900/60 rounded transition"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ACADEMIC CALENDAR & EVENTS */}
      {activeTab === 'events' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search events by title or venue..."
                  className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white w-64 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              <select
                value={selectedEventCategory}
                onChange={(e) => setSelectedEventCategory(e.target.value)}
                className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
              >
                <option value="All">All Event Categories</option>
                <option value="Holiday">Official Holidays</option>
                <option value="Exam">Exam Periods</option>
                <option value="Sports">Sports</option>
                <option value="Academic">Academic</option>
                <option value="PTM">PTM Conferences</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const csvRows = [
                    ['SL', 'Event Title', 'Category', 'Start Date', 'End Date', 'Venue', 'Holiday Flag', 'Organizer'].join(','),
                    ...filteredEvents.map((ev, i) =>
                      [
                        i + 1,
                        `"${ev.eventTitle}"`,
                        ev.eventCategory,
                        ev.startDate,
                        ev.endDate,
                        `"${ev.venue}"`,
                        ev.isHoliday ? 'YES' : 'NO',
                        `"${ev.organizer}"`,
                      ].join(',')
                    ),
                  ].join('\n');
                  const blob = new Blob([csvRows], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `Academic_Calendar_${new Date().toISOString().split('T')[0]}.csv`;
                  link.click();
                  showAlert('success', 'Academic calendar schedule exported to CSV!');
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
              >
                <Download className="w-3.5 h-3.5 text-emerald-600" />
                <span>Export CSV</span>
              </button>

              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print Calendar</span>
              </button>

              <button
                onClick={() => setShowEventModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Event</span>
              </button>
            </div>
          </div>

          {/* Events Grid Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredEvents.map((ev) => (
              <div
                key={ev.id}
                className={`p-4 rounded-xl border bg-white dark:bg-slate-900 shadow-sm transition space-y-3 ${
                  ev.isHoliday
                    ? 'border-l-4 border-l-rose-500 border-rose-200 dark:border-rose-900/60'
                    : 'border-l-4 border-l-blue-500 border-slate-200 dark:border-slate-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded uppercase"
                      style={{
                        backgroundColor: `${ev.colorCode}20`,
                        color: ev.colorCode,
                      }}
                    >
                      {ev.eventCategory}
                    </span>
                    {ev.isHoliday && (
                      <span className="ml-1.5 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-400">
                        ★ SCHOOL HOLIDAY
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteEvent(ev.id)}
                    className="text-slate-400 hover:text-rose-600 text-xs"
                    title="Delete Event"
                  >
                    &times;
                  </button>
                </div>

                <h4 className="font-bold text-sm text-slate-900 dark:text-white">{ev.eventTitle}</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                  {ev.description || 'Institutional academic activity scheduled in official school planner.'}
                </p>

                <div className="text-xs space-y-1 text-slate-600 dark:text-slate-300 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      {ev.startDate} {ev.endDate !== ev.startDate ? `to ${ev.endDate}` : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>{ev.startTime && ev.endTime ? `${ev.startTime} - ${ev.endTime}` : 'All Day'}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span className="truncate">{ev.venue}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                    <Users className="w-3.5 h-3.5" />
                    <span>Organizer: {ev.organizer}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: OFFICIAL CIRCULAR LETTERHEAD PREVIEW */}
      {activeTab === 'letterhead' && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Left: Circular Selector */}
          <div className="md:col-span-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">Published Circulars</h3>
            <p className="text-xs text-slate-400">Select circular memo to format on official letterhead</p>

            <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[500px] overflow-y-auto">
              {notices.map((n) => (
                <button
                  key={n.id}
                  onClick={() => setSelectedNoticeForPrint(n)}
                  className={`w-full text-left p-3 rounded-lg flex flex-col gap-1 transition ${
                    selectedNoticeForPrint?.id === n.id
                      ? 'bg-blue-50 dark:bg-blue-950/40 border border-blue-500'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold text-blue-600 dark:text-blue-400">{n.referenceNo}</span>
                    <span className="text-[10px] text-slate-400">{n.publishDate}</span>
                  </div>
                  <h5 className="font-semibold text-xs text-slate-900 dark:text-white truncate">{n.title}</h5>
                  <span className="text-[10px] text-slate-500">Audience: {n.targetAudience}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Right: Printable Letterhead Document */}
          <div className="md:col-span-8 bg-white dark:bg-slate-900 p-8 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col space-y-6">
            <div className="flex justify-between items-center pb-4 border-b">
              <span className="text-xs font-semibold text-slate-400">
                Official Letterhead View (Portrait A4 Standard)
              </span>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-sm transition"
              >
                <Printer className="w-4 h-4" />
                <span>Print Official Letterhead</span>
              </button>
            </div>

            {selectedNoticeForPrint ? (
              <div
                id="notice-letterhead"
                className="bg-white text-slate-900 p-8 rounded-xl border border-slate-300 shadow-lg font-serif space-y-6"
              >
                {/* School Header */}
                <div className="text-center border-b-2 border-blue-900 pb-4 space-y-1">
                  <h2 className="text-2xl font-bold tracking-tight text-blue-950">
                    IDEAL MODEL HIGH SCHOOL & COLLEGE
                  </h2>
                  <p className="text-xs text-slate-600">
                    Plot 12, Sector 7, Uttara, Dhaka-1230 &bull; EIIN: 134211 &bull; Estd: 1998
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Phone: +880 1712-345678 &bull; Email: contact@idealmodel.edu.bd &bull; Web: idealmodel.edu.bd
                  </p>
                </div>

                {/* Memo Meta Box */}
                <div className="bg-slate-50 p-3 rounded border border-slate-200 text-xs font-sans grid grid-cols-2 gap-2">
                  <div>
                    <strong>Circular Memo Ref:</strong>{' '}
                    <span className="text-blue-900 font-bold">{selectedNoticeForPrint.referenceNo}</span>
                  </div>
                  <div className="text-right">
                    <strong>Date:</strong> {selectedNoticeForPrint.publishDate}
                  </div>
                  <div>
                    <strong>Target Audience:</strong> {selectedNoticeForPrint.targetAudience}
                  </div>
                  <div className="text-right">
                    <strong>Priority:</strong>{' '}
                    <span
                      className={`font-bold ${
                        selectedNoticeForPrint.priority === 'Urgent'
                          ? 'text-rose-600'
                          : selectedNoticeForPrint.priority === 'Important'
                          ? 'text-amber-600'
                          : 'text-emerald-600'
                      }`}
                    >
                      {selectedNoticeForPrint.priority.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Subject Heading */}
                <div className="text-center font-sans font-bold text-base underline text-slate-900 tracking-wide">
                  SUBJECT: {selectedNoticeForPrint.title.toUpperCase()}
                </div>

                {/* Notice Body */}
                <div className="text-sm font-sans text-slate-800 leading-relaxed whitespace-pre-wrap min-h-[160px]">
                  {selectedNoticeForPrint.content}
                </div>

                {/* Principal Signature Area */}
                <div className="pt-10 flex justify-between items-end text-xs font-sans border-t border-slate-200">
                  <div>
                    <p className="text-slate-500">Prepared by:</p>
                    <p className="font-semibold text-slate-800">Executive Office Assistant</p>
                    <p className="text-slate-500">General Administration</p>
                  </div>
                  <div className="text-right">
                    <p className="text-slate-400 font-script text-base italic mb-1">Md. Rafiqul Islam</p>
                    <div className="w-40 border-t border-slate-800 ml-auto mb-1" />
                    <p className="font-bold text-slate-900">Prof. Dr. Mohammad Rafiqul Islam</p>
                    <p className="text-slate-600">Principal & Head of Institution</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">No circular selected for preview</div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: PUBLISH NOTICE */}
      {showNoticeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Publish School Notice / Circular</h3>
              <button onClick={() => setShowNoticeModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveNotice} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Subject / Circular Title *
                </label>
                <input
                  type="text"
                  required
                  value={noticeForm.title}
                  onChange={(e) => setNoticeForm({ ...noticeForm, title: e.target.value })}
                  placeholder="e.g. Schedule of Annual Term Examinations"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Category *</label>
                  <select
                    value={noticeForm.category}
                    onChange={(e) => setNoticeForm({ ...noticeForm, category: e.target.value as any })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="Academic">Academic</option>
                    <option value="Exam">Exam</option>
                    <option value="Holiday">Holiday</option>
                    <option value="Administrative">Administrative</option>
                    <option value="Sports">Sports</option>
                    <option value="Fee">Fee Reminder</option>
                    <option value="Emergency">Emergency</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Target Audience *</label>
                  <select
                    value={noticeForm.targetAudience}
                    onChange={(e) => setNoticeForm({ ...noticeForm, targetAudience: e.target.value as any })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="All">All Campus Patrons</option>
                    <option value="Students">Students Only</option>
                    <option value="Teachers">Teachers Only</option>
                    <option value="Parents">Parents Only</option>
                    <option value="Staff">Staff Only</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Priority Level</label>
                  <select
                    value={noticeForm.priority}
                    onChange={(e) =>
                      setNoticeForm({
                        ...noticeForm,
                        priority: e.target.value as any,
                        isPinned: e.target.value === 'Urgent' || noticeForm.isPinned,
                      })
                    }
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="Normal">Normal</option>
                    <option value="Important">Important</option>
                    <option value="Urgent">Urgent / High Alert</option>
                  </select>
                </div>
                <div className="flex items-center pt-5">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={noticeForm.isPinned}
                      onChange={(e) => setNoticeForm({ ...noticeForm, isPinned: e.target.checked })}
                      className="rounded text-blue-600"
                    />
                    <span className="font-semibold text-slate-700 dark:text-slate-300">Pin to Top of Board</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Notice Content Body *
                </label>
                <textarea
                  rows={4}
                  required
                  value={noticeForm.content}
                  onChange={(e) => setNoticeForm({ ...noticeForm, content: e.target.value })}
                  placeholder="Full text of executive notice or instructions..."
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Attachment Name</label>
                <input
                  type="text"
                  value={noticeForm.attachmentName}
                  onChange={(e) => setNoticeForm({ ...noticeForm, attachmentName: e.target.value })}
                  placeholder="e.g. Exam_Routine_2026.pdf"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowNoticeModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold"
                >
                  Publish Circular
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: SCHEDULE EVENT */}
      {showEventModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Schedule Event or Holiday</h3>
              <button onClick={() => setShowEventModal(false)} className="text-slate-400 hover:text-slate-600 text-lg">
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveEvent} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Event Title *</label>
                <input
                  type="text"
                  required
                  value={eventForm.eventTitle}
                  onChange={(e) => setEventForm({ ...eventForm, eventTitle: e.target.value })}
                  placeholder="e.g. Science Fair & Tech Exhibition"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Category</label>
                  <select
                    value={eventForm.eventCategory}
                    onChange={(e) =>
                      setEventForm({
                        ...eventForm,
                        eventCategory: e.target.value as any,
                        isHoliday: e.target.value === 'Holiday' || eventForm.isHoliday,
                      })
                    }
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="Academic">Academic</option>
                    <option value="Holiday">Official Holiday</option>
                    <option value="Exam">Exam Period</option>
                    <option value="Sports">Sports</option>
                    <option value="Cultural">Cultural</option>
                    <option value="PTM">PTM Conference</option>
                    <option value="Meeting">Meeting</option>
                    <option value="Tour">Study Tour</option>
                  </select>
                </div>
                <div className="flex items-center pt-5">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={eventForm.isHoliday}
                      onChange={(e) => setEventForm({ ...eventForm, isHoliday: e.target.checked })}
                      className="rounded text-rose-600"
                    />
                    <span className="font-semibold text-rose-600 dark:text-rose-400">Official School Holiday</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Start Date *</label>
                  <input
                    type="date"
                    required
                    value={eventForm.startDate}
                    onChange={(e) => setEventForm({ ...eventForm, startDate: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">End Date *</label>
                  <input
                    type="date"
                    required
                    value={eventForm.endDate}
                    onChange={(e) => setEventForm({ ...eventForm, endDate: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Start Time</label>
                  <input
                    type="text"
                    value={eventForm.startTime}
                    onChange={(e) => setEventForm({ ...eventForm, startTime: e.target.value })}
                    placeholder="09:00 AM"
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">End Time</label>
                  <input
                    type="text"
                    value={eventForm.endTime}
                    onChange={(e) => setEventForm({ ...eventForm, endTime: e.target.value })}
                    placeholder="02:00 PM"
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Venue / Location</label>
                <input
                  type="text"
                  value={eventForm.venue}
                  onChange={(e) => setEventForm({ ...eventForm, venue: e.target.value })}
                  placeholder="Campus Main Grounds, Auditorium"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Organizer</label>
                <input
                  type="text"
                  value={eventForm.organizer}
                  onChange={(e) => setEventForm({ ...eventForm, organizer: e.target.value })}
                  placeholder="Cultural Committee / Exam Board"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Description</label>
                <textarea
                  rows={2}
                  value={eventForm.description}
                  onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })}
                  placeholder="Brief details regarding event format and dress code..."
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowEventModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold"
                >
                  Save Event
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
