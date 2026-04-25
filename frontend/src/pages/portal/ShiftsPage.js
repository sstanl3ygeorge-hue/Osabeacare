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
  CalendarClock,
  Loader2,
  Plus,
  MoreHorizontal,
  UserPlus,
  UserX,
  CheckCircle2,
  Eye,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [attendanceSaving, setAttendanceSaving] = useState(false);
  const [selectedAttendance, setSelectedAttendance] = useState(null);
  const [isRejectAttendanceOpen, setIsRejectAttendanceOpen] = useState(false);
  const [attendanceRejectReason, setAttendanceRejectReason] = useState('');

  const [newShift, setNewShift] = useState({
    start_at: '',
    end_at: '',
    location_text: '',
    role_required: '',
    service_user_id: '',
    care_location_id: '',
    notes: '',
  });

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

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
        params: { status: 'active' },
      });
      const rows = Array.isArray(res.data) ? res.data : (res.data?.employees || []);
      setEmployees(rows.filter((e) => e?.status === 'active'));
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

  const fetchAttendanceQueue = async () => {
    try {
      setAttendanceLoading(true);
      const res = await axios.get(`${API}/shift-attendance`, {
        headers,
        params: { status: 'submitted' },
      });
      setAttendanceRecords(res.data?.attendance_records || []);
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
    setSaving(true);
    try {
      await axios.post(
        `${API}/shifts`,
        {
          start_at: startIso,
          end_at: endIso,
          location_text: newShift.location_text,
          role_required: newShift.role_required,
          service_user_id: normalizeOptionalId(newShift.service_user_id),
          care_location_id: normalizeOptionalId(newShift.care_location_id),
          notes: newShift.notes || null,
        },
        { headers }
      );
      toast.success('Shift created');
      setIsCreateOpen(false);
      setNewShift({
        start_at: '',
        end_at: '',
        location_text: '',
        role_required: '',
        service_user_id: '',
        care_location_id: '',
        notes: '',
      });
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
      if (error.response?.status === 409) {
        toast.error('Shift already assigned — duplicate assignment blocked');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to assign worker');
      }
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
                <DialogDescription>Required: start, end, location, and role required.</DialogDescription>
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
                  <Label htmlFor="location_text">Location</Label>
                  <Input
                    id="location_text"
                    value={newShift.location_text}
                    onChange={(e) => setNewShift((prev) => ({ ...prev, location_text: e.target.value }))}
                    required
                  />
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
                <div className="space-y-2">
                  <Label htmlFor="service_user_id">Service User ID (optional)</Label>
                  <Input
                    id="service_user_id"
                    value={newShift.service_user_id}
                    onChange={(e) => setNewShift((prev) => ({ ...prev, service_user_id: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="care_location_id">Care Location (optional)</Label>
                  <Select
                    value={newShift.care_location_id || 'none'}
                    onValueChange={(value) => setNewShift((prev) => ({ ...prev, care_location_id: value === 'none' ? '' : value }))}
                  >
                    <SelectTrigger id="care_location_id">
                      <SelectValue placeholder="Select care location" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {careLocations.map((loc) => (
                        <SelectItem key={loc.id} value={loc.id}>
                          {loc.name} {loc.city ? `(${loc.city})` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                      <p className="font-medium text-text-primary">{shift.location_text}</p>
                      {shift.care_location ? (
                        <p className="text-xs text-text-muted">
                          Care location: {shift.care_location.name}
                          {shift.care_location.address_line_1 ? `, ${shift.care_location.address_line_1}` : ''}
                          {shift.care_location.city ? `, ${shift.care_location.city}` : ''}
                        </p>
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
                        <p className="font-medium text-text-primary">Shift: {row.shift_id}</p>
                        <p className="text-text-muted">Employee: {row.employee_id}</p>
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

      <Dialog open={isAssignOpen} onOpenChange={setIsAssignOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Assign Worker</DialogTitle>
            <DialogDescription>
              Select an active employee. Eligibility and overlap are enforced by backend.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>Active employee</Label>
              <Select value={assignEmployeeId} onValueChange={setAssignEmployeeId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select employee" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.first_name} {emp.last_name} ({emp.employee_code || emp.id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            <Button onClick={handleAssign} disabled={assigning || !assignEmployeeId}>
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
                <p className="text-text-muted">{detailShift.shift.location_text}</p>
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
