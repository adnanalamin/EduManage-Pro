import React, { useState, useEffect, useMemo } from 'react';
import {
  BadgeCheck,
  Award,
  FileText,
  Printer,
  Plus,
  Search,
  ShieldCheck,
  ShieldAlert,
  CreditCard,
  CheckCircle2,
  X,
  Ban,
  Users,
  Sparkles,
} from 'lucide-react';
import { StorageService } from '../services/storage';
import {
  CertificateType,
  CertificateRecordInfo,
  CertificateStatsInfo,
  Student,
  Teacher,
  Staff,
  SchoolSetting,
} from '../types';

interface CertificateManagementProps {
  isDark?: boolean;
}

const CERTIFICATE_TYPES: CertificateType[] = [
  'Transfer Certificate',
  'Character Certificate',
  'Testimonial',
  'Bonafide Certificate',
  'Merit Certificate',
  'Staff Experience Letter',
];

export const CertificateManagement: React.FC<CertificateManagementProps> = ({ isDark = true }) => {
  const [activeTab, setActiveTab] = useState<'registry' | 'studio' | 'idcards'>('registry');
  const [certificates, setCertificates] = useState<CertificateRecordInfo[]>([]);
  const [stats, setStats] = useState<CertificateStatsInfo>(() => StorageService.getCertificateStats());
  const [schoolSetting, setSchoolSetting] = useState<SchoolSetting>(() => StorageService.getSchoolSettings());
  const [students, setStudents] = useState<Student[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [staffList, setStaffList] = useState<Staff[]>([]);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [idClassFilter, setIdClassFilter] = useState<string>('All');
  const [idCardMode, setIdCardMode] = useState<'students' | 'teachers'>('students');

  // Selected certificate for studio preview
  const [selectedCert, setSelectedCert] = useState<CertificateRecordInfo | null>(null);

  // Verification lookup
  const [verifyQuery, setVerifyQuery] = useState('');
  const [verifyResult, setVerifyResult] = useState<CertificateRecordInfo | null | 'NOT_FOUND'>(null);

  // Toast
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Issue Modal state
  const [showIssueModal, setShowIssueModal] = useState(false);
  const [issueForm, setIssueForm] = useState({
    certificateType: 'Bonafide Certificate' as CertificateType,
    recipientType: 'Student' as 'Student' | 'Teacher' | 'Staff',
    recipientId: 0,
    conductGrade: 'Exemplary',
    reasonOrPurpose: '',
    leavingDate: new Date().toISOString().split('T')[0],
    remarks: '',
    markStudentTransferred: false,
  });

  const loadData = () => {
    const allCerts = StorageService.getCertificates();
    setCertificates(allCerts);
    setStats(StorageService.getCertificateStats());
    setSchoolSetting(StorageService.getSchoolSettings());
    const stu = StorageService.getStudents();
    const tch = StorageService.getTeachers();
    const stf = StorageService.getStaff();
    setStudents(stu);
    setTeachers(tch);
    setStaffList(stf);
    if (!selectedCert && allCerts.length > 0) {
      setSelectedCert(allCerts[0]);
    }
    if (issueForm.recipientId === 0 && stu.length > 0) {
      setIssueForm((prev) => ({ ...prev, recipientId: stu[0].id }));
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 4000);
  };

  const filteredCertificates = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return certificates.filter((c) => {
      if (typeFilter !== 'All' && c.certificateType !== typeFilter) return false;
      if (statusFilter !== 'All' && c.status !== statusFilter) return false;
      if (!q) return true;
      return (
        c.certificateNumber.toLowerCase().includes(q) ||
        c.verificationCode.toLowerCase().includes(q) ||
        c.recipientName.toLowerCase().includes(q) ||
        c.recipientCode.toLowerCase().includes(q)
      );
    });
  }, [certificates, searchTerm, typeFilter, statusFilter]);

  const distinctClasses = useMemo(() => {
    const set = new Set(students.map((s) => s.className).filter(Boolean));
    return ['All', ...Array.from(set)];
  }, [students]);

  const filteredIdStudents = useMemo(() => {
    return students.filter((s) => idClassFilter === 'All' || s.className === idClassFilter);
  }, [students, idClassFilter]);

  const handleOpenIssueModal = () => {
    const defaultStuId = students[0]?.id || 0;
    setIssueForm({
      certificateType: 'Bonafide Certificate',
      recipientType: 'Student',
      recipientId: defaultStuId,
      conductGrade: 'Exemplary',
      reasonOrPurpose: '',
      leavingDate: new Date().toISOString().split('T')[0],
      remarks: '',
      markStudentTransferred: false,
    });
    setShowIssueModal(true);
  };

  const handleRecipientTypeChange = (nextType: 'Student' | 'Teacher' | 'Staff') => {
    let nextId = 0;
    if (nextType === 'Student' && students.length > 0) nextId = students[0].id;
    if (nextType === 'Teacher' && teachers.length > 0) nextId = teachers[0].id;
    if (nextType === 'Staff' && staffList.length > 0) nextId = staffList[0].id;
    setIssueForm((prev) => ({ ...prev, recipientType: nextType, recipientId: nextId }));
  };

  const handleSubmitIssue = (e: React.FormEvent) => {
    e.preventDefault();
    let recipientName = '';
    let recipientCode = '';
    let classOrDesignation = '';
    let fatherOrGuardian = 'N/A';

    if (issueForm.recipientType === 'Student') {
      const stu = students.find((s) => s.id === issueForm.recipientId);
      if (!stu) return;
      recipientName = stu.fullName;
      recipientCode = stu.studentId;
      classOrDesignation = `${stu.className} (Section ${stu.sectionName || 'A'}, Roll ${stu.rollNumber})`;
      fatherOrGuardian = stu.guardian?.fatherName || stu.guardian?.guardianName || 'N/A';
    } else if (issueForm.recipientType === 'Teacher') {
      const tch = teachers.find((t) => t.id === issueForm.recipientId);
      if (!tch) return;
      recipientName = tch.fullName;
      recipientCode = tch.teacherId;
      classOrDesignation = `${tch.designation} — ${tch.department}`;
    } else {
      const stf = staffList.find((st) => st.id === issueForm.recipientId);
      if (!stf) return;
      recipientName = stf.fullName;
      recipientCode = stf.staffId;
      classOrDesignation = `${stf.position} — ${stf.department}`;
    }

    const issued = StorageService.issueCertificate({
      certificateType: issueForm.certificateType,
      recipientType: issueForm.recipientType,
      studentId: issueForm.recipientType === 'Student' ? issueForm.recipientId : undefined,
      staffOrTeacherId: issueForm.recipientType !== 'Student' ? issueForm.recipientId : undefined,
      recipientName,
      recipientCode,
      classOrDesignation,
      fatherOrGuardian,
      leavingDate:
        issueForm.certificateType === 'Transfer Certificate' || issueForm.certificateType === 'Staff Experience Letter'
          ? issueForm.leavingDate
          : undefined,
      conductGrade: issueForm.conductGrade,
      reasonOrPurpose: issueForm.reasonOrPurpose.trim() || 'Official Academic Verification',
      remarks: issueForm.remarks.trim(),
      markStudentTransferred: issueForm.markStudentTransferred,
    });

    setShowIssueModal(false);
    setSelectedCert(issued);
    setActiveTab('studio');
    loadData();
    showToast(`Issued ${issued.certificateNumber} to ${issued.recipientName}`);
  };

  const handleRevoke = (cert: CertificateRecordInfo) => {
    const updated = StorageService.revokeCertificate(cert.id, 'Revoked via Certificate Center');
    if (updated) {
      if (selectedCert?.id === cert.id) setSelectedCert(updated);
      loadData();
      showToast(`Credential ${cert.certificateNumber} marked as Revoked`);
    }
  };

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    const found = StorageService.verifyCertificate(verifyQuery);
    setVerifyResult(found || 'NOT_FOUND');
  };

  const buildAttestationParagraphs = (cert: CertificateRecordInfo): string[] => {
    const issueStr = cert.issueDate;
    const leaveStr = cert.leavingDate || cert.issueDate;
    switch (cert.certificateType) {
      case 'Transfer Certificate':
        return [
          `This is to certify that ${cert.recipientName} (ID: ${cert.recipientCode}), Son/Daughter of ${cert.fatherOrGuardian}, was a bona fide student of this institution enrolled in ${cert.classOrDesignation}.`,
          `Having cleared all institutional dues and library obligations, he/she is granted an honorable Transfer Certificate effective ${leaveStr} (${cert.reasonOrPurpose}). His/Her moral character and academic conduct during tenure remained ${cert.conductGrade}.`,
        ];
      case 'Character Certificate':
        return [
          `This is to certify that ${cert.recipientName} (ID: ${cert.recipientCode}), Son/Daughter of ${cert.fatherOrGuardian}, is/was a regular student of ${cert.classOrDesignation} at this Academy.`,
          `To the best of our institutional knowledge and disciplinary records, he/she bears a ${cert.conductGrade} moral character and has upheld exemplary school discipline. Issued for ${cert.reasonOrPurpose}.`,
        ];
      case 'Testimonial':
        return [
          `We take immense pleasure in certifying that ${cert.recipientName} (ID: ${cert.recipientCode}), ward of ${cert.fatherOrGuardian}, successfully pursued studies in ${cert.classOrDesignation}.`,
          `He/She demonstrated ${cert.conductGrade} diligence, scholarly discipline, and leadership in co-curricular pursuits. This official testimonial is awarded on ${issueStr} for ${cert.reasonOrPurpose}.`,
        ];
      case 'Merit Certificate':
        return [
          `This Certificate of Academic & Co-Curricular Merit is proudly conferred upon ${cert.recipientName} (ID: ${cert.recipientCode}) of ${cert.classOrDesignation} in recognition of outstanding achievement in: ${cert.reasonOrPurpose}.`,
          `Awarded on ${issueStr} for exemplary dedication, innovation, and ${cert.conductGrade} conduct.`,
        ];
      case 'Staff Experience Letter':
        return [
          `This is to certify that ${cert.recipientName} (Employee ID: ${cert.recipientCode}) served our institution with distinction in the capacity of ${cert.classOrDesignation}.`,
          `Throughout his/her tenure up to ${leaveStr}, his/her professional integrity, pedagogical commitment, and workplace conduct remained ${cert.conductGrade}. Issued upon request for ${cert.reasonOrPurpose}.`,
        ];
      default:
        return [
          `This is to certify that ${cert.recipientName} (ID: ${cert.recipientCode}), Son/Daughter of ${cert.fatherOrGuardian}, is a bona fide full-time student currently enrolled in ${cert.classOrDesignation} for the active academic session.`,
          `His/Her attendance standing and conduct are verified as ${cert.conductGrade}. Issued on ${issueStr} specifically for ${cert.reasonOrPurpose}.`,
        ];
    }
  };

  const cardBg = isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200';
  const subCardBg = isDark ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200';
  const textPrimary = isDark ? 'text-white' : 'text-slate-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-slate-500';
  const inputBg = isDark
    ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-400'
    : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400';

  return (
    <div className="space-y-6">
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-xl border border-emerald-500 text-sm font-medium">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/15 text-amber-500 border border-amber-500/20">
            <BadgeCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className={`text-2xl font-bold tracking-tight ${textPrimary}`}>
              Certificate, Credential & ID Card Center
            </h1>
            <p className={`text-sm ${textMuted}`}>
              Transfer Certificates, Testimonials, Merit Citations, Verification Tokens & Bulk CR80 ID Cards
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setActiveTab('idcards')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg border text-sm font-medium transition-colors ${
              isDark
                ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <CreditCard className="w-4 h-4 text-blue-500" />
            Bulk ID Card Studio
          </button>
          <button
            onClick={handleOpenIssueModal}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Issue New Certificate
          </button>
        </div>
      </div>

      {/* 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-blue-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Active Issued</span>
            <FileText className="w-4 h-4 text-blue-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{stats.issued}</div>
          <div className={`text-xs mt-1 ${textMuted}`}>{stats.total} total registered records</div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-amber-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Transfer Certificates</span>
            <BadgeCheck className="w-4 h-4 text-amber-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{stats.transferCertificates}</div>
          <div className={`text-xs mt-1 ${textMuted}`}>Alumni & leaving clearances</div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-emerald-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Merit & Testimonials</span>
            <Award className="w-4 h-4 text-emerald-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{stats.meritAndTestimonials}</div>
          <div className={`text-xs mt-1 text-emerald-500 font-medium`}>Verified with QR/Serial Tokens</div>
        </div>

        <div className={`p-4 rounded-xl border ${cardBg} border-l-4 border-l-rose-500`}>
          <div className="flex items-center justify-between">
            <span className={`text-xs font-semibold uppercase tracking-wider ${textMuted}`}>Revoked Credentials</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className={`text-2xl font-bold mt-2 ${textPrimary}`}>{stats.revoked}</div>
          <div className={`text-xs mt-1 ${textMuted}`}>Invalidated in verification ledger</div>
        </div>
      </div>

      {/* Tabs */}
      <div className={`flex flex-wrap gap-2 border-b pb-3 ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        {[
          { id: 'registry', label: 'Certificate Issuance & Registry', icon: FileText },
          { id: 'studio', label: 'Ornamental Certificate Studio (A4)', icon: Sparkles },
          { id: 'idcards', label: 'Bulk CR80 ID Cards & Verifier', icon: CreditCard },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                active
                  ? 'bg-blue-600 text-white shadow-sm'
                  : isDark
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/70'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: REGISTRY */}
      {activeTab === 'registry' && (
        <div className="space-y-4">
          <div className={`p-4 rounded-xl border flex flex-col md:flex-row gap-3 ${cardBg}`}>
            <div className="relative flex-1">
              <Search className={`w-4 h-4 absolute left-3 top-2.5 ${textMuted}`} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by serial (CERT-...), verify token (VER-...), name or student ID..."
                className={`w-full pl-9 pr-3 py-2 rounded-lg border text-sm ${inputBg}`}
              />
            </div>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className={`px-3 py-2 rounded-lg border text-sm ${inputBg}`}
            >
              <option value="All">All Certificate Types</option>
              {CERTIFICATE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className={`px-3 py-2 rounded-lg border text-sm ${inputBg}`}
            >
              <option value="All">All Statuses</option>
              <option value="Issued">Issued</option>
              <option value="Revoked">Revoked</option>
            </select>
          </div>

          <div className={`rounded-xl border overflow-hidden ${cardBg}`}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className={isDark ? 'bg-slate-800/80 text-slate-300' : 'bg-slate-100 text-slate-700'}>
                  <tr>
                    <th className="px-4 py-3 font-semibold">Serial Number</th>
                    <th className="px-4 py-3 font-semibold">Type</th>
                    <th className="px-4 py-3 font-semibold">Recipient</th>
                    <th className="px-4 py-3 font-semibold">Class / Designation</th>
                    <th className="px-4 py-3 font-semibold">Issue Date</th>
                    <th className="px-4 py-3 font-semibold">Verify Token</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className={`divide-y ${isDark ? 'divide-slate-800' : 'divide-slate-200'}`}>
                  {filteredCertificates.map((cert) => (
                    <tr key={cert.id} className={isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'}>
                      <td className="px-4 py-3 font-mono text-xs text-blue-400 font-semibold">
                        {cert.certificateNumber}
                      </td>
                      <td className={`px-4 py-3 font-medium ${textPrimary}`}>{cert.certificateType}</td>
                      <td className="px-4 py-3">
                        <div className={`font-semibold ${textPrimary}`}>{cert.recipientName}</div>
                        <div className={`text-xs ${textMuted}`}>{cert.recipientCode}</div>
                      </td>
                      <td className={`px-4 py-3 text-xs ${textMuted}`}>{cert.classOrDesignation}</td>
                      <td className={`px-4 py-3 text-xs ${textMuted}`}>{cert.issueDate}</td>
                      <td className="px-4 py-3 font-mono text-xs text-amber-400">{cert.verificationCode}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            cert.status === 'Issued'
                              ? 'bg-emerald-500/15 text-emerald-400'
                              : 'bg-rose-500/15 text-rose-400'
                          }`}
                        >
                          {cert.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => {
                              setSelectedCert(cert);
                              setActiveTab('studio');
                            }}
                            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium inline-flex items-center gap-1"
                          >
                            <Printer className="w-3.5 h-3.5" />
                            Preview
                          </button>
                          {cert.status === 'Issued' && (
                            <button
                              onClick={() => handleRevoke(cert)}
                              className="px-2.5 py-1 rounded bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 text-xs font-medium inline-flex items-center gap-1"
                            >
                              <Ban className="w-3.5 h-3.5" />
                              Revoke
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ORNAMENTAL CERTIFICATE STUDIO (LANDSCAPE A4) */}
      {activeTab === 'studio' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <label className={`text-xs font-semibold ${textMuted}`}>Select Credential:</label>
              <select
                value={selectedCert?.id ?? ''}
                onChange={(e) => {
                  const target = certificates.find((c) => c.id === Number(e.target.value));
                  if (target) setSelectedCert(target);
                }}
                className={`px-3 py-2 rounded-lg border text-sm ${inputBg}`}
              >
                {certificates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.certificateNumber} — {c.recipientName} ({c.certificateType})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold"
            >
              <Printer className="w-4 h-4" />
              Print / Export Landscape A4 PDF
            </button>
          </div>

          {selectedCert && (
            <div className="bg-[#FFFDF7] text-slate-900 rounded-xl shadow-2xl max-w-5xl mx-auto p-5 border border-slate-300">
              {/* Double Ornamental Frame */}
              <div className="border-4 border-blue-950 p-2 relative">
                <div className="border-2 border-amber-600 p-8 md:p-10 relative space-y-6">
                  {/* Corner Gold Accents */}
                  <div className="w-3 h-3 rounded-full bg-amber-600 absolute -top-1.5 -left-1.5" />
                  <div className="w-3 h-3 rounded-full bg-amber-600 absolute -top-1.5 -right-1.5" />
                  <div className="w-3 h-3 rounded-full bg-amber-600 absolute -bottom-1.5 -left-1.5" />
                  <div className="w-3 h-3 rounded-full bg-amber-600 absolute -bottom-1.5 -right-1.5" />

                  {/* Serial Header */}
                  <div className="flex justify-between text-[11px] font-bold font-mono text-slate-600">
                    <span>SERIAL NO: {selectedCert.certificateNumber}</span>
                    <span>VERIFY TOKEN: {selectedCert.verificationCode}</span>
                  </div>

                  {/* School Header */}
                  <div className="text-center space-y-1">
                    <h2 className="text-2xl md:text-3xl font-extrabold text-blue-950 tracking-wide uppercase">
                      {schoolSetting.schoolName}
                    </h2>
                    <p className="text-xs italic text-slate-600">
                      {schoolSetting.motto} &bull; EIIN: {schoolSetting.eiinNumber} &bull; {schoolSetting.address}
                    </p>
                  </div>

                  {/* Ribbon Title */}
                  <div className="flex justify-center">
                    <div className="bg-blue-950 text-amber-200 px-8 py-2.5 rounded-md font-bold text-lg tracking-widest uppercase shadow-md border border-amber-500/40">
                      {selectedCert.certificateType}
                    </div>
                  </div>

                  {selectedCert.status === 'Revoked' && (
                    <div className="text-center">
                      <span className="inline-block px-4 py-1 bg-rose-600 text-white font-extrabold text-xs tracking-widest rounded uppercase">
                        REVOKED / INVALIDATED CREDENTIAL
                      </span>
                    </div>
                  )}

                  {/* Recipient Name */}
                  <div className="text-center space-y-2 pt-2">
                    <div className="text-xs font-bold uppercase tracking-widest text-slate-500">
                      To Whom It May Concern
                    </div>
                    <div className="text-3xl md:text-4xl font-serif italic font-bold text-slate-900 border-b-2 border-amber-500 inline-block pb-1 px-8">
                      {selectedCert.recipientName}
                    </div>
                  </div>

                  {/* Attestation Paragraphs */}
                  <div className="max-w-3xl mx-auto text-center font-serif text-base leading-relaxed text-slate-800 space-y-3">
                    {buildAttestationParagraphs(selectedCert).map((p, i) => (
                      <p key={i}>{p}</p>
                    ))}
                    {selectedCert.remarks && (
                      <p className="text-xs italic text-slate-500 pt-1">Note: {selectedCert.remarks}</p>
                    )}
                  </div>

                  {/* Footer Seal & Signatures */}
                  <div className="grid grid-cols-3 items-end gap-6 pt-8">
                    <div className="text-center">
                      <div className="border-t border-slate-500 pt-2 text-xs font-bold text-slate-900">
                        Academic Registrar / Office
                      </div>
                      <div className="text-[11px] text-slate-500">Issued Date: {selectedCert.issueDate}</div>
                    </div>

                    <div className="flex justify-center">
                      <div className="w-20 h-20 rounded-full border-2 border-amber-700 bg-amber-100 flex flex-col items-center justify-center text-amber-900 shadow-inner">
                        <span className="text-[9px] font-extrabold tracking-wider">OFFICIAL</span>
                        <span className="text-[8px] font-bold">INSTITUTE SEAL</span>
                      </div>
                    </div>

                    <div className="text-center">
                      <div className="border-t border-slate-500 pt-2 text-xs font-bold text-slate-900">
                        {schoolSetting.principalName}
                      </div>
                      <div className="text-[11px] text-slate-500">Principal & Head of Institution</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: BULK CR80 ID CARD STUDIO & VERIFICATION */}
      {activeTab === 'idcards' && (
        <div className="space-y-6">
          {/* Live Credential Verifier */}
          <div className={`p-5 rounded-xl border ${cardBg} space-y-3`}>
            <h3 className={`text-base font-bold flex items-center gap-2 ${textPrimary}`}>
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              Instant Credential Serial & Token Verification
            </h3>
            <form onSubmit={handleVerify} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={verifyQuery}
                onChange={(e) => setVerifyQuery(e.target.value)}
                placeholder="Enter Certificate Serial (e.g. CERT-BF-2026-0001) or Token (e.g. VER-8A41D9C2)..."
                className={`flex-1 px-3.5 py-2 rounded-lg border text-sm font-mono ${inputBg}`}
              />
              <button
                type="submit"
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold"
              >
                Verify Authenticity
              </button>
            </form>

            {verifyResult === 'NOT_FOUND' && (
              <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 text-sm font-medium">
                Credential not found in institutional registry. Please verify the serial number.
              </div>
            )}
            {verifyResult && verifyResult !== 'NOT_FOUND' && (
              <div
                className={`p-4 rounded-lg border text-sm ${
                  verifyResult.status === 'Issued'
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                }`}
              >
                <div className="font-bold">
                  Status: {verifyResult.status.toUpperCase()} — {verifyResult.certificateType}
                </div>
                <div className="text-xs mt-1 space-y-0.5">
                  <div>
                    Serial: <span className="font-mono">{verifyResult.certificateNumber}</span> | Token:{' '}
                    <span className="font-mono">{verifyResult.verificationCode}</span>
                  </div>
                  <div>
                    Recipient: <strong>{verifyResult.recipientName}</strong> ({verifyResult.recipientCode}) —{' '}
                    {verifyResult.classOrDesignation}
                  </div>
                  <div>
                    Issued: {verifyResult.issueDate} | Conduct: {verifyResult.conductGrade}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bulk CR80 PVC ID Card Grid */}
          <div className={`p-5 rounded-xl border ${cardBg} space-y-4`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-blue-500" />
                <div>
                  <h3 className={`text-base font-bold ${textPrimary}`}>
                    Batch CR80 PVC Identity Card Print Sheet (85.6mm × 54mm)
                  </h3>
                  <p className={`text-xs ${textMuted}`}>
                    Matches Python ReportLab <code className="text-blue-400">generate_batch_student_id_sheet</code>
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="flex rounded-lg overflow-hidden border border-slate-700 text-xs font-semibold">
                  <button
                    onClick={() => setIdCardMode('students')}
                    className={`px-3 py-1.5 ${
                      idCardMode === 'students' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    Students ({students.length})
                  </button>
                  <button
                    onClick={() => setIdCardMode('teachers')}
                    className={`px-3 py-1.5 ${
                      idCardMode === 'teachers' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    Faculty ({teachers.length})
                  </button>
                </div>

                {idCardMode === 'students' && (
                  <select
                    value={idClassFilter}
                    onChange={(e) => setIdClassFilter(e.target.value)}
                    className={`px-3 py-1.5 rounded-lg border text-xs ${inputBg}`}
                  >
                    {distinctClasses.map((cls) => (
                      <option key={cls} value={cls}>
                        {cls === 'All' ? 'All Classes' : cls}
                      </option>
                    ))}
                  </select>
                )}

                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold"
                >
                  <Printer className="w-3.5 h-3.5" />
                  Print Sheet
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {idCardMode === 'students'
                ? filteredIdStudents.map((stu) => (
                    <div
                      key={stu.id}
                      className="bg-white text-slate-900 rounded-xl shadow-lg border border-slate-300 overflow-hidden flex flex-col justify-between"
                    >
                      <div className="bg-blue-900 text-white px-4 py-2 text-center">
                        <div className="text-xs font-bold truncate">{schoolSetting.schoolName}</div>
                        <div className="text-[9px] tracking-widest uppercase text-blue-200">
                          Student Identity Card
                        </div>
                      </div>

                      <div className="p-4 flex gap-3.5 items-center">
                        <div className="w-16 h-20 rounded border border-slate-300 bg-slate-100 flex flex-col items-center justify-center shrink-0 text-[10px] font-bold text-slate-500">
                          <span>PHOTO</span>
                          <span className="text-[9px] font-normal">#{stu.rollNumber}</span>
                        </div>
                        <div className="min-w-0 flex-1 space-y-0.5 text-[11px]">
                          <div className="font-bold text-sm text-slate-950 truncate">{stu.fullName}</div>
                          <div className="font-mono text-blue-700 font-semibold">ID: {stu.studentId}</div>
                          <div>
                            Class: <strong>{stu.className}</strong> | Sec: <strong>{stu.sectionName || 'A'}</strong>
                          </div>
                          <div>
                            Roll: <strong>{stu.rollNumber}</strong> | Blood:{' '}
                            <strong className="text-rose-600">{stu.bloodGroup || 'N/A'}</strong>
                          </div>
                          <div className="truncate text-slate-600">
                            Guardian: {stu.guardian?.guardianName || 'N/A'}
                          </div>
                          <div className="font-mono text-[10px] text-slate-600">
                            Tel: {stu.guardian?.guardianPhone || 'N/A'}
                          </div>
                        </div>
                      </div>

                      <div className="bg-slate-900 text-white px-3 py-1.5 flex items-center justify-between text-[9px]">
                        <span>Adm: {stu.admissionNumber}</span>
                        <span>Principal Signature</span>
                      </div>
                    </div>
                  ))
                : teachers.map((tch) => (
                    <div
                      key={tch.id}
                      className="bg-white text-slate-900 rounded-xl shadow-lg border border-slate-300 overflow-hidden flex flex-col justify-between"
                    >
                      <div className="bg-emerald-800 text-white px-4 py-2 text-center">
                        <div className="text-xs font-bold truncate">{schoolSetting.schoolName}</div>
                        <div className="text-[9px] tracking-widest uppercase text-emerald-200">
                          Faculty Identity Card
                        </div>
                      </div>

                      <div className="p-4 flex gap-3.5 items-center">
                        <div className="w-16 h-20 rounded border border-slate-300 bg-slate-100 flex flex-col items-center justify-center shrink-0 text-[10px] font-bold text-slate-500">
                          <span>FACULTY</span>
                        </div>
                        <div className="min-w-0 flex-1 space-y-0.5 text-[11px]">
                          <div className="font-bold text-sm text-slate-950 truncate">{tch.fullName}</div>
                          <div className="font-mono text-emerald-700 font-semibold">ID: {tch.teacherId}</div>
                          <div className="font-semibold text-slate-700">{tch.designation}</div>
                          <div>Dept: {tch.department}</div>
                          <div>Subject: {tch.primarySubject}</div>
                          <div className="font-mono text-[10px] text-slate-600">Tel: {tch.phone}</div>
                        </div>
                      </div>

                      <div className="bg-slate-900 text-white px-3 py-1.5 flex items-center justify-between text-[9px]">
                        <span>Emp: {tch.employeeId}</span>
                        <span>Authorized Faculty Pass</span>
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        </div>
      )}

      {/* ISSUE CERTIFICATE MODAL */}
      {showIssueModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-lg rounded-2xl border shadow-2xl overflow-hidden ${cardBg}`}>
            <div className={`px-5 py-4 border-b flex items-center justify-between ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
              <h3 className={`font-bold text-base flex items-center gap-2 ${textPrimary}`}>
                <BadgeCheck className="w-5 h-5 text-blue-500" />
                Issue Official Certificate
              </h3>
              <button onClick={() => setShowIssueModal(false)} className={`p-1 rounded-lg ${textMuted} hover:text-white`}>
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitIssue} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Certificate Type</label>
                  <select
                    value={issueForm.certificateType}
                    onChange={(e) => {
                      const next = e.target.value as CertificateType;
                      setIssueForm((prev) => ({
                        ...prev,
                        certificateType: next,
                      }));
                      if (next === 'Staff Experience Letter' && issueForm.recipientType === 'Student') {
                        handleRecipientTypeChange('Teacher');
                      }
                    }}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                  >
                    {CERTIFICATE_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Recipient Category</label>
                  <select
                    value={issueForm.recipientType}
                    onChange={(e) => handleRecipientTypeChange(e.target.value as 'Student' | 'Teacher' | 'Staff')}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                  >
                    <option value="Student">Student</option>
                    <option value="Teacher">Teacher</option>
                    <option value="Staff">Staff</option>
                  </select>
                </div>
              </div>

              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Select Recipient</label>
                <select
                  value={issueForm.recipientId}
                  onChange={(e) => setIssueForm((prev) => ({ ...prev, recipientId: Number(e.target.value) }))}
                  className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                >
                  {issueForm.recipientType === 'Student' &&
                    students.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.fullName} ({s.studentId} — {s.className})
                      </option>
                    ))}
                  {issueForm.recipientType === 'Teacher' &&
                    teachers.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.fullName} ({t.teacherId} — {t.designation})
                      </option>
                    ))}
                  {issueForm.recipientType === 'Staff' &&
                    staffList.map((st) => (
                      <option key={st.id} value={st.id}>
                        {st.fullName} ({st.staffId} — {st.position})
                      </option>
                    ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Conduct / Standing</label>
                  <select
                    value={issueForm.conductGrade}
                    onChange={(e) => setIssueForm((prev) => ({ ...prev, conductGrade: e.target.value }))}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                  >
                    <option value="Exemplary">Exemplary</option>
                    <option value="Very Good">Very Good</option>
                    <option value="Good">Good</option>
                    <option value="Satisfactory">Satisfactory</option>
                  </select>
                </div>

                <div>
                  <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Effective / Leaving Date</label>
                  <input
                    type="date"
                    value={issueForm.leavingDate}
                    onChange={(e) => setIssueForm((prev) => ({ ...prev, leavingDate: e.target.value }))}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                  />
                </div>
              </div>

              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Purpose / Achievement</label>
                <input
                  type="text"
                  required
                  value={issueForm.reasonOrPurpose}
                  onChange={(e) => setIssueForm((prev) => ({ ...prev, reasonOrPurpose: e.target.value }))}
                  placeholder="e.g. Higher Secondary Admission / Science Fair 1st Prize"
                  className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                />
              </div>

              {issueForm.certificateType === 'Transfer Certificate' && issueForm.recipientType === 'Student' && (
                <label className="flex items-center gap-2 text-xs text-amber-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={issueForm.markStudentTransferred}
                    onChange={(e) =>
                      setIssueForm((prev) => ({ ...prev, markStudentTransferred: e.target.checked }))
                    }
                    className="rounded"
                  />
                  <span>Update student enrollment status to &quot;Transferred&quot;</span>
                </label>
              )}

              <div>
                <label className={`block text-xs font-semibold mb-1 ${textMuted}`}>Official Remarks (Optional)</label>
                <textarea
                  rows={2}
                  value={issueForm.remarks}
                  onChange={(e) => setIssueForm((prev) => ({ ...prev, remarks: e.target.value }))}
                  placeholder="Optional registrar citation..."
                  className={`w-full px-3 py-2 rounded-lg border text-sm ${inputBg}`}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIssueModal(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    isDark ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold"
                >
                  Issue & Sign Certificate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
