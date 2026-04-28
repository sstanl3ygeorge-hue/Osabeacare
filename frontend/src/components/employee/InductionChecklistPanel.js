import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  CheckCircle, Circle, Loader2, RefreshCw, FileText, 
  AlertTriangle, Clock, RotateCcw, Download, Award, Eye, CornerDownLeft
} from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

async function openAuthenticatedBlob(route, fallbackName = 'evidence.pdf') {
  const token = localStorage.getItem('token');
  const response = await axios.get(
    route.startsWith('http') ? route : `${API}${route}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob',
    }
  );
  const contentType = response.headers['content-type'] || response.data?.type || 'application/octet-stream';
  const blob = new Blob([response.data], { type: contentType });
  const objectUrl = window.URL.createObjectURL(blob);
  const openedWindow = window.open(objectUrl, '_blank', 'noopener,noreferrer');
  if (!openedWindow) {
    const link = document.createElement('a');
    link.href = objectUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.download = fallbackName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 60000);
}

// ─── Evidence detail modal ──────────────────────────────────────────────────

function EvidenceModal({ item, onClose }) {
  const evidence = item.linked_evidence || [];
  const [openingRoute, setOpeningRoute] = useState(null);

  const handleOpenEvidence = async (ev) => {
    if (!ev?.view_route) return;
    setOpeningRoute(ev.view_route);
    try {
      await openAuthenticatedBlob(ev.view_route, ev.file_name || ev.title || 'evidence.pdf');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to open evidence file.');
    } finally {
      setOpeningRoute(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="font-semibold text-sm text-slate-800">
            Evidence — {item.label || item.name}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">&times;</button>
        </div>
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-3">
          {evidence.length === 0 && (
            <p className="text-sm text-slate-500">No evidence records found for this item.</p>
          )}
          {evidence.map((ev, i) => (
            <div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                  <span className="text-xs font-medium text-slate-700 break-all">
                    {ev.file_name || ev.title || ev.code || 'Unnamed file'}
                  </span>
                </div>
                {ev.verified && (
                  <span className="flex-shrink-0 text-[10px] font-semibold bg-green-100 text-green-700 rounded-full px-2 py-0.5">Verified</span>
                )}
              </div>
              <div className="text-[11px] text-slate-500 space-y-0.5 pl-5">
                {ev.source_label && <p>Source: {ev.source_label}</p>}
                {ev.verified_at && <p>Verified: {formatBackendDate(ev.verified_at)}{ev.verified_by ? ` by ${ev.verified_by}` : ''}</p>}
                {ev.uploaded_at && <p>Uploaded: {formatBackendDate(ev.uploaded_at)}</p>}
              </div>
              {ev.view_route && (
                <div className="pl-5">
                  <button
                    type="button"
                    onClick={() => handleOpenEvidence(ev)}
                    disabled={openingRoute === ev.view_route}
                    className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 hover:underline disabled:opacity-60"
                  >
                    {openingRoute === ev.view_route ? <Loader2 className="h-3 w-3 animate-spin" /> : <Eye className="h-3 w-3" />} Open file
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="px-5 py-3 border-t flex justify-end">
          <Button size="sm" variant="outline" onClick={onClose} className="h-8 px-4 text-xs">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Shadow Shift notes dialog ───────────────────────────────────────────────

function ShadowShiftDialog({ existingDetails, onConfirm, onCancel, saving }) {
  const [form, setForm] = useState({
    shift_date: existingDetails?.shift_date || '',
    location_unit: existingDetails?.location_unit || '',
    supervisor_name: existingDetails?.supervisor_name || '',
    summary_notes: existingDetails?.summary_notes || '',
    ready_for_deployment: existingDetails?.ready_for_deployment === false ? 'no' : 'yes',
    follow_up_actions: existingDetails?.follow_up_actions || '',
  });

  const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }));
  const requiredComplete = form.shift_date &&
    form.location_unit.trim() &&
    form.supervisor_name.trim() &&
    form.summary_notes.trim() &&
    (form.ready_for_deployment === 'yes' || form.follow_up_actions.trim());

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl">
        <div className="px-6 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">Shadow Shift Sign-off</h3>
          <p className="text-xs text-slate-500 mt-1">Record the supervised shift details before this item can be completed.</p>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs font-medium text-slate-700">
              Shift date
              <input
                type="date"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={form.shift_date}
                onChange={e => setField('shift_date', e.target.value)}
                autoFocus
              />
            </label>
            <label className="text-xs font-medium text-slate-700">
              Location / unit
              <input
                type="text"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={form.location_unit}
                onChange={e => setField('location_unit', e.target.value)}
                placeholder="e.g. Ward 4 / community round"
              />
            </label>
          </div>
          <label className="block text-xs font-medium text-slate-700">
            Supervisor name
            <input
              type="text"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={form.supervisor_name}
              onChange={e => setField('supervisor_name', e.target.value)}
              placeholder="Name of supervisor or witness"
            />
          </label>
          <label className="block text-xs font-medium text-slate-700">
            Summary notes
            <textarea
              rows={4}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="What was observed, what the worker completed, and any concerns."
              value={form.summary_notes}
              onChange={e => setField('summary_notes', e.target.value)}
            />
          </label>
          <div>
            <p className="text-xs font-medium text-slate-700 mb-2">Outcome</p>
            <div className="flex flex-wrap gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="radio"
                  checked={form.ready_for_deployment === 'yes'}
                  onChange={() => setField('ready_for_deployment', 'yes')}
                />
                Ready for deployment
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="radio"
                  checked={form.ready_for_deployment === 'no'}
                  onChange={() => setField('ready_for_deployment', 'no')}
                />
                Follow-up required
              </label>
            </div>
          </div>
          {form.ready_for_deployment === 'no' && (
            <label className="block text-xs font-medium text-slate-700">
              Follow-up actions
              <textarea
                rows={3}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                value={form.follow_up_actions}
                onChange={e => setField('follow_up_actions', e.target.value)}
                placeholder="What needs to happen before deployment?"
              />
            </label>
          )}
        </div>
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={saving}>Cancel</Button>
          <Button
            size="sm"
            onClick={() => onConfirm({
              ...form,
              ready_for_deployment: form.ready_for_deployment === 'yes',
            })}
            disabled={!requiredComplete || saving}
          >
            {saving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
            {form.ready_for_deployment === 'yes' ? 'Complete sign-off' : 'Save follow-up'}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Hybrid: View Submission modal ──────────────────────────────────────────

function SubmissionViewModal({ employeeId, item, onClose, onSignOff, onReturn, onReopen }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [returnReason, setReturnReason] = useState('');
  const [showReturn, setShowReturn] = useState(false);
  const [acting, setActing] = useState(false);
  const [adminNotes, setAdminNotes] = useState('');
  const [reopenReason, setReopenReason] = useState('');
  const [showReopen, setShowReopen] = useState(false);
  const [openingEvidence, setOpeningEvidence] = useState(false);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (detail?.message) return detail.message;
    return err?.message || fallback;
  };

  useEffect(() => {
    const token = localStorage.getItem('token');
    axios.get(`${API}/employees/${employeeId}/induction/items/${item.code}/submission`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setData(res.data))
      .catch(() => toast.error('Could not load submission.'))
      .finally(() => setLoading(false));
  }, [employeeId, item.code]);

  const handleSignOff = async () => {
    setActing(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/induction/items/${item.code}/signoff`,
        { notes: adminNotes },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${item.name} signed off.`);
      onSignOff && onSignOff();
    } catch (err) {
      console.error('Induction sign-off failed', {
        employeeId,
        itemCode: item.code,
        itemName: item.name,
        status: err?.response?.status,
        detail: err?.response?.data,
      });
      toast.error(getErrorMessage(err, 'Sign-off failed.'));
    } finally {
      setActing(false);
    }
  };

  const handleReturn = async () => {
    if (!returnReason.trim()) { toast.error('Return reason is required.'); return; }
    setActing(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/induction/items/${item.code}/return`,
        { return_reason: returnReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Form returned to worker for correction.');
      onReturn && onReturn();
    } catch (err) {
      console.error('Induction return failed', {
        employeeId,
        itemCode: item.code,
        itemName: item.name,
        status: err?.response?.status,
        detail: err?.response?.data,
      });
      toast.error(getErrorMessage(err, 'Return failed.'));
    } finally {
      setActing(false);
    }
  };

  const handleReopen = async () => {
    setActing(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/induction/items/${item.code}/reopen`,
        { reason: reopenReason || 'Admin reopened sign-off for review' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Sign-off reopened. The submission can be reviewed again.');
      onReopen && onReopen();
    } catch (err) {
      console.error('Induction reopen failed', {
        employeeId,
        itemCode: item.code,
        itemName: item.name,
        status: err?.response?.status,
        detail: err?.response?.data,
      });
      toast.error(getErrorMessage(err, 'Reopen failed.'));
    } finally {
      setActing(false);
    }
  };

  const subStatus = data?.submission_status;
  const schema = data?.schema || {};
  const submittedData = data?.submitted_data || {};
  const fields = schema.fields || [];

  const handleOpenEvidenceRecord = async () => {
    if (!item?.evidence_view_route) return;
    setOpeningEvidence(true);
    try {
      await openAuthenticatedBlob(item.evidence_view_route, `${item.code || 'induction'}_evidence.pdf`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to open evidence record.');
    } finally {
      setOpeningEvidence(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 overflow-y-auto py-10 px-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">Worker Submission</p>
            <h2 className="text-base font-semibold text-slate-900">{item.name}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl font-bold">&times;</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {loading && <p className="text-sm text-slate-400">Loading…</p>}

          {!loading && !data?.submission && (
            <p className="text-sm text-slate-500">No submission found for this item.</p>
          )}

          {!loading && subStatus && (
            <div className={`rounded-lg p-3 text-sm border ${
              subStatus === 'submitted' ? 'bg-amber-50 border-amber-200 text-amber-800' :
              subStatus === 'signed_off' ? 'bg-green-50 border-green-200 text-green-800' :
              subStatus === 'returned' ? 'bg-red-50 border-red-200 text-red-800' :
              'bg-slate-50 border-slate-200 text-slate-600'
            }`}>
              Status: <strong>{subStatus.replace(/_/g, ' ')}</strong>
              {data?.submitted_at && <> · Submitted {formatBackendDate(data.submitted_at)}</>}
            </div>
          )}

          {!loading && fields.length > 0 && fields.map(field => {
            const val = submittedData[field.key];
            if (val === undefined || val === null || val === '') return null;
            return (
              <div key={field.key}>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{field.label}</p>
                {Array.isArray(val) ? (
                  <ul className="mt-1 list-disc list-inside text-sm text-slate-800 space-y-0.5">
                    {val.map(v => <li key={v}>{(field.options || []).find(o => o.value === v)?.label || v}</li>)}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-slate-800 whitespace-pre-wrap">{
                    field.type === 'radio'
                      ? (field.options || []).find(o => o.value === val)?.label || val
                      : val
                  }</p>
                )}
              </div>
            );
          })}

          {/* Admin notes for sign-off */}
          {!loading && subStatus === 'submitted' && !showReturn && (
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Sign-off notes (optional)
              </label>
              <textarea
                rows={2}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Any observations or comments…"
                value={adminNotes}
                onChange={e => setAdminNotes(e.target.value)}
              />
            </div>
          )}

          {/* Return reason */}
          {showReturn && (
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Return reason <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Explain what the worker should correct or add…"
                value={returnReason}
                onChange={e => setReturnReason(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {/* Reopen reason */}
          {showReopen && (
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Reopen reason
              </label>
              <textarea
                rows={3}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Why is this sign-off being reopened?"
                value={reopenReason}
                onChange={e => setReopenReason(e.target.value)}
                autoFocus
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
          <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-700">Close</button>
          {!loading && (subStatus === 'submitted' || subStatus === 'signed_off') && (
            <div className="flex gap-2">
              {subStatus === 'signed_off' && item?.evidence_view_route && (
                <Button
                  variant="outline" size="sm"
                  onClick={handleOpenEvidenceRecord}
                  disabled={acting || openingEvidence}
                >
                  {openingEvidence ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <FileText className="h-3 w-3 mr-1" />}
                  Evidence record
                </Button>
              )}
              {!showReturn && !showReopen ? (
                <>
                  <Button
                    variant="outline" size="sm"
                    onClick={() => setShowReturn(true)}
                    className="text-red-600 border-red-300 hover:bg-red-50"
                    disabled={acting}
                  >
                    <CornerDownLeft className="h-3 w-3 mr-1" /> Return for retake
                  </Button>
                  {subStatus === 'signed_off' && (
                    <Button
                      variant="outline" size="sm"
                      onClick={() => setShowReopen(true)}
                      disabled={acting}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" /> Reopen
                    </Button>
                  )}
                  {subStatus === 'submitted' && (
                    <Button size="sm" onClick={handleSignOff} disabled={acting}>
                      {acting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <CheckCircle className="h-3 w-3 mr-1" />}
                      Sign off
                    </Button>
                  )}
                </>
              ) : showReturn ? (
                <>
                  <Button variant="outline" size="sm" onClick={() => setShowReturn(false)} disabled={acting}>Cancel</Button>
                  <Button size="sm" onClick={handleReturn} disabled={acting || !returnReason.trim()}
                    className="bg-red-600 hover:bg-red-700">
                    {acting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                    Confirm return
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="outline" size="sm" onClick={() => setShowReopen(false)} disabled={acting}>Cancel</Button>
                  <Button size="sm" onClick={handleReopen} disabled={acting}>
                    {acting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                    Confirm reopen
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InductionChecklistPanel({ employeeId, employeeName, isAuditor = false, onStatusChange }) {
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [shadowShiftItem, setShadowShiftItem] = useState(null); // item to show notes dialog for
  const [savingNotes, setSavingNotes] = useState(false);
  const [viewSubmissionItem, setViewSubmissionItem] = useState(null); // item to view submission for
  const [viewEvidenceItem, setViewEvidenceItem] = useState(null); // item to view evidence for

  const fetchChecklist = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/induction-checklist`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChecklist(response.data);
    } catch (error) {
      console.error('Failed to fetch induction checklist:', error);
      setLoadError('Cannot assess induction checklist. Checklist rules or evidence could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [employeeId]);

  useEffect(() => {
    if (employeeId) fetchChecklist();
  }, [employeeId, fetchChecklist]);

  const openEvidenceRecord = useCallback(async (route, fileName) => {
    try {
      await openAuthenticatedBlob(route, fileName);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to open evidence record.');
    }
  }, []);

  const updateItem = async (itemName, newStatus, notes = '', extraPayload = {}) => {
    setUpdating(itemName);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.put(
        `${API}/employees/${employeeId}/induction-checklist`,
        { item_name: itemName, status: newStatus, notes, ...extraPayload },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${itemName} marked as ${newStatus}`);
      fetchChecklist();
      if (onStatusChange) onStatusChange(response.data.overall_status);
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update checklist');
      return false;
    } finally {
      setUpdating(null);
    }
  };

  const handleShadowShiftSignOff = async (details) => {
    if (!shadowShiftItem) return;
    setSavingNotes(true);
    const nextStatus = details.ready_for_deployment ? 'completed' : 'pending';
    const saved = await updateItem(shadowShiftItem.name, nextStatus, details.summary_notes, {
      shadow_shift_signoff: details,
    });
    setSavingNotes(false);
    if (saved) setShadowShiftItem(null);
  };

  const handleDownloadCertificate = async () => {
    if (checklist?.overall_status !== 'completed') {
      toast.error('Induction must be completed before downloading certificate');
      return;
    }
    try {
      setDownloading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/employees/${employeeId}/induction-completion/download-pdf`,
        { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
      );
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `induction_certificate_${employeeName?.replace(/\s+/g, '_') || 'employee'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Induction certificate downloaded');
    } catch {
      toast.error('Failed to download certificate');
    } finally {
      setDownloading(false);
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'complete' || status === 'completed') return <Badge className="bg-green-100 text-green-700">Completed</Badge>;
    if (status === 'not_started') return <Badge variant="outline" className="text-slate-600 border-slate-300">Not started</Badge>;
    if (status === 'awaiting_manager_signoff' || status === 'submitted') return <Badge className="bg-amber-100 text-amber-700">Awaiting manager sign-off</Badge>;
    if (status === 'returned') return <Badge className="bg-red-100 text-red-700">Returned</Badge>;
    if (status === 'pending_review') return <Badge className="bg-blue-100 text-blue-700">Pending review</Badge>;
    if (status === 'cannot_assess') return <Badge className="bg-red-100 text-red-700">Cannot assess</Badge>;
    return <Badge variant="outline" className="text-amber-600 border-amber-300">Pending</Badge>;
  };

  const getHybridDisplayStatus = (item) => {
    const subStatus = item?.submission_status;
    if (subStatus === 'returned') return 'returned';
    if (subStatus === 'submitted') return 'awaiting_manager_signoff';
    if (subStatus === 'signed_off') return 'completed';
    return 'not_started';
  };

  const getOverallStatusBadge = (status) => {
    switch (status) {
      case 'completed': return <Badge className="bg-green-100 text-green-700">Completed</Badge>;
      case 'in_progress': return <Badge className="bg-blue-100 text-blue-700">In Progress</Badge>;
      default: return <Badge variant="outline" className="text-gray-500">Not Started</Badge>;
    }
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const items = checklist?.items || [];
  const completedCount = items.filter(i => i.status === 'completed').length;
  const mandatoryItems = items.filter(i => i.mandatory);
  const mandatoryCompleted = mandatoryItems.filter(i => i.status === 'completed').length;
  const overallStatus = checklist?.overall_status || 'pending';
  const progressPercent = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;
  const cannotAssess = Boolean(loadError);

  return (
    <>
      <Card className="border-[#E4E8EB] shadow-sm" data-testid="induction-checklist-panel">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Induction Checklist
            </CardTitle>
            <div className="flex items-center gap-2">
              {cannotAssess ? (
                <Badge className="bg-red-100 text-red-700">Cannot assess</Badge>
              ) : getOverallStatusBadge(overallStatus)}
              {overallStatus === 'completed' && (
                <Button
                  variant="outline" size="sm"
                  onClick={handleDownloadCertificate}
                  disabled={downloading}
                  className="rounded-lg text-green-700 border-green-300 hover:bg-green-50"
                >
                  {downloading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Award className="h-4 w-4 mr-1" />}
                  Certificate
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={fetchChecklist} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {loadError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{loadError}</span>
            </div>
          )}

          {!loadError && checklist?.role_rule_warning && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{checklist.role_rule_warning}</span>
            </div>
          )}

          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Progress</span>
              <span className="font-medium">{completedCount}/{items.length} items ({progressPercent}%)</span>
            </div>
            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${
                  overallStatus === 'completed' ? 'bg-green-500' :
                  overallStatus === 'in_progress' ? 'bg-blue-500' : 'bg-gray-300'
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                Mandatory: {mandatoryCompleted}/{mandatoryItems.length}
              </span>
              {mandatoryCompleted < mandatoryItems.length && (
                <span className="text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  {mandatoryItems.length - mandatoryCompleted} required items remaining
                </span>
              )}
            </div>
          </div>

          {overallStatus === 'completed' && checklist?.completed_at && (
            <p className="text-sm text-green-600 mt-3 flex items-center gap-1 bg-green-50 p-2 rounded-lg">
              <CheckCircle className="h-4 w-4" />
              Induction completed on {formatBackendDate(checklist.completed_at)}
            </p>
          )}
        </CardHeader>

        <CardContent>
          <div className="space-y-1">
            {items.map((item, idx) => {
              const itemRuleStatus = item.rule_status || (item.status === 'completed' ? 'complete' : 'incomplete');
              const isHybrid = item.completion_type === 'hybrid';
              const hybridDisplayStatus = isHybrid ? getHybridDisplayStatus(item) : null;
              const rowStatus = isHybrid ? hybridDisplayStatus : itemRuleStatus;
              const isComplete = rowStatus === 'complete' || rowStatus === 'completed';
              const isManual = item.completion_type === 'manual';
              const isAutomatic = item.completion_type === 'automatic';
              const canManualComplete = !isAuditor && item.manual_action_allowed !== false && item.status !== 'completed' && !isHybrid && !isAutomatic && !isManual;
              const canUndoManual = !isAuditor && item.status === 'completed' && item.manual_action_allowed !== false && !item.synced_from_training && !isHybrid && !isAutomatic;

              return (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-3 rounded-lg transition-colors ${
                    isComplete ? 'bg-green-50/50 border border-green-100' : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                  }`}
                  data-testid={`induction-item-${idx}`}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className={`flex-shrink-0 ${isComplete ? 'text-green-600' : rowStatus === 'awaiting_manager_signoff' || rowStatus === 'submitted' || rowStatus === 'pending_review' ? 'text-blue-500' : rowStatus === 'returned' ? 'text-red-500' : 'text-gray-300'}`}>
                      {isComplete ? <CheckCircle className="h-5 w-5" /> : <Circle className="h-5 w-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`font-medium ${isComplete ? 'text-green-800' : 'text-gray-800'}`}>{item.name}</span>
                        {item.mandatory && <span className="text-[10px] text-red-600 bg-red-50 px-1.5 py-0.5 rounded font-medium">REQUIRED</span>}
                        {getStatusBadge(rowStatus)}
                        {item.completion_type && (
                          <span className="text-[10px] text-gray-600 bg-white border border-gray-200 px-1.5 py-0.5 rounded font-medium uppercase">
                            {item.completion_type}
                          </span>
                        )}
                      </div>
                      {item.description && <p className="text-xs text-gray-600 mt-1">{item.description}</p>}
                      {(item.status_reason || item.completion_reason) && (
                        <p className={`text-xs mt-1 ${isComplete ? 'text-green-700' : itemRuleStatus === 'pending_review' ? 'text-blue-700' : 'text-amber-700'}`}>
                          {item.completion_reason || item.status_reason}
                        </p>
                      )}
                      {item.linked_evidence?.length > 0 && (
                        <button
                          onClick={() => setViewEvidenceItem(item)}
                          className="mt-1 flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 group"
                        >
                          <FileText className="h-3 w-3 text-slate-400 group-hover:text-slate-600" />
                          <span>
                            {item.linked_evidence.length} evidence file{item.linked_evidence.length !== 1 ? 's' : ''}
                          </span>
                          {item.linked_evidence[0]?.source_label && (
                            <><span className="text-slate-300">·</span><span>{item.linked_evidence[0].source_label}</span></>
                          )}
                          <Eye className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      )}
                      {item.completed_at && (
                        <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatBackendDate(item.completed_at)}
                          {item.completed_by_name && <span>by {item.completed_by_name}</span>}
                        </div>
                      )}
                      {item.shadow_shift_signoff && (
                        <div className="text-xs text-slate-600 mt-2 rounded-md border border-slate-200 bg-slate-50 p-2">
                          <p>
                            Shadow shift: {item.shadow_shift_signoff.shift_date || 'date not recorded'}
                            {item.shadow_shift_signoff.location_unit ? ` at ${item.shadow_shift_signoff.location_unit}` : ''}
                          </p>
                          <p>Supervisor: {item.shadow_shift_signoff.supervisor_name || 'not recorded'}</p>
                          <p>
                            Outcome: {item.shadow_shift_signoff.ready_for_deployment ? 'Ready for deployment' : 'Follow-up required'}
                          </p>
                          {!item.shadow_shift_signoff.ready_for_deployment && item.shadow_shift_signoff.follow_up_actions && (
                            <p>Follow-up: {item.shadow_shift_signoff.follow_up_actions}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  {!isAuditor && (
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">

                      {/* Hybrid items: view submission + sign-off / already done */}
                      {isHybrid && !isComplete && (
                        <Button
                          size="sm" variant="outline"
                          onClick={() => setViewSubmissionItem(item)}
                          className="h-8 px-3 text-xs rounded-lg"
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          View &amp; sign off
                        </Button>
                      )}
                      {isHybrid && isComplete && (
                        <>
                          <Button
                            size="sm" variant="ghost"
                            onClick={() => setViewSubmissionItem(item)}
                            className="h-8 px-3 text-xs rounded-lg text-slate-400"
                          >
                            <Eye className="h-3 w-3 mr-1" /> View
                          </Button>
                          {item.evidence_view_route && (
                            <Button
                              size="sm" variant="ghost"
                              onClick={() => openEvidenceRecord(item.evidence_view_route, `${item.code || 'induction'}_evidence.pdf`)}
                              className="h-8 px-3 text-xs rounded-lg text-slate-400 hover:text-slate-600"
                            >
                              <FileText className="h-3 w-3 mr-1" /> Evidence
                            </Button>
                          )}
                        </>
                      )}

                      {/* Manual (shadow shift) sign-off */}
                      {isManual && !isComplete && (
                        <Button
                          size="sm" variant="outline"
                          onClick={() => setShadowShiftItem(item)}
                          disabled={updating === item.name}
                          className="h-8 px-3 text-xs rounded-lg hover:bg-green-50 hover:text-green-700 hover:border-green-300"
                        >
                          {updating === item.name ? <Loader2 className="h-3 w-3 animate-spin" /> : <><CheckCircle className="h-3 w-3 mr-1" />Sign off</>}
                        </Button>
                      )}
                      {isManual && isComplete && item.evidence_view_route && (
                        <Button
                          size="sm" variant="ghost"
                          onClick={() => openEvidenceRecord(item.evidence_view_route, `${item.code || 'induction'}_evidence.pdf`)}
                          className="h-8 px-3 text-xs rounded-lg text-slate-400 hover:text-slate-600"
                        >
                          <FileText className="h-3 w-3 mr-1" /> Evidence
                        </Button>
                      )}

                      {/* Non-hybrid/non-manual completable items */}
                      {canManualComplete && (
                        <Button
                          size="sm" variant="outline"
                          onClick={() => updateItem(item.name, 'completed')}
                          disabled={updating === item.name}
                          className="h-8 px-3 text-xs rounded-lg hover:bg-green-50 hover:text-green-700 hover:border-green-300"
                          data-testid={`complete-item-${idx}`}
                        >
                          {updating === item.name ? <Loader2 className="h-3 w-3 animate-spin" /> : <><CheckCircle className="h-3 w-3 mr-1" />Complete</>}
                        </Button>
                      )}

                      {/* Automatic evidenced item — view evidence if available, else disabled hint */}
                      {isAutomatic && isComplete && item.linked_evidence?.length > 0 && (
                        <Button size="sm" variant="ghost"
                          onClick={() => setViewEvidenceItem(item)}
                          className="h-8 px-3 text-xs rounded-lg text-slate-400 hover:text-slate-600">
                          <Eye className="h-3 w-3 mr-1" /> Evidence
                        </Button>
                      )}
                      {isAutomatic && !isComplete && (
                        <Button size="sm" variant="outline" disabled className="h-8 px-3 text-xs rounded-lg text-gray-400"
                          title={item.next_action || 'Upload and verify matching training evidence'}>
                          Upload evidence
                        </Button>
                      )}

                      {/* Undo for non-synced, non-hybrid manual completions */}
                      {canUndoManual && (
                        <Button
                          size="sm" variant="ghost"
                          onClick={() => updateItem(item.name, 'pending')}
                          disabled={updating === item.name}
                          className="h-8 px-2 text-xs text-gray-400 hover:text-gray-600"
                          title="Mark as pending"
                        >
                          {updating === item.name ? <Loader2 className="h-3 w-3 animate-spin" /> : <RotateCcw className="h-3 w-3" />}
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <p className="text-xs text-blue-700">
              <strong>CQC Requirement:</strong> Applicable induction items must be completed before unsupervised work.
              Training-derived items require verified evidence. Manual and hybrid items require admin or manager sign-off.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Shadow shift dialog */}
      {shadowShiftItem && (
        <ShadowShiftDialog
          existingDetails={shadowShiftItem.shadow_shift_signoff}
          onConfirm={handleShadowShiftSignOff}
          onCancel={() => setShadowShiftItem(null)}
          saving={savingNotes}
        />
      )}

      {/* Hybrid submission modal */}
      {viewSubmissionItem && (
        <SubmissionViewModal
          employeeId={employeeId}
          item={viewSubmissionItem}
          onClose={() => setViewSubmissionItem(null)}
          onSignOff={() => { setViewSubmissionItem(null); fetchChecklist(); }}
          onReturn={() => { setViewSubmissionItem(null); fetchChecklist(); }}
          onReopen={() => { setViewSubmissionItem(null); fetchChecklist(); }}
        />
      )}

      {/* Evidence detail modal */}
      {viewEvidenceItem && (
        <EvidenceModal item={viewEvidenceItem} onClose={() => setViewEvidenceItem(null)} />
      )}
    </>
  );
}

