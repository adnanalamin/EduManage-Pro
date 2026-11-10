import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Plus,
  Search,
  Filter,
  Receipt,
  Printer,
  Calendar,
  Layers,
  Building,
  CheckCircle,
  AlertCircle,
  CreditCard,
  PieChart,
  Tag,
  X,
  Check,
  FileText,
  UserCheck,
  Scale
} from 'lucide-react';
import { storage } from '../services/storage';
import {
  AccountCategoryInfo,
  AccountTransactionRecord,
  FinancialSummary,
  SchoolSetting,
} from '../types';

interface AccountingManagementProps {
  currentUserRole?: string;
}

export const AccountingManagement: React.FC<AccountingManagementProps> = ({ currentUserRole }) => {
  const [activeTab, setActiveTab] = useState<'cashbook' | 'pnl' | 'categories'>('cashbook');

  // Data states
  const [transactions, setTransactions] = useState<AccountTransactionRecord[]>(() => storage.getAccountTransactions());
  const [categories, setCategories] = useState<AccountCategoryInfo[]>(() => storage.getAccountCategories());
  const [schoolSettings] = useState<SchoolSetting>(() => storage.getSchoolSettings());

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<'All' | 'Income' | 'Expense'>('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedMethod, setSelectedMethod] = useState('All');

  // Modals
  const [showVoucherModal, setShowVoucherModal] = useState(false);
  const [voucherModalType, setVoucherModalType] = useState<'Income' | 'Expense'>('Expense');
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showStatementModal, setShowStatementModal] = useState(false);
  const [showVoucherDetailModal, setShowVoucherDetailModal] = useState<AccountTransactionRecord | null>(null);

  // Form states for Voucher
  const [vchCategory, setVchCategory] = useState<number>(0);
  const [vchAmount, setVchAmount] = useState<number>(5000);
  const [vchDate, setVchDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [vchMethod, setVchMethod] = useState<AccountTransactionRecord['paymentMethod']>('Cash');
  const [vchRef, setVchRef] = useState('');
  const [vchParty, setVchParty] = useState('');
  const [vchDesc, setVchDesc] = useState('');
  const [vchError, setVchError] = useState<string | null>(null);

  // Form states for Category
  const [newCatName, setNewCatName] = useState('');
  const [newCatCode, setNewCatCode] = useState('');
  const [newCatType, setNewCatType] = useState<'Income' | 'Expense'>('Expense');
  const [newCatDesc, setNewCatDesc] = useState('');
  const [catError, setCatError] = useState<string | null>(null);

  const reloadData = () => {
    setTransactions(storage.getAccountTransactions());
    setCategories(storage.getAccountCategories());
  };

  // Financial KPIs
  const summary: FinancialSummary = useMemo(() => {
    return storage.getFinancialSummary();
  }, [transactions]);

  // Income & Expense breakdowns for P&L
  const incomeBreakdown = useMemo(() => {
    return storage.getAccountingCategoryBreakdown('Income');
  }, [transactions]);

  const expenseBreakdown = useMemo(() => {
    return storage.getAccountingCategoryBreakdown('Expense');
  }, [transactions]);

  // Filtered transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      const matchSearch =
        t.voucherNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.paidToReceivedFrom.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.categoryName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.referenceNo && t.referenceNo.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchType = selectedType === 'All' || t.type === selectedType;
      const matchCat = selectedCategory === 'All' || t.categoryName === selectedCategory;
      const matchMethod = selectedMethod === 'All' || t.paymentMethod === selectedMethod;

      return matchSearch && matchType && matchCat && matchMethod;
    });
  }, [transactions, searchQuery, selectedType, selectedCategory, selectedMethod]);

  // Open voucher modal
  const handleOpenVoucherModal = (type: 'Income' | 'Expense') => {
    setVoucherModalType(type);
    const availableCats = categories.filter((c) => c.type === type && c.isActive);
    if (availableCats.length > 0) {
      setVchCategory(availableCats[0].id);
    }
    setVchAmount(type === 'Expense' ? 3500 : 25000);
    setVchDate(new Date().toISOString().split('T')[0]);
    setVchMethod('Cash');
    setVchRef('');
    setVchParty('');
    setVchDesc('');
    setVchError(null);
    setShowVoucherModal(true);
  };

  // Save Voucher
  const handleSaveVoucher = (e: React.FormEvent) => {
    e.preventDefault();
    if (!vchParty.trim()) {
      setVchError('Please specify the recipient or payer party name.');
      return;
    }
    if (vchAmount <= 0) {
      setVchError('Transaction amount must be strictly greater than 0.');
      return;
    }

    try {
      const created = storage.recordAccountTransaction({
        type: voucherModalType,
        categoryId: Number(vchCategory),
        amount: Number(vchAmount),
        transactionDate: vchDate,
        paymentMethod: vchMethod,
        referenceNo: vchRef.trim() || undefined,
        paidToReceivedFrom: vchParty.trim(),
        description: vchDesc.trim() || undefined,
        recordedBy: 'Chief Accountant',
      });

      setShowVoucherModal(false);
      reloadData();
      setShowVoucherDetailModal(created);
    } catch (err: any) {
      setVchError(err.message || 'Failed to record transaction');
    }
  };

  // Save Category
  const handleSaveCategory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim() || !newCatCode.trim()) {
      setCatError('Both category name and code are required.');
      return;
    }

    try {
      storage.addAccountCategory({
        name: newCatName.trim(),
        code: newCatCode.trim().toUpperCase(),
        type: newCatType,
        description: newCatDesc.trim() || undefined,
        isSystem: false,
        isActive: true,
      });

      setShowCategoryModal(false);
      reloadData();
      setNewCatName('');
      setNewCatCode('');
      setNewCatDesc('');
    } catch (err: any) {
      setCatError(err.message || 'Failed to add account category');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">School Accounting & Expense Management</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Phase 7 Active
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Official cash book, operational expense vouchers, revenue receipts, and audited Profit &amp; Loss statements.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleOpenVoucherModal('Income')}
            className="flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold transition shadow-sm cursor-pointer"
          >
            <TrendingUp className="w-4 h-4" />
            <span>+ Add Income</span>
          </button>
          <button
            onClick={() => handleOpenVoucherModal('Expense')}
            className="flex items-center gap-2 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-semibold transition shadow-sm cursor-pointer"
          >
            <TrendingDown className="w-4 h-4" />
            <span>+ Record Expense</span>
          </button>
          <button
            onClick={() => setShowStatementModal(true)}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium transition cursor-pointer"
          >
            <FileText className="w-4 h-4 text-blue-400" />
            <span>Financial Statement</span>
          </button>
        </div>
      </div>

      {/* Financial KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Inflow */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Total Revenue Inflows</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">
              {schoolSettings.currencySymbol} {summary.totalIncome.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Student fees, grants &amp; endowments</p>
        </div>

        {/* Total Outflow */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Operational Expenditures</span>
            <div className="p-2 bg-rose-500/10 text-rose-400 rounded-lg">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-400">
              {schoolSettings.currencySymbol} {summary.totalExpense.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Salaries, utilities, stationery &amp; repairs</p>
        </div>

        {/* Net Operating Surplus / Deficit */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Net Operating Balance</span>
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
              <Scale className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold ${
                summary.isProfit ? 'text-blue-400' : 'text-rose-400'
              }`}
            >
              {schoolSettings.currencySymbol} {summary.netSurplus.toLocaleString()}
            </span>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded ${
                summary.isProfit
                  ? 'bg-emerald-500/10 text-emerald-300'
                  : 'bg-rose-500/10 text-rose-300'
              }`}
            >
              {summary.isProfit ? 'Surplus' : 'Deficit'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Operating margin:{' '}
            {summary.totalIncome > 0
              ? `${((summary.netSurplus / summary.totalIncome) * 100).toFixed(1)}%`
              : '0.0%'}
          </p>
        </div>

        {/* Cash-in-Hand */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-sm font-medium">
            <span>Cash-in-Hand Balance</span>
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-400">
              {schoolSettings.currencySymbol} {summary.cashInHand.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Liquid physical cash in vault</p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-800 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('cashbook')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition cursor-pointer ${
              activeTab === 'cashbook'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Receipt className="w-4 h-4" />
            <span>Cash Book &amp; Vouchers</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300">
              {transactions.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('pnl')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition cursor-pointer ${
              activeTab === 'pnl'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <PieChart className="w-4 h-4" />
            <span>Income &amp; Expense Breakdown</span>
          </button>

          <button
            onClick={() => setActiveTab('categories')}
            className={`flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 transition cursor-pointer ${
              activeTab === 'categories'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Chart of Accounts</span>
            <span className="px-2 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300">
              {categories.length}
            </span>
          </button>
        </div>
      </div>

      {/* TAB 1: CASH BOOK & VOUCHERS */}
      {activeTab === 'cashbook' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap gap-3 items-center justify-between">
            <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
              <div className="relative flex-1 min-w-[200px] max-w-md">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search voucher #, payee, reference, memo..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition"
                />
              </div>

              {/* Type Filter */}
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                <option value="All">All Types (Income &amp; Expense)</option>
                <option value="Income">Income Inflows Only</option>
                <option value="Expense">Expense Outflows Only</option>
              </select>

              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                <option value="All">All Account Heads</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name} ({c.type})
                  </option>
                ))}
              </select>

              {/* Method Filter */}
              <select
                value={selectedMethod}
                onChange={(e) => setSelectedMethod(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
              >
                <option value="All">All Payment Channels</option>
                <option value="Cash">Cash</option>
                <option value="Bank Transfer">Bank Transfer</option>
                <option value="bKash">bKash</option>
                <option value="Nagad">Nagad</option>
                <option value="Cheque">Cheque</option>
              </select>
            </div>

            <span className="text-xs text-slate-400">
              Showing <strong className="text-white">{filteredTransactions.length}</strong> of {transactions.length} vouchers
            </span>
          </div>

          {/* Transactions Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold text-xs border-b border-slate-800 uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Voucher No</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Account Head</th>
                    <th className="py-3 px-4">Party / Beneficiary</th>
                    <th className="py-3 px-4">Channel &amp; Ref</th>
                    <th className="py-3 px-4 text-right">Debit (Expense)</th>
                    <th className="py-3 px-4 text-right">Credit (Income)</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredTransactions.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500">
                        No financial vouchers found matching criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredTransactions.map((tx) => {
                      const isIncome = tx.type === 'Income';

                      return (
                        <tr key={tx.id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-mono font-semibold text-blue-400 text-xs">
                            {tx.voucherNo}
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 text-xs whitespace-nowrap">
                            <div className="flex items-center gap-1.5">
                              <Calendar className="w-3.5 h-3.5 text-slate-500" />
                              <span>{tx.transactionDate}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
                                isIncome
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              }`}
                            >
                              {isIncome ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                              <span>{tx.type}</span>
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-medium text-slate-200">{tx.categoryName}</div>
                            <span className="text-[10px] text-slate-500 font-mono">{tx.categoryCode}</span>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-white">{tx.paidToReceivedFrom}</div>
                            {tx.description && (
                              <div className="text-xs text-slate-400 truncate max-w-xs">{tx.description}</div>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="text-xs text-slate-300 font-medium">{tx.paymentMethod}</span>
                            {tx.referenceNo && (
                              <span className="text-[10px] text-slate-500 block font-mono">
                                Ref: {tx.referenceNo}
                              </span>
                            )}
                          </td>
                          {/* Debit (Expense) */}
                          <td className="py-3.5 px-4 text-right font-bold text-rose-400">
                            {!isIncome ? `${schoolSettings.currencySymbol} ${tx.amount.toLocaleString()}` : '—'}
                          </td>
                          {/* Credit (Income) */}
                          <td className="py-3.5 px-4 text-right font-bold text-emerald-400">
                            {isIncome ? `${schoolSettings.currencySymbol} ${tx.amount.toLocaleString()}` : '—'}
                          </td>
                          <td className="py-3.5 px-4 text-right whitespace-nowrap">
                            <button
                              onClick={() => setShowVoucherDetailModal(tx)}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded text-xs transition cursor-pointer flex items-center gap-1 ml-auto"
                            >
                              <Printer className="w-3 h-3" />
                              <span>Voucher</span>
                            </button>
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

      {/* TAB 2: P&L BREAKDOWN */}
      {activeTab === 'pnl' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Inflow Heads */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-base font-bold text-white">Revenue Inflow Breakdown</h3>
                </div>
                <span className="text-sm font-bold text-emerald-400">
                  {schoolSettings.currencySymbol} {summary.totalIncome.toLocaleString()}
                </span>
              </div>

              <div className="space-y-3">
                {incomeBreakdown.length === 0 ? (
                  <p className="text-xs text-slate-500 py-4 text-center">No revenue records found.</p>
                ) : (
                  incomeBreakdown.map((row) => {
                    const share =
                      summary.totalIncome > 0 ? (row.amount / summary.totalIncome) * 100 : 0;
                    return (
                      <div key={row.code} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-300 font-medium">
                            {row.category} <span className="text-slate-500 font-mono">({row.code})</span>
                          </span>
                          <span className="font-semibold text-white">
                            {schoolSettings.currencySymbol} {row.amount.toLocaleString()} ({share.toFixed(1)}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-emerald-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, share)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Expenditure Outflow Heads */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-rose-400" />
                  <h3 className="text-base font-bold text-white">Operational Expenditure Breakdown</h3>
                </div>
                <span className="text-sm font-bold text-rose-400">
                  {schoolSettings.currencySymbol} {summary.totalExpense.toLocaleString()}
                </span>
              </div>

              <div className="space-y-3">
                {expenseBreakdown.length === 0 ? (
                  <p className="text-xs text-slate-500 py-4 text-center">No expenditure records found.</p>
                ) : (
                  expenseBreakdown.map((row) => {
                    const share =
                      summary.totalExpense > 0 ? (row.amount / summary.totalExpense) * 100 : 0;
                    return (
                      <div key={row.code} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-300 font-medium">
                            {row.category} <span className="text-slate-500 font-mono">({row.code})</span>
                          </span>
                          <span className="font-semibold text-white">
                            {schoolSettings.currencySymbol} {row.amount.toLocaleString()} ({share.toFixed(1)}%)
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-rose-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, share)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CHART OF ACCOUNTS */}
      {activeTab === 'categories' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div>
              <h2 className="text-base font-semibold text-white">School Chart of Accounts (COA)</h2>
              <p className="text-xs text-slate-400">
                Standard revenue heads and expenditure accounts used for accounting audit compliance.
              </p>
            </div>
            <button
              onClick={() => {
                setCatError(null);
                setNewCatName('');
                setNewCatCode('');
                setNewCatDesc('');
                setShowCategoryModal(true);
              }}
              className="flex items-center gap-2 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ Add Account Category</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((c) => {
              const isIncome = c.type === 'Income';
              return (
                <div key={c.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
                  <div className="flex items-start justify-between">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        isIncome
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {c.type}
                    </span>
                    <span className="font-mono text-xs text-slate-400">{c.code}</span>
                  </div>
                  <h3 className="text-base font-bold text-white mt-2.5">{c.name}</h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{c.description || 'General school accounting head'}</p>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                    <span>{c.isSystem ? 'Standard System Head' : 'Custom Category'}</span>
                    <span className="text-emerald-400 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      <span>Active</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MODAL 1: RECORD TRANSACTION VOUCHER */}
      {showVoucherModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                {voucherModalType === 'Income' ? (
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-rose-400" />
                )}
                <h3 className="text-lg font-bold text-white">Record {voucherModalType} Voucher</h3>
              </div>
              <button
                onClick={() => setShowVoucherModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {vchError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{vchError}</span>
              </div>
            )}

            <form onSubmit={handleSaveVoucher} className="space-y-4">
              {/* Type Switcher */}
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setVoucherModalType('Income');
                    const incCats = categories.filter((c) => c.type === 'Income' && c.isActive);
                    if (incCats.length > 0) setVchCategory(incCats[0].id);
                  }}
                  className={`py-1.5 text-xs font-bold rounded transition cursor-pointer ${
                    voucherModalType === 'Income'
                      ? 'bg-emerald-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Revenue Inflow (Income)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setVoucherModalType('Expense');
                    const expCats = categories.filter((c) => c.type === 'Expense' && c.isActive);
                    if (expCats.length > 0) setVchCategory(expCats[0].id);
                  }}
                  className={`py-1.5 text-xs font-bold rounded transition cursor-pointer ${
                    voucherModalType === 'Expense'
                      ? 'bg-rose-600 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Expenditure Outflow (Expense)
                </button>
              </div>

              {/* Category */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Account Category Head *</label>
                <select
                  value={vchCategory}
                  onChange={(e) => setVchCategory(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                >
                  {categories
                    .filter((c) => c.type === voucherModalType && c.isActive)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code})
                      </option>
                    ))}
                </select>
              </div>

              {/* Amount & Date */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Amount ({schoolSettings.currencySymbol}) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={vchAmount}
                    onChange={(e) => setVchAmount(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-white font-bold text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Voucher Date *</label>
                  <input
                    type="date"
                    required
                    value={vchDate}
                    onChange={(e) => setVchDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Payment Channel & Ref */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Payment Method *</label>
                  <select
                    value={vchMethod}
                    onChange={(e) => setVchMethod(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="Cash">Cash</option>
                    <option value="Bank Transfer">Bank Transfer</option>
                    <option value="bKash">bKash</option>
                    <option value="Nagad">Nagad</option>
                    <option value="Cheque">Cheque</option>
                    <option value="Card">Card</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Reference / Slip #</label>
                  <input
                    type="text"
                    placeholder="e.g. Cheque #4501, TrxID"
                    value={vchRef}
                    onChange={(e) => setVchRef(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Payee / Payer */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  {voucherModalType === 'Income' ? 'Received From (Payer) *' : 'Paid To (Beneficiary / Vendor) *'}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DESCO, Kamal Hossain, Student Accounts Counter"
                  value={vchParty}
                  onChange={(e) => setVchParty(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Memo */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Particulars / Memo</label>
                <textarea
                  rows={2}
                  placeholder="Detailed explanation of the expense or receipt..."
                  value={vchDesc}
                  onChange={(e) => setVchDesc(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVoucherModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`flex items-center gap-2 px-5 py-2 text-white rounded-lg text-sm font-semibold transition cursor-pointer ${
                    voucherModalType === 'Income'
                      ? 'bg-emerald-600 hover:bg-emerald-500'
                      : 'bg-rose-600 hover:bg-rose-500'
                  }`}
                >
                  <Check className="w-4 h-4" />
                  <span>Confirm Voucher</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD CATEGORY */}
      {showCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white">Create Account Head</h3>
              <button
                onClick={() => setShowCategoryModal(false)}
                className="text-slate-400 hover:text-white transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {catError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{catError}</span>
              </div>
            )}

            <form onSubmit={handleSaveCategory} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Category Type *</label>
                <select
                  value={newCatType}
                  onChange={(e) => setNewCatType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="Expense">Expense Head</option>
                  <option value="Income">Revenue Income Head</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Category Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Science Laboratory Reagents"
                  value={newCatName}
                  onChange={(e) => setNewCatName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Account Code *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. EXP-LAB-01"
                  value={newCatCode}
                  onChange={(e) => setNewCatCode(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Purpose of this accounting category..."
                  value={newCatDesc}
                  onChange={(e) => setNewCatDesc(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCategoryModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition cursor-pointer"
                >
                  Create Head
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: VOUCHER PRINT PREVIEW */}
      {showVoucherDetailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white text-slate-900 rounded-xl max-w-xl w-full p-8 shadow-2xl space-y-6 my-8 animate-in fade-in duration-200 border-2 border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 print:hidden">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                Official Financial Debit/Credit Voucher
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition cursor-pointer"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Voucher</span>
                </button>
                <button
                  onClick={() => setShowVoucherDetailModal(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="space-y-6">
              {/* Header */}
              <div className="text-center space-y-1">
                <h2 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                  {schoolSettings.schoolName}
                </h2>
                <p className="text-xs text-slate-500">
                  {schoolSettings.address}, {schoolSettings.city} &bull; EIIN: {schoolSettings.eiinNumber} &bull; Tel: {schoolSettings.phone}
                </p>
                <div className="pt-2">
                  <span className="inline-block border-y-2 border-slate-900 px-6 py-0.5 text-xs font-black uppercase tracking-widest">
                    {showVoucherDetailModal.type === 'Income' ? 'Cash / Bank Credit Voucher' : 'Cash / Bank Debit Voucher'}
                  </span>
                </div>
              </div>

              {/* Voucher Meta */}
              <div className="grid grid-cols-2 gap-4 text-xs bg-slate-50 p-4 rounded-lg border border-slate-200">
                <div className="space-y-1.5">
                  <div>
                    <span className="text-slate-500">Voucher No:</span>{' '}
                    <strong className="font-mono text-slate-900 text-sm">
                      {showVoucherDetailModal.voucherNo}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Transaction Date:</span>{' '}
                    <strong className="text-slate-800">{showVoucherDetailModal.transactionDate}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Payment Channel:</span>{' '}
                    <strong className="text-slate-800">{showVoucherDetailModal.paymentMethod}</strong>
                    {showVoucherDetailModal.referenceNo && (
                      <span className="text-slate-600 block text-[11px] font-mono">
                        Ref: {showVoucherDetailModal.referenceNo}
                      </span>
                    )}
                  </div>
                </div>

                <div className="space-y-1.5 text-right">
                  <div>
                    <span className="text-slate-500">Account Head:</span>{' '}
                    <strong className="text-slate-900 text-sm">
                      {showVoucherDetailModal.categoryName}
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Head Code:</span>{' '}
                    <strong className="font-mono text-slate-800">{showVoucherDetailModal.categoryCode}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Party / Payee:</span>{' '}
                    <strong className="text-slate-800">{showVoucherDetailModal.paidToReceivedFrom}</strong>
                  </div>
                </div>
              </div>

              {/* Particulars & Amount */}
              <div className="border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex justify-between items-baseline border-b border-slate-200 pb-2">
                  <span className="text-xs font-bold text-slate-700 uppercase">Particulars / Details</span>
                  <span className="text-xs font-bold text-slate-700 uppercase">Amount</span>
                </div>
                <div className="flex justify-between items-start text-xs">
                  <p className="text-slate-800 max-w-sm">
                    {showVoucherDetailModal.description || `Payment regarding ${showVoucherDetailModal.categoryName}`}
                  </p>
                  <span className="text-lg font-bold text-slate-900">
                    {schoolSettings.currencySymbol} {showVoucherDetailModal.amount.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Signatures */}
              <div className="pt-12 grid grid-cols-3 text-center text-xs">
                <div>
                  <div className="w-32 mx-auto border-t border-slate-400 pt-1.5">
                    <p className="font-semibold text-slate-800">{showVoucherDetailModal.recordedBy}</p>
                    <p className="text-[11px] text-slate-500">Prepared By</p>
                  </div>
                </div>
                <div>
                  <div className="w-32 mx-auto border-t border-slate-400 pt-1.5">
                    <p className="font-semibold text-slate-800">Shafiqul Alam</p>
                    <p className="text-[11px] text-slate-500">Accountant</p>
                  </div>
                </div>
                <div>
                  <div className="w-32 mx-auto border-t border-slate-400 pt-1.5">
                    <p className="font-semibold text-slate-800">{schoolSettings.principalName}</p>
                    <p className="text-[11px] text-slate-500">Principal / Approved</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: OFFICIAL FINANCIAL STATEMENT MODAL */}
      {showStatementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white text-slate-900 rounded-xl max-w-3xl w-full p-8 shadow-2xl space-y-6 my-8 animate-in fade-in duration-200 border-2 border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 print:hidden">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
                Official Statement of Accounts &bull; ReportLab Architecture
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition cursor-pointer"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print Statement</span>
                </button>
                <button
                  onClick={() => setShowStatementModal(false)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 transition cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="space-y-6 text-xs">
              <div className="text-center space-y-1">
                <h2 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                  {schoolSettings.schoolName}
                </h2>
                <p className="text-xs text-slate-500">
                  EIIN: {schoolSettings.eiinNumber} &bull; {schoolSettings.address}, {schoolSettings.city}
                </p>
                <div className="pt-2">
                  <span className="inline-block border-y-2 border-slate-900 px-6 py-0.5 text-xs font-black uppercase tracking-widest">
                    Statement of Revenue, Expenditure &amp; Operating Surplus
                  </span>
                </div>
              </div>

              {/* KPI Summary Block */}
              <div className="grid grid-cols-4 gap-2 text-center bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-[11px] text-slate-500 block">Total Revenue</span>
                  <strong className="text-emerald-700 text-sm">
                    {schoolSettings.currencySymbol} {summary.totalIncome.toLocaleString()}
                  </strong>
                </div>
                <div>
                  <span className="text-[11px] text-slate-500 block">Total Expenditure</span>
                  <strong className="text-rose-700 text-sm">
                    {schoolSettings.currencySymbol} {summary.totalExpense.toLocaleString()}
                  </strong>
                </div>
                <div>
                  <span className="text-[11px] text-slate-500 block">Net Surplus / Deficit</span>
                  <strong className={summary.isProfit ? 'text-blue-700 text-sm' : 'text-rose-700 text-sm'}>
                    {schoolSettings.currencySymbol} {summary.netSurplus.toLocaleString()}
                  </strong>
                </div>
                <div>
                  <span className="text-[11px] text-slate-500 block">Cash-in-Hand Vault</span>
                  <strong className="text-amber-700 text-sm">
                    {schoolSettings.currencySymbol} {summary.cashInHand.toLocaleString()}
                  </strong>
                </div>
              </div>

              {/* Tables */}
              <div className="space-y-4">
                <div>
                  <h4 className="font-bold text-slate-800 text-xs mb-1.5 uppercase">1. Revenue Inflow Heads</h4>
                  <table className="w-full text-left border border-slate-200">
                    <thead className="bg-slate-100 font-bold border-b border-slate-200">
                      <tr>
                        <th className="p-2">Code</th>
                        <th className="p-2">Revenue Particulars</th>
                        <th className="p-2 text-right">Transactions</th>
                        <th className="p-2 text-right">Amount ({schoolSettings.currencySymbol})</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {incomeBreakdown.map((r) => (
                        <tr key={r.code}>
                          <td className="p-2 font-mono text-slate-600">{r.code}</td>
                          <td className="p-2 font-medium">{r.category}</td>
                          <td className="p-2 text-right">{r.count}</td>
                          <td className="p-2 text-right font-semibold text-emerald-700">
                            {r.amount.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-slate-50 font-bold">
                        <td colSpan={3} className="p-2 text-right">Subtotal Revenue:</td>
                        <td className="p-2 text-right text-emerald-800">
                          {summary.totalIncome.toLocaleString()}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 className="font-bold text-slate-800 text-xs mb-1.5 uppercase">2. Operational Expenditure Heads</h4>
                  <table className="w-full text-left border border-slate-200">
                    <thead className="bg-slate-100 font-bold border-b border-slate-200">
                      <tr>
                        <th className="p-2">Code</th>
                        <th className="p-2">Expenditure Particulars</th>
                        <th className="p-2 text-right">Vouchers</th>
                        <th className="p-2 text-right">Amount ({schoolSettings.currencySymbol})</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {expenseBreakdown.map((r) => (
                        <tr key={r.code}>
                          <td className="p-2 font-mono text-slate-600">{r.code}</td>
                          <td className="p-2 font-medium">{r.category}</td>
                          <td className="p-2 text-right">{r.count}</td>
                          <td className="p-2 text-right font-semibold text-rose-700">
                            {r.amount.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-slate-50 font-bold">
                        <td colSpan={3} className="p-2 text-right">Subtotal Expenditure:</td>
                        <td className="p-2 text-right text-rose-800">
                          {summary.totalExpense.toLocaleString()}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Signature Blocks */}
              <div className="pt-10 grid grid-cols-3 text-center">
                <div>
                  <div className="w-36 mx-auto border-t border-slate-400 pt-1">
                    <p className="font-semibold text-slate-800">Shafiqul Alam</p>
                    <p className="text-[10px] text-slate-500">Chief Accountant</p>
                  </div>
                </div>
                <div>
                  <div className="w-36 mx-auto border-t border-slate-400 pt-1">
                    <p className="font-semibold text-slate-800">Audit Committee</p>
                    <p className="text-[10px] text-slate-500">Internal Audit</p>
                  </div>
                </div>
                <div>
                  <div className="w-36 mx-auto border-t border-slate-400 pt-1">
                    <p className="font-semibold text-slate-800">{schoolSettings.principalName}</p>
                    <p className="text-[10px] text-slate-500">Principal / Headmaster</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
