/**
 * ConsolidatedStatusPanel - Single source of truth for employee status
 * 
 * Replaces the duplicate:
 * - RecruitmentApprovalPanel (was showing 2x)
 * - WorkReadinessPanel (was showing 2x)
 * - PreEmploymentGatesPanel
 * - Full Compliance card
 * - Blocking Items card
 * 
 * Shows ONE view with:
 * - Status header (BLOCKED/READY)
 * - ONE blocker list with color-coded severity
 * - ONE progress summary
 * - Quick actions
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  AlertTriangle,
  FileText, Users, GraduationCap, ClipboardCheck,
  Send, Plus, RefreshCw, Loader2, Shield,
  FileCheck, UserCheck, Briefcase, Heart, Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import API_BASE from '../../utils/apiBase';


const API = API_BASE;

export default function ConsolidatedStatusPanel({
  employeeId,
  employeeName,
  role,
  personStage,
  recruitmentApproved,
  onRefresh
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [gateResult, setGateResult] = useState(null); // structured recruitment gate
  const [gateLoading, setGateLoading] = useState(false);
  const [gateFetchFailed, setGateFetchFailed] = useState(false); // true when gate endpoint errored

  const fetchStatus = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      // Fetch unified progress and pre-employment gates
      const [progressRes, gatesRes] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}/unified-progress`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/employees/${employeeId}/pre-employment-gates`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setData({
        progress: progressRes.data,
        gates: gatesRes.data
      });
    } catch (error) {
      console.error('Failed to fetch status:', error);
      setData(null);
      setLoadError(error.response?.data?.detail || error.message || 'Unable to load readiness status');
    } finally {
      setLoading(false);
    }
  };

  const fetchGate = async () => {
    if (!token || !employeeId) return;
    setGateLoading(true);
    try {
      const res = await axios.get(
        `${API}/employees/${employeeId}/recruitment-gate`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setGateResult(res.data?.gate ?? null);
      setGateFetchFailed(false);
    } catch (err) {
      console.warn('Could not load recruitment gate:', err.response?.data?.detail || err.message);
      setGateResult(null);
      setGateFetchFailed(true);
    } finally {
      setGateLoading(false);
    }
  };

  useEffect(() => {
    if (token && employeeId) {
      fetchStatus();
      // Only fetch the gate for applicants (not yet recruited)
      if (personStage === 'applicant' && !recruitmentApproved) {
        fetchGate();
      }
    }
  }, [token, employeeId, personStage, recruitmentApproved]);

  const handleSendReminder = async () => {
    setActionLoading('reminder');
    try {
      await axios.post(
        `${API}/workers/${employeeId}/send-reminder`,
        { reminder_type: 'general' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Reminder sent to worker');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reminder');
    } finally {
      setActionLoading(null);
    }
  };

  const handleApproveRecruitment = async () => {
    setActionLoading('approve');
    try {
      await axios.post(
        `${API}/employees/${employeeId}/approve-recruitment`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${employeeName} approved for recruitment!`);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <Card className="border-2 border-gray-200">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-4" data-testid="consolidated-status-panel">
        <Card className="border-2 border-gray-300 bg-gray-50/40">
          <CardContent className="py-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-gray-600" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-800">
                    Readiness status unavailable
                  </p>
                  <p className="text-sm text-gray-600">
                    {employeeName} • {role} • Canonical readiness could not be loaded
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={fetchStatus}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
            <CardTitle className="text-base font-semibold text-gray-700">
              PRE-EMPLOYMENT PROGRESS: unavailable
            </CardTitle>
          </CardHeader>
          <CardContent className="py-4">
            <p className="text-sm text-gray-600">
              Readiness, blockers, and promotion actions are hidden until canonical status loads.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const progress = data?.progress || {};
  const gates = data?.gates || {};
  const progressBlockerDetails = Array.isArray(progress.blocker_details) ? progress.blocker_details : [];
  const progressBlockerStrings = Array.isArray(progress.blockers)
    ? progress.blockers.map((blocker) => (
        typeof blocker === 'string'
          ? { gate: '', label: blocker, reason: blocker, severity: 'critical' }
          : blocker
      ))
    : [];
  const blockers = progressBlockerDetails.length > 0
    ? progressBlockerDetails
    : progressBlockerStrings.length > 0
      ? progressBlockerStrings
      : [];
  const progressCompleted = progress.completed_requirements;
  const progressTotal = progress.total_requirements;
  const progressCountAvailable = Number.isFinite(progressTotal) && progressTotal > 0;
  
  // Canonical readiness/progression percentage comes from unified-progress.
  const progressPercentage = progress.overall_percentage ?? 0;
  
  // Use categories breakdown from unified-progress for the detailed grid
  const breakdown = progress.categories || {};

  // Determine overall status
  const isApplicant = personStage === 'applicant';

  // Gate-derived approval readiness (canonical — overrides old isBlocked for the approve CTA)
  const gateAllowed = gateResult?.allowed === true;
  const gateHasData = gateResult !== null;
  // Approval CTA guard: gate is the ONLY signal — no fallback to legacy isBlocked
  const canApproveRecruitment = gateAllowed;

  return (
    <div className="space-y-4" data-testid="consolidated-status-panel">
      {/* PROGRESS SUMMARY - ONE CARD */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-gray-700">
              Submission Progress — {progressCountAvailable
                ? `${progressCompleted ?? 0} of ${progressTotal} items submitted (${progressPercentage}%)`
                : `item count unavailable (${progressPercentage}%)`}
            </CardTitle>
            <p className="text-[11px] text-gray-400 mt-0.5">Tracks document and form submission only — not approval readiness</p>
            <Button variant="ghost" size="sm" onClick={fetchStatus}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="py-4">
          <Progress value={progressPercentage} className="h-3 mb-4" />
          
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {[
              { label: 'Documents', key: 'documents', icon: FileText },
              { label: 'Forms', key: 'forms', icon: ClipboardCheck },
              { label: 'Training', key: 'training', icon: GraduationCap },
              { label: 'References', key: 'references', icon: Users },
              { label: 'Agreements', key: 'agreements', icon: FileCheck },
              { label: 'Induction', key: 'induction', icon: Briefcase }
            ].map((cat) => {
              const catData = breakdown[cat.key] || { completed: 0, total: 0 };
              const Icon = cat.icon;
              const isComplete = catData.completed >= catData.total && catData.total > 0;
              
              return (
                <div 
                  key={cat.key}
                  className={cn(
                    "p-2 rounded-lg text-center border",
                    isComplete ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"
                  )}
                >
                  <Icon className={cn(
                    "h-4 w-4 mx-auto mb-1",
                    isComplete ? "text-green-600" : "text-gray-400"
                  )} />
                  <p className={cn(
                    "text-sm font-medium",
                    isComplete ? "text-green-700" : "text-gray-700"
                  )}>
                    {catData.completed}/{catData.total}
                  </p>
                  <p className="text-xs text-gray-500">{cat.label}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* QUICK ACTIONS */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <CardTitle className="text-base font-semibold text-gray-700">
            QUICK ACTIONS
          </CardTitle>
        </CardHeader>
        <CardContent className="py-3 px-4">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSendReminder}
              disabled={actionLoading === 'reminder'}
            >
              {actionLoading === 'reminder' ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <Send className="h-4 w-4 mr-1" />
              )}
              Send Reminder to Worker
            </Button>
            {isApplicant && !recruitmentApproved && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleApproveRecruitment}
                disabled={actionLoading === 'approve' || gateLoading || !canApproveRecruitment || gateFetchFailed || (!gateHasData && !gateLoading)}
                title={
                  gateFetchFailed ? 'Approval check unavailable — reload to retry' :
                  !gateHasData ? 'Approval check not yet loaded' :
                  !canApproveRecruitment ? 'Resolve all blockers before approving' :
                  undefined
                }
              >
                {actionLoading === 'approve' ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <UserCheck className="h-4 w-4 mr-1" />
                )}
                Approve for Recruitment
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

