/**
 * SupervisionsPanel — minimal employee-profile tab for the Supervisions
 * domain (Phase 1 governance — Step 2).
 *
 * Scope rules:
 *  - Employee profile surface only; gated by parent (not rendered in
 *    recruitment/applicant context).
 *  - No redesign: follows the existing panel conventions (Card + Table +
 *    Dialog) already used by SpotChecksPanel / CompetencyAssessmentsPanel.
 *  - Read truth from GET /api/supervisions/{employee_id} — summary card
 *    uses the backend summary helper output (single truth source).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from '../ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../ui/table';
import { toast } from 'sonner';
import {
  Plus, CheckCircle, XCircle, Clock, AlertTriangle, Loader2, Calendar, RefreshCw,
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SUPERVISION_TYPES = [
  { value: 'probation',             label: 'Probation' },
  { value: 'routine',               label: 'Routine' },
  { value: 'return_to_work',        label: 'Return to work' },
  { value: 'performance',           label: 'Performance' },
  { value: 'safeguarding_followup', label: 'Safeguarding follow-up' },
  { value: 'capability',            label: 'Capability' },
  { value: 'ad_hoc',                label: 'Ad-hoc' },
];

const OUTCOME_OPTIONS = [
  { value: 'satisfactory',      label: 'Satisfactory' },
  { value: 'needs_improvement', label: 'Needs improvement' },
  { value: 'action_required',   label: 'Action required' },
  { value: 'not_applicable',    label: 'Not applicable' },
];

const STATUS_STYLE = {
  scheduled: { label: 'Scheduled', cls: 'bg-slate-100 text-slate-700 border-slate-200', icon: Clock },
  completed: { label: 'Completed', cls: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: CheckCircle },
  overdue:   { label: 'Overdue',   cls: 'bg-rose-100 text-rose-700 border-rose-200',       icon: AlertTriangle },
  cancelled: { label: 'Cancelled', cls: 'bg-zinc-100 text-zinc-600 border-zinc-200',       icon: XCircle },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.scheduled;
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={s.cls}>
      <Icon className="h-3 w-3 mr-1" /> {s.label}
    </Badge>
  );
}

export default function SupervisionsPanel({ employeeId, employeeName }) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [completeTarget, setCompleteTarget] = useState(null);
  const [cancelTarget, setCancelTarget] = useState(null);
  const [saving, setSaving] = useState(false);

  const authHeaders = useMemo(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  const load = useCallback(async () => {
    if (!employeeId) return;
    setLoading(true);
    try {
      const res = await axios.get(
        `${API}/supervisions/${employeeId}`,
        { headers: authHeaders }
      );
      setItems(res.data?.items || []);
      setSummary(res.data?.summary || null);
    } catch (err) {
      if (err?.response?.status === 403) {
        toast.error('Supervisions are not available for applicants.');
      } else {
        toast.error('Could not load supervisions');
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, authHeaders]);

  useEffect(() => { load(); }, [load]);

  // ── Summary card truth (derived from backend summary) ─────────────────
  const overdueBadge = summary?.overdue ? (
    <Badge variant="outline" className="bg-rose-100 text-rose-700 border-rose-200">
      <AlertTriangle className="h-3 w-3 mr-1" /> Overdue
    </Badge>
  ) : summary?.due_within_14d ? (
    <Badge variant="outline" className="bg-amber-100 text-amber-700 border-amber-200">
      <Clock className="h-3 w-3 mr-1" /> Due soon
    </Badge>
  ) : null;

  return (
    <div className="space-y-6" data-testid="section-supervisions-root">
      {/* ── Summary card ────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" /> Supervisions
            </CardTitle>
            <CardDescription>
              {employeeName ? `${employeeName} · ` : ''}
              Managerial, clinical and follow-up supervision records
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setScheduleOpen(true)}>
              <Plus className="h-4 w-4 mr-2" /> Schedule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-muted-foreground uppercase">Last supervision</p>
              <p className="text-sm font-medium" data-testid="supervisions-last-completed">
                {summary?.last_completed_at
                  ? formatBackendDate(summary.last_completed_at)
                  : 'No supervision on record'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase">Next due</p>
              <p className="text-sm font-medium flex items-center gap-2" data-testid="supervisions-next-due">
                {summary?.next_due_at
                  ? formatBackendDate(summary.next_due_at)
                  : '—'}
                {overdueBadge}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase">Counts</p>
              <p className="text-sm font-medium">
                {summary?.completed_count ?? 0} completed ·{' '}
                {summary?.due_soon_count ?? 0} due soon ·{' '}
                {summary?.overdue_count ?? 0} overdue
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── History table ──────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">History</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No supervisions recorded yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Scheduled</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((it) => (
                  <TableRow key={it.id}>
                    <TableCell className="capitalize">
                      {SUPERVISION_TYPES.find((t) => t.value === it.supervision_type)?.label
                        || it.supervision_type}
                    </TableCell>
                    <TableCell>{formatBackendDate(it.scheduled_at)}</TableCell>
                    <TableCell>{it.completed_at ? formatBackendDate(it.completed_at) : '—'}</TableCell>
                    <TableCell>{it.outcome || '—'}</TableCell>
                    <TableCell><StatusBadge status={it.status} /></TableCell>
                    <TableCell className="text-right space-x-2">
                      {it.status === 'scheduled' && (
                        <>
                          <Button size="sm" variant="outline"
                                  onClick={() => setCompleteTarget(it)}>
                            Complete
                          </Button>
                          <Button size="sm" variant="ghost"
                                  onClick={() => setCancelTarget(it)}>
                            Cancel
                          </Button>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ScheduleDialog
        open={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        employeeId={employeeId}
        authHeaders={authHeaders}
        saving={saving}
        setSaving={setSaving}
        onDone={() => { setScheduleOpen(false); load(); }}
      />
      <CompleteDialog
        target={completeTarget}
        onClose={() => setCompleteTarget(null)}
        authHeaders={authHeaders}
        saving={saving}
        setSaving={setSaving}
        onDone={() => { setCompleteTarget(null); load(); }}
      />
      <CancelDialog
        target={cancelTarget}
        onClose={() => setCancelTarget(null)}
        authHeaders={authHeaders}
        saving={saving}
        setSaving={setSaving}
        onDone={() => { setCancelTarget(null); load(); }}
      />
    </div>
  );
}

// ── Dialog: schedule ──────────────────────────────────────────────────
function ScheduleDialog({ open, onClose, employeeId, authHeaders, saving, setSaving, onDone }) {
  const [supervisionType, setSupervisionType] = useState('routine');
  const [supervisorId, setSupervisorId] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [summary, setSummary] = useState('');

  useEffect(() => {
    if (open) {
      setSupervisionType('routine');
      setSupervisorId('');
      setScheduledAt('');
      setSummary('');
    }
  }, [open]);

  const submit = async () => {
    if (!supervisorId || !scheduledAt) {
      toast.error('Supervisor and scheduled date are required');
      return;
    }
    setSaving(true);
    try {
      await axios.post(
        `${API}/supervisions`,
        {
          employee_id: employeeId,
          supervisor_id: supervisorId,
          supervision_type: supervisionType,
          scheduled_at: new Date(scheduledAt).toISOString(),
          summary: summary || null,
        },
        { headers: authHeaders }
      );
      toast.success('Supervision scheduled');
      onDone();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to schedule');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule supervision</DialogTitle>
          <DialogDescription>Select type, supervisor and date.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Type</Label>
            <Select value={supervisionType} onValueChange={setSupervisionType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {SUPERVISION_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Supervisor user id</Label>
            <Input value={supervisorId} onChange={(e) => setSupervisorId(e.target.value)} />
          </div>
          <div>
            <Label>Scheduled at</Label>
            <Input type="datetime-local" value={scheduledAt}
                   onChange={(e) => setScheduledAt(e.target.value)} />
          </div>
          <div>
            <Label>Summary (optional)</Label>
            <Textarea value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={submit} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: complete ──────────────────────────────────────────────────
function CompleteDialog({ target, onClose, authHeaders, saving, setSaving, onDone }) {
  const [outcome, setOutcome] = useState('satisfactory');
  const [summary, setSummary] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (target) {
      setOutcome('satisfactory');
      setSummary('');
      setNotes('');
    }
  }, [target]);

  if (!target) return null;

  const submit = async () => {
    setSaving(true);
    try {
      await axios.post(
        `${API}/supervisions/${target.id}/complete`,
        {
          completed_at: new Date().toISOString(),
          outcome,
          summary: summary || null,
          notes: notes || null,
          actions: [],
        },
        { headers: authHeaders }
      );
      toast.success('Supervision recorded');
      onDone();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to complete');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Complete supervision</DialogTitle>
          <DialogDescription>Record outcome and summary.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Outcome</Label>
            <Select value={outcome} onValueChange={setOutcome}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {OUTCOME_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Summary</Label>
            <Textarea value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          <div>
            <Label>Notes</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Back</Button>
          <Button onClick={submit} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Record completion
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: cancel ────────────────────────────────────────────────────
function CancelDialog({ target, onClose, authHeaders, saving, setSaving, onDone }) {
  const [reason, setReason] = useState('');
  useEffect(() => { if (target) setReason(''); }, [target]);
  if (!target) return null;

  const submit = async () => {
    if (!reason.trim()) {
      toast.error('A reason is required to cancel');
      return;
    }
    setSaving(true);
    try {
      await axios.post(
        `${API}/supervisions/${target.id}/cancel`,
        { reason },
        { headers: authHeaders }
      );
      toast.success('Supervision cancelled');
      onDone();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to cancel');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel supervision</DialogTitle>
          <DialogDescription>
            Cancelling one occurrence does not clear the required cadence.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Reason</Label>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Back</Button>
          <Button variant="destructive" onClick={submit} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Confirm cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
