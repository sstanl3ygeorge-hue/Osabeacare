import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { 
  History, Upload, CheckCircle, XCircle, Edit, Eye, FileText,
  Loader2, RefreshCw, Clock, AlertTriangle, ChevronRight, Shield, ArrowRight
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

/* ─── Strict CQC-safe action labels ──────────────────────────── */
const ACTION_CONFIG = {
  document_uploaded:             { label: 'Document uploaded', color: 'bg-blue-100 text-blue-700', icon: Upload },
  upload_evidence:               { label: 'Evidence uploaded', color: 'bg-blue-100 text-blue-700', icon: Upload },
  document_verified:             { label: 'Document verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  verify_document:               { label: 'Document verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  start_document_review:         { label: 'Review checklist confirmed', color: 'bg-blue-100 text-blue-700', icon: Eye },
  verify_with_digital_stamp:     { label: 'Verified — digital stamp applied', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  verify_and_stamp_identity:     { label: 'Identity verified — stamped', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  verify_and_stamp_address:      { label: 'Address verified — stamped', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  document_rejected:             { label: 'Document rejected — action required', color: 'bg-red-100 text-red-700', icon: XCircle },
  reject_document:               { label: 'Document rejected — action required', color: 'bg-red-100 text-red-700', icon: XCircle },
  document_replaced:             { label: 'Document replaced', color: 'bg-amber-100 text-amber-700', icon: RefreshCw },
  document_removed:              { label: 'Document removed', color: 'bg-red-100 text-red-700', icon: XCircle },
  mark_uploaded_in_error:        { label: 'Marked uploaded in error', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
  request_replacement:           { label: 'Replacement requested', color: 'bg-cyan-100 text-cyan-700', icon: RefreshCw },
  delete_evidence:               { label: 'Evidence deleted', color: 'bg-red-100 text-red-700', icon: XCircle },
  remove_evidence:               { label: 'Evidence removed', color: 'bg-red-100 text-red-700', icon: XCircle },
  verify_requirement:            { label: 'Check complete', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  unverify_requirement:          { label: 'Requirement satisfaction revoked', color: 'bg-red-100 text-red-700', icon: XCircle },
  check_recorded:                { label: 'Check recorded', color: 'bg-purple-100 text-purple-700', icon: FileText },
  reference_requested:           { label: 'Reference requested', color: 'bg-cyan-100 text-cyan-700', icon: FileText },
  request_reference_replacement: { label: 'Reference replacement requested', color: 'bg-cyan-100 text-cyan-700', icon: RefreshCw },
  reference_received:            { label: 'Reference response received', color: 'bg-indigo-100 text-indigo-700', icon: FileText },
  reference_verified:            { label: 'Reference — satisfactory', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  verify_reference:              { label: 'Reference — satisfactory', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  health_declaration_submitted:  { label: 'Health declaration submitted', color: 'bg-teal-100 text-teal-700', icon: FileText },
  health_declaration_reviewed:   { label: 'Health declaration reviewed', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  training_completed:            { label: 'Training completed', color: 'bg-violet-100 text-violet-700', icon: CheckCircle },
  training_record_created:       { label: 'Training record created', color: 'bg-violet-100 text-violet-700', icon: CheckCircle },
  training_record_updated:       { label: 'Training record corrected', color: 'bg-amber-100 text-amber-700', icon: Edit },
  training_evidence_added:       { label: 'Training evidence uploaded', color: 'bg-violet-100 text-violet-700', icon: Upload },
  verify_training:               { label: 'Training verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  training_correction:           { label: 'Training record corrected', color: 'bg-amber-100 text-amber-700', icon: Edit },
  upload_training_certificate:   { label: 'Training certificate uploaded', color: 'bg-violet-100 text-violet-700', icon: Upload },
  form_request_sent:             { label: 'Form request sent', color: 'bg-blue-100 text-blue-700', icon: FileText },
  form_completed:                { label: 'Form completed', color: 'bg-blue-100 text-blue-700', icon: CheckCircle },
  complete_form:                 { label: 'Form completed', color: 'bg-blue-100 text-blue-700', icon: CheckCircle },
  form_viewed:                   { label: 'Form viewed', color: 'bg-slate-100 text-slate-600', icon: Eye },
  create_form:                   { label: 'Form created', color: 'bg-blue-100 text-blue-700', icon: FileText },
  update_form:                   { label: 'Form updated', color: 'bg-amber-100 text-amber-700', icon: Edit },
  signoff_form:                  { label: 'Form signed off', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  verify_agreement_submission:   { label: 'Agreement verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  reject_agreement_submission:   { label: 'Agreement rejected — action required', color: 'bg-red-100 text-red-700', icon: XCircle },
  policy_signed:                 { label: 'Policy signed', color: 'bg-lime-100 text-lime-700', icon: FileText },
  policy_acknowledged:           { label: 'Policy acknowledged', color: 'bg-lime-100 text-lime-700', icon: FileText },
  policy_admin_reviewed:         { label: 'Policy reviewed by admin', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  status_changed:                { label: 'Status changed', color: 'bg-amber-100 text-amber-700', icon: Edit },
  status_change:                 { label: 'Status changed', color: 'bg-amber-100 text-amber-700', icon: Edit },
  deactivate_employee:           { label: 'Set inactive', color: 'bg-amber-100 text-amber-700', icon: Clock },
  reactivate_employee:           { label: 'Reactivated to onboarding', color: 'bg-blue-100 text-blue-700', icon: RefreshCw },
  archive_employee:              { label: 'Archived', color: 'bg-slate-100 text-slate-700', icon: AlertTriangle },
  restore_employee:              { label: 'Restored', color: 'bg-blue-100 text-blue-700', icon: RefreshCw },
  refresh_status:                { label: 'Status recalculated', color: 'bg-gray-100 text-gray-600', icon: RefreshCw },
  profile_updated:               { label: 'Profile updated', color: 'bg-gray-100 text-gray-600', icon: Edit },
  update_employee:               { label: 'Employee record updated', color: 'bg-gray-100 text-gray-600', icon: Edit },
  edit_personal_details:         { label: 'Personal details edited', color: 'bg-gray-100 text-gray-600', icon: Edit },
  // ── Readiness-critical decisions (already written canonically by backend;
  //    labels added so the panel renders them with the same Critical/Sign-off
  //    treatment as other governance events. No new truth introduced.) ──
  approve_for_work:              { label: 'Fit for work approval recorded', color: 'bg-emerald-100 text-emerald-700', icon: Shield },
  auto_promoted_to_active:       { label: 'Promoted to active (auto)', color: 'bg-emerald-100 text-emerald-700', icon: ArrowRight },
  manual_promotion_to_active:    { label: 'Promoted to active (manual override)', color: 'bg-amber-100 text-amber-700', icon: ArrowRight },
  cv_approved:                   { label: 'CV approved', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  cv_rejected:                   { label: 'CV rejected — action required', color: 'bg-red-100 text-red-700', icon: XCircle },
  cv_replacement_requested:      { label: 'CV replacement requested', color: 'bg-cyan-100 text-cyan-700', icon: RefreshCw },
  cv_document_linked:            { label: 'CV document linked', color: 'bg-blue-100 text-blue-700', icon: FileText },
  reject_reference:              { label: 'Reference rejected', color: 'bg-red-100 text-red-700', icon: XCircle },
  viewed:                        { label: 'Viewed', color: 'bg-slate-100 text-slate-600', icon: Eye },
};

/* ─── Critical recruitment event actions ─────────────────────── *
 * These are the actions that prove recruitment decisions were made,
 * including both positive sign-offs AND corrective/destructive acts.
 * A CQC inspector should be able to filter to this set and see
 * every consequential decision for an employee.                   */
const CRITICAL_ACTIONS = new Set([
  'document_verified', 'verify_document', 'verify_with_digital_stamp',
  'verify_and_stamp_identity', 'verify_and_stamp_address',
  'check_recorded', 'verify_requirement', 'unverify_requirement',
  'verify_training', 'training_correction',
  'reference_verified', 'verify_reference', 'reject_reference',
  'signoff_form',
  'verify_agreement_submission', 'reject_agreement_submission',
  'health_declaration_reviewed',
  'document_rejected', 'reject_document',
  'mark_uploaded_in_error',
  'delete_evidence', 'remove_evidence', 'document_removed',
  'status_changed', 'status_change',
  'deactivate_employee', 'reactivate_employee',
  'archive_employee', 'restore_employee',
  // Readiness-critical decisions (see ACTION_CONFIG above)
  'approve_for_work',
  'auto_promoted_to_active', 'manual_promotion_to_active',
  'cv_approved', 'cv_rejected', 'cv_replacement_requested',
]);

/* ─── Sign-off subset of critical ────────────────────────────── */
const SIGNOFF_ACTIONS = new Set([
  'signoff_form', 'verify_document', 'document_verified',
  'verify_with_digital_stamp', 'verify_and_stamp_identity', 'verify_and_stamp_address',
  'check_recorded', 'verify_requirement', 'verify_training',
  'reference_verified', 'verify_reference',
  'verify_agreement_submission', 'health_declaration_reviewed',
  'approve_for_work', 'cv_approved',
  'auto_promoted_to_active', 'manual_promotion_to_active',
]);

/* ─── Corrective / destructive actions that require a reason ─── */
const REASON_REQUIRED_ACTIONS = new Set([
  'document_rejected', 'reject_document',
  'reject_agreement_submission',
  'mark_uploaded_in_error',
  'request_replacement', 'request_reference_replacement',
  'training_record_updated', 'training_correction',
  'unverify_requirement',
  'delete_evidence', 'remove_evidence', 'document_removed', 'document_replaced',
  'cv_rejected', 'cv_replacement_requested',
  'reject_reference',
  'manual_promotion_to_active',
  'deactivate_employee', 'reactivate_employee',
  'archive_employee',
]);

/* ─── Normalise a single audit log entry ─────────────────────── *
 * The backend has three writers (log_audit_action, log_audit_change,
 * AuditTrailService.log) that each use slightly different field names.
 * This function normalises them into a consistent shape.            */
function normaliseLog(log) {
  let action = log.action || 'unknown';
  const meta = log.metadata || {};
  const details = log.details || {};

  const actor = log.user_name || meta.changed_by_name || meta.user_name || log.user_email || null;
  const ts = log.timestamp || log.created_at || null;
  const entityType = log.entity_type ? log.entity_type.replace(/_/g, ' ') : null;
  const entityId = log.entity_id || meta.requirement_id || meta.file_id || null;

  // State transition — three possible shapes
  let prevState = null;
  let newState = null;

  if (log.previous_state && typeof log.previous_state === 'object' && Object.keys(log.previous_state).length > 0) {
    prevState = log.previous_state;
  } else if (details.before != null) {
    prevState = { [log.field_name || 'value']: details.before };
  } else if (meta.old_value != null) {
    prevState = { [meta.field_changed || log.field_name || 'value']: meta.old_value };
  } else if (meta.old_values && typeof meta.old_values === 'object') {
    prevState = meta.old_values;
  }

  if (log.new_state && typeof log.new_state === 'object' && Object.keys(log.new_state).length > 0) {
    newState = log.new_state;
  } else if (details.after != null) {
    newState = { [log.field_name || 'value']: details.after };
  } else if (meta.new_value != null) {
    newState = { [meta.field_changed || log.field_name || 'value']: meta.new_value };
  } else if (meta.new_values && typeof meta.new_values === 'object') {
    newState = meta.new_values;
  }

  const lifecyclePrev = meta.previous_status || null;
  const lifecycleNext = meta.status || meta.new_status || null;
  if (action === 'update_employee' && lifecyclePrev && lifecycleNext && lifecyclePrev !== lifecycleNext) {
    if (lifecyclePrev === 'active' && lifecycleNext === 'inactive') {
      action = 'deactivate_employee';
    } else if (lifecyclePrev === 'inactive' && lifecycleNext === 'onboarding') {
      action = 'reactivate_employee';
    } else if (lifecycleNext === 'active') {
      action = 'auto_promoted_to_active';
    }
  }

  if (!prevState && lifecyclePrev && lifecycleNext && lifecyclePrev !== lifecycleNext) {
    prevState = { status: lifecyclePrev };
    newState = { status: lifecycleNext };
  }

  const reason =
    log.notes ||
    details.reason ||
    meta.reason ||
    meta.status_change_reason ||
    meta.lifecycle_last_transition_reason ||
    null;
  const description = log.description || meta.description || null;

  const isCritical = CRITICAL_ACTIONS.has(action);
  const isSignoff = SIGNOFF_ACTIONS.has(action);
  const reasonRequired = REASON_REQUIRED_ACTIONS.has(action);

  return {
    ...log,
    _action: action,
    _actor: actor,
    _ts: ts,
    _entityType: entityType,
    _entityId: entityId,
    _prevState: prevState,
    _newState: newState,
    _reason: reason,
    _description: description,
    _isCritical: isCritical,
    _isSignoff: isSignoff,
    _reasonRequired: reasonRequired,
    _missingReason: reasonRequired && !reason,
    _missingActor: isCritical && !actor,
    _hasWeakness: (reasonRequired && !reason) || (isCritical && !actor),
  };
}

/* ─── Format a state object for display ──────────────────────── */
function formatState(state) {
  if (!state) return '—';
  const entries = Object.entries(state);
  if (entries.length === 0) return '—';
  if (entries.length === 1) {
    const [key, val] = entries[0];
    const v = typeof val === 'object' ? JSON.stringify(val) : String(val);
    return key === 'value' ? v : `${key.replace(/_/g, ' ')}: ${v}`;
  }
  return entries.map(([k, v]) => {
    const sv = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return `${k.replace(/_/g, ' ')}: ${sv}`;
  }).join(' · ');
}

/* ─── Single audit event row ─────────────────────────────────── */
function AuditEventRow({ log, index, isLast }) {
  const config = ACTION_CONFIG[log._action] || { label: log._action, color: 'bg-gray-100 text-gray-600', icon: Clock };
  const ActionIcon = config.icon;

  return (
    <div
      className={`flex items-start gap-3 py-3 px-2 rounded-lg transition-colors hover:bg-gray-50 ${
        log._isCritical ? 'border-l-4 border-l-blue-400 bg-blue-50/30' : 'border-b border-gray-100 last:border-0'
      }`}
      data-testid={`audit-log-${index}`}
    >
      {/* Timeline indicator */}
      <div className="flex flex-col items-center pt-1 shrink-0">
        <div className={`w-8 h-8 rounded-full ${config.color.split(' ')[0]} flex items-center justify-center`}>
          <ActionIcon className={`h-4 w-4 ${config.color.split(' ')[1]}`} />
        </div>
        {!isLast && <div className="w-0.5 h-full bg-gray-200 mt-1" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Row 1: Badge + critical flag + entity type */}
        <div className="flex items-center gap-2 flex-wrap">
          <Badge className={`${config.color} text-xs`}>{config.label}</Badge>
          {log._isCritical && (
            <Badge className="bg-blue-600 text-white text-[10px] px-1.5 py-0">
              <Shield className="h-3 w-3 mr-0.5 inline" />
              Critical
            </Badge>
          )}
          {log._entityType && (
            <span className="text-xs text-gray-500 capitalize">{log._entityType}</span>
          )}
        </div>

        {/* Row 2: Description */}
        {log._description && (
          <p className="text-sm text-gray-700 mt-1">{log._description}</p>
        )}

        {/* Row 3: State transition (previous → new) */}
        {(log._prevState || log._newState) && (
          <div className="flex items-center gap-1.5 text-xs mt-1.5 flex-wrap">
            {log._prevState && (
              <span className="text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{formatState(log._prevState)}</span>
            )}
            <ArrowRight className="h-3 w-3 text-gray-400 shrink-0" />
            {log._newState ? (
              <span className="text-gray-700 bg-gray-100 px-1.5 py-0.5 rounded font-medium">{formatState(log._newState)}</span>
            ) : (
              <span className="text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">—</span>
            )}
          </div>
        )}

        {/* Row 4: Reason (if present) or missing-reason warning */}
        {log._reason ? (
          <p className="text-xs text-gray-600 mt-1">
            <span className="font-medium">Reason:</span> {log._reason}
          </p>
        ) : log._missingReason ? (
          <div className="flex items-center gap-1 text-xs text-amber-700 mt-1">
            <AlertTriangle className="h-3 w-3 shrink-0" />
            <span className="font-medium">Audit weakness:</span> No reason recorded for this corrective action
          </div>
        ) : null}

        {/* Row 5: Linked entity / evidence ID */}
        {log._entityId && log._entityId !== log.employee_id && (
          <div className="text-xs text-gray-500 mt-1">
            <span className="font-medium">Linked ID:</span> <span className="font-mono">{log._entityId}</span>
          </div>
        )}

        {/* Row 6: Metadata context (non-critical supplementary details) */}
        {log.metadata && Object.keys(log.metadata).length > 0 && (() => {
          const skipKeys = new Set(['employee_id', 'old_value', 'new_value', 'old_values', 'new_values', 'reason', 'description', 'changed_by_name', 'user_name', 'field_changed']);
          const entries = Object.entries(log.metadata).filter(([k]) => !skipKeys.has(k));
          if (entries.length === 0) return null;
          return (
            <div className="mt-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2 space-y-1">
              {entries.slice(0, 4).map(([key, value]) => (
                <div key={key} className="flex items-center gap-2">
                  <ChevronRight className="h-3 w-3 shrink-0" />
                  <span className="font-medium">{key.replace(/_/g, ' ')}:</span>
                  <span className="truncate">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                </div>
              ))}
            </div>
          );
        })()}

        {/* Row 7: Actor + timestamp + actor-missing flag */}
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-400 flex-wrap">
          {log._actor ? (
            <span>By: <span className="text-gray-600">{log._actor}</span></span>
          ) : log._missingActor ? (
            <span className="text-amber-600 font-medium flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Actor not recorded
            </span>
          ) : (
            <span className="text-gray-400">System</span>
          )}
          {log._ts && <span>{formatBackendDate(log._ts)}</span>}
        </div>
      </div>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────── */
export default function AuditTrailPanel({ employeeId }) {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [filter, setFilter] = useState('all');

  const fetchAuditTrail = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/audit-logs?employee_id=${encodeURIComponent(employeeId)}&limit=500`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // /api/audit-logs returns array directly; handle both shapes for safety
      setAuditLogs(Array.isArray(response.data) ? response.data : response.data?.audit_trail || []);
    } catch (error) {
      console.error('Failed to fetch audit trail:', error);
      setAuditLogs([]);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) fetchAuditTrail();
  }, [employeeId]);

  // Normalise all logs and compute summary counts
  const { normalised, criticalLogs, summary } = useMemo(() => {
    const n = auditLogs.map(normaliseLog);
    const crit = n.filter(l => l._isCritical);
    return {
      normalised: n,
      criticalLogs: crit,
      summary: {
        total: n.length,
        critical: crit.length,
        signoffs: n.filter(l => l._isSignoff).length,
        corrections: n.filter(l => l._reasonRequired).length,
        missingReasons: n.filter(l => l._missingReason).length,
        missingActors: n.filter(l => l._missingActor).length,
        weaknesses: n.filter(l => l._hasWeakness).length,
      },
    };
  }, [auditLogs]);

  // Client-side filtering
  const displayLogs = useMemo(() => {
    switch (filter) {
      case 'critical':    return criticalLogs;
      case 'weaknesses':  return normalised.filter(l => l._hasWeakness);
      case 'corrections': return normalised.filter(l => l._reasonRequired);
      default:            return normalised;
    }
  }, [normalised, criticalLogs, filter]);

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Audit Trail
          </span>
          <div className="flex items-center gap-2">
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-56 rounded-lg">
                <SelectValue placeholder="Filter..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All events ({summary.total})</SelectItem>
                <SelectItem value="critical">Critical recruitment events ({summary.critical})</SelectItem>
                <SelectItem value="corrections">Corrections & rejections ({summary.corrections})</SelectItem>
                <SelectItem value="weaknesses">Audit weaknesses ({summary.weaknesses})</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={fetchAuditTrail} disabled={loading} className="rounded-xl">
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Osabea audit trail for checks and staff-file decisions
        </p>
      </CardHeader>
      <CardContent>
        {/* ── Fail-closed: cannot assess ── */}
        {loadError ? (
          <div className="text-center py-12 text-red-700">
            <AlertTriangle className="h-12 w-12 mx-auto mb-3 text-red-400" />
            <p className="font-medium text-lg">Cannot assess audit trail</p>
            <p className="text-sm mt-1">Audit data unavailable. Do not rely on this tab for sign-off evidence until it loads.</p>
            <Button variant="outline" size="sm" onClick={fetchAuditTrail} className="mt-4 rounded-lg">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* ── Audit summary banner ── */}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-2">
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                <span><span className="font-semibold text-blue-700">{summary.critical}</span> critical recruitment events</span>
                <span><span className="font-semibold text-green-700">{summary.signoffs}</span> sign-offs</span>
                <span><span className="font-semibold text-amber-700">{summary.corrections}</span> corrections / rejections</span>
                <span><span className="font-semibold">{summary.total}</span> total events</span>
              </div>
              {summary.weaknesses > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 w-fit">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  <span className="font-medium">{summary.weaknesses} audit weakness{summary.weaknesses !== 1 ? 'es' : ''} detected</span>
                  <span className="text-amber-600">
                    {summary.missingReasons > 0 && ` · ${summary.missingReasons} corrective action${summary.missingReasons !== 1 ? 's' : ''} without recorded reason`}
                    {summary.missingActors > 0 && ` · ${summary.missingActors} critical event${summary.missingActors !== 1 ? 's' : ''} without recorded actor`}
                  </span>
                </div>
              )}
              {summary.total === 0 && (
                <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 w-fit">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  <span className="font-medium">No audit events recorded</span>
                  <span className="text-amber-600">— cannot confirm any recruitment actions have been properly logged</span>
                </div>
              )}
            </div>

            {/* ── Critical recruitment events section (shown in "all" view) ── */}
            {filter === 'all' && criticalLogs.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-blue-600" />
                  Critical Recruitment Events ({criticalLogs.length})
                </h3>
                <div className="space-y-1 border border-blue-200 rounded-lg p-2 bg-blue-50/20">
                  {criticalLogs.slice(0, 20).map((log, i) => (
                    <AuditEventRow key={log.id || `crit-${i}`} log={log} index={i} isLast={i === Math.min(criticalLogs.length, 20) - 1} />
                  ))}
                  {criticalLogs.length > 20 && (
                    <p className="text-xs text-gray-500 text-center py-2">
                      Showing 20 of {criticalLogs.length} — use the &quot;Critical recruitment events&quot; filter to see all
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* ── Full / filtered log ── */}
            <div className="space-y-2">
              {filter === 'all' && criticalLogs.length > 0 && (
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <History className="h-4 w-4 text-gray-500" />
                  All Events ({summary.total})
                </h3>
              )}
              {displayLogs.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <History className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No events match this filter</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {displayLogs.map((log, i) => (
                    <AuditEventRow key={log.id || `log-${i}`} log={log} index={i} isLast={i === displayLogs.length - 1} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

