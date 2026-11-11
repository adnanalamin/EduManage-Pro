import React, { useState, useEffect } from 'react';
import {
  Building2,
  Bed,
  Users,
  Key,
  ShieldCheck,
  Plus,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  Printer,
  Download,
  FileSpreadsheet,
  AlertTriangle,
  RefreshCw,
  Calendar,
  Phone,
  Home,
  UserCheck,
  Compass,
} from 'lucide-react';
import { StorageService } from '../services/storage';
import {
  HostelBlockInfo,
  HostelRoomInfo,
  HostelAllocationInfo,
  HostelGatePassInfo,
  HostelStatsInfo,
  Student,
} from '../types';

export const HostelManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'rooms' | 'allocations' | 'gatepasses' | 'passes'>('rooms');

  // Datasets
  const [blocks, setBlocks] = useState<HostelBlockInfo[]>([]);
  const [rooms, setRooms] = useState<HostelRoomInfo[]>([]);
  const [allocations, setAllocations] = useState<HostelAllocationInfo[]>([]);
  const [gatePasses, setGatePasses] = useState<HostelGatePassInfo[]>([]);
  const [stats, setStats] = useState<HostelStatsInfo>({
    totalBlocks: 0,
    totalRooms: 0,
    totalCapacity: 0,
    occupiedBeds: 0,
    availableBeds: 0,
    occupancyRate: 0,
    boardersOut: 0,
    presentInHostel: 0,
  });
  const [students, setStudents] = useState<Student[]>([]);

  // Filtering & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBlockFilter, setSelectedBlockFilter] = useState<string>('all');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all');

  // Modals
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [showRoomModal, setShowRoomModal] = useState(false);
  const [showAllocModal, setShowAllocModal] = useState(false);
  const [showPassModal, setShowPassModal] = useState(false);
  const [showRollCallModal, setShowRollCallModal] = useState(false);

  // Form State - Block
  const [blockForm, setBlockForm] = useState({
    blockName: '',
    genderType: 'Boys' as 'Boys' | 'Girls' | 'Co-ed',
    wardenName: '',
    wardenPhone: '',
    address: '',
    totalFloors: 3,
    status: 'Active' as 'Active' | 'Maintenance',
  });

  // Form State - Room
  const [roomForm, setRoomForm] = useState({
    blockId: 1,
    roomNumber: '',
    floorNumber: 1,
    roomType: 'Double' as 'Single' | 'Double' | 'Triple' | '4-Bed Dorm' | '6-Bed Dorm',
    capacity: 2,
    monthlyFee: 3000,
    amenities: 'Attached Bath, Study Table, Wi-Fi',
    status: 'Available' as 'Available' | 'Full' | 'Maintenance',
  });

  // Form State - Allocation
  const [allocForm, setAllocForm] = useState({
    roomId: 1,
    studentId: 1,
    bedNumber: 'Bed-1',
    admissionDate: new Date().toISOString().split('T')[0],
    guardianContact: '',
    emergencyPhone: '',
    remarks: '',
  });

  // Form State - Gate Pass
  const [gatePassForm, setGatePassForm] = useState({
    allocationId: 1,
    purpose: 'Home Visit (Weekend Leave)',
    leaveDate: new Date().toISOString().split('T')[0],
    expectedReturnDate: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    remarks: '',
  });

  // Card Preview Selection
  const [selectedResidentForCard, setSelectedResidentForCard] = useState<HostelAllocationInfo | null>(null);

  // Status Alerts
  const [alertMessage, setAlertMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const showAlert = (type: 'success' | 'error', text: string) => {
    setAlertMessage({ type, text });
    setTimeout(() => setAlertMessage(null), 4000);
  };

  const loadData = () => {
    const b = StorageService.getHostelBlocks();
    const r = StorageService.getHostelRooms();
    const a = StorageService.getHostelAllocations();
    const g = StorageService.getHostelGatePasses();
    const s = StorageService.getHostelStats();
    const stu = StorageService.getStudents();

    setBlocks(b);
    setRooms(r);
    setAllocations(a);
    setGatePasses(g);
    setStats(s);
    setStudents(stu);

    if (a.length > 0 && !selectedResidentForCard) {
      setSelectedResidentForCard(a[0]);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Room Type change helper
  const handleRoomTypeChange = (type: string) => {
    let cap = 2;
    if (type === 'Single') cap = 1;
    else if (type === 'Double') cap = 2;
    else if (type === 'Triple') cap = 3;
    else if (type === '4-Bed Dorm') cap = 4;
    else if (type === '6-Bed Dorm') cap = 6;

    setRoomForm((prev) => ({
      ...prev,
      roomType: type as any,
      capacity: cap,
    }));
  };

  // Block creation
  const handleCreateBlock = (e: React.FormEvent) => {
    e.preventDefault();
    if (!blockForm.blockName.trim()) {
      showAlert('error', 'Block Name is required.');
      return;
    }
    StorageService.saveHostelBlock(blockForm);
    showAlert('success', `Block '${blockForm.blockName}' created successfully.`);
    setShowBlockModal(false);
    setBlockForm({
      blockName: '',
      genderType: 'Boys',
      wardenName: '',
      wardenPhone: '',
      address: '',
      totalFloors: 3,
      status: 'Active',
    });
    loadData();
  };

  // Room creation
  const handleCreateRoom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomForm.roomNumber.trim()) {
      showAlert('error', 'Room Number is required.');
      return;
    }
    StorageService.saveHostelRoom(roomForm);
    showAlert('success', `Room '${roomForm.roomNumber}' created successfully.`);
    setShowRoomModal(false);
    setRoomForm({
      blockId: blocks[0]?.id || 1,
      roomNumber: '',
      floorNumber: 1,
      roomType: 'Double',
      capacity: 2,
      monthlyFee: 3000,
      amenities: 'Attached Bath, Study Table, Wi-Fi',
      status: 'Available',
    });
    loadData();
  };

  // Allocation creation with rule enforcement
  const handleAllocateBed = (e: React.FormEvent) => {
    e.preventDefault();
    const res = StorageService.allocateHostelBed({
      roomId: Number(allocForm.roomId),
      studentId: Number(allocForm.studentId),
      bedNumber: allocForm.bedNumber,
      admissionDate: allocForm.admissionDate,
      guardianContact: allocForm.guardianContact,
      emergencyPhone: allocForm.emergencyPhone,
      remarks: allocForm.remarks,
    });

    if (!res.success) {
      showAlert('error', res.message || 'Failed to allocate bed.');
      return;
    }

    showAlert('success', `Student allocated to Bed '${allocForm.bedNumber}' successfully!`);
    setShowAllocModal(false);
    loadData();
  };

  // Vacate student
  const handleVacate = (id: number) => {
    if (confirm('Are you sure you want to vacate this resident from their hostel bed?')) {
      StorageService.vacateHostelBed(id, 'Standard check-out');
      showAlert('success', 'Resident vacated successfully.');
      loadData();
    }
  };

  // Gate pass issue
  const handleIssueGatePass = (e: React.FormEvent) => {
    e.preventDefault();
    const res = StorageService.createHostelGatePass({
      allocationId: Number(gatePassForm.allocationId),
      purpose: gatePassForm.purpose,
      leaveDate: gatePassForm.leaveDate,
      expectedReturnDate: gatePassForm.expectedReturnDate,
      remarks: gatePassForm.remarks,
    });

    if (!res.success) {
      showAlert('error', res.message || 'Failed to issue gate pass.');
      return;
    }

    showAlert('success', `Gate pass #${res.gatePass?.passNumber} issued successfully!`);
    setShowPassModal(false);
    loadData();
  };

  // Return gate pass
  const handleMarkReturned = (id: number) => {
    StorageService.returnHostelGatePass(id);
    showAlert('success', 'Resident marked as returned.');
    loadData();
  };

  // Filtered rooms
  const filteredRooms = rooms.filter((r) => {
    const matchesSearch =
      r.roomNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.blockName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesBlock = selectedBlockFilter === 'all' || r.blockId.toString() === selectedBlockFilter;
    const matchesType = selectedTypeFilter === 'all' || r.roomType === selectedTypeFilter;
    return matchesSearch && matchesBlock && matchesType;
  });

  // Filtered allocations
  const filteredAllocations = allocations.filter((a) => {
    return (
      a.studentName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.studentRegNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.roomNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.blockName.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 rounded-xl">
            <Building2 className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">Hostel & Dormitory Management</h1>
              <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 rounded-full border border-emerald-200 dark:border-emerald-800">
                Phase 12 Live
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Halls of residence, room capacity caps, resident bed allocations, curfew gate passes & PVC passes
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => {
              StorageService.getHostelBlocks();
              loadData();
              showAlert('success', 'Hostel demo dataset refreshed successfully.');
            }}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reload Defaults</span>
          </button>
          <button
            onClick={() => setShowBlockModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Block</span>
          </button>
          <button
            onClick={() => setShowRoomModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Room</span>
          </button>
          <button
            onClick={() => setShowAllocModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition shadow-sm"
          >
            <Bed className="w-3.5 h-3.5" />
            <span>Allocate Bed</span>
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
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Hostel Blocks</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{stats.totalBlocks}</h3>
            <span className="text-[11px] font-medium text-blue-600">Active</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Halls of Residence</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-teal-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Rooms</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white">{stats.totalRooms}</h3>
            <span className="text-[11px] font-medium text-teal-600">Multi-Tier</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Singles, Doubles & Dorms</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-emerald-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Bed Capacity</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {stats.occupiedBeds} / {stats.totalCapacity}
            </h3>
            <span className="text-[11px] font-bold text-emerald-600">{stats.occupancyRate}% Full</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">{stats.availableBeds} Beds Available</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-amber-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Outpasses / Leave</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-amber-600 dark:text-amber-400">{stats.boardersOut}</h3>
            <span className="text-[11px] font-medium text-amber-600">On Outpass</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Weekend / Medical Leave</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 border-l-4 border-l-indigo-600 shadow-sm">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Present in Hostel</p>
          <div className="flex items-baseline justify-between mt-1">
            <h3 className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{stats.presentInHostel}</h3>
            <span className="text-[11px] font-medium text-indigo-600">Boarders</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-1">Curfew Roll Call Count</p>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('rooms')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'rooms'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Hostel Blocks & Rooms</span>
          <span className="px-1.5 py-0.2 bg-white/20 text-white rounded-full text-[10px]">{rooms.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('allocations')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'allocations'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Bed className="w-4 h-4" />
          <span>Resident Boarder Allocations</span>
          <span className="px-1.5 py-0.2 bg-white/20 text-white rounded-full text-[10px]">{allocations.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('gatepasses')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'gatepasses'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Key className="w-4 h-4" />
          <span>Gate Passes & Curfew</span>
          <span className="px-1.5 py-0.2 bg-white/20 text-white rounded-full text-[10px]">{gatePasses.length}</span>
        </button>

        <button
          onClick={() => setActiveTab('passes')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition ${
            activeTab === 'passes'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Resident Cards (CR80 PVC)</span>
        </button>
      </div>

      {/* TAB 1: BLOCKS & ROOMS */}
      {activeTab === 'rooms' && (
        <div className="space-y-6">
          {/* Hostel Blocks Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {blocks.map((block) => {
              const blockRooms = rooms.filter((r) => r.blockId === block.id);
              const blockCapacity = blockRooms.reduce((sum, r) => sum + r.capacity, 0);
              const blockOccupied = blockRooms.reduce((sum, r) => sum + (r.occupiedCount || 0), 0);
              const pct = blockCapacity > 0 ? Math.round((blockOccupied / blockCapacity) * 100) : 0;

              return (
                <div
                  key={block.id}
                  className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-sm text-slate-900 dark:text-white">{block.blockName}</h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{block.address}</p>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        block.genderType === 'Boys'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400'
                          : block.genderType === 'Girls'
                          ? 'bg-pink-100 text-pink-700 dark:bg-pink-950/60 dark:text-pink-400'
                          : 'bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-400'
                      }`}
                    >
                      {block.genderType}
                    </span>
                  </div>

                  <div className="text-xs space-y-1 text-slate-600 dark:text-slate-400">
                    <p>
                      <strong>Warden:</strong> {block.wardenName} ({block.wardenPhone})
                    </p>
                    <p>
                      <strong>Structure:</strong> {block.totalFloors} Floors &bull; {blockRooms.length} Rooms
                    </p>
                  </div>

                  {/* Capacity Bar */}
                  <div>
                    <div className="flex justify-between text-[11px] font-semibold text-slate-500 mb-1">
                      <span>Occupancy</span>
                      <span>
                        {blockOccupied} / {blockCapacity} Beds ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          pct >= 100 ? 'bg-rose-500' : pct >= 75 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Rooms List Header & Filter */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search rooms by number or block..."
                    className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white w-64 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <select
                    value={selectedBlockFilter}
                    onChange={(e) => setSelectedBlockFilter(e.target.value)}
                    className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                  >
                    <option value="all">All Blocks</option>
                    {blocks.map((b) => (
                      <option key={b.id} value={b.id.toString()}>
                        {b.blockName}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedTypeFilter}
                    onChange={(e) => setSelectedTypeFilter(e.target.value)}
                    className="text-xs py-1.5 px-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                  >
                    <option value="all">All Room Types</option>
                    <option value="Single">Single</option>
                    <option value="Double">Double</option>
                    <option value="Triple">Triple</option>
                    <option value="4-Bed Dorm">4-Bed Dorm</option>
                    <option value="6-Bed Dorm">6-Bed Dorm</option>
                  </select>
                </div>
              </div>

              <div className="text-xs font-semibold text-slate-500">Showing {filteredRooms.length} rooms</div>
            </div>

            {/* Rooms Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredRooms.map((room) => {
                const isFull = (room.occupiedCount || 0) >= room.capacity;
                return (
                  <div
                    key={room.id}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isFull
                        ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/60'
                        : 'bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 hover:border-emerald-500'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-base text-slate-900 dark:text-white">Room {room.roomNumber}</h4>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                          {room.blockName} &bull; Floor {room.floorNumber}
                        </p>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isFull
                            ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/80 dark:text-rose-400'
                            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-400'
                        }`}
                      >
                        {isFull ? 'Full' : `${room.capacity - (room.occupiedCount || 0)} Beds Left`}
                      </span>
                    </div>

                    <div className="my-2 py-2 border-y border-inherit text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Room Type:</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{room.roomType}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Monthly Rent:</span>
                        <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                          ৳ {room.monthlyFee.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Occupancy:</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {room.occupiedCount || 0} / {room.capacity} Beds
                        </span>
                      </div>
                    </div>

                    <p className="text-[10px] text-slate-400 truncate mb-3" title={room.amenities}>
                      ✨ {room.amenities}
                    </p>

                    <div className="flex items-center gap-2">
                      <button
                        disabled={isFull}
                        onClick={() => {
                          setAllocForm((prev) => ({ ...prev, roomId: room.id }));
                          setShowAllocModal(true);
                        }}
                        className={`w-full py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center gap-1 transition ${
                          isFull
                            ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                            : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm'
                        }`}
                      >
                        <Bed className="w-3.5 h-3.5" />
                        <span>{isFull ? 'Room Full' : 'Assign Bed'}</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: RESIDENT BOARDER ALLOCATIONS */}
      {activeTab === 'allocations' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search resident student, roll, or bed..."
                  className="pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white w-64 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const csvRows = [
                    ['SL', 'Student Name', 'Student ID', 'Hostel Block', 'Room No', 'Bed No', 'Admission Date', 'Guardian Phone', 'Status'].join(','),
                    ...filteredAllocations.map((a, i) =>
                      [
                        i + 1,
                        `"${a.studentName}"`,
                        a.studentRegNo,
                        `"${a.blockName}"`,
                        a.roomNumber,
                        a.bedNumber,
                        a.admissionDate,
                        a.emergencyPhone,
                        a.status,
                      ].join(',')
                    ),
                  ].join('\n');
                  const blob = new Blob([csvRows], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `Hostel_Boarders_Manifest_${new Date().toISOString().split('T')[0]}.csv`;
                  link.click();
                  showAlert('success', 'Hostel boarders manifest exported to CSV!');
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                <span>Export CSV / Excel</span>
              </button>

              <button
                onClick={() => setShowRollCallModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Night Roll Call Sheet</span>
              </button>

              <button
                onClick={() => setShowAllocModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Allocation</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 uppercase font-semibold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Resident Student</th>
                  <th className="py-3 px-4">Hostel Block</th>
                  <th className="py-3 px-4">Room & Bed</th>
                  <th className="py-3 px-4">Admission Date</th>
                  <th className="py-3 px-4">Emergency Contact</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
                {filteredAllocations.map((alloc) => (
                  <tr key={alloc.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-emerald-600/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs uppercase">
                          {alloc.studentName.charAt(0)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 dark:text-white">{alloc.studentName}</p>
                          <p className="text-[10px] text-slate-400 font-mono">
                            {alloc.studentRegNo} {alloc.studentGender ? `(${alloc.studentGender})` : ''}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium">{alloc.blockName}</td>
                    <td className="py-3 px-4">
                      <span className="font-bold text-slate-900 dark:text-white">Room {alloc.roomNumber}</span>
                      <span className="ml-1.5 px-2 py-0.5 text-[10px] bg-slate-100 dark:bg-slate-800 rounded font-semibold text-emerald-600 dark:text-emerald-400">
                        {alloc.bedNumber}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{alloc.admissionDate}</td>
                    <td className="py-3 px-4 font-mono text-slate-500">{alloc.emergencyPhone || 'N/A'}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          alloc.status === 'Active'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                        }`}
                      >
                        {alloc.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right space-x-1">
                      <button
                        onClick={() => {
                          setSelectedResidentForCard(alloc);
                          setActiveTab('passes');
                        }}
                        className="px-2.5 py-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/50 dark:hover:bg-emerald-900/60 rounded transition"
                      >
                        PVC Card
                      </button>
                      {alloc.status === 'Active' && (
                        <button
                          onClick={() => handleVacate(alloc.id)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 dark:hover:bg-rose-900/60 rounded transition"
                        >
                          Vacate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: GATE PASSES & CURFEW */}
      {activeTab === 'gatepasses' && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden space-y-4">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Resident Outpass & Gate Register</h3>
              <p className="text-xs text-slate-400">
                Authorized weekend leaves, medical visits, and curfew roll-call monitoring
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPassModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Issue Gate Pass</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 uppercase font-semibold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Pass Number</th>
                  <th className="py-3 px-4">Resident Student</th>
                  <th className="py-3 px-4">Hall & Room</th>
                  <th className="py-3 px-4">Purpose</th>
                  <th className="py-3 px-4">Departure</th>
                  <th className="py-3 px-4">Expected Return</th>
                  <th className="py-3 px-4">Actual Return</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
                {gatePasses.map((pass) => (
                  <tr key={pass.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      {pass.passNumber}
                    </td>
                    <td className="py-3 px-4 font-semibold">{pass.studentName}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {pass.blockName} (Room {pass.roomNumber})
                    </td>
                    <td className="py-3 px-4 font-medium">{pass.purpose}</td>
                    <td className="py-3 px-4 text-slate-500">{pass.leaveDate}</td>
                    <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">
                      {pass.expectedReturnDate}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500">{pass.actualReturnDate || '—'}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          pass.status === 'Out'
                            ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400'
                            : pass.status === 'Returned'
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400'
                            : 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-400'
                        }`}
                      >
                        {pass.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {pass.status === 'Out' && (
                        <button
                          onClick={() => handleMarkReturned(pass.id)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/50 dark:hover:bg-emerald-900/60 rounded transition"
                        >
                          Mark Returned
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: RESIDENT CARDS (CR80 PVC) */}
      {activeTab === 'passes' && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Left: Resident Selector */}
          <div className="md:col-span-5 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">Active Resident Boarders</h3>
            <p className="text-xs text-slate-400">Select a resident to preview and print their PVC identity card</p>

            <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[460px] overflow-y-auto">
              {allocations
                .filter((a) => a.status === 'Active')
                .map((a) => (
                  <button
                    key={a.id}
                    onClick={() => setSelectedResidentForCard(a)}
                    className={`w-full text-left p-3 rounded-lg flex items-center justify-between transition ${
                      selectedResidentForCard?.id === a.id
                        ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-500'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-xs text-slate-900 dark:text-white">{a.studentName}</p>
                      <p className="text-[10px] text-slate-400 font-mono">
                        {a.studentRegNo} &bull; Room {a.roomNumber} ({a.bedNumber})
                      </p>
                    </div>
                    <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">{a.blockName}</span>
                  </button>
                ))}
            </div>
          </div>

          {/* Right: CR80 PVC Card Graphic Preview */}
          <div className="md:col-span-7 bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col items-center justify-center space-y-4">
            <div className="text-center">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                CR80 PVC Printable Hostel Resident Card
              </h3>
              <p className="text-xs text-slate-400">ISO/IEC 7810 ID-1 Standard (85.60 mm × 53.98 mm)</p>
            </div>

            {selectedResidentForCard ? (
              <div
                id="hostel-pvc-card"
                className="w-[340px] h-[215px] bg-slate-900 rounded-2xl p-4 text-white shadow-2xl relative border border-slate-700 flex flex-col justify-between overflow-hidden"
              >
                {/* Header Strip with School Name */}
                <div className="absolute top-0 left-0 right-0 h-10 bg-gradient-to-r from-emerald-700 to-teal-800 px-4 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm">🎓</span>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white">
                      EDUMANAGE RESIDENTIAL ACADEMY
                    </span>
                  </div>
                  <span className="text-[8px] font-bold bg-white/20 text-white px-2 py-0.5 rounded-full uppercase tracking-wider">
                    RESIDENT
                  </span>
                </div>

                {/* Body Content */}
                <div className="mt-8 flex gap-3 items-center">
                  {/* Photo Box */}
                  <div className="w-16 h-20 rounded-lg bg-slate-800 border border-slate-700 flex flex-col items-center justify-center shrink-0">
                    <span className="text-2xl">👤</span>
                    <span className="text-[8px] text-slate-400 font-mono mt-1">PHOTO</span>
                  </div>

                  {/* Info Column */}
                  <div className="space-y-1 text-left flex-1 min-w-0">
                    <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wide truncate">
                      {selectedResidentForCard.studentName}
                    </h4>
                    <p className="text-[10px] text-slate-300 font-mono">
                      ID: <strong className="text-white">{selectedResidentForCard.studentRegNo}</strong>
                    </p>
                    <p className="text-[10px] text-slate-300 truncate">
                      Hall: <strong className="text-white">{selectedResidentForCard.blockName}</strong>
                    </p>
                    <p className="text-[10px] text-slate-300">
                      Room:{' '}
                      <strong className="text-amber-300">
                        {selectedResidentForCard.roomNumber} ({selectedResidentForCard.bedNumber})
                      </strong>
                    </p>
                    <p className="text-[9px] text-slate-400 truncate">
                      Emergency: {selectedResidentForCard.emergencyPhone || '+880 1700-000000'}
                    </p>
                  </div>
                </div>

                {/* Footer Simulated Barcode */}
                <div className="bg-slate-950 p-1.5 rounded-lg border border-slate-800 text-center">
                  <div className="flex justify-center items-center gap-0.5 h-3">
                    {[2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 2, 3, 1, 2, 1, 3, 1, 2, 2, 1, 3, 1, 1, 2, 3, 1].map((w, i) => (
                      <div key={i} className="bg-white h-full" style={{ width: `${w}px` }} />
                    ))}
                  </div>
                  <p className="text-[7.5px] font-mono text-slate-400 mt-0.5">
                    *HST-ALLOC-{String(selectedResidentForCard.id).padStart(4, '0')}*
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">No resident selected</div>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg shadow-sm transition"
              >
                <Printer className="w-4 h-4" />
                <span>Print Resident Pass</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ADD HOSTEL BLOCK */}
      {showBlockModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Add New Hostel Block</h3>
              <button onClick={() => setShowBlockModal(false)} className="text-slate-400 hover:text-slate-600">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateBlock} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Block / Hall Name *
                </label>
                <input
                  type="text"
                  required
                  value={blockForm.blockName}
                  onChange={(e) => setBlockForm({ ...blockForm, blockName: e.target.value })}
                  placeholder="e.g. Nazrul Hall (Senior Block)"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Gender Type *</label>
                  <select
                    value={blockForm.genderType}
                    onChange={(e) => setBlockForm({ ...blockForm, genderType: e.target.value as any })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="Boys">Boys</option>
                    <option value="Girls">Girls</option>
                    <option value="Co-ed">Co-ed</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Total Floors</label>
                  <input
                    type="number"
                    min="1"
                    max="15"
                    value={blockForm.totalFloors}
                    onChange={(e) => setBlockForm({ ...blockForm, totalFloors: Number(e.target.value) })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Warden Name</label>
                <input
                  type="text"
                  value={blockForm.wardenName}
                  onChange={(e) => setBlockForm({ ...blockForm, wardenName: e.target.value })}
                  placeholder="Prof. / Mr. Warden"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Warden Phone</label>
                <input
                  type="text"
                  value={blockForm.wardenPhone}
                  onChange={(e) => setBlockForm({ ...blockForm, wardenPhone: e.target.value })}
                  placeholder="+880 1700-000000"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Campus Location</label>
                <input
                  type="text"
                  value={blockForm.address}
                  onChange={(e) => setBlockForm({ ...blockForm, address: e.target.value })}
                  placeholder="South Quadrangle, Gate 2"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowBlockModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold"
                >
                  Save Block
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD ROOM */}
      {showRoomModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Add Hostel Room</h3>
              <button onClick={() => setShowRoomModal(false)} className="text-slate-400 hover:text-slate-600">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateRoom} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Hostel Block *</label>
                <select
                  value={roomForm.blockId}
                  onChange={(e) => setRoomForm({ ...roomForm, blockId: Number(e.target.value) })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                >
                  {blocks.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.blockName} ({b.genderType})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Room Number *</label>
                  <input
                    type="text"
                    required
                    value={roomForm.roomNumber}
                    onChange={(e) => setRoomForm({ ...roomForm, roomNumber: e.target.value })}
                    placeholder="e.g. A-301"
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Floor Number</label>
                  <input
                    type="number"
                    min="1"
                    value={roomForm.floorNumber}
                    onChange={(e) => setRoomForm({ ...roomForm, floorNumber: Number(e.target.value) })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Room Type</label>
                  <select
                    value={roomForm.roomType}
                    onChange={(e) => handleRoomTypeChange(e.target.value)}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  >
                    <option value="Single">Single (1 Bed)</option>
                    <option value="Double">Double (2 Beds)</option>
                    <option value="Triple">Triple (3 Beds)</option>
                    <option value="4-Bed Dorm">4-Bed Dorm</option>
                    <option value="6-Bed Dorm">6-Bed Dorm</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Bed Capacity *</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={roomForm.capacity}
                    onChange={(e) => setRoomForm({ ...roomForm, capacity: Number(e.target.value) })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Monthly Fee (BDT)</label>
                <input
                  type="number"
                  value={roomForm.monthlyFee}
                  onChange={(e) => setRoomForm({ ...roomForm, monthlyFee: Number(e.target.value) })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Amenities</label>
                <input
                  type="text"
                  value={roomForm.amenities}
                  onChange={(e) => setRoomForm({ ...roomForm, amenities: e.target.value })}
                  placeholder="Attached Bath, Study Table, Wi-Fi"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowRoomModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold"
                >
                  Save Room
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ALLOCATE BED */}
      {showAllocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Allocate Student to Bed</h3>
              <button onClick={() => setShowAllocModal(false)} className="text-slate-400 hover:text-slate-600">
                &times;
              </button>
            </div>

            <form onSubmit={handleAllocateBed} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Target Room *</label>
                <select
                  value={allocForm.roomId}
                  onChange={(e) => setAllocForm({ ...allocForm, roomId: Number(e.target.value) })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                >
                  {rooms.map((r) => {
                    const occupied = r.occupiedCount || 0;
                    const isFull = occupied >= r.capacity;
                    return (
                      <option key={r.id} value={r.id} disabled={isFull}>
                        Room {r.roomNumber} ({r.blockName}) &bull; {occupied}/{r.capacity} Beds {isFull ? '[FULL]' : ''}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Student *</label>
                <select
                  value={allocForm.studentId}
                  onChange={(e) => setAllocForm({ ...allocForm, studentId: Number(e.target.value) })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                >
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.studentId} - {s.firstName} {s.lastName} ({s.gender || 'General'})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                    Bed Identifier *
                  </label>
                  <input
                    type="text"
                    required
                    value={allocForm.bedNumber}
                    onChange={(e) => setAllocForm({ ...allocForm, bedNumber: e.target.value })}
                    placeholder="Bed-1, Bed-A, Bunk 2"
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Admission Date</label>
                  <input
                    type="date"
                    value={allocForm.admissionDate}
                    onChange={(e) => setAllocForm({ ...allocForm, admissionDate: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">
                  Guardian / Emergency Phone
                </label>
                <input
                  type="text"
                  value={allocForm.emergencyPhone}
                  onChange={(e) => setAllocForm({ ...allocForm, emergencyPhone: e.target.value })}
                  placeholder="+880 1700-000000"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Remarks / Notes</label>
                <input
                  type="text"
                  value={allocForm.remarks}
                  onChange={(e) => setAllocForm({ ...allocForm, remarks: e.target.value })}
                  placeholder="Medical conditions, dietary requirements, etc."
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowAllocModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold"
                >
                  Confirm Allocation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ISSUE GATE PASS */}
      {showPassModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-5 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Issue Warden Gate Pass</h3>
              <button onClick={() => setShowPassModal(false)} className="text-slate-400 hover:text-slate-600">
                &times;
              </button>
            </div>

            <form onSubmit={handleIssueGatePass} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Resident Student *</label>
                <select
                  value={gatePassForm.allocationId}
                  onChange={(e) => setGatePassForm({ ...gatePassForm, allocationId: Number(e.target.value) })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                >
                  {allocations
                    .filter((a) => a.status === 'Active')
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.studentName} (Room {a.roomNumber}, {a.bedNumber})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Purpose / Reason *</label>
                <select
                  value={gatePassForm.purpose}
                  onChange={(e) => setGatePassForm({ ...gatePassForm, purpose: e.target.value })}
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                >
                  <option value="Home Visit (Weekend Leave)">Home Visit (Weekend Leave)</option>
                  <option value="Medical Emergency / Doctor Appointment">Medical Emergency / Doctor Appointment</option>
                  <option value="Local Market / Personal Errands">Local Market / Personal Errands</option>
                  <option value="School Sports Competition">School Sports Competition</option>
                  <option value="Academic Seminar / Excursion">Academic Seminar / Excursion</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Departure Date</label>
                  <input
                    type="date"
                    value={gatePassForm.leaveDate}
                    onChange={(e) => setGatePassForm({ ...gatePassForm, leaveDate: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Expected Return *</label>
                  <input
                    type="date"
                    value={gatePassForm.expectedReturnDate}
                    onChange={(e) => setGatePassForm({ ...gatePassForm, expectedReturnDate: e.target.value })}
                    className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-700 dark:text-slate-300 font-semibold mb-1">Warden Remarks</label>
                <input
                  type="text"
                  value={gatePassForm.remarks}
                  onChange={(e) => setGatePassForm({ ...gatePassForm, remarks: e.target.value })}
                  placeholder="Guardian consent verified via phone call"
                  className="w-full p-2 border rounded-lg dark:bg-slate-800 dark:border-slate-700"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowPassModal(false)}
                  className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold"
                >
                  Authorize Gate Pass
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: NIGHT ROLL CALL SHEET PREVIEW */}
      {showRollCallModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b pb-3">
              <div>
                <h3 className="font-bold text-base text-slate-900 dark:text-white">
                  Night Roll Call & Curfew Inspection Sheet
                </h3>
                <p className="text-xs text-slate-400">Official ReportLab Landscape A4 Warden Inspection Manifest</p>
              </div>
              <button onClick={() => setShowRollCallModal(false)} className="text-slate-400 hover:text-slate-600 text-xl">
                &times;
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border text-xs space-y-3">
              <div className="flex justify-between border-b pb-2">
                <span>
                  <strong>Date:</strong> {new Date().toLocaleDateString()}
                </span>
                <span>
                  <strong>Curfew Time:</strong> 09:30 PM
                </span>
                <span>
                  <strong>Active Boarders:</strong> {allocations.filter((a) => a.status === 'Active').length}
                </span>
              </div>

              <table className="w-full text-left">
                <thead className="border-b font-bold text-slate-600 dark:text-slate-300">
                  <tr>
                    <th className="py-2">SL</th>
                    <th className="py-2">Room / Bed</th>
                    <th className="py-2">Resident Student</th>
                    <th className="py-2">Hall Block</th>
                    <th className="py-2">Attendance Check</th>
                    <th className="py-2">Warden Initial</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {allocations
                    .filter((a) => a.status === 'Active')
                    .map((a, i) => (
                      <tr key={a.id}>
                        <td className="py-2">{i + 1}</td>
                        <td className="py-2 font-bold">
                          {a.roomNumber} ({a.bedNumber})
                        </td>
                        <td className="py-2">{a.studentName}</td>
                        <td className="py-2">{a.blockName}</td>
                        <td className="py-2">
                          <span className="inline-block border px-1.5 py-0.5 rounded text-[10px] mr-1">
                            [ &nbsp; ] Present
                          </span>
                          <span className="inline-block border px-1.5 py-0.5 rounded text-[10px] mr-1">
                            [ &nbsp; ] Absent
                          </span>
                          <span className="inline-block border px-1.5 py-0.5 rounded text-[10px]">
                            [ &nbsp; ] Outpass
                          </span>
                        </td>
                        <td className="py-2 text-slate-400">______________</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                onClick={() => setShowRollCallModal(false)}
                className="px-4 py-2 border rounded-lg font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 text-xs"
              >
                Close
              </button>
              <button
                onClick={() => window.print()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold text-xs flex items-center gap-1.5"
              >
                <Printer className="w-4 h-4" />
                <span>Print Night Roll Call</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
