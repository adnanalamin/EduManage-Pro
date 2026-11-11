import React, { useState, useMemo } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  Download,
  Printer,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RotateCcw,
  UserCheck,
  Tag,
  Layers,
  Edit,
  Trash2,
  DollarSign,
  Barcode,
  X,
  CreditCard,
  FileSpreadsheet,
} from 'lucide-react';
import { storage } from '../services/storage';
import {
  BookInfo,
  BookCategoryInfo,
  LibraryMemberInfo,
  BookCirculationRecord,
} from '../types';

export const LibraryManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'circulation' | 'members' | 'categories'>('catalog');
  
  // Data State
  const [books, setBooks] = useState<BookInfo[]>(() => storage.getBooks());
  const [categories, setCategories] = useState<BookCategoryInfo[]>(() => storage.getBookCategories());
  const [members, setMembers] = useState<LibraryMemberInfo[]>(() => storage.getLibraryMembers());
  const [circulations, setCirculations] = useState<BookCirculationRecord[]>(() => storage.getCirculations());

  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedLoanStatus, setSelectedLoanStatus] = useState<string>('all');
  const [onlyAvailable, setOnlyAvailable] = useState<boolean>(false);

  // Modals
  const [showBookModal, setShowBookModal] = useState(false);
  const [editingBook, setEditingBook] = useState<BookInfo | null>(null);

  const [showIssueModal, setShowIssueModal] = useState(false);
  const [selectedBookForIssue, setSelectedBookForIssue] = useState<number | null>(null);

  const [showReturnModal, setShowReturnModal] = useState(false);
  const [selectedCirculationForReturn, setSelectedCirculationForReturn] = useState<BookCirculationRecord | null>(null);

  const [showCardModal, setShowCardModal] = useState(false);
  const [selectedMemberForCard, setSelectedMemberForCard] = useState<LibraryMemberInfo | null>(null);

  const [showAddMemberModal, setShowAddMemberModal] = useState(false);

  // Form States for Book Modal
  const [bookForm, setBookForm] = useState({
    accessionNo: '',
    title: '',
    author: '',
    publisher: '',
    isbn: '',
    edition: '',
    publicationYear: 2024,
    categoryId: 1,
    rackNumber: 'Rack 01',
    shelfNumber: 'Shelf A',
    totalCopies: 5,
    price: 35.0,
  });

  // Form States for Issue Modal
  const [issueForm, setIssueForm] = useState({
    bookId: 1,
    memberId: 1,
    issueDate: new Date().toISOString().split('T')[0],
    dueDate: new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString().split('T')[0],
    issuedBy: 'Chief Librarian',
    remarks: '',
  });

  // Form States for Return Modal
  const [returnForm, setReturnForm] = useState({
    returnDate: new Date().toISOString().split('T')[0],
    fineRatePerDay: 5.0,
    finePaid: true,
    remarks: 'Returned in good order',
  });

  // Form States for Member Modal
  const [memberForm, setMemberForm] = useState({
    memberId: '',
    memberType: 'Student' as 'Student' | 'Teacher' | 'Staff',
    patronName: '',
    rollOrDesignation: '',
    maxAllowedBooks: 3,
  });

  const refreshAll = () => {
    setBooks(storage.getBooks());
    setCategories(storage.getBookCategories());
    setMembers(storage.getLibraryMembers());
    setCirculations(storage.getCirculations());
  };

  // KPIs
  const stats = useMemo(() => storage.getLibraryStats(), [books, circulations, members]);

  // Filtered Books
  const filteredBooks = useMemo(() => {
    let result = books;
    if (selectedCategory !== 'all') {
      result = result.filter((b) => b.categoryId === parseInt(selectedCategory, 10));
    }
    if (onlyAvailable) {
      result = result.filter((b) => b.availableCopies > 0);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (b) =>
          b.title.toLowerCase().includes(q) ||
          b.author.toLowerCase().includes(q) ||
          b.accessionNo.toLowerCase().includes(q) ||
          (b.isbn && b.isbn.toLowerCase().includes(q))
      );
    }
    return result;
  }, [books, selectedCategory, onlyAvailable, searchQuery]);

  // Filtered Circulations
  const filteredCirculations = useMemo(() => {
    if (selectedLoanStatus === 'all') return circulations;
    if (selectedLoanStatus === 'Active') return circulations.filter((c) => c.status === 'Issued' || c.status === 'Overdue');
    return circulations.filter((c) => c.status === selectedLoanStatus);
  }, [circulations, selectedLoanStatus]);

  // Export Book Catalog to CSV
  const exportCatalogCSV = () => {
    const headers = ['Accession No', 'Title', 'Author', 'Category', 'ISBN', 'Rack', 'Shelf', 'Total Copies', 'Available', 'Issued', 'Price', 'Status'];
    const rows = filteredBooks.map((b) => [
      `"${b.accessionNo}"`,
      `"${b.title.replace(/"/g, '""')}"`,
      `"${b.author.replace(/"/g, '""')}"`,
      `"${b.categoryName}"`,
      `"${b.isbn || '-'}"`,
      `"${b.rackNumber || '-'}"`,
      `"${b.shelfNumber || '-'}"`,
      b.totalCopies,
      b.availableCopies,
      b.issuedCopies,
      b.price,
      `"${b.status}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `EduManage_Library_Catalog_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export Circulation to CSV
  const exportCirculationCSV = () => {
    const headers = ['Loan ID', 'Accession', 'Book Title', 'Borrower', 'Member Code', 'Type', 'Issue Date', 'Due Date', 'Return Date', 'Status', 'Fine', 'Fine Paid'];
    const rows = filteredCirculations.map((c) => [
      c.id,
      `"${c.accessionNo}"`,
      `"${c.bookTitle.replace(/"/g, '""')}"`,
      `"${c.patronName.replace(/"/g, '""')}"`,
      `"${c.memberCode}"`,
      `"${c.memberType}"`,
      c.issueDate,
      c.dueDate,
      c.returnDate || '-',
      c.status,
      c.fineAmount,
      c.finePaid ? 'Yes' : 'No',
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `EduManage_Circulation_Audit_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Handle Book Form Submit
  const handleSaveBook = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingBook) {
      storage.saveBook({
        id: editingBook.id,
        ...bookForm,
      });
    } else {
      storage.saveBook({
        ...bookForm,
      });
    }
    setShowBookModal(false);
    setEditingBook(null);
    refreshAll();
  };

  // Open Edit Book Modal
  const openEditBook = (b: BookInfo) => {
    setEditingBook(b);
    setBookForm({
      accessionNo: b.accessionNo,
      title: b.title,
      author: b.author,
      publisher: b.publisher || '',
      isbn: b.isbn || '',
      edition: b.edition || '',
      publicationYear: b.publicationYear || 2024,
      categoryId: b.categoryId,
      rackNumber: b.rackNumber || 'Rack 01',
      shelfNumber: b.shelfNumber || 'Shelf A',
      totalCopies: b.totalCopies,
      price: b.price,
    });
    setShowBookModal(true);
  };

  // Open New Book Modal
  const openNewBook = () => {
    setEditingBook(null);
    setBookForm({
      accessionNo: `ACC-2026-${String(books.length + 1).padStart(4, '0')}`,
      title: '',
      author: '',
      publisher: '',
      isbn: '',
      edition: '1st Edition',
      publicationYear: 2024,
      categoryId: categories[0]?.id || 1,
      rackNumber: 'Rack 01',
      shelfNumber: 'Shelf A',
      totalCopies: 5,
      price: 25.0,
    });
    setShowBookModal(true);
  };

  // Handle Quick Issue from Book Table
  const handleQuickIssue = (b: BookInfo) => {
    setSelectedBookForIssue(b.id);
    setIssueForm({
      bookId: b.id,
      memberId: members[0]?.id || 1,
      issueDate: new Date().toISOString().split('T')[0],
      dueDate: new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString().split('T')[0],
      issuedBy: 'Chief Librarian',
      remarks: '',
    });
    setShowIssueModal(true);
  };

  // Handle Confirm Issue
  const handleConfirmIssue = (e: React.FormEvent) => {
    e.preventDefault();
    const res = storage.issueBook(
      issueForm.bookId,
      issueForm.memberId,
      issueForm.issueDate,
      issueForm.dueDate,
      issueForm.issuedBy,
      issueForm.remarks
    );
    if (!res.success) {
      alert(`Issue Rejected: ${res.message}`);
      return;
    }
    setShowIssueModal(false);
    refreshAll();
  };

  // Handle Open Return Modal
  const handleOpenReturn = (c: BookCirculationRecord) => {
    setSelectedCirculationForReturn(c);
    setReturnForm({
      returnDate: new Date().toISOString().split('T')[0],
      fineRatePerDay: 5.0,
      finePaid: true,
      remarks: 'Returned in good order',
    });
    setShowReturnModal(true);
  };

  // Computed Overdue Days in Return Modal
  const returnOverdueInfo = useMemo(() => {
    if (!selectedCirculationForReturn) return { overdueDays: 0, fine: 0 };
    const dueTime = new Date(selectedCirculationForReturn.dueDate).getTime();
    const retTime = new Date(returnForm.returnDate).getTime();
    const diffDays = Math.max(0, Math.ceil((retTime - dueTime) / (1000 * 3600 * 24)));
    const fine = diffDays * returnForm.fineRatePerDay;
    return { overdueDays: diffDays, fine };
  }, [selectedCirculationForReturn, returnForm.returnDate, returnForm.fineRatePerDay]);

  // Handle Confirm Return
  const handleConfirmReturn = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCirculationForReturn) return;
    const res = storage.returnBook(
      selectedCirculationForReturn.id,
      returnForm.returnDate,
      returnForm.fineRatePerDay,
      returnForm.finePaid,
      returnForm.remarks
    );
    if (!res.success) {
      alert(`Return Failed: ${res.message}`);
      return;
    }
    setShowReturnModal(false);
    setSelectedCirculationForReturn(null);
    refreshAll();
  };

  // Handle Add Member
  const handleSaveMember = (e: React.FormEvent) => {
    e.preventDefault();
    storage.saveLibraryMember({
      memberId: memberForm.memberId || `LIB-${memberForm.memberType.substring(0, 3).toUpperCase()}-${String(members.length + 1001)}`,
      memberType: memberForm.memberType,
      patronName: memberForm.patronName,
      rollOrDesignation: memberForm.rollOrDesignation,
      maxAllowedBooks: memberForm.maxAllowedBooks,
      cardIssueDate: new Date().toISOString().split('T')[0],
      status: 'Active',
    });
    setShowAddMemberModal(false);
    refreshAll();
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-800">
      {/* 1. Header & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-700 text-white rounded-xl shadow-sm">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Library Circulation & Book Management
              </h1>
              <p className="text-sm text-slate-500">
                Phase 10: Cataloging, Accession Numbers, Shelf Allocation, Loan Checkout & CR80 Passes
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={exportCatalogCSV}
            className="flex items-center gap-2 px-3.5 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export Catalog
          </button>
          <button
            onClick={() => {
              setSelectedBookForIssue(null);
              setIssueForm({
                bookId: books.find((b) => b.availableCopies > 0)?.id || 1,
                memberId: members[0]?.id || 1,
                issueDate: new Date().toISOString().split('T')[0],
                dueDate: new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString().split('T')[0],
                issuedBy: 'Chief Librarian',
                remarks: '',
              });
              setShowIssueModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 shadow-sm transition"
          >
            <RotateCcw className="w-4 h-4" />
            Issue Book (Checkout)
          </button>
          <button
            onClick={openNewBook}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            Add Book
          </button>
        </div>
      </div>

      {/* 2. KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-blue-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Catalog Titles</span>
            <BookOpen className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{stats.totalTitles}</div>
          <span className="text-xs text-slate-400 mt-1 block">Active ISBN catalog</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-slate-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Copies</span>
            <Layers className="w-4 h-4 text-slate-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{stats.totalInventoryCopies}</div>
          <span className="text-xs text-slate-400 mt-1 block">Physical shelf stock</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-emerald-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Available</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-2">{stats.availableCopies}</div>
          <span className="text-xs text-emerald-600 mt-1 block">Ready for loan</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-amber-500 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Loans</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-600 mt-2">{stats.currentlyIssued}</div>
          <span className="text-xs text-slate-400 mt-1 block">Checked out</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-rose-500 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Overdue</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-600 mt-2">{stats.overdueCount}</div>
          <span className="text-xs text-rose-500 mt-1 block">Past due date</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-purple-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Fines Paid</span>
            <DollarSign className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-purple-700 mt-2">${stats.totalFineCollected.toFixed(2)}</div>
          <span className="text-xs text-slate-400 mt-1 block">Total penalty receipts</span>
        </div>
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-1">
        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'catalog'
              ? 'border-emerald-700 text-emerald-800 bg-emerald-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Book Catalog & Inventory ({filteredBooks.length})
        </button>

        <button
          onClick={() => setActiveTab('circulation')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'circulation'
              ? 'border-emerald-700 text-emerald-800 bg-emerald-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          Circulation Desk ({circulations.length})
        </button>

        <button
          onClick={() => setActiveTab('members')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'members'
              ? 'border-emerald-700 text-emerald-800 bg-emerald-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <CreditCard className="w-4 h-4" />
          Member Passes ({members.length})
        </button>

        <button
          onClick={() => setActiveTab('categories')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'categories'
              ? 'border-emerald-700 text-emerald-800 bg-emerald-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Tag className="w-4 h-4" />
          Categories & Shelves ({categories.length})
        </button>
      </div>

      {/* 4. Tab Content */}
      {activeTab === 'catalog' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              <div className="relative min-w-[280px]">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search title, author, accession no, ISBN..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-600"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600"
                >
                  <option value="all">All Categories</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={onlyAvailable}
                  onChange={(e) => setOnlyAvailable(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span>Only Available Copies</span>
              </label>
            </div>

            <div className="text-xs text-slate-500 font-medium">
              Showing {filteredBooks.length} of {books.length} titles
            </div>
          </div>

          {/* Book Catalog Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Accession</th>
                    <th className="py-3 px-4">Book Title & Author</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-center">Rack / Shelf</th>
                    <th className="py-3 px-4 text-center">Copies (Avail / Tot)</th>
                    <th className="py-3 px-4 text-right">Price</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredBooks.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-medium text-emerald-800 text-xs">
                        {b.accessionNo}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{b.title}</div>
                        <div className="text-xs text-slate-500">
                          by <span className="font-medium text-slate-700">{b.author}</span>
                          {b.publisher && ` • ${b.publisher}`}
                          {b.edition && ` (${b.edition})`}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                          {b.categoryName}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-600">
                        {b.rackNumber || '-'} / {b.shelfNumber || '-'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block font-semibold px-2 py-0.5 rounded-full text-xs ${
                            b.availableCopies > 0
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {b.availableCopies} / {b.totalCopies}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-medium text-slate-900">
                        ${b.price.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                            b.status === 'Available'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {b.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            disabled={b.availableCopies <= 0}
                            onClick={() => handleQuickIssue(b)}
                            className={`px-2.5 py-1 text-xs font-semibold rounded transition ${
                              b.availableCopies > 0
                                ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                            }`}
                            title={b.availableCopies > 0 ? 'Issue to borrower' : 'No copies available'}
                          >
                            Issue
                          </button>
                          <button
                            onClick={() => openEditBook(b)}
                            className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded"
                            title="Edit book metadata"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => {
                              if (window.confirm(`Delete '${b.title}' from catalog?`)) {
                                storage.deleteBook(b.id);
                                refreshAll();
                              }
                            }}
                            className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded"
                            title="Delete book"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}

                  {filteredBooks.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-slate-400">
                        No book titles found matching your search or filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'circulation' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-600">Filter Status:</span>
              <div className="flex gap-1.5">
                {['all', 'Active', 'Issued', 'Overdue', 'Returned'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setSelectedLoanStatus(st)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                      selectedLoanStatus === st
                        ? 'bg-emerald-700 text-white shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {st === 'all' ? 'All Loans' : st}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={exportCirculationCSV}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                Audit CSV
              </button>
              <span className="text-xs text-slate-400">
                {filteredCirculations.length} Records
              </span>
            </div>
          </div>

          {/* Circulations Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Loan ID</th>
                    <th className="py-3 px-4">Book Title & Accession</th>
                    <th className="py-3 px-4">Borrower Patron</th>
                    <th className="py-3 px-4 text-center">Type</th>
                    <th className="py-3 px-4 text-center">Issue Date</th>
                    <th className="py-3 px-4 text-center">Due Date</th>
                    <th className="py-3 px-4 text-center">Return Date</th>
                    <th className="py-3 px-4 text-right">Fine ($)</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredCirculations.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-medium text-slate-600 text-xs">
                        #{c.id.toString().padStart(4, '0')}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{c.bookTitle}</div>
                        <div className="text-xs font-mono text-emerald-800">{c.accessionNo}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-900">{c.patronName}</div>
                        <div className="text-xs text-slate-400 font-mono">{c.memberCode}</div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                          {c.memberType}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-600">
                        {c.issueDate}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs font-medium text-slate-800">
                        {c.dueDate}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-500">
                        {c.returnDate || '—'}
                      </td>
                      <td className="py-3 px-4 text-right font-medium">
                        {c.fineAmount > 0 ? (
                          <span className="text-rose-600 font-semibold">${c.fineAmount.toFixed(2)}</span>
                        ) : (
                          <span className="text-slate-400">$0.00</span>
                        )}
                        {c.finePaid && c.fineAmount > 0 && (
                          <span className="ml-1 text-[10px] text-emerald-600 font-semibold">(Paid)</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${
                            c.status === 'Returned'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : c.status === 'Overdue'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200 animate-pulse'
                              : 'bg-blue-50 text-blue-700 border border-blue-200'
                          }`}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {c.status !== 'Returned' ? (
                          <button
                            onClick={() => handleOpenReturn(c)}
                            className="px-3 py-1 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-sm transition"
                          >
                            Check In
                          </button>
                        ) : (
                          <span className="text-xs text-slate-400">Completed</span>
                        )}
                      </td>
                    </tr>
                  ))}

                  {filteredCirculations.length === 0 && (
                    <tr>
                      <td colSpan={10} className="py-8 text-center text-slate-400">
                        No loans found matching filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'members' && (
        <div className="space-y-4">
          {/* Header Action */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between shadow-sm">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Registered Library Patrons</h2>
              <p className="text-xs text-slate-500">
                Borrower cards for students and faculty with auto-checked borrowing limits
              </p>
            </div>
            <button
              onClick={() => {
                setMemberForm({
                  memberId: `LIB-STD-${String(members.length + 1001)}`,
                  memberType: 'Student',
                  patronName: '',
                  rollOrDesignation: 'Class 10 (Roll 5)',
                  maxAllowedBooks: 3,
                });
                setShowAddMemberModal(true);
              }}
              className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              Register New Member
            </button>
          </div>

          {/* Members Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Card ID</th>
                    <th className="py-3 px-4">Patron Name</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Class / Designation</th>
                    <th className="py-3 px-4 text-center">Active Loans</th>
                    <th className="py-3 px-4 text-center">Max Quota</th>
                    <th className="py-3 px-4 text-center">Issue Date</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-medium text-emerald-800 text-xs">
                        {m.memberId}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {m.patronName}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            m.memberType === 'Student'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}
                        >
                          {m.memberType}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 text-xs">
                        {m.rollOrDesignation || '-'}
                      </td>
                      <td className="py-3 px-4 text-center font-semibold text-slate-800">
                        {m.activeLoanCount}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-600">
                        {m.maxAllowedBooks} Books
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-500">
                        {m.cardIssueDate}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => {
                            setSelectedMemberForCard(m);
                            setShowCardModal(true);
                          }}
                          className="flex items-center gap-1.5 ml-auto px-3 py-1 text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-300 hover:bg-emerald-100 rounded transition"
                        >
                          <CreditCard className="w-3.5 h-3.5" />
                          Print Pass
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

      {activeTab === 'categories' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((cat) => {
              const bookCount = books.filter((b) => b.categoryId === cat.id).length;
              const copyCount = books
                .filter((b) => b.categoryId === cat.id)
                .reduce((acc, b) => acc + b.totalCopies, 0);

              return (
                <div
                  key={cat.id}
                  className="bg-white p-5 rounded-xl border border-slate-200 hover:border-emerald-500/50 hover:shadow-md transition space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-mono text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        {cat.code}
                      </span>
                      <h3 className="font-bold text-slate-900 text-base mt-2">{cat.name}</h3>
                    </div>
                    <Tag className="w-5 h-5 text-slate-400" />
                  </div>
                  <p className="text-xs text-slate-500 min-h-[32px]">{cat.description || 'General collection.'}</p>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs font-semibold">
                    <span className="text-slate-600">{bookCount} Titles</span>
                    <span className="text-emerald-700">{copyCount} Physical Copies</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 1: ADD / EDIT BOOK MODAL
      ======================================================== */}
      {showBookModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">
                {editingBook ? 'Edit Book Metadata' : 'Add New Book to Catalog'}
              </h3>
              <button
                onClick={() => setShowBookModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveBook} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Accession No *</label>
                  <input
                    type="text"
                    required
                    value={bookForm.accessionNo}
                    onChange={(e) => setBookForm({ ...bookForm, accessionNo: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">ISBN</label>
                  <input
                    type="text"
                    placeholder="978-..."
                    value={bookForm.isbn}
                    onChange={(e) => setBookForm({ ...bookForm, isbn: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Book Title *</label>
                <input
                  type="text"
                  required
                  placeholder="Full Title"
                  value={bookForm.title}
                  onChange={(e) => setBookForm({ ...bookForm, title: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Author(s) *</label>
                  <input
                    type="text"
                    required
                    placeholder="Author name"
                    value={bookForm.author}
                    onChange={(e) => setBookForm({ ...bookForm, author: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Category *</label>
                  <select
                    value={bookForm.categoryId}
                    onChange={(e) => setBookForm({ ...bookForm, categoryId: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Publisher</label>
                  <input
                    type="text"
                    value={bookForm.publisher}
                    onChange={(e) => setBookForm({ ...bookForm, publisher: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Edition</label>
                  <input
                    type="text"
                    value={bookForm.edition}
                    onChange={(e) => setBookForm({ ...bookForm, edition: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Year</label>
                  <input
                    type="number"
                    value={bookForm.publicationYear}
                    onChange={(e) => setBookForm({ ...bookForm, publicationYear: parseInt(e.target.value, 10) || 2024 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Rack Location</label>
                  <input
                    type="text"
                    placeholder="Rack 01"
                    value={bookForm.rackNumber}
                    onChange={(e) => setBookForm({ ...bookForm, rackNumber: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Shelf Number</label>
                  <input
                    type="text"
                    placeholder="Shelf A"
                    value={bookForm.shelfNumber}
                    onChange={(e) => setBookForm({ ...bookForm, shelfNumber: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Total Copies *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={bookForm.totalCopies}
                    onChange={(e) => setBookForm({ ...bookForm, totalCopies: parseInt(e.target.value, 10) || 1 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Unit Price ($)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={bookForm.price}
                    onChange={(e) => setBookForm({ ...bookForm, price: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowBookModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm"
                >
                  Save Book Title
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 2: ISSUE BOOK (CHECKOUT) MODAL
      ======================================================== */}
      {showIssueModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-emerald-700" />
                <h3 className="font-bold text-lg text-slate-900">Check Out Book (Issue Loan)</h3>
              </div>
              <button
                onClick={() => setShowIssueModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConfirmIssue} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Book *</label>
                <select
                  value={issueForm.bookId}
                  onChange={(e) => setIssueForm({ ...issueForm, bookId: parseInt(e.target.value, 10) })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {books
                    .filter((b) => b.availableCopies > 0 || b.id === issueForm.bookId)
                    .map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.accessionNo} — {b.title} ({b.availableCopies} avail)
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Borrower Patron *</label>
                <select
                  value={issueForm.memberId}
                  onChange={(e) => setIssueForm({ ...issueForm, memberId: parseInt(e.target.value, 10) })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.memberId} — {m.patronName} ({m.memberType}) [Limit: {m.maxAllowedBooks}]
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Issue Date *</label>
                  <input
                    type="date"
                    required
                    value={issueForm.issueDate}
                    onChange={(e) => setIssueForm({ ...issueForm, issueDate: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Due Date *</label>
                  <input
                    type="date"
                    required
                    value={issueForm.dueDate}
                    onChange={(e) => setIssueForm({ ...issueForm, dueDate: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Issued By Officer</label>
                <input
                  type="text"
                  value={issueForm.issuedBy}
                  onChange={(e) => setIssueForm({ ...issueForm, issuedBy: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Remarks</label>
                <input
                  type="text"
                  placeholder="e.g. Reference loan for class project"
                  value={issueForm.remarks}
                  onChange={(e) => setIssueForm({ ...issueForm, remarks: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowIssueModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm"
                >
                  Confirm Issue
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 3: CHECK IN / RETURN BOOK MODAL
      ======================================================== */}
      {showReturnModal && selectedCirculationForReturn && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">Check In Book & Fine Audit</h3>
              <button
                onClick={() => setShowReturnModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl space-y-1.5 text-xs text-slate-700">
              <div>
                <span className="font-semibold text-slate-500">Book:</span>{' '}
                <span className="font-bold text-slate-900">{selectedCirculationForReturn.bookTitle}</span> (
                {selectedCirculationForReturn.accessionNo})
              </div>
              <div>
                <span className="font-semibold text-slate-500">Borrower:</span>{' '}
                <span className="font-medium text-slate-900">{selectedCirculationForReturn.patronName}</span> (
                {selectedCirculationForReturn.memberCode})
              </div>
              <div>
                <span className="font-semibold text-slate-500">Due Date:</span>{' '}
                <span className="font-bold text-rose-700">{selectedCirculationForReturn.dueDate}</span>
              </div>
            </div>

            <form onSubmit={handleConfirmReturn} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Return Date *</label>
                <input
                  type="date"
                  required
                  value={returnForm.returnDate}
                  onChange={(e) => setReturnForm({ ...returnForm, returnDate: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              {/* Overdue Calculation Banner */}
              <div
                className={`p-3 rounded-xl border ${
                  returnOverdueInfo.overdueDays > 0
                    ? 'bg-rose-50 border-rose-200 text-rose-800'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                }`}
              >
                <div className="flex items-center justify-between font-bold text-sm">
                  <span>
                    {returnOverdueInfo.overdueDays > 0
                      ? `${returnOverdueInfo.overdueDays} Days OVERDUE`
                      : 'On Time (No Overdue)'}
                  </span>
                  <span>${returnOverdueInfo.fine.toFixed(2)} Fine</span>
                </div>
                <div className="text-[11px] opacity-80 mt-1">
                  Fine rate: ${returnForm.fineRatePerDay.toFixed(2)} / day past deadline
                </div>
              </div>

              {returnOverdueInfo.fine > 0 && (
                <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={returnForm.finePaid}
                    onChange={(e) => setReturnForm({ ...returnForm, finePaid: e.target.checked })}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>Fine Collected in Cash / Waived</span>
                </label>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Return Remarks / Condition</label>
                <input
                  type="text"
                  value={returnForm.remarks}
                  onChange={(e) => setReturnForm({ ...returnForm, remarks: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowReturnModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
                >
                  Complete Check In
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 4: CR80 PVC PRINTABLE LIBRARY PASS MODAL
      ======================================================== */}
      {showCardModal && selectedMemberForCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">CR80 PVC Library Membership Pass</h3>
              <button
                onClick={() => setShowCardModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Simulated CR80 Card Frame (85.6mm x 54mm aspect ratio approx 1.58) */}
            <div className="mx-auto w-[340px] h-[215px] bg-white rounded-2xl shadow-lg border-2 border-slate-300 overflow-hidden relative flex flex-col justify-between">
              {/* Header Bar */}
              <div className="bg-emerald-800 text-white px-4 py-2 text-center">
                <div className="text-[11px] font-bold tracking-wide uppercase">Ideal Model High School & College</div>
                <div className="text-[9px] font-semibold text-emerald-200 tracking-wider">OFFICIAL LIBRARY BORROWER PASS</div>
              </div>

              {/* Body */}
              <div className="p-3.5 flex gap-3 items-center flex-1">
                {/* Photo container */}
                <div className="w-16 h-20 bg-emerald-50 border border-emerald-300 rounded-lg flex flex-col items-center justify-center text-emerald-800 font-bold text-xs shadow-inner shrink-0">
                  <div className="text-lg">
                    {selectedMemberForCard.patronName
                      .split(' ')
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join('')}
                  </div>
                  <span className="text-[8px] uppercase tracking-wider text-emerald-600 mt-1">
                    {selectedMemberForCard.memberType}
                  </span>
                </div>

                {/* Details */}
                <div className="space-y-1 text-xs">
                  <div className="font-bold text-slate-900 text-sm leading-tight">
                    {selectedMemberForCard.patronName}
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    {selectedMemberForCard.rollOrDesignation || selectedMemberForCard.memberType}
                  </div>
                  <div className="font-mono text-[11px] text-emerald-800 font-bold">
                    Card: {selectedMemberForCard.memberId}
                  </div>
                  <div className="text-[10px] text-slate-600">
                    Loan Limit: <span className="font-bold">{selectedMemberForCard.maxAllowedBooks} Books</span>
                  </div>
                  <div className="text-[9px] text-slate-400">
                    Issued: {selectedMemberForCard.cardIssueDate} • Valid 2026
                  </div>
                </div>
              </div>

              {/* Barcode Graphic simulation */}
              <div className="px-4 py-1.5 bg-slate-50 border-t border-slate-200 flex flex-col items-center justify-center">
                <div className="flex items-center gap-[2px] h-4">
                  {selectedMemberForCard.memberId.split('').map((char, i) => (
                    <div
                      key={i}
                      className="bg-slate-900 h-full"
                      style={{
                        width: (char.charCodeAt(0) % 3) + 1.2 + 'px',
                        marginRight: (char.charCodeAt(0) % 2) + 0.5 + 'px',
                      }}
                    />
                  ))}
                  {/* repeated pattern to fill card width */}
                  {selectedMemberForCard.memberId.split('').map((char, i) => (
                    <div
                      key={`r-${i}`}
                      className="bg-slate-900 h-full"
                      style={{
                        width: (char.charCodeAt(0) % 2) + 1.5 + 'px',
                        marginRight: 1 + 'px',
                      }}
                    />
                  ))}
                </div>
                <div className="text-[8px] font-mono text-slate-500 tracking-widest mt-0.5">
                  *{selectedMemberForCard.memberId}*
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t">
              <span className="text-xs text-slate-400">Standard ISO/IEC 7810 ID-1 PVC</span>
              <button
                onClick={() => {
                  window.print();
                }}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm"
              >
                <Printer className="w-4 h-4" />
                Print PVC Card
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL 5: REGISTER NEW LIBRARY MEMBER MODAL
      ======================================================== */}
      {showAddMemberModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">Register New Library Member</h3>
              <button
                onClick={() => setShowAddMemberModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Member Type *</label>
                <select
                  value={memberForm.memberType}
                  onChange={(e) => {
                    const mType = e.target.value as 'Student' | 'Teacher' | 'Staff';
                    setMemberForm({
                      ...memberForm,
                      memberType: mType,
                      maxAllowedBooks: mType === 'Teacher' ? 5 : 3,
                    });
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="Student">Student (Limit: 3 Books)</option>
                  <option value="Teacher">Teacher / Faculty (Limit: 5 Books)</option>
                  <option value="Staff">School Staff (Limit: 3 Books)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Member Card ID *</label>
                <input
                  type="text"
                  required
                  value={memberForm.memberId}
                  onChange={(e) => setMemberForm({ ...memberForm, memberId: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Patron Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Mahfuzur Rahman"
                  value={memberForm.patronName}
                  onChange={(e) => setMemberForm({ ...memberForm, patronName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Class / Roll or Designation</label>
                <input
                  type="text"
                  placeholder="e.g. Class 10 (Roll 5)"
                  value={memberForm.rollOrDesignation}
                  onChange={(e) => setMemberForm({ ...memberForm, rollOrDesignation: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Borrowing Quota</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={memberForm.maxAllowedBooks}
                  onChange={(e) => setMemberForm({ ...memberForm, maxAllowedBooks: parseInt(e.target.value, 10) || 3 })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm"
                >
                  Register Patron
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
