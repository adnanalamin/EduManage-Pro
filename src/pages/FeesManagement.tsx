import React, { useState, useMemo } from 'react';
import {
  DollarSign,
  Receipt,
  CreditCard,
  Plus,
  Search,
  Filter,
  CheckCircle,
  Clock,
  AlertCircle,
  Download,
  Printer,
  Calendar,
  Layers,
  FileText,
  UserCheck,
  TrendingUp,
  Tag,
  Eye,
  X,
  Building,
  Check
} from 'lucide-react';
import { storage } from '../services/storage';
import {
  FeeCategoryInfo,
  FeeStructureInfo,
  StudentFeeInvoice,
  FeePaymentRecord,
  SchoolSetting,
} from '../types';

interface FeesManagementProps {
  currentUserRole?: string;
}

export const FeesManagement: React.FC<FeesManagementProps> = ({ currentUserRole }) => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'structures' | 'history'>('invoices');
  
  // Data states
  const [invoices, setInvoices] = useState<StudentFeeInvoice[]>(() => storage.getStudentFeeInvoices());
  const [structures, setStructures] = useState<FeeStructureInfo[]>(() => storage.getFeeStructures());
  const [categories, setCategories] = useState<FeeCategoryInfo[]>(() => storage.getFeeCategories());
  const [schoolSettings] = useState<SchoolSetting>(() => storage.getSchoolSettings());

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Modals
  const [showCollectModal, setShowCollectModal] = useState(false);
  const [selectedInvoiceForPayment, setSelectedInvoiceForPayment] = useState<StudentFeeInvoice | null>(null);
  
  const [showStructureModal, setShowStructureModal] = useState(false);
  const [showReceiptModal, setShowReceiptModal] = useState(false);
  const [selectedReceiptPayment, setSelectedReceiptPayment] = useState<{ payment: FeePaymentRecord; invoice: StudentFeeInvoice } | null>(null);

  // Form states for Payment
  const [paymentAmount, setPaymentAmount] = useState<number>(0);
  const [paymentDiscount, setPaymentDiscount] = useState<number>(0);
  const [paymentMethod, setPaymentMethod] = useState<FeePaymentRecord['paymentMethod']>('Cash');
  const [transactionRef, setTransactionRef] = useState('');
  const [receivedBy, setReceivedBy] = useState('Shafiqul Alam (Accounts)');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [paymentError, setPaymentError] = useState<string | null>(null);

  // Form states for Structure
  const [newStructCategory, setNewStructCategory] = useState<number>(1);
  const [newStructClass, setNewStructClass] = useState('Class 9');
  const [newStructTitle, setNewStructTitle] = useState('');
  const [newStructAmount, setNewStructAmount] = useState<number>(2000);
  const [newStructDueDate, setNewStructDueDate] = useState('2025-04-15');
  const [newStructAutoAssign, setNewStructAutoAssign] = useState(true);

  // Refresh data from storage
  const reloadData = () => {
    setInvoices(storage.getStudentFeeInvoices());
    setStructures(storage.getFeeStructures());
    setCategories(storage.getFeeCategories());
  };

  // KPIs
  const stats = useMemo(() => storage.getFeeStats(), [invoices]);

  // Unique classes for filter
  const classOptions = useMemo(() => {
    const set = new Set<string>();
    invoices.forEach((i) => set.add(i.className));
    return ['All', ...Array.from(set)];
  }, [invoices]);

  // Filtered invoices
  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      const matchSearch =
        inv.studentName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.studentCode.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.feeTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.rollNumber.toString().includes(searchQuery);

      const matchClass = selectedClass === 'All' || inv.className === selectedClass;
      const matchStatus = selectedStatus === 'All' || inv.status === selectedStatus;
      const matchCategory = selectedCategory === 'All' || inv.categoryName === selectedCategory;

      return matchSearch && matchClass && matchStatus && matchCategory;
    });
  }, [invoices, searchQuery, selectedClass, selectedStatus, selectedCategory]);

  // Flattened payment history
  const allPayments = useMemo(() => {
    const list: { payment: FeePaymentRecord; invoice: StudentFeeInvoice }[] = [];
    invoices.forEach((inv) => {
      inv.payments?.forEach((pmt) => {
        list.push({ payment: pmt, invoice: inv });
      });
    });
    return list.sort((a, b) => b.payment.id - a.payment.id);
  }, [invoices]);

  // Handlers
  const handleOpenPayment = (inv: StudentFeeInvoice) => {
    setSelectedInvoiceForPayment(inv);
    setPaymentAmount(inv.dueAmount);
    setPaymentDiscount(0);
    setPaymentMethod('bKash');
    setTransactionRef('');
    setPaymentNotes('');
    setPaymentError(null);
    setShowCollectModal(true);
  };

  const handleProcessPayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvoiceForPayment) return;

    try {
      setPaymentError(null);
      const res = storage.recordFeePayment({
        studentFeeId: selectedInvoiceForPayment.id,
        amount: Number(paymentAmount),
        discountAmount: Number(paymentDiscount),
        paymentMethod,
        transactionRef: transactionRef.trim() || undefined,
        receivedBy: receivedBy.trim() || 'Accounts Office',
        notes: paymentNotes.trim() || undefined,
      });

      setShowCollectModal(false);
      reloadData();
      // Show receipt right away
      setSelectedReceiptPayment({ payment: res.payment, invoice: res.invoice });
      setShowReceiptModal(true);
    } catch (err: any) {
      setPaymentError(err.message || 'Payment collection failed');
    }
  };

  const handleCreateStructure = (e: React.FormEvent) => {
    e.preventDefault();
    const cat = categories.find((c) => c.id === Number(newStructCategory));
    if (!cat) return;

    storage.addFeeStructure(
      {
        categoryId: cat.id,
        categoryName: cat.name,
        classId: newStructClass === 'Class 10' ? 5 : 4,
        className: newStructClass,
        academicYearId: 1,
        academicYearName: '2025-2026',
        title: newStructTitle || `${newStructClass} - ${cat.name}`,
        amount: Number(newStructAmount),
        dueDate: newStructDueDate,
      },
      newStructAutoAssign
    );

    setShowStructureModal(false);
    reloadData();
    setNewStructTitle('');
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">Fees & Billing Management</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Phase 6 Active
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Student fee structures, invoice generation, discount waivers, multi-channel payment collection & PDF receipts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (invoices.filter((i) => i.dueAmount > 0).length > 0) {
                handleOpenPayment(invoices.filter((i) => i.dueAmount > 0)[0]);
              }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition shadow-sm cursor-pointer"
          >
            <CreditCard className="w-4 h-4" />
            <span>Collect Fee</span>
          </button>
          <button
            onClick={() => setShowStructureModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Fee Schedule</span>
          </button>
        </div>
      </div>

      {/* Financial KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Invoiced */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Total Invoiced</span>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {schoolSettings.currencySymbol} {stats.totalInvoiced.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">{stats.totalInvoices} student invoices issued</p>
        </div>

        {/* Total Collected */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Total Collected</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">
              {schoolSettings.currencySymbol} {stats.totalCollected.toLocaleString()}
            </span>
            <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300">
              {stats.collectionRate.toFixed(1)}%
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, stats.collectionRate)}%` }}
            />
          </div>
        </div>

        {/* Total Outstanding Due */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Outstanding Due</span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-400">
              {schoolSettings.currencySymbol} {stats.totalDue.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {stats.unpaidInvoices} Unpaid &bull; {stats.partialInvoices} Partial
          </p>
        </div>

        {/* Scholarships & Waivers */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Scholarships / Waivers</span>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Tag className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-purple-400">
              {schoolSettings.currencySymbol} {stats.totalDiscounts.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Merit & sibling aid granted</p>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="border-b border-slate-800 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('invoices')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'invoices'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Receipt className="w-4 h-4" />
            <span>Student Invoices</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300">
              {invoices.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('structures')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'structures'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Fee Schedules & Structures</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300">
              {structures.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'history'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CreditCard className="w-4 h-4" />
            <span>Payment History & Receipts</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300">
              {allPayments.length}
            </span>
          </button>
        </div>
      </div>

      {/* TAB 1: INVOICES & COLLECTION */}
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap gap-3 items-center justify-between">
            <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
              <div className="relative flex-1 min-w-[200px] max-w-md">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search student name, ID, roll, or fee title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition"
                />
              </div>

              {/* Class Filter */}
              <select
                value={selectedClass}
                onChange={(e) => setSelectedClass(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                {classOptions.map((c) => (
                  <option key={c} value={c}>
                    {c === 'All' ? 'All Classes' : c}
                  </option>
                ))}
              </select>

              {/* Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                <option value="All">All Statuses</option>
                <option value="Paid">Paid</option>
                <option value="Partial">Partial</option>
                <option value="Unpaid">Unpaid</option>
              </select>

              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                <option value="All">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <span className="text-xs text-slate-400">
              Showing <strong className="text-white">{filteredInvoices.length}</strong> of {invoices.length} invoices
            </span>
          </div>

          {/* Invoices Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold text-xs border-b border-slate-800 uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Student</th>
                    <th className="py-3 px-4">Class & Roll</th>
                    <th className="py-3 px-4">Fee Schedule</th>
                    <th className="py-3 px-4">Due Date</th>
                    <th className="py-3 px-4 text-right">Total</th>
                    <th className="py-3 px-4 text-right">Waiver</th>
                    <th className="py-3 px-4 text-right">Paid</th>
                    <th className="py-3 px-4 text-right">Balance Due</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredInvoices.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="py-12 text-center text-slate-500">
                        No fee invoices found matching the current criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredInvoices.map((inv) => {
                      const isPaid = inv.status === 'Paid';
                      const isPartial = inv.status === 'Partial';
                      const isUnpaid = inv.status === 'Unpaid';

                      return (
                        <tr key={inv.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-white">{inv.studentName}</div>
                            <div className="text-xs text-slate-400 font-mono">{inv.studentCode}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="text-slate-200">{inv.className}</div>
                            <div className="text-xs text-slate-400">Roll: {inv.rollNumber} &bull; {inv.sectionName || 'Main'}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-medium text-slate-200">{inv.feeTitle}</div>
                            <span className="text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full inline-block mt-0.5">
                              {inv.categoryName}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 text-xs whitespace-nowrap">
                            <div className="flex items-center gap-1.5">
                              <Calendar className="w-3.5 h-3.5 text-slate-500" />
                              <span>{inv.dueDate}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-right font-medium text-slate-300">
                            {schoolSettings.currencySymbol} {inv.totalAmount.toLocaleString()}
                          </td>
                          <td className="py-3.5 px-4 text-right text-purple-400 text-xs">
                            {inv.discountAmount > 0 ? `${schoolSettings.currencySymbol} ${inv.discountAmount.toLocaleString()}` : '—'}
                          </td>
                          <td className="py-3.5 px-4 text-right font-medium text-emerald-400">
                            {schoolSettings.currencySymbol} {inv.paidAmount.toLocaleString()}
                          </td>
                          <td className="py-3.5 px-4 text-right font-bold text-amber-400">
                            {schoolSettings.currencySymbol} {inv.dueAmount.toLocaleString()}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <span
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                isPaid
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                  : isPartial
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {isPaid && <CheckCircle className="w-3 h-3" />}
                              {isPartial && <Clock className="w-3 h-3" />}
                              {isUnpaid && <AlertCircle className="w-3 h-3" />}
                              <span>{inv.status}</span>
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1.5">
                              {inv.dueAmount > 0 && (
                                <button
                                  onClick={() => handleOpenPayment(inv)}
                                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition cursor-pointer flex items-center gap-1"
                                  title="Collect Payment"
                                >
                                  <CreditCard className="w-3.5 h-3.5" />
                                  <span>Collect</span>
                                </button>
                              )}
                              {inv.payments && inv.payments.length > 0 && (
                                <button
                                  onClick={() => {
                                    setSelectedReceiptPayment({ payment: inv.payments[0], invoice: inv });
                                    setShowReceiptModal(true);
                                  }}
                                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded text-xs transition cursor-pointer"
                                  title="Print Money Receipt"
                                >
                                  <Receipt className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: FEE STRUCTURES */}
      {activeTab === 'structures' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div>
              <h2 className="text-base font-semibold text-white">Class Fee Schedules</h2>
              <p className="text-xs text-slate-400">
                Pre-configured fee amounts mapped to academic classes, terms, and recurring billing cycles.
              </p>
            </div>
            <button
              onClick={() => setShowStructureModal(true)}
              className="flex items-center gap-2 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Fee Structure</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {structures.map((st) => (
              <div key={st.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
                <div className="flex items-start justify-between">
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {st.categoryName}
                  </span>
                  <span className="text-xs text-slate-400">{st.className}</span>
                </div>
                <h3 className="text-base font-bold text-white mt-2.5">{st.title}</h3>
                
                <div className="mt-4 flex items-baseline justify-between border-t border-slate-800/80 pt-3">
                  <div>
                    <span className="text-xs text-slate-500 block">Standard Amount</span>
                    <span className="text-xl font-bold text-white">
                      {schoolSettings.currencySymbol} {st.amount.toLocaleString()}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-500 block">Due Date</span>
                    <span className="text-xs font-medium text-slate-300">{st.dueDate}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <UserCheck className="w-3.5 h-3.5 text-slate-500" />
                    <span>{st.assignedCount} Enrolled Students</span>
                  </span>
                  <span className="text-slate-500 font-mono">ID: FS-{st.id.toString().padStart(4, '0')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: PAYMENT HISTORY & AUDIT RECEIPTS */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex justify-between items-center">
            <div>
              <h2 className="text-base font-semibold text-white">All Collected Transactions & Money Receipts</h2>
              <p className="text-xs text-slate-400">
                Official audit trail of fee voucher receipts issued with cashier timestamps and payment gateway channels.
              </p>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold text-xs border-b border-slate-800 uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Receipt #</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Student</th>
                    <th className="py-3 px-4">Fee Item</th>
                    <th className="py-3 px-4">Payment Method</th>
                    <th className="py-3 px-4 text-right">Amount Paid</th>
                    <th className="py-3 px-4 text-right">Waiver Applied</th>
                    <th className="py-3 px-4">Cashier / Staff</th>
                    <th className="py-3 px-4 text-right">Voucher</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {allPayments.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500">
                        No payment transactions recorded yet.
                      </td>
                    </tr>
                  ) : (
                    allPayments.map(({ payment: pmt, invoice: inv }) => (
                      <tr key={pmt.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3.5 px-4 font-mono font-semibold text-blue-400">
                          {pmt.receiptNumber}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 text-xs whitespace-nowrap">
                          {pmt.paymentDate}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-medium text-white">{inv.studentName}</div>
                          <div className="text-xs text-slate-400">{inv.className} &bull; Roll: {inv.rollNumber}</div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-300 text-xs">
                          {inv.feeTitle}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-200 border border-slate-700">
                            <CreditCard className="w-3 h-3 text-slate-400" />
                            <span>{pmt.paymentMethod}</span>
                          </span>
                          {pmt.transactionRef && (
                            <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                              Ref: {pmt.transactionRef}
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right font-bold text-emerald-400">
                          {schoolSettings.currencySymbol} {pmt.amount.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 text-right text-purple-400 text-xs">
                          {pmt.discountAmount > 0 ? `${schoolSettings.currencySymbol} ${pmt.discountAmount.toLocaleString()}` : '—'}
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-400">
                          {pmt.receivedBy}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedReceiptPayment({ payment: pmt, invoice: inv });
                              setShowReceiptModal(true);
                            }}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition cursor-pointer flex items-center gap-1 ml-auto"
                          >
                            <Printer className="w-3 h-3" />
                            <span>Receipt</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: COLLECT PAYMENT */}
      {showCollectModal && selectedInvoiceForPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">Fee Payment Collection</h3>
              </div>
              <button
                onClick={() => setShowCollectModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Student & Fee Snapshot */}
            <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3.5 text-xs space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-400">Student:</span>
                <span className="font-semibold text-white">
                  {selectedInvoiceForPayment.studentName} ({selectedInvoiceForPayment.studentCode})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Class & Section:</span>
                <span className="text-slate-200">
                  {selectedInvoiceForPayment.className} &bull; Roll: {selectedInvoiceForPayment.rollNumber}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Fee Item:</span>
                <span className="text-blue-400 font-medium">{selectedInvoiceForPayment.feeTitle}</span>
              </div>
              <div className="flex justify-between pt-1 border-t border-slate-800 text-sm">
                <span className="text-slate-300">Current Outstanding Due:</span>
                <span className="font-bold text-amber-400">
                  {schoolSettings.currencySymbol} {selectedInvoiceForPayment.dueAmount.toLocaleString()}
                </span>
              </div>
            </div>

            {paymentError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{paymentError}</span>
              </div>
            )}

            <form onSubmit={handleProcessPayment} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {/* Collection Amount */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Payment Amount ({schoolSettings.currencySymbol}) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={selectedInvoiceForPayment.dueAmount}
                    required
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-bold text-base focus:outline-none focus:border-emerald-500"
                  />
                </div>

                {/* Discount / Scholarship Waiver */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Scholarship / Waiver ({schoolSettings.currencySymbol})
                  </label>
                  <input
                    type="number"
                    min="0"
                    max={selectedInvoiceForPayment.dueAmount - paymentAmount}
                    value={paymentDiscount}
                    onChange={(e) => setPaymentDiscount(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-purple-400 font-medium text-base focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              {/* Payment Method */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Payment Method *</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
                  >
                    <option value="Cash">Cash</option>
                    <option value="bKash">bKash Merchant</option>
                    <option value="Nagad">Nagad</option>
                    <option value="Rocket">Rocket</option>
                    <option value="Bank Transfer">Bank Transfer</option>
                    <option value="Card">Debit / Credit Card</option>
                    <option value="Cheque">Cheque</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Trx ID / Bank Ref No.
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. BK789012, Cheque #4501"
                    value={transactionRef}
                    onChange={(e) => setTransactionRef(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Received By */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Received By / Cashier *</label>
                <input
                  type="text"
                  required
                  value={receivedBy}
                  onChange={(e) => setReceivedBy(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Voucher Notes / Memo</label>
                <input
                  type="text"
                  placeholder="Optional memo (e.g. 1st installment, clearance)"
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              {/* Live Preview Calculation */}
              <div className="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg text-xs space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span>Balance Due After This Transaction:</span>
                  <span className="font-bold text-white">
                    {schoolSettings.currencySymbol}{' '}
                    {Math.max(
                      0,
                      selectedInvoiceForPayment.dueAmount - (Number(paymentAmount) + Number(paymentDiscount))
                    ).toLocaleString()}
                  </span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  Unique receipt number will be generated automatically in audit compliance format.
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCollectModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold transition cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>Confirm & Print Receipt</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: NEW FEE STRUCTURE */}
      {showStructureModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-bold text-white">Create Fee Schedule & Structure</h3>
              </div>
              <button
                onClick={() => setShowStructureModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateStructure} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Fee Category *</label>
                <select
                  value={newStructCategory}
                  onChange={(e) => setNewStructCategory(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.frequency})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Target Class *</label>
                  <select
                    value={newStructClass}
                    onChange={(e) => setNewStructClass(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Class 9">Class 9</option>
                    <option value="Class 10">Class 10</option>
                    <option value="Class 8">Class 8</option>
                    <option value="Class 7">Class 7</option>
                    <option value="Class 6">Class 6</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Standard Fee Amount ({schoolSettings.currencySymbol}) *
                  </label>
                  <input
                    type="number"
                    min="10"
                    required
                    value={newStructAmount}
                    onChange={(e) => setNewStructAmount(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-bold text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Fee Title / Description</label>
                <input
                  type="text"
                  placeholder="e.g. Class 9 - Monthly Tuition (April 2025)"
                  value={newStructTitle}
                  onChange={(e) => setNewStructTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Default Due Date *</label>
                <input
                  type="date"
                  required
                  value={newStructDueDate}
                  onChange={(e) => setNewStructDueDate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-start gap-2.5">
                <input
                  type="checkbox"
                  id="autoAssignCheckbox"
                  checked={newStructAutoAssign}
                  onChange={(e) => setNewStructAutoAssign(e.target.checked)}
                  className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="autoAssignCheckbox" className="text-xs text-slate-300 cursor-pointer">
                  <span className="font-semibold text-white block">Auto-generate invoices for enrolled students</span>
                  Creates unpaid billing vouchers for every active student currently registered in this class.
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowStructureModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create Fee Structure</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: OFFICIAL PRINTABLE MONEY RECEIPT VOUCHER */}
      {showReceiptModal && selectedReceiptPayment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white text-slate-900 rounded-xl max-w-2xl w-full p-8 shadow-2xl space-y-6 my-8 animate-in fade-in duration-200 border-2 border-slate-200">
            {/* Action Bar */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 print:hidden">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
                Official Money Receipt &bull; Landscape Voucher
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition cursor-pointer"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Receipt</span>
                </button>
                <button
                  onClick={() => setShowReceiptModal(false)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Receipt Voucher Body (Styled like real school money receipt voucher) */}
            <div className="space-y-6">
              {/* School Header */}
              <div className="text-center space-y-1">
                <h2 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                  {schoolSettings.schoolName}
                </h2>
                {schoolSettings.schoolNameBn && (
                  <p className="text-sm font-medium text-slate-600">{schoolSettings.schoolNameBn}</p>
                )}
                <p className="text-xs text-slate-500">
                  {schoolSettings.address}, {schoolSettings.city} &bull; EIIN: {schoolSettings.eiinNumber} &bull; Tel: {schoolSettings.phone}
                </p>
                <div className="pt-2">
                  <span className="inline-block border-y-2 border-slate-900 px-6 py-0.5 text-xs font-black uppercase tracking-widest">
                    Student Fee Money Receipt
                  </span>
                </div>
              </div>

              {/* Receipt Metadata & Details */}
              <div className="grid grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div className="space-y-1.5">
                  <div>
                    <span className="text-slate-500">Receipt No:</span>{' '}
                    <strong className="font-mono text-slate-900 text-sm">
                      {selectedReceiptPayment.payment.receiptNumber}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Payment Date:</span>{' '}
                    <strong className="text-slate-800">{selectedReceiptPayment.payment.paymentDate}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Payment Channel:</span>{' '}
                    <strong className="text-slate-800">{selectedReceiptPayment.payment.paymentMethod}</strong>
                    {selectedReceiptPayment.payment.transactionRef && (
                      <span className="text-slate-600 block text-[11px] font-mono">
                        Trx Ref: {selectedReceiptPayment.payment.transactionRef}
                      </span>
                    )}
                  </div>
                </div>

                <div className="space-y-1.5 text-right">
                  <div>
                    <span className="text-slate-500">Student Name:</span>{' '}
                    <strong className="text-slate-900 text-sm">
                      {selectedReceiptPayment.invoice.studentName}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Student ID / Roll:</span>{' '}
                    <strong className="text-slate-800">
                      {selectedReceiptPayment.invoice.studentCode} (Roll: {selectedReceiptPayment.invoice.rollNumber})
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Class & Section:</span>{' '}
                    <strong className="text-slate-800">
                      {selectedReceiptPayment.invoice.className} &bull; {selectedReceiptPayment.invoice.sectionName || 'Main'}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Breakdown Table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-700 uppercase font-bold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">SL</th>
                      <th className="py-2.5 px-3">Fee Particulars</th>
                      <th className="py-2.5 px-3 text-right">Billed Amount</th>
                      <th className="py-2.5 px-3 text-right">Waiver</th>
                      <th className="py-2.5 px-3 text-right">Paid Today</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    <tr>
                      <td className="py-2.5 px-3 text-slate-500">01</td>
                      <td className="py-2.5 px-3">
                        <strong className="text-slate-900">{selectedReceiptPayment.invoice.feeTitle}</strong>
                        <span className="text-[11px] text-slate-500 block">
                          Category: {selectedReceiptPayment.invoice.categoryName}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                        {schoolSettings.currencySymbol} {selectedReceiptPayment.invoice.totalAmount.toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 text-right text-purple-700">
                        {selectedReceiptPayment.payment.discountAmount > 0
                          ? `${schoolSettings.currencySymbol} ${selectedReceiptPayment.payment.discountAmount.toLocaleString()}`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-emerald-700 text-sm">
                        {schoolSettings.currencySymbol} {selectedReceiptPayment.payment.amount.toLocaleString()}
                      </td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-slate-50 font-semibold border-t-2 border-slate-300 text-xs">
                    <tr>
                      <td colSpan={4} className="py-2 px-3 text-right text-slate-700">
                        Total Amount Received:
                      </td>
                      <td className="py-2 px-3 text-right text-emerald-800 font-bold text-base">
                        {schoolSettings.currencySymbol} {selectedReceiptPayment.payment.amount.toLocaleString()}
                      </td>
                    </tr>
                    <tr>
                      <td colSpan={4} className="py-1.5 px-3 text-right text-slate-600">
                        Remaining Due Balance:
                      </td>
                      <td className="py-1.5 px-3 text-right text-amber-700 font-bold">
                        {schoolSettings.currencySymbol} {selectedReceiptPayment.invoice.dueAmount.toLocaleString()}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Memo Note */}
              {selectedReceiptPayment.payment.notes && (
                <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200 italic">
                  Note: {selectedReceiptPayment.payment.notes}
                </div>
              )}

              {/* Signatures */}
              <div className="pt-12 grid grid-cols-2 text-center text-xs">
                <div>
                  <div className="w-48 mx-auto border-t border-slate-400 pt-1.5">
                    <p className="font-semibold text-slate-800">{selectedReceiptPayment.payment.receivedBy}</p>
                    <p className="text-[11px] text-slate-500">Cashier / Authorized Signature</p>
                  </div>
                </div>
                <div>
                  <div className="w-48 mx-auto border-t border-slate-400 pt-1.5">
                    <p className="font-semibold text-slate-800">{schoolSettings.principalName}</p>
                    <p className="text-[11px] text-slate-500">Principal / Head of Institution</p>
                  </div>
                </div>
              </div>

              <div className="text-center text-[10px] text-slate-400 pt-2 border-t border-slate-100">
                This is a computer-generated money receipt voucher issued by EduManage Pro. Valid without physical stamp if verified by EIIN {schoolSettings.eiinNumber}.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
