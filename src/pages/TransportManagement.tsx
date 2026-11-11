import React, { useState, useMemo } from 'react';
import {
  Bus,
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
  MapPin,
  Users,
  ShieldCheck,
  Phone,
  Navigation,
} from 'lucide-react';
import { storage } from '../services/storage';
import {
  VehicleInfo,
  TransportRouteInfo,
  TransportStopInfo,
  TransportPassengerInfo,
  Student,
  Teacher,
} from '../types';

export const TransportManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'vehicles' | 'routes' | 'passengers' | 'passes'>('vehicles');

  // Data State
  const [vehicles, setVehicles] = useState<VehicleInfo[]>(() => storage.getVehicles());
  const [routes, setRoutes] = useState<TransportRouteInfo[]>(() => storage.getRoutes());
  const [passengers, setPassengers] = useState<TransportPassengerInfo[]>(() => storage.getTransportPassengers());
  const [students] = useState<Student[]>(() => storage.getStudents());
  const [teachers] = useState<Teacher[]>(() => storage.getTeachers());

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRouteFilter, setSelectedRouteFilter] = useState<string>('all');
  const [selectedVehicleTypeFilter, setSelectedVehicleTypeFilter] = useState<string>('all');

  // Modals
  const [showVehicleModal, setShowVehicleModal] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<VehicleInfo | null>(null);

  const [showRouteModal, setShowRouteModal] = useState(false);
  const [editingRoute, setEditingRoute] = useState<TransportRouteInfo | null>(null);

  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [showPassModal, setShowPassModal] = useState(false);
  const [selectedPassengerForPass, setSelectedPassengerForPass] = useState<TransportPassengerInfo | null>(null);

  // Form States
  const [vehicleForm, setVehicleForm] = useState({
    vehicleNumber: '',
    vehicleModel: '',
    vehicleType: 'Bus' as 'Bus' | 'Minibus' | 'Van' | 'Coaster',
    seatingCapacity: 40,
    driverName: '',
    driverPhone: '',
    driverLicense: '',
    helperName: '',
    helperPhone: '',
    status: 'Active' as 'Active' | 'Maintenance' | 'Out of Service',
  });

  const [routeForm, setRouteForm] = useState({
    routeCode: '',
    routeName: '',
    startPoint: '',
    endPoint: 'School Main Campus',
    distanceKm: 12.0,
    monthlyFee: 2500.0,
    vehicleId: 1,
    pickupTime: '06:45 AM',
    dropTime: '02:30 PM',
    status: 'Active' as 'Active' | 'Inactive',
  });

  const [allocateForm, setAllocateForm] = useState({
    passengerType: 'Student' as 'Student' | 'Teacher' | 'Staff',
    studentId: 1,
    teacherId: 1,
    routeId: 1,
    stopId: 1,
    seatNumber: 'Seat 05A',
    monthlyFare: 2500.0,
    remarks: '',
  });

  const refreshAll = () => {
    setVehicles(storage.getVehicles());
    setRoutes(storage.getRoutes());
    setPassengers(storage.getTransportPassengers());
  };

  const stats = useMemo(() => storage.getTransportStats(), [vehicles, routes, passengers]);

  // Filtered passengers
  const filteredPassengers = useMemo(() => {
    let result = passengers;
    if (selectedRouteFilter !== 'all') {
      result = result.filter((p) => p.routeId === parseInt(selectedRouteFilter, 10));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (p) =>
          p.patronName.toLowerCase().includes(q) ||
          p.routeName.toLowerCase().includes(q) ||
          (p.stopName && p.stopName.toLowerCase().includes(q)) ||
          (p.seatNumber && p.seatNumber.toLowerCase().includes(q)) ||
          (p.vehicleNumber && p.vehicleNumber.toLowerCase().includes(q))
      );
    }
    return result;
  }, [passengers, selectedRouteFilter, searchQuery]);

  // Filtered vehicles
  const filteredVehicles = useMemo(() => {
    if (selectedVehicleTypeFilter === 'all') return vehicles;
    return vehicles.filter((v) => v.vehicleType === selectedVehicleTypeFilter);
  }, [vehicles, selectedVehicleTypeFilter]);

  // Export Passenger Manifest to CSV
  const exportManifestCSV = () => {
    const headers = ['Pass ID', 'Passenger Name', 'Type', 'Class / Designation', 'Phone', 'Emergency Contact', 'Route Code', 'Route Name', 'Stop Name', 'Bus Number', 'Seat No', 'Monthly Fare ($)', 'Status'];
    const rows = filteredPassengers.map((p) => [
      p.id,
      `"${p.patronName.replace(/"/g, '""')}"`,
      `"${p.passengerType}"`,
      `"${p.rollOrDesignation || '-'}"`,
      `"${p.phone || '-'}"`,
      `"${p.emergencyContact || '-'}"`,
      `"${p.routeCode}"`,
      `"${p.routeName.replace(/"/g, '""')}"`,
      `"${p.stopName || '-'}"`,
      `"${p.vehicleNumber || '-'}"`,
      `"${p.seatNumber || '-'}"`,
      p.monthlyFare,
      `"${p.status}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `EduManage_Passenger_Manifest_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Open New Vehicle
  const openNewVehicle = () => {
    setEditingVehicle(null);
    setVehicleForm({
      vehicleNumber: `DHK-METRO-CHA-11-${String(vehicles.length + 2045)}`,
      vehicleModel: 'Tata Marcopolo 40-S',
      vehicleType: 'Bus',
      seatingCapacity: 40,
      driverName: '',
      driverPhone: '+880 1711-000000',
      driverLicense: '',
      helperName: '',
      helperPhone: '',
      status: 'Active',
    });
    setShowVehicleModal(true);
  };

  // Open Edit Vehicle
  const openEditVehicle = (v: VehicleInfo) => {
    setEditingVehicle(v);
    setVehicleForm({
      vehicleNumber: v.vehicleNumber,
      vehicleModel: v.vehicleModel,
      vehicleType: v.vehicleType,
      seatingCapacity: v.seatingCapacity,
      driverName: v.driverName,
      driverPhone: v.driverPhone,
      driverLicense: v.driverLicense || '',
      helperName: v.helperName || '',
      helperPhone: v.helperPhone || '',
      status: v.status,
    });
    setShowVehicleModal(true);
  };

  // Handle Save Vehicle
  const handleSaveVehicle = (e: React.FormEvent) => {
    e.preventDefault();
    storage.saveVehicle({
      id: editingVehicle ? editingVehicle.id : undefined,
      ...vehicleForm,
    });
    setShowVehicleModal(false);
    refreshAll();
  };

  // Open New Route
  const openNewRoute = () => {
    setEditingRoute(null);
    setRouteForm({
      routeCode: `RT-${String(routes.length + 1).padStart(2, '0')}`,
      routeName: '',
      startPoint: '',
      endPoint: 'School Main Campus',
      distanceKm: 15.0,
      monthlyFee: 2600.0,
      vehicleId: vehicles[0]?.id || 1,
      pickupTime: '06:45 AM',
      dropTime: '02:30 PM',
      status: 'Active',
    });
    setShowRouteModal(true);
  };

  // Open Edit Route
  const openEditRoute = (r: TransportRouteInfo) => {
    setEditingRoute(r);
    setRouteForm({
      routeCode: r.routeCode,
      routeName: r.routeName,
      startPoint: r.startPoint,
      endPoint: r.endPoint,
      distanceKm: r.distanceKm,
      monthlyFee: r.monthlyFee,
      vehicleId: r.vehicleId || vehicles[0]?.id || 1,
      pickupTime: r.pickupTime || '06:45 AM',
      dropTime: r.dropTime || '02:30 PM',
      status: r.status,
    });
    setShowRouteModal(true);
  };

  // Handle Save Route
  const handleSaveRoute = (e: React.FormEvent) => {
    e.preventDefault();
    storage.saveRoute({
      id: editingRoute ? editingRoute.id : undefined,
      ...routeForm,
      stops: editingRoute ? editingRoute.stops : [
        { id: 1, routeId: 1, stopName: `${routeForm.startPoint} (Origin)`, stopOrder: 1, pickupTime: routeForm.pickupTime, dropTime: routeForm.dropTime, fare: routeForm.monthlyFee },
        { id: 2, routeId: 1, stopName: 'Intermediate Intersection', stopOrder: 2, pickupTime: '07:15 AM', dropTime: '03:00 PM', fare: routeForm.monthlyFee - 200 },
        { id: 3, routeId: 1, stopName: routeForm.endPoint, stopOrder: 3, pickupTime: '07:45 AM', dropTime: '03:30 PM', fare: 0 },
      ],
    });
    setShowRouteModal(false);
    refreshAll();
  };

  // Open Allocate Modal
  const openAllocateModal = () => {
    const firstRoute = routes[0];
    setAllocateForm({
      passengerType: 'Student',
      studentId: students[0]?.id || 1,
      teacherId: teachers[0]?.id || 1,
      routeId: firstRoute?.id || 1,
      stopId: firstRoute?.stops[0]?.id || 1,
      seatNumber: `Seat ${String(passengers.length + 1).padStart(2, '0')}A`,
      monthlyFare: firstRoute?.monthlyFee || 2500.0,
      remarks: 'Regular school commute',
    });
    setShowAllocateModal(true);
  };

  // Confirm Passenger Allocation
  const handleConfirmAllocate = (e: React.FormEvent) => {
    e.preventDefault();
    let name = 'Commuter';
    let affil = '-';
    let phone = '';
    let emg = '';

    if (allocateForm.passengerType === 'Student') {
      const s = students.find((std) => std.id === allocateForm.studentId);
      if (s) {
        name = s.fullName;
        affil = `Class ${s.className} (Roll ${s.rollNumber})`;
        phone = s.phone || '';
        emg = s.emergencyContact || s.guardian?.guardianPhone || '';
      }
    } else {
      const t = teachers.find((tch) => tch.id === allocateForm.teacherId);
      if (t) {
        name = t.fullName;
        affil = t.designation || 'Faculty';
        phone = t.phone || '';
        emg = t.phone || '';
      }
    }

    const res = storage.allocatePassenger({
      passengerType: allocateForm.passengerType,
      studentId: allocateForm.passengerType === 'Student' ? allocateForm.studentId : undefined,
      teacherId: allocateForm.passengerType === 'Teacher' ? allocateForm.teacherId : undefined,
      patronName: name,
      rollOrDesignation: affil,
      phone,
      emergencyContact: emg,
      routeId: allocateForm.routeId,
      stopId: allocateForm.stopId,
      seatNumber: allocateForm.seatNumber,
      allocationDate: new Date().toISOString().split('T')[0],
      monthlyFare: allocateForm.passengerType === 'Student' ? allocateForm.monthlyFare : 0.0,
      remarks: allocateForm.remarks,
    });

    if (!res.success) {
      alert(`Allocation Denied: ${res.message}`);
      return;
    }

    setShowAllocateModal(false);
    refreshAll();
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-800">
      {/* 1. Header & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-700 text-white rounded-xl shadow-sm">
              <Bus className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Transport & Fleet Management
              </h1>
              <p className="text-sm text-slate-500">
                Phase 11: School Buses, Transit Routes, Passenger Seat Allocations & Printable CR80 Passes
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={exportManifestCSV}
            className="flex items-center gap-2 px-3.5 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export Manifest (CSV)
          </button>
          <button
            onClick={openAllocateModal}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-amber-700 rounded-lg hover:bg-amber-800 shadow-sm transition"
          >
            <Users className="w-4 h-4" />
            Allocate Commuter
          </button>
          <button
            onClick={openNewVehicle}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            Add Vehicle
          </button>
        </div>
      </div>

      {/* 2. KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-amber-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Fleet Buses</span>
            <Bus className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {stats.activeVehicles} / {stats.totalVehicles}
          </div>
          <span className="text-xs text-slate-400 mt-1 block">Active / Registered</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-blue-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Transit Routes</span>
            <Navigation className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{stats.totalRoutes}</div>
          <span className="text-xs text-slate-400 mt-1 block">Active service routes</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-slate-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Seats</span>
            <Layers className="w-4 h-4 text-slate-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{stats.totalCapacity}</div>
          <span className="text-xs text-slate-400 mt-1 block">Fleet capacity</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-emerald-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Allocated</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 mt-2">{stats.allocatedPassengers}</div>
          <span className="text-xs text-emerald-600 mt-1 block">Assigned commuters</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-indigo-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Available Seats</span>
            <Users className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-indigo-700 mt-2">{stats.availableSeats}</div>
          <span className="text-xs text-slate-400 mt-1 block">Vacant seats</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 border-l-4 border-l-purple-600 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Monthly Revenue</span>
            <DollarSign className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-purple-700 mt-2">${stats.monthlyRevenue.toFixed(2)}</div>
          <span className="text-xs text-slate-400 mt-1 block">Transport billing</span>
        </div>
      </div>

      {/* 3. Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-1">
        <button
          onClick={() => setActiveTab('vehicles')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'vehicles'
              ? 'border-amber-700 text-amber-800 bg-amber-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Bus className="w-4 h-4" />
          Fleet Vehicles ({vehicles.length})
        </button>

        <button
          onClick={() => setActiveTab('routes')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'routes'
              ? 'border-amber-700 text-amber-800 bg-amber-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <MapPin className="w-4 h-4" />
          Transit Routes & Stops ({routes.length})
        </button>

        <button
          onClick={() => setActiveTab('passengers')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'passengers'
              ? 'border-amber-700 text-amber-800 bg-amber-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Users className="w-4 h-4" />
          Passenger Seat Allocations ({passengers.length})
        </button>

        <button
          onClick={() => setActiveTab('passes')}
          className={`flex items-center gap-2 px-5 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${
            activeTab === 'passes'
              ? 'border-amber-700 text-amber-800 bg-amber-50/50'
              : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <CreditCard className="w-4 h-4" />
          School Bus Passes ({passengers.filter((p) => p.status === 'Active').length})
        </button>
      </div>

      {/* 4. Tab 1: Vehicles */}
      {activeTab === 'vehicles' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-slate-600">Type Filter:</span>
              <div className="flex gap-1.5">
                {['all', 'Bus', 'Minibus', 'Van'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedVehicleTypeFilter(t)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                      selectedVehicleTypeFilter === t
                        ? 'bg-amber-700 text-white shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {t === 'all' ? 'All Vehicles' : t}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-xs text-slate-400">
              Showing {filteredVehicles.length} of {vehicles.length} fleet units
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {filteredVehicles.map((v) => {
              const bookedSeats = passengers.filter((p) => p.vehicleId === v.id && p.status === 'Active').length;
              const loadPercent = Math.round((bookedSeats / v.seatingCapacity) * 100);

              return (
                <div
                  key={v.id}
                  className="bg-white rounded-xl border border-slate-200 p-5 space-y-4 hover:border-amber-500/50 hover:shadow-md transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200">
                        {v.vehicleNumber}
                      </span>
                      <h3 className="font-bold text-slate-900 text-base mt-2">{v.vehicleModel}</h3>
                      <span className="text-xs text-slate-500">{v.vehicleType}</span>
                    </div>
                    <span
                      className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                        v.status === 'Active'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {v.status}
                    </span>
                  </div>

                  {/* Capacity Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-500">Occupancy</span>
                      <span className="text-slate-900">
                        {bookedSeats} / {v.seatingCapacity} Seats ({loadPercent}%)
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          loadPercent >= 100
                            ? 'bg-rose-600'
                            : loadPercent > 75
                            ? 'bg-amber-500'
                            : 'bg-emerald-600'
                        }`}
                        style={{ width: `${Math.min(100, loadPercent)}%` }}
                      />
                    </div>
                  </div>

                  {/* Driver & Crew Info */}
                  <div className="pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
                    <div className="flex items-center gap-2">
                      <UserCheck className="w-3.5 h-3.5 text-amber-700" />
                      <span className="font-medium text-slate-900">{v.driverName}</span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-500">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      <span>{v.driverPhone}</span>
                    </div>
                    {v.helperName && (
                      <div className="text-[11px] text-slate-500">
                        Conductor: <span className="font-medium text-slate-700">{v.helperName}</span> ({v.helperPhone})
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                    <button
                      onClick={() => openEditVehicle(v)}
                      className="px-3 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition"
                    >
                      Edit Bus
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Tab 2: Routes & Stops */}
      {activeTab === 'routes' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Active Transit Network</h2>
              <p className="text-xs text-slate-500">
                Morning pickup & afternoon return stages with distance in kilometers and flat monthly fare
              </p>
            </div>
            <button
              onClick={openNewRoute}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Transit Route
            </button>
          </div>

          <div className="space-y-4">
            {routes.map((r) => {
              const allocatedCount = passengers.filter((p) => p.routeId === r.id && p.status === 'Active').length;

              return (
                <div key={r.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-amber-800 bg-amber-50 px-2.5 py-1 rounded border border-amber-200">
                        {r.routeCode}
                      </span>
                      <div>
                        <h3 className="font-bold text-slate-900 text-base">{r.routeName}</h3>
                        <p className="text-xs text-slate-500">
                          {r.startPoint} ➔ {r.endPoint} • <span className="font-semibold text-slate-700">{r.distanceKm} km</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-xs">
                      <div>
                        <span className="text-slate-400">Monthly Fare:</span>{' '}
                        <span className="font-bold text-slate-900">${r.monthlyFee.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Assigned Bus:</span>{' '}
                        <span className="font-mono font-semibold text-emerald-800">{r.vehicleNumber || 'None'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Commuters:</span>{' '}
                        <span className="font-bold text-amber-700">{allocatedCount}</span>
                      </div>
                      <button
                        onClick={() => openEditRoute(r)}
                        className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Stop sequence */}
                  <div>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
                      Boarding Stages & Schedule ({r.stops.length} stops)
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {r.stops.map((s, idx) => (
                        <div
                          key={s.id}
                          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs flex items-center gap-2"
                        >
                          <span className="w-5 h-5 rounded-full bg-amber-700 text-white flex items-center justify-center font-bold text-[10px]">
                            {idx + 1}
                          </span>
                          <div>
                            <div className="font-semibold text-slate-800">{s.stopName}</div>
                            <div className="text-[10px] text-slate-400">
                              Pickup: {s.pickupTime || r.pickupTime} • Drop: {s.dropTime || r.dropTime}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. Tab 3: Passengers */}
      {activeTab === 'passengers' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3 flex-1">
              <div className="relative min-w-[280px]">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search commuter name, route, stop, seat..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-600"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={selectedRouteFilter}
                  onChange={(e) => setSelectedRouteFilter(e.target.value)}
                  className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-600"
                >
                  <option value="all">All Transit Routes</option>
                  {routes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.routeCode}: {r.routeName}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="text-xs text-slate-400 font-medium">
              Showing {filteredPassengers.length} of {passengers.length} commuter allocations
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Pass ID</th>
                    <th className="py-3 px-4">Commuter Name</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Class / Designation</th>
                    <th className="py-3 px-4">Route</th>
                    <th className="py-3 px-4">Boarding Stop</th>
                    <th className="py-3 px-4 text-center">Bus Plate</th>
                    <th className="py-3 px-4 text-center">Seat No</th>
                    <th className="py-3 px-4 text-right">Monthly Fee</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredPassengers.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-medium text-amber-800 text-xs">
                        #{p.id.toString().padStart(4, '0')}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{p.patronName}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            p.passengerType === 'Student'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}
                        >
                          {p.passengerType}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-600">{p.rollOrDesignation || '-'}</td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-xs font-bold text-slate-700">{p.routeCode}</span>
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-700">{p.stopName || 'Campus Origin'}</td>
                      <td className="py-3 px-4 text-center font-mono text-xs text-slate-600">
                        {p.vehicleNumber || '-'}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-xs font-bold text-amber-800">
                        {p.seatNumber || 'Assigned'}
                      </td>
                      <td className="py-3 px-4 text-right font-medium text-slate-900">
                        ${p.monthlyFare.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                            p.status === 'Active'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {p.status === 'Active' && (
                          <button
                            onClick={() => {
                              if (window.confirm(`Cancel transport allocation for '${p.patronName}'?`)) {
                                storage.cancelPassengerAllocation(p.id, 'User cancelled');
                                refreshAll();
                              }
                            }}
                            className="text-xs font-semibold text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-2 py-1 rounded"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {filteredPassengers.length === 0 && (
                    <tr>
                      <td colSpan={11} className="py-8 text-center text-slate-400">
                        No commuters found matching filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 7. Tab 4: Bus Transit Passes */}
      {activeTab === 'passes' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between shadow-sm">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Printable Student & Faculty Bus Passes</h2>
              <p className="text-xs text-slate-500">
                Official CR80 PVC transit cards with route codes, boarding stops, seat allocations & emergency contacts
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {passengers
              .filter((p) => p.status === 'Active')
              .map((p) => (
                <div
                  key={p.id}
                  className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      PASS-{p.id.toString().padStart(4, '0')}
                    </span>
                    <span className="text-xs font-semibold text-slate-500">{p.passengerType}</span>
                  </div>

                  <div>
                    <h4 className="font-bold text-slate-900 text-sm">{p.patronName}</h4>
                    <p className="text-xs text-slate-500">{p.rollOrDesignation || '-'}</p>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Route:</span>
                      <span className="font-semibold text-slate-800">{p.routeCode}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Boarding Stop:</span>
                      <span className="font-medium text-slate-800 truncate max-w-[180px]">{p.stopName}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Bus Plate:</span>
                      <span className="font-mono text-emerald-800 font-semibold">{p.vehicleNumber}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Seat Number:</span>
                      <span className="font-bold text-amber-700">{p.seatNumber}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedPassengerForPass(p);
                      setShowPassModal(true);
                    }}
                    className="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-300 hover:bg-amber-100 rounded-lg transition"
                  >
                    <CreditCard className="w-3.5 h-3.5" />
                    Print CR80 Bus Pass
                  </button>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL: ALLOCATE COMMUTER MODAL
      ======================================================== */}
      {showAllocateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">Allocate Commuter to Transit Route</h3>
              <button
                onClick={() => setShowAllocateModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConfirmAllocate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Passenger Type *</label>
                <select
                  value={allocateForm.passengerType}
                  onChange={(e) => {
                    const t = e.target.value as 'Student' | 'Teacher' | 'Staff';
                    setAllocateForm({
                      ...allocateForm,
                      passengerType: t,
                      monthlyFare: t === 'Student' ? 2500.0 : 0.0,
                    });
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="Student">Student Commuter</option>
                  <option value="Teacher">Teacher / Faculty</option>
                  <option value="Staff">School Staff</option>
                </select>
              </div>

              {allocateForm.passengerType === 'Student' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Select Student *</label>
                  <select
                    value={allocateForm.studentId}
                    onChange={(e) => setAllocateForm({ ...allocateForm, studentId: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {students.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.studentId} — {s.fullName} (Class {s.className})
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Select Faculty / Teacher *</label>
                  <select
                    value={allocateForm.teacherId}
                    onChange={(e) => setAllocateForm({ ...allocateForm, teacherId: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {teachers.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.employeeId} — {t.fullName} ({t.designation || 'Faculty'})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Route *</label>
                <select
                  value={allocateForm.routeId}
                  onChange={(e) => {
                    const rId = parseInt(e.target.value, 10);
                    const selRoute = routes.find((r) => r.id === rId);
                    setAllocateForm({
                      ...allocateForm,
                      routeId: rId,
                      stopId: selRoute?.stops[0]?.id || 1,
                      monthlyFare: allocateForm.passengerType === 'Student' ? (selRoute?.monthlyFee || 2500) : 0,
                    });
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {routes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.routeCode}: {r.routeName} [{r.vehicleNumber || 'No Bus'}]
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Boarding Stop Stage</label>
                <select
                  value={allocateForm.stopId}
                  onChange={(e) => setAllocateForm({ ...allocateForm, stopId: parseInt(e.target.value, 10) })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  {routes
                    .find((r) => r.id === allocateForm.routeId)
                    ?.stops.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.stopOrder}. {s.stopName} (Pickup: {s.pickupTime || '-'})
                      </option>
                    ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Seat Number</label>
                  <input
                    type="text"
                    value={allocateForm.seatNumber}
                    onChange={(e) => setAllocateForm({ ...allocateForm, seatNumber: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly Fare ($)</label>
                  <input
                    type="number"
                    disabled={allocateForm.passengerType !== 'Student'}
                    value={allocateForm.monthlyFare}
                    onChange={(e) => setAllocateForm({ ...allocateForm, monthlyFare: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Remarks</label>
                <input
                  type="text"
                  placeholder="Special instructions or medical note"
                  value={allocateForm.remarks}
                  onChange={(e) => setAllocateForm({ ...allocateForm, remarks: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowAllocateModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm"
                >
                  Confirm Allocation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL: VEHICLE MODAL (ADD / EDIT)
      ======================================================== */}
      {showVehicleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">
                {editingVehicle ? 'Edit Fleet Vehicle' : 'Register New Fleet Vehicle'}
              </h3>
              <button
                onClick={() => setShowVehicleModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveVehicle} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Plate Number *</label>
                  <input
                    type="text"
                    required
                    value={vehicleForm.vehicleNumber}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, vehicleNumber: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Vehicle Model *</label>
                  <input
                    type="text"
                    required
                    value={vehicleForm.vehicleModel}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, vehicleModel: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Type *</label>
                  <select
                    value={vehicleForm.vehicleType}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, vehicleType: e.target.value as any })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    <option value="Bus">Bus</option>
                    <option value="Minibus">Minibus</option>
                    <option value="Van">Van</option>
                    <option value="Coaster">Coaster</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Seating Capacity *</label>
                  <input
                    type="number"
                    min="5"
                    max="100"
                    required
                    value={vehicleForm.seatingCapacity}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, seatingCapacity: parseInt(e.target.value, 10) || 40 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Driver Name *</label>
                  <input
                    type="text"
                    required
                    value={vehicleForm.driverName}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, driverName: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Driver Phone *</label>
                  <input
                    type="text"
                    required
                    value={vehicleForm.driverPhone}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, driverPhone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Helper Name</label>
                  <input
                    type="text"
                    value={vehicleForm.helperName}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, helperName: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Helper Phone</label>
                  <input
                    type="text"
                    value={vehicleForm.helperPhone}
                    onChange={(e) => setVehicleForm({ ...vehicleForm, helperPhone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Status</label>
                <select
                  value={vehicleForm.status}
                  onChange={(e) => setVehicleForm({ ...vehicleForm, status: e.target.value as any })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="Active">Active</option>
                  <option value="Maintenance">Maintenance</option>
                  <option value="Out of Service">Out of Service</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowVehicleModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm"
                >
                  Save Vehicle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL: ROUTE MODAL (ADD / EDIT)
      ======================================================== */}
      {showRouteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">
                {editingRoute ? 'Edit Transit Route' : 'Create New Transit Route'}
              </h3>
              <button
                onClick={() => setShowRouteModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveRoute} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Route Code *</label>
                  <input
                    type="text"
                    required
                    value={routeForm.routeCode}
                    onChange={(e) => setRouteForm({ ...routeForm, routeCode: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Bus</label>
                  <select
                    value={routeForm.vehicleId}
                    onChange={(e) => setRouteForm({ ...routeForm, vehicleId: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                  >
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.vehicleNumber} ({v.seatingCapacity} seats)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Route Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Route 04: Badda - Rampura - Campus"
                  value={routeForm.routeName}
                  onChange={(e) => setRouteForm({ ...routeForm, routeName: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Origin Point *</label>
                  <input
                    type="text"
                    required
                    value={routeForm.startPoint}
                    onChange={(e) => setRouteForm({ ...routeForm, startPoint: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Destination *</label>
                  <input
                    type="text"
                    required
                    value={routeForm.endPoint}
                    onChange={(e) => setRouteForm({ ...routeForm, endPoint: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Distance (km)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={routeForm.distanceKm}
                    onChange={(e) => setRouteForm({ ...routeForm, distanceKm: parseFloat(e.target.value) || 10 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly Fee ($)</label>
                  <input
                    type="number"
                    value={routeForm.monthlyFee}
                    onChange={(e) => setRouteForm({ ...routeForm, monthlyFee: parseFloat(e.target.value) || 2500 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-bold"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowRouteModal(false)}
                  className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm"
                >
                  Save Route
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL: CR80 PVC SCHOOL BUS TRANSIT PASS MODAL
      ======================================================== */}
      {showPassModal && selectedPassengerForPass && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-lg text-slate-900">CR80 PVC Bus Transit Pass</h3>
              <button
                onClick={() => setShowPassModal(false)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Simulated CR80 Card Frame (85.6mm x 54mm) */}
            <div className="mx-auto w-[340px] h-[215px] bg-white rounded-2xl shadow-lg border-2 border-slate-300 overflow-hidden relative flex flex-col justify-between">
              {/* Header Bar */}
              <div className="bg-amber-700 text-white px-4 py-2 text-center">
                <div className="text-[11px] font-bold tracking-wide uppercase">Ideal Model High School & College</div>
                <div className="text-[9px] font-semibold text-amber-200 tracking-wider">OFFICIAL SCHOOL BUS TRANSIT PASS</div>
              </div>

              {/* Body */}
              <div className="p-3.5 flex gap-3 items-center flex-1">
                <div className="w-16 h-20 bg-amber-50 border border-amber-300 rounded-lg flex flex-col items-center justify-center text-amber-800 font-bold text-xs shadow-inner shrink-0">
                  <div className="text-lg">
                    {selectedPassengerForPass.patronName
                      .split(' ')
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join('')}
                  </div>
                  <span className="text-[8px] uppercase tracking-wider text-amber-700 mt-1">
                    {selectedPassengerForPass.passengerType}
                  </span>
                </div>

                <div className="space-y-1 text-xs">
                  <div className="font-bold text-slate-900 text-sm leading-tight">
                    {selectedPassengerForPass.patronName}
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    {selectedPassengerForPass.rollOrDesignation || '-'}
                  </div>
                  <div className="font-mono text-[11px] text-amber-800 font-bold">
                    {selectedPassengerForPass.routeCode} • {selectedPassengerForPass.seatNumber}
                  </div>
                  <div className="text-[10px] text-slate-600">
                    Stop: <span className="font-semibold text-slate-800">{selectedPassengerForPass.stopName}</span>
                  </div>
                  <div className="text-[9px] text-slate-400">
                    Bus: {selectedPassengerForPass.vehicleNumber} • Valid 2026
                  </div>
                </div>
              </div>

              {/* Barcode Graphic */}
              <div className="px-4 py-1.5 bg-slate-50 border-t border-slate-200 flex flex-col items-center justify-center">
                <div className="flex items-center gap-[2px] h-4">
                  {selectedPassengerForPass.routeCode.split('').map((char, i) => (
                    <div
                      key={i}
                      className="bg-slate-900 h-full"
                      style={{
                        width: (char.charCodeAt(0) % 3) + 1.2 + 'px',
                        marginRight: (char.charCodeAt(0) % 2) + 0.5 + 'px',
                      }}
                    />
                  ))}
                  {selectedPassengerForPass.patronName.split('').slice(0, 6).map((char, i) => (
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
                  *BUS-{String(selectedPassengerForPass.id).padStart(4, '0')}*
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t">
              <span className="text-xs text-slate-400">ISO/IEC 7810 ID-1 PVC Standard</span>
              <button
                onClick={() => window.print()}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm"
              >
                <Printer className="w-4 h-4" />
                Print PVC Pass
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
