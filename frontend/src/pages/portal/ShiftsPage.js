import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import {
import { API_BASE_URL, API_ROOT_URL } from './';
  CalendarClock,
  Loader2,
  Plus,
  MoreHorizontal,
  UserPlus,
  UserX,
  CheckCircle2,
  Eye,
  Download,
  Printer,
} from 'lucide-react';

const API = API_BASE_URL;

const STATUS_OPTIONS = ['open', 'assigned', 'completed', 'cancelled'];

const statusClass = {
  open: 'bg-blue-50 text-blue-700 border-blue-200',
  assigned: 'bg-amber-50 text-amber-700 border-amber-200',
  completed: 'bg-green-50 text-green-700 border-green-200',
  cancelled: 'bg-gray-100 text-gray-700 border-gray-300',
};

function formatDateTime(value) {
  if (!value) return '—';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

function toIso(value) {
  if (!value) return null;
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return null;
  return dt.toISOString();
}

function normalizeOptionalId(value) {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text) return null;
  const lowered = text.toLowerCase();
  if (lowered === 'none' || lowered === 'null' || lowered === 'undefined') return null;
  return text;
}

function getInitialNewShift(defaultServiceUserId = '') {
  const normalizedServiceUserId = normalizeOptionalId(defaultServiceUserId) || '';
  return {
    shift_type: normalizedServiceUserId ? 'service_user_visit' : 'care_location',
    start_at: '',
    end_at: '',
    location_text: '',
    role_required: '',
    service_user_id: normalizedServiceUserId,
    care_location_id: '',
    notes: '',
  };
}

function getServiceUserDisplayName(serviceUser) {
  if (!serviceUser) return '';
  return serviceUser.full_name || serviceUser.service_user_code || serviceUser.id || '';
}

function getServiceUserLocationFallback(serviceUser) {
  if (!serviceUser) return '';
  const name = getServiceUserDisplayName(serviceUser);
  const addressBits = [serviceUser.address_line_1, serviceUser.city, serviceUser.postcode].filter(Boolean);
  if (!name) return addressBits.join(', ');
  if (addressBits.length === 0) return name;
  return `${name} - ${addressBits.join(', ')}`;
}

function getShiftLocationLabel(shift) {
  if (!shift) return '';
  return shift?.location_text || shift?.care_location?.name || shift?.service_user_name || 'Location pending';
}

function normalizeRoleText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, ' ')
    .trim();
}

function getRoleFamily(value) {
  const text = normalizeRoleText(value);
  if (!text) return 'unknown';

  const nurseTokens = ['nurse', 'registered nurse', 'rn', 'rgn', 'rmn'];
  const careTokens = [
    'healthcare assistant',
    'hca',
    'support worker',
    'care assistant',
    'care worker',
    'carer',
    'senior care assistant',
  ];

  if (nurseTokens.some((token) => text.includes(token))) return 'nurse';
  if (careTokens.some((token) => text.includes(token))) return 'care';
  return 'unknown';
}

function isEmployeeEligibleForShift(shift, employee) {
  const shiftFamily = getRoleFamily(shift?.role_required);
  if (shiftFamily === 'unknown') return true;

  const employeeRole = employee?.role || employee?.job_title || employee?.system_role;
  const workerFamily = getRoleFamily(employeeRole);
  if (workerFamily === 'unknown') return true;
  return shiftFamily === workerFamily;
}

export default function ShiftsPage() {
  const { token, isAuditor } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const serviceUserIdFilter = searchParams.get('service_user_id') || '';
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [shifts, setShifts] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [careLocations, setCareLocations] = useState([]);
  const [serviceUsers, setServiceUsers] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [detailShift, setDetailShift] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [assignEmployeeId, setAssignEmployeeId] = useState('');
  const [assignNotes, setAssignNotes] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [approvedAttendanceRecords, setApprovedAttendanceRecords] = useState([]);
  const [attendanceShiftsById, setAttendanceShiftsById] = useState({});
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attendanceSaving, setAttendanceSaving] = useState(false);
  const [selectedAttendance, setSelectedAttendance] = useState(null);
  const [isRejectAttendanceOpen, setIsRejectAttendanceOpen] = useState(false);
  const [attendanceRejectReason, setAttendanceRejectReason] = useState('');

  const [newShift, setNewShift] = useState(() => getInitialNewShift(serviceUserIdFilter));

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const activeEmployees = useMemo(
    () => (employees || []).filter((employee) => employee?.status === 'active'),
    [employees]
  );
  const employeeById = useMemo(() => {
    const map = {};
    for (const employee of employees || []) {
      if (employee?.id) {
        map[employee.id] = employee;
      }
    }
    return map;
  }, [employees]);
  const serviceUserById = useMemo(() => {
    const map = {};
    for (const serviceUser of serviceUsers || []) {
      if (serviceUser?.id) {
        map[serviceUser.id] = serviceUser;
      }
    }
    return map;
  }, [serviceUsers]);
  const shiftLocationById = useMemo(() => {
    const map = {};
    for (const shift of shifts || []) {
      if (shift?.id) map[shift.id] = getShiftLocationLabel(shift);
    }
    return map;
  }, [shifts]);

  const shiftById = useMemo(() => {
    const map = { ...attendanceShiftsById };
    for (const shift of shifts || []) {
      if (shift?.id) {
        map[shift.id] = shift;
      }
    }
    return map;
  }, [shifts, attendanceShiftsById]);

  const eligibleActiveEmployees = useMemo(() => {
    if (!selectedShift) return activeEmployees;
    return activeEmployees.filter((employee) => isEmployeeEligibleForShift(selectedShift, employee));
  }, [activeEmployees, selectedShift]);

  const getComplianceReason = (employee) => {
    const blockers = employee?.canonical_readiness?.blockers;
    if (!Array.isArray(blockers) || blockers.length === 0) return null;
    return String(blockers[0] || '').trim() || null;
  };

  const isComplianceEligible = (employee) => {
    const blockers = employee?.canonical_readiness?.blockers;
    if (!Array.isArray(blockers)) return true;
    return blockers.length === 0;
  };

  const assignableEligibleEmployees = useMemo(
    () => eligibleActiveEmployees.filter((employee) => isComplianceEligible(employee)),
    [eligibleActiveEmployees]
  );

  const blockedEligibleEmployees = useMemo(
    () => eligibleActiveEmployees.filter((employee) => !isComplianceEligible(employee)),
    [eligibleActiveEmployees]
  );

  const hasEligibleActiveEmployees = assignableEligibleEmployees.length > 0;

  useEffect(() => {
    if (!assignEmployeeId) return;
    const stillEligible = assignableEligibleEmployees.some((employee) => employee.id === assignEmployeeId);
    if (!stillEligible) {
      setAssignEmployeeId('');
    }
  }, [assignableEligibleEmployees, assignEmployeeId]);

  const getEmployeeDisplay = (employeeId) => {
    if (!employeeId) return 'Unknown employee';
    const employee = employeeById[employeeId];
    if (!employee) return employeeId;
    const fullName = `${employee.first_name || ''} ${employee.last_name || ''}`.trim();
    return fullName || employee.employee_code || employee.id;
  };

  const getShiftDisplay = (shiftId) => {
    if (!shiftId) return 'Unknown shift';
    const shift = shiftById[shiftId];
    if (!shift) return shiftId;
    const location = getShiftLocationLabel(shift);
    const role = shift.role_required || 'Role pending';
    return `${location} — ${role} (${formatDateTime(shift.start_at)} → ${formatDateTime(shift.end_at)})`;
  };

  const getShiftLocationForAttendance = (shiftId) => {
    const shift = shiftById[shiftId];
    return getShiftLocationLabel(shift) || shiftLocationById[shiftId] || '—';
  };

  const getShiftRoleForAttendance = (shiftId) => {
    const shift = shiftById[shiftId];
    return shift?.role_required || '—';
  };

  const getShiftScheduledStartForAttendance = (shiftId) => {
    const shift = shiftById[shiftId];
    return shift?.start_at ? formatDateTime(shift.start_at) : '—';
  };

  const getShiftScheduledEndForAttendance = (shiftId) => {
    const shift = shiftById[shiftId];
    return shift?.end_at ? formatDateTime(shift.end_at) : '—';
  };

  const getEmployeeCodeForAttendance = (employeeId) => {
    const employee = employeeById[employeeId];
    return employee?.employee_code || '—';
  };

  const getApprovedAttendanceExportRows = () => {
    return (approvedAttendanceRecords || []).map((row) => ({
      employeeName: getEmployeeDisplay(row.employee_id),
      employeeCode: getEmployeeCodeForAttendance(row.employee_id),
      shiftLocation: getShiftLocationForAttendance(row.shift_id),
      roleRequired: getShiftRoleForAttendance(row.shift_id),
      scheduledStart: getShiftScheduledStartForAttendance(row.shift_id),
      scheduledEnd: getShiftScheduledEndForAttendance(row.shift_id),
      clockIn: formatDateTime(row.clock_in_at),
      clockOut: formatDateTime(row.clock_out_at),
      approvedAt: formatDateTime(row.reviewed_at),
      approvedForTimesheet: row.approved_for_timesheet ? 'Yes' : 'No',
    }));
  };

  const csvEscape = (value) => {
    const text = value === null || value === undefined ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  };

  const htmlEscape = (value) => {
    const text = value === null || value === undefined ? '' : String(value);
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  const handleExportApprovedAttendanceCsv = () => {
    const rows = getApprovedAttendanceExportRows();
    if (rows.length === 0) {
      toast.error('No approved attendance records to export');
      return;
    }
    const headersRow = [
      'Employee Name',
      'Employee Code',
      'Shift Location/Care Location',
      'Role Required',
      'Scheduled Start',
      'Scheduled End',
      'Clock In',
      'Clock Out',
      'Approved At',
      'Approved For Timesheet',
    ];
    const csvLines = [
      headersRow.map(csvEscape).join(','),
      ...rows.map((item) => [
        item.employeeName,
        item.employeeCode,
        item.shiftLocation,
        item.roleRequired,
        item.scheduledStart,
        item.scheduledEnd,
        item.clockIn,
        item.clockOut,
        item.approvedAt,
        item.approvedForTimesheet,
      ].map(csvEscape).join(',')),
    ];
    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `approved_attendance_timesheet_ready_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handlePrintApprovedAttendance = () => {
    const rows = getApprovedAttendanceExportRows();
    if (rows.length === 0) {
      toast.error('No approved attendance records to print');
      return;
    }
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toast.error('Could not open print window');
      return;
    }
    const generatedAt = formatDateTime(new Date().toISOString());
    const logoSrc = `${window.location.origin}/osabea_logo.png`;
    const tableRows = rows.map((item) => `
      <tr>
        <td>${htmlEscape(item.employeeName)}</td>
        <td>${htmlEscape(item.employeeCode)}</td>
        <td>${htmlEscape(item.shiftLocation)}</td>
        <td>${htmlEscape(item.roleRequired)}</td>
        <td>${htmlEscape(item.scheduledStart)}</td>
        <td>${htmlEscape(item.scheduledEnd)}</td>
        <td>${htmlEscape(item.clockIn)}</td>
        <td>${htmlEscape(item.clockOut)}</td>
        <td>${htmlEscape(item.approvedAt)}</td>
        <td>${htmlEscape(item.approvedForTimesheet)}</td>
      </tr>
    `).join('');

    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <title>Approved Attendance / Timesheet Ready</title>
          <style>
            :root {
              --brand-primary: #0D6E6E;
              --brand-secondary: #1F2937;
              --brand-muted: #6B7280;
              --brand-border: #D1D5DB;
              --surface: #F9FAFB;
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              padding: 18px;
              font-family: "Segoe UI", Arial, sans-serif;
              color: var(--brand-secondary);
              background: #ffffff;
            }
            .document {
              max-width: 1040px;
              margin: 0 auto;
            }
            .header {
              text-align: center;
              margin-bottom: 12px;
            }
            .logo {
              max-height: 56px;
              width: auto;
              display: block;
              margin: 0 auto 8px;
            }
            .company {
              margin: 0;
              font-size: 14px;
              font-weight: 600;
              color: var(--brand-secondary);
            }
            .title {
              margin: 4px 0 0;
              font-size: 22px;
              font-weight: 700;
              color: var(--brand-primary);
            }
            .meta {
              margin: 6px 0 0;
              font-size: 12px;
              color: var(--brand-muted);
            }
            .section-heading {
              margin: 14px 0 8px;
              font-size: 13px;
              font-weight: 700;
              color: var(--brand-primary);
              text-transform: uppercase;
              letter-spacing: 0.04em;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              font-size: 11px;
              background: #fff;
            }
            th, td {
              border: 1px solid var(--brand-border);
              padding: 7px;
              text-align: left;
              vertical-align: top;
            }
            th {
              background: var(--brand-primary);
              color: #ffffff;
              font-weight: 600;
            }
            tr:nth-child(even) td {
              background: var(--surface);
            }
            .footer {
              margin-top: 14px;
              padding-top: 8px;
              border-top: 1px solid #E5E7EB;
              text-align: center;
              color: var(--brand-muted);
              font-size: 11px;
            }
            @media print {
              body { padding: 0; }
              .document { max-width: none; }
            }
          </style>
        </head>
        <body>
          <main class="document">
            <header class="header">
              <img class="logo" src="${htmlEscape(logoSrc)}" alt="Osabea Healthcare Solutions logo" />
              <p class="company">Osabea Healthcare Solutions</p>
              <h1 class="title">Approved Attendance / Timesheet Ready</h1>
              <p class="meta">Generated: ${htmlEscape(generatedAt)}</p>
            </header>

            <h2 class="section-heading">Approved Attendance Register</h2>
            <table>
              <thead>
                <tr>
                  <th>Employee Name</th>
                  <th>Employee Code</th>
                  <th>Shift Location / Care Location</th>
                  <th>Role Required</th>
                  <th>Scheduled Start</th>
                  <th>Scheduled End</th>
                  <th>Clock In</th>
                  <th>Clock Out</th>
                  <th>Approved At</th>
                  <th>Approved For Timesheet</th>
                </tr>
              </thead>
              <tbody>${tableRows}</tbody>
            </table>

            <footer class="footer">
              <div>Osabea Healthcare Solutions</div>
              <div>Page generated from Compliance Portal</div>
            </footer>
          </main>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  const fetchShifts = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (serviceUserIdFilter) params.service_user_id = serviceUserIdFilter;
      const res = await axios.get(`${API}/shifts`, { params, headers });
      setShifts(res.data?.shifts || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load shifts');
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveEmployees = async () => {
    try {
      const res = await axios.get(`${API}/staff/employees`, {
        headers,
      });
      const rows = Array.isArray(res.data) ? res.data : (res.data?.employees || []);
      const employeeIds = rows.map((employee) => employee.id).filter(Boolean);
      const readinessRes = employeeIds.length > 0
        ? await axios.get(`${API}/employees/unified-progress-summary`, {
            params: { employee_ids: employeeIds.join(',') },
            headers,
          }).catch(() => ({ data: [] }))
        : { data: [] };
      const readinessByEmployeeId = new Map(
        (readinessRes.data || []).map((summary) => [summary.employee_id, summary])
      );
      setEmployees(rows.map((employee) => ({
        ...employee,
        canonical_readiness: readinessByEmployeeId.get(employee.id) || null,
      })));
    } catch (error) {
      toast.error('Failed to load active employees for assignment');
    }
  };

  const fetchActiveCareLocations = async () => {
    try {
      const res = await axios.get(`${API}/care-locations`, {
        headers,
        params: { include_inactive: false },
      });
      const rows = Array.isArray(res.data)
        ? res.data
        : (res.data?.care_locations || []);
      setCareLocations(rows.filter((loc) => loc?.is_active !== false));
    } catch (error) {
      toast.error('Failed to load care locations');
    }
  };

  const fetchServiceUsers = async () => {
    try {
      const res = await axios.get(`${API}/service-users`, { headers });
      const rows = Array.isArray(res.data) ? res.data : (res.data?.service_users || []);
      setServiceUsers(rows);
    } catch (error) {
      toast.error('Failed to load service users');
    }
  };

  const fetchAttendanceQueue = async () => {
    try {
      setAttendanceLoading(true);
      const [submittedRes, approvedRes] = await Promise.all([
        axios.get(`${API}/shift-attendance`, {
          headers,
          params: { status: 'submitted' },
        }),
        axios.get(`${API}/shift-attendance`, {
          headers,
          params: { status: 'approved' },
        }),
      ]);
      const submittedRows = submittedRes.data?.attendance_records || [];
      const approvedRows = approvedRes.data?.attendance_records || [];
      const combinedRows = [...submittedRows, ...approvedRows];
      setAttendanceRecords(submittedRows);
      setApprovedAttendanceRecords(approvedRows);

      const knownShiftIds = new Set((shifts || []).map((shift) => shift?.id).filter(Boolean));
      const missingShiftIds = [...new Set(combinedRows.map((row) => row?.shift_id).filter(Boolean))]
        .filter((shiftId) => !knownShiftIds.has(shiftId));
      if (missingShiftIds.length > 0) {
        const shiftResponses = await Promise.all(
          missingShiftIds.map((shiftId) => axios.get(`${API}/shifts/${shiftId}`, { headers }))
        );
        const next = {};
        for (const response of shiftResponses) {
          const shift = response.data?.shift;
          if (shift?.id) next[shift.id] = shift;
        }
        if (Object.keys(next).length > 0) {
          setAttendanceShiftsById((prev) => ({ ...prev, ...next }));
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load attendance review queue');
    } finally {
      setAttendanceLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    fetchShifts();
    fetchActiveEmployees();
    fetchActiveCareLocations();
    fetchServiceUsers();
    if (!isAuditor()) {
      fetchAttendanceQueue();
    }
  }, [token, statusFilter, serviceUserIdFilter]);

  const handleApproveAttendance = async (attendanceId) => {
    if (!attendanceId) return;
    try {
      setAttendanceSaving(true);
      await axios.post(
        `${API}/shift-attendance/${attendanceId}/approve`,
        { reason: null },
        { headers }
      );
      toast.success('Attendance approved');
      fetchAttendanceQueue();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve attendance');
    } finally {
      setAttendanceSaving(false);
    }
  };

  const handleRejectAttendance = async () => {
    if (!selectedAttendance?.id) {
      toast.error('Attendance record not found');
      return;
    }
    const reason = (attendanceRejectReason || '').trim();
    if (reason.length < 3) {
      toast.error('Rejection reason must be at least 3 characters');
      return;
    }
    try {
      setAttendanceSaving(true);
      await axios.post(
        `${API}/shift-attendance/${selectedAttendance.id}/reject`,
        { reason },
        { headers }
      );
      toast.success('Attendance rejected');
      setIsRejectAttendanceOpen(false);
      setSelectedAttendance(null);
      setAttendanceRejectReason('');
      fetchAttendanceQueue();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject attendance');
    } finally {
      setAttendanceSaving(false);
    }
  };

  const handleCreateShift = async (e) => {
    e.preventDefault();
    const startIso = toIso(newShift.start_at);
    const endIso = toIso(newShift.end_at);
    if (!startIso || !endIso) {
      toast.error('Start and end date/time are required');
      return;
    }
    const shiftType = newShift.shift_type || 'care_location';
    const serviceUserId = normalizeOptionalId(newShift.service_user_id);
    const careLocationId = normalizeOptionalId(newShift.care_location_id);
    const selectedServiceUser = serviceUserId ? serviceUserById[serviceUserId] : null;
    const selectedCareLocation = careLocationId
      ? careLocations.find((location) => location.id === careLocationId)
      : null;
    if (shiftType === 'care_location' && !careLocationId) {
      toast.error('Select a care location for this shift type');
      return;
    }
    if (shiftType === 'service_user_visit' && !serviceUserId) {
      toast.error('Select a service user for this shift type');
      return;
    }
    const autoLocationText = shiftType === 'care_location'
      ? (selectedCareLocation?.name || '')
      : shiftType === 'service_user_visit'
        ? getServiceUserLocationFallback(selectedServiceUser)
        : '';
    const locationText = (newShift.location_text || '').trim() || autoLocationText;
    if (!locationText) {
      toast.error('Location is required');
      return;
    }
    setSaving(true);
    try {
      await axios.post(
        `${API}/shifts`,
        {
          start_at: startIso,
          end_at: endIso,
          location_text: locationText,
          role_required: newShift.role_required,
          service_user_id: serviceUserId,
          care_location_id: careLocationId,
          notes: newShift.notes || null,
        },
        { headers }
      );
      toast.success('Shift created');
      setIsCreateOpen(false);
      setNewShift(getInitialNewShift(serviceUserIdFilter));
      fetchShifts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create shift');
    } finally {
      setSaving(false);
    }
  };

  const openShiftDetail = async (shiftId) => {
    setDetailLoading(true);
    try {
      const res = await axios.get(`${API}/shifts/${shiftId}`, { headers });
      setDetailShift(res.data || null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load shift detail');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedShift?.id || !assignEmployeeId) {
      toast.error('Select an employee to assign');
      return;
    }
    setAssigning(true);
    try {
      await axios.post(
        `${API}/shifts/${selectedShift.id}/assign`,
        { employee_id: assignEmployeeId, notes: assignNotes || null },
        { headers }
      );
      toast.success('Worker assigned to shift');
      setIsAssignOpen(false);
      setAssignEmployeeId('');
      setAssignNotes('');
      fetchShifts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign worker');
    } finally {
      setAssigning(false);
    }
  };

  const handleUnassign = async (shiftId) => {
    try {
      await axios.post(
        `${API}/shifts/${shiftId}/unassign`,
        { reason: null },
        { headers }
      );
      toast.success('Worker unassigned');
      fetchShifts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unassign worker');
    }
  };

  const handleComplete = async (shiftId) => {
    try {
      await axios.post(`${API}/shifts/${shiftId}/complete`, {}, { headers });
      toast.success('Shift marked as completed');
      fetchShifts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete shift');
    }
  };

  const handleCancelShift = async () => {
    if (!selectedShift?.id) {
      toast.error('Shift not found');
      return;
    }
    const reason = (cancelReason || '').trim();
    if (reason.length < 3) {
      toast.error('Cancellation reason must be at least 3 characters');
      return;
    }
    setSaving(true);
    try {
      await axios.patch(
        `${API}/shifts/${selectedShift.id}`,
        { status: 'cancelled', cancel_reason: reason },
        { headers }
      );
      toast.success('Shift cancelled');
      setIsCancelOpen(false);
      setSelectedShift(null);
      setCancelReason('');
      fetchShifts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel shift');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="shifts-page">
      {serviceUserIdFilter && (
        <div className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
          <span className="text-sm text-blue-700 font-medium">Filtered by service user</span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 border-blue-200 text-blue-700 hover:bg-blue-100"
            onClick={() => {
              const next = new URLSearchParams(searchParams);
              next.delete('service_user_id');
              setSearchParams(next, { replace: true });
            }}
          >
            Clear filter
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">Shifts</h1>
          <p className="text-text-muted mt-1">Create and operate shifts with canonical assignment truth.</p>
        </div>
        {!isAuditor() && (
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="w-full sm:w-auto">
                <Plus className="h-4 w-4 mr-2" />
                Create Shift
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-xl">
              <DialogHeader>
                <DialogTitle>Create Shift</DialogTitle>
                <DialogDescription>Select the shift type, then confirm the linked location or service user.</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateShift} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="start_at">Start</Label>
                    <Input
                      id="start_at"
                      type="datetime-local"
                      value={newShift.start_at}
                      onChange={(e) => setNewShift((prev) => ({ ...prev, start_at: e.target.value }))}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end_at">End</Label>
                    <Input
                      id="end_at"
                      type="datetime-local"
                      value={newShift.end_at}
                      onChange={(e) => setNewShift((prev) => ({ ...prev, end_at: e.target.value }))}
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="shift_type">Shift Type</Label>
                  <Select
                    value={newShift.shift_type}
                    onValueChange={(value) => setNewShift((prev) => ({
                      ...prev,
                      shift_type: value,
                      service_user_id: value === 'care_location' || value === 'external_location' ? '' : prev.service_user_id,
                      care_location_id: value === 'service_user_visit' || value === 'external_location' ? '' : prev.care_location_id,
                    }))}
                  >
                    <SelectTrigger id="shift_type">
                      <SelectValue placeholder="Select shift type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="care_location">Care location shift</SelectItem>
                      <SelectItem value="service_user_visit">Service user visit</SelectItem>
                      <SelectItem value="external_location">External location</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role_required">Role Required</Label>
                  <Input
                    id="role_required"
                    value={newShift.role_required}
                    onChange={(e) => setNewShift((prev) => ({ ...prev, role_required: e.target.value }))}
                    required
                  />
                </div>
                {newShift.shift_type === 'care_location' ? (
                  <div className="space-y-2">
                    <Label htmlFor="care_location_id">Care Location</Label>
                    <Select
                      value={newShift.care_location_id || 'none'}
                      onValueChange={(value) => {
                        const nextId = value === 'none' ? '' : value;
                        const selectedLocation = careLocations.find((loc) => loc.id === nextId);
                        setNewShift((prev) => ({
                          ...prev,
                          care_location_id: nextId,
                          service_user_id: '',
                          location_text: prev.location_text || selectedLocation?.name || '',
                        }));
                      }}
                    >
                      <SelectTrigger id="care_location_id">
                        <SelectValue placeholder="Select care location" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select care location</SelectItem>
                        {careLocations.map((loc) => (
                          <SelectItem key={loc.id} value={loc.id}>
                            {loc.name} {loc.city ? `(${loc.city})` : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ) : null}
                {newShift.shift_type === 'service_user_visit' ? (
                  <div className="space-y-2">
                    <Label htmlFor="service_user_id">Service User</Label>
                    <Select
                      value={newShift.service_user_id || 'none'}
                      onValueChange={(value) => {
                        const nextId = value === 'none' ? '' : value;
                        const selectedServiceUser = serviceUserById[nextId];
                        setNewShift((prev) => ({
                          ...prev,
                          service_user_id: nextId,
                          care_location_id: '',
                          location_text: prev.location_text || getServiceUserLocationFallback(selectedServiceUser),
                        }));
                      }}
                    >
                      <SelectTrigger id="service_user_id">
                        <SelectValue placeholder="Select service user" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select service user</SelectItem>
                        {serviceUsers.map((serviceUser) => (
                          <SelectItem key={serviceUser.id} value={serviceUser.id}>
                            {getServiceUserDisplayName(serviceUser) || serviceUser.id}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {newShift.service_user_id && serviceUserById[newShift.service_user_id] ? (
                      <p className="text-xs text-text-muted">
                        {getServiceUserLocationFallback(serviceUserById[newShift.service_user_id])}
                      </p>
                    ) : null}
                  </div>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="location_text">
                    {newShift.shift_type === 'external_location' ? 'Location' : 'Location Text Override / Fallback'}
                  </Label>
                  <Input
                    id="location_text"
                    value={newShift.location_text}
                    onChange={(e) => setNewShift((prev) => ({ ...prev, location_text: e.target.value }))}
                    placeholder={
                      newShift.shift_type === 'care_location'
                        ? 'Defaults to selected care location name'
                        : newShift.shift_type === 'service_user_visit'
                          ? 'Defaults to selected service user name/address'
                          : 'Enter external location'
                    }
                    required={newShift.shift_type === 'external_location'}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="shift_notes">Notes (optional)</Label>
                  <Textarea
                    id="shift_notes"
                    value={newShift.notes}
                    onChange={(e) => setNewShift((prev) => ({ ...prev, notes: e.target.value }))}
                    rows={3}
                  />
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Create
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5 text-primary" />
            Shift Operations
          </CardTitle>
          <div className="w-full sm:w-56">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : shifts.length === 0 ? (
            <p className="text-text-muted py-4">No shifts found.</p>
          ) : (
            <div className="space-y-3">
              {shifts.map((shift) => (
                <div key={shift.id} className="border rounded-lg p-3 sm:p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="font-medium text-text-primary">{getShiftLocationLabel(shift)}</p>
                      {shift.care_location ? (
                        <p className="text-xs text-text-muted">
                          Care location: {shift.care_location.name}
                          {shift.care_location.address_line_1 ? `, ${shift.care_location.address_line_1}` : ''}
                          {shift.care_location.city ? `, ${shift.care_location.city}` : ''}
                        </p>
                      ) : null}
                      {shift.service_user_name ? (
                        <p className="text-xs text-text-muted">Service user: {shift.service_user_name}</p>
                      ) : null}
                      <p className="text-sm text-text-muted">{shift.role_required}</p>
                      <p className="text-xs text-text-muted">
                        {formatDateTime(shift.start_at)} → {formatDateTime(shift.end_at)}
                      </p>
                      {shift.assigned_employee_id && (
                        <p className="text-xs text-text-muted">Assigned employee: {shift.assigned_employee_id}</p>
                      )}
                      {shift.latest_assignment?.worker_response_status && (
                        <p className="text-xs text-text-muted">
                          Worker response: {shift.latest_assignment.worker_response_status}
                          {shift.latest_assignment.worker_response_note ? ` — ${shift.latest_assignment.worker_response_note}` : ''}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className={statusClass[shift.status] || ''}>
                        {shift.status}
                      </Badge>
                      {!isAuditor() && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openShiftDetail(shift.id)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Detail
                            </DropdownMenuItem>
                            {shift.status !== 'completed' && shift.status !== 'cancelled' && !shift.assigned_employee_id && (
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedShift(shift);
                                  setIsAssignOpen(true);
                                }}
                              >
                                <UserPlus className="h-4 w-4 mr-2" />
                                Assign Worker
                              </DropdownMenuItem>
                            )}
                            {shift.assigned_employee_id && shift.status !== 'completed' && shift.status !== 'cancelled' && (
                              <DropdownMenuItem onClick={() => handleUnassign(shift.id)}>
                                <UserX className="h-4 w-4 mr-2" />
                                Unassign Worker
                              </DropdownMenuItem>
                            )}
                            {shift.status === 'assigned' && (
                              <DropdownMenuItem onClick={() => handleComplete(shift.id)}>
                                <CheckCircle2 className="h-4 w-4 mr-2" />
                                Complete Shift
                              </DropdownMenuItem>
                            )}
                            {shift.status !== 'completed' && shift.status !== 'cancelled' && (
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedShift(shift);
                                  setCancelReason('');
                                  setIsCancelOpen(true);
                                }}
                              >
                                <UserX className="h-4 w-4 mr-2" />
                                Cancel Shift
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {!isAuditor() && (
        <Card>
          <CardHeader>
            <CardTitle>Attendance Review Queue</CardTitle>
          </CardHeader>
          <CardContent>
            {attendanceLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            ) : attendanceRecords.length === 0 ? (
              <p className="text-text-muted py-2">No submitted attendance records waiting for review.</p>
            ) : (
              <div className="space-y-3">
                {attendanceRecords.map((row) => (
                  <div key={row.id} className="rounded-lg border p-3 sm:p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1 text-sm">
                        <p className="font-medium text-text-primary">Shift: {getShiftDisplay(row.shift_id)}</p>
                        <p className="text-text-muted">Employee: {getEmployeeDisplay(row.employee_id)}</p>
                        <p className="text-text-muted">Clock in: {formatDateTime(row.clock_in_at)}</p>
                        <p className="text-text-muted">Clock out: {formatDateTime(row.clock_out_at)}</p>
                        {row.clock_in_note ? <p className="text-text-muted">Clock-in note: {row.clock_in_note}</p> : null}
                        {row.clock_out_note ? <p className="text-text-muted">Clock-out note: {row.clock_out_note}</p> : null}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">submitted</Badge>
                        <Button
                          size="sm"
                          onClick={() => handleApproveAttendance(row.id)}
                          disabled={attendanceSaving}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            setSelectedAttendance(row);
                            setAttendanceRejectReason('');
                            setIsRejectAttendanceOpen(true);
                          }}
                          disabled={attendanceSaving}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!isAuditor() && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle>Approved Attendance / Timesheet Ready</CardTitle>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleExportApprovedAttendanceCsv}
                  disabled={approvedAttendanceRecords.length === 0}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handlePrintApprovedAttendance}
                  disabled={approvedAttendanceRecords.length === 0}
                >
                  <Printer className="h-4 w-4 mr-1" />
                  Print / PDF
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {attendanceLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            ) : approvedAttendanceRecords.length === 0 ? (
              <p className="text-text-muted py-2">No approved attendance records yet.</p>
            ) : (
              <div className="space-y-3">
                {approvedAttendanceRecords.map((row) => (
                  <div key={row.id} className="rounded-lg border p-3 sm:p-4">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="space-y-1 text-sm">
                        <p className="font-medium text-text-primary">Employee: {getEmployeeDisplay(row.employee_id)}</p>
                        <p className="text-text-muted">Employee code: {getEmployeeCodeForAttendance(row.employee_id)}</p>
                        <p className="text-text-muted">Shift: {getShiftDisplay(row.shift_id)}</p>
                        <p className="text-text-muted">Location: {shiftLocationById[row.shift_id] || '—'}</p>
                        <p className="text-text-muted">Role required: {getShiftRoleForAttendance(row.shift_id)}</p>
                        <p className="text-text-muted">Scheduled start: {getShiftScheduledStartForAttendance(row.shift_id)}</p>
                        <p className="text-text-muted">Scheduled end: {getShiftScheduledEndForAttendance(row.shift_id)}</p>
                        <p className="text-text-muted">Clock in: {formatDateTime(row.clock_in_at)}</p>
                        <p className="text-text-muted">Clock out: {formatDateTime(row.clock_out_at)}</p>
                        <p className="text-text-muted">Approved at: {formatDateTime(row.reviewed_at)}</p>
                        <p className="text-text-muted">Approved for timesheet: {row.approved_for_timesheet ? 'Yes' : 'No'}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">approved</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog open={isAssignOpen} onOpenChange={setIsAssignOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Assign Worker</DialogTitle>
            <DialogDescription>
              Select an active employee. Worker list is filtered by role requirements and non-compliant staff are disabled.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>Active employee</Label>
              <Select value={assignEmployeeId} onValueChange={setAssignEmployeeId}>
                <SelectTrigger disabled={!hasEligibleActiveEmployees}>
                  <SelectValue placeholder={hasEligibleActiveEmployees ? 'Select employee' : 'No compliant active workers match this shift role.'} />
                </SelectTrigger>
                <SelectContent>
                  {assignableEligibleEmployees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.employee_code || emp.id})
                    </SelectItem>
                  ))}
                  {blockedEligibleEmployees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id} disabled>
                      {emp.first_name} {emp.last_name} ({emp.employee_code || emp.id}) - Not compliant
                    </SelectItem>
                  ))}
                  {!hasEligibleActiveEmployees ? (
                    <div className="px-2 py-2 text-sm text-text-muted">No compliant active workers match this shift role.</div>
                  ) : null}
                </SelectContent>
              </Select>
              {blockedEligibleEmployees.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800 space-y-1">
                  {blockedEligibleEmployees.slice(0, 3).map((emp) => (
                    <p key={emp.id}>
                      {emp.first_name} {emp.last_name}: {getComplianceReason(emp) || 'Non-compliant for assignment'}
                    </p>
                  ))}
                  {blockedEligibleEmployees.length > 3 && (
                    <p>+ {blockedEligibleEmployees.length - 3} more non-compliant worker(s)</p>
                  )}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Textarea value={assignNotes} onChange={(e) => setAssignNotes(e.target.value)} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAssignOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAssign} disabled={assigning || !assignEmployeeId || !hasEligibleActiveEmployees}>
              {assigning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!detailShift || detailLoading} onOpenChange={(open) => !open && setDetailShift(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Shift Detail</DialogTitle>
            <DialogDescription>Canonical shift and active assignment state.</DialogDescription>
          </DialogHeader>
          {detailLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : detailShift?.shift ? (
            <div className="space-y-3 text-sm">
              <div>
                <p className="font-medium">Location</p>
                <p className="text-text-muted">{getShiftLocationLabel(detailShift.shift)}</p>
              </div>
              {detailShift.shift.care_location ? (
                <div>
                  <p className="font-medium">Linked Care Location</p>
                  <p className="text-text-muted">
                    {detailShift.shift.care_location.name}
                    {detailShift.shift.care_location.address_line_1 ? `, ${detailShift.shift.care_location.address_line_1}` : ''}
                    {detailShift.shift.care_location.city ? `, ${detailShift.shift.care_location.city}` : ''}
                    {detailShift.shift.care_location.postcode ? `, ${detailShift.shift.care_location.postcode}` : ''}
                  </p>
                </div>
              ) : null}
              {detailShift.shift.service_user_name ? (
                <div>
                  <p className="font-medium">Linked Service User</p>
                  <p className="text-text-muted">{detailShift.shift.service_user_name}</p>
                </div>
              ) : null}
              <div>
                <p className="font-medium">Role Required</p>
                <p className="text-text-muted">{detailShift.shift.role_required}</p>
              </div>
              <div>
                <p className="font-medium">Window</p>
                <p className="text-text-muted">
                  {formatDateTime(detailShift.shift.start_at)} → {formatDateTime(detailShift.shift.end_at)}
                </p>
              </div>
              <div>
                <p className="font-medium">Status</p>
                <Badge variant="outline" className={statusClass[detailShift.shift.status] || ''}>
                  {detailShift.shift.status}
                </Badge>
              </div>
              {detailShift.shift.cancelled_reason ? (
                <div>
                  <p className="font-medium">Cancellation Reason</p>
                  <p className="text-text-muted">{detailShift.shift.cancelled_reason}</p>
                </div>
              ) : null}
              <div>
                <p className="font-medium">Active Assignment</p>
                <p className="text-text-muted">
                  {detailShift.active_assignment
                    ? `${detailShift.active_assignment.employee_id} (${detailShift.active_assignment.status})`
                    : 'None'}
                </p>
              </div>
              <div>
                <p className="font-medium">Latest Worker Response</p>
                <p className="text-text-muted">
                  {detailShift.latest_assignment?.worker_response_status || 'No response yet'}
                  {detailShift.latest_assignment?.worker_response_note ? ` — ${detailShift.latest_assignment.worker_response_note}` : ''}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-text-muted">No detail loaded.</p>
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={isCancelOpen}
        onOpenChange={(open) => {
          setIsCancelOpen(open);
          if (!open) {
            setCancelReason('');
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Cancel Shift</DialogTitle>
            <DialogDescription>
              A cancellation reason is required and will be visible in worker-safe shift history.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="cancel_reason">Cancellation reason</Label>
            <Textarea
              id="cancel_reason"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              rows={3}
              placeholder="Explain why this shift was cancelled"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCancelOpen(false)}>
              Back
            </Button>
            <Button variant="destructive" onClick={handleCancelShift} disabled={saving || cancelReason.trim().length < 3}>
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Cancel shift
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={isRejectAttendanceOpen}
        onOpenChange={(open) => {
          setIsRejectAttendanceOpen(open);
          if (!open) {
            setSelectedAttendance(null);
            setAttendanceRejectReason('');
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Reject Attendance</DialogTitle>
            <DialogDescription>
              Rejection reason is required and recorded in attendance audit metadata.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="attendance_reject_reason">Reason</Label>
            <Textarea
              id="attendance_reject_reason"
              value={attendanceRejectReason}
              onChange={(e) => setAttendanceRejectReason(e.target.value)}
              rows={3}
              placeholder="Explain why this attendance is being rejected"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRejectAttendanceOpen(false)}>
              Back
            </Button>
            <Button
              variant="destructive"
              onClick={handleRejectAttendance}
              disabled={attendanceSaving || attendanceRejectReason.trim().length < 3}
            >
              {attendanceSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Reject attendance
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

