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
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  AlertTriangle, CheckCircle, XCircle, ChevronRight,
  FileText, Users, GraduationCap, ClipboardCheck,
  Send, Eye, Plus, RefreshCw, Loader2, Shield,
  FileCheck, UserCheck, Briefcase, Heart, Calendar,
  Clock, AlertCircle, Lock, Info, Edit
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

const API = process.env.REACT_APP_BACKEND_URL;

// Blocker icons mapping
const BLOCKER_ICONS = {
  'identity': FileCheck,
  'proof_of_address': FileText,
  'right_to_work': Shield,
  'dbs': Shield,
  'reference': Users,
  'interview': ClipboardCheck,
  'contract': FileText,
  'induction': ClipboardCheck,
  'health': Heart,
  'training': GraduationCap,
  'gaps': Calendar,
  'default': AlertTriangle
};

// Blocker severity classification
// Critical: Missing/unverified required documents
// Pending: Uploaded but awaiting verification
// Complete: Fully verified (not shown in blockers)
const BLOCKER_SEVERITY = {
  CRITICAL: {
    label: 'Critical',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    iconColor: 'text-red-600',
    iconBg: 'bg-red-100',
    dot: '🔴'
  },
  PENDING: {
    label: 'Pending',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    iconColor: 'text-amber-600',
    iconBg: 'bg-amber-100',
    dot: '🟡'
  },
  COMPLETE: {
    label: 'Complete',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-700',
    iconColor: 'text-green-600',
    iconBg: 'bg-green-100',
    dot: '🟢'
  }
};

// Determine blocker severity based on gate status
const getBlockerSeverity = (blocker, gateData) => {
  // Check if there's evidence uploaded but not verified
  const hasUploaded = gateData?.has_uploaded || blocker.has_evidence;
  const isPending = gateData?.status === 'pending' || 
                    gateData?.status === 'uploaded' ||
                    gateData?.status === 'under_review' ||
                    blocker.status === 'pending';
  
  if (hasUploaded || isPending) {
    return 'PENDING';
  }
  
  // Default to critical for missing items
  return 'CRITICAL';
};

const getBlockerIcon = (blockerKey) => {
  for (const [key, Icon] of Object.entries(BLOCKER_ICONS)) {
    if (blockerKey?.toLowerCase().includes(key)) {
      return Icon;
    }
  }
  return BLOCKER_ICONS.default;
};

export default function ConsolidatedStatusPanel({
  employeeId,
  employeeName,
  role,
  personStage,
  recruitmentApproved,
  onNavigateToTab,
  onNavigateToItem,
  onRefresh,
  onVerifyWithEvidence,  // NEW: Callback to open verification modal
  onViewDocument         // NEW: Callback to open document viewer
}) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchStatus = async () => {
    try {
      // Fetch unified progress and pre-employment gates
      const [progressRes, gatesRes] = await Promise.all([
        axios.get(`${API}/api/employees/${employeeId}/unified-progress`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/employees/${employeeId}/pre-employment-gates`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setData({
        progress: progressRes.data,
        gates: gatesRes.data
      });
    } catch (error) {
      console.error('Failed to fetch status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token && employeeId) {
      fetchStatus();
    }
  }, [token, employeeId]);

  const handleSendReminder = async () => {
    setActionLoading('reminder');
    try {
      await axios.post(
        `${API}/api/workers/${employeeId}/send-reminder`,
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
        `${API}/api/employees/${employeeId}/approve-recruitment`,
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

  const handlePromoteToActive = async () => {
    setActionLoading('promote');
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/promote-to-active`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${employeeName} promoted to Active Employee!`);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to promote');
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

  const progress = data?.progress || {};
  const gates = data?.gates || {};
  const blockers = gates.blockers || [];
  const canPromote = gates.can_promote;
  const gatesPassed = gates.gates_passed || 0;
  const totalGates = gates.total_gates || 12;
  
  // Calculate percentage from gates (pre-employment gates are the real promotion blockers)
  const gatesPercentage = totalGates > 0 ? Math.round((gatesPassed / totalGates) * 100) : 0;
  
  // Use categories breakdown from unified-progress for the detailed grid
  const breakdown = progress.categories || {};

  // Determine overall status
  const isBlocked = blockers.length > 0;
  const isApplicant = personStage === 'applicant';
  const isEmployee = personStage === 'employee' || recruitmentApproved;

  return (
    <div className="space-y-4" data-testid="consolidated-status-panel">
      {/* STATUS HEADER */}
      <Card className={cn(
        "border-2",
        isBlocked ? "border-amber-300 bg-amber-50/30" : "border-green-300 bg-green-50/30"
      )}>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isBlocked ? (
                <div className="w-12 h-12 rounded-full bg-amber-100 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-amber-600" />
                </div>
              ) : (
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
              )}
              <div>
                <p className={cn(
                  "text-lg font-semibold",
                  isBlocked ? "text-amber-800" : "text-green-800"
                )}>
                  {isBlocked ? (
                    <>Cannot be promoted yet</>
                  ) : (
                    <>No current pre-employment blockers</>
                  )}
                </p>
                <p className="text-sm text-gray-600">
                  {employeeName} • {role} • {isApplicant ? 'Applicant' : 'Onboarding'}
                </p>
              </div>
            </div>
            
            {/* Main Action Button */}
            <div>
              {isApplicant && !recruitmentApproved && !isBlocked && (
                <Button
                  onClick={handleApproveRecruitment}
                  disabled={actionLoading === 'approve'}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {actionLoading === 'approve' ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <UserCheck className="h-4 w-4 mr-2" />
                  )}
                  Approve for Recruitment
                </Button>
              )}
              {isEmployee && canPromote && (
                <Button
                  onClick={handlePromoteToActive}
                  disabled={actionLoading === 'promote'}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {actionLoading === 'promote' ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Promote to Active Employee
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* BLOCKING ITEMS - ONE LIST WITH COLOR CODING */}
      {blockers.length > 0 && (
        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-red-50/50 border-b border-red-100">
            <CardTitle className="text-base font-semibold text-red-800 flex items-center gap-2">
              <XCircle className="h-5 w-5" />
              OPEN PRE-EMPLOYMENT BLOCKERS ({blockers.length} items)
            </CardTitle>
            <p className="text-xs text-gray-600 mt-1">
              🔴 Critical = Missing/Unverified &nbsp;|&nbsp; 🟡 Pending = Awaiting Verification
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {blockers.map((blocker, idx) => {
                const Icon = getBlockerIcon(blocker.gate);
                const gateData = gates.gates?.[blocker.gate];
                const severity = getBlockerSeverity(blocker, gateData);
                const severityConfig = BLOCKER_SEVERITY[severity];
                
                const getAction = () => {
                  // Reference blockers
                  if (blocker.gate?.includes('reference')) {
                    return { 
                      label: 'Review', 
                      tab: 'references',
                      sectionId: 'section-references-root',
                      tooltip: 'Review and verify the reference response'
                    };
                  }
                  // Interview Record
                  if (blocker.gate?.includes('interview')) {
                    return { 
                      label: 'Complete Interview', 
                      tab: 'forms',
                      sectionId: 'section-forms-interview',
                      tooltip: 'Complete the interview record form'
                    };
                  }
                  // Contract: Locked until all other requirements complete
                  if (blocker.gate?.includes('contract')) {
                    return { 
                      label: 'Locked', 
                      tab: 'checklist', 
                      sectionId: 'section-agreements',
                      locked: true,
                      tooltip: 'Contract signing unlocks when all other requirements are complete. Worker signs via their dashboard.'
                    };
                  }
                  // Induction Checklist
                  if (blocker.gate?.includes('induction')) {
                    return { 
                      label: 'Start', 
                      tab: 'training',
                      sectionId: 'section-training-induction',
                      tooltip: 'Start the 15-item induction checklist'
                    };
                  }
                  // Health Questionnaire
                  if (blocker.gate?.includes('health')) {
                    return { 
                      label: 'Send to Worker', 
                      tab: 'forms',
                      sectionId: 'section-forms-core',
                      tooltip: 'Send health questionnaire link to worker'
                    };
                  }
                  // Training
                  if (blocker.gate?.includes('training')) {
                    return { 
                      label: 'View Training', 
                      tab: 'training',
                      sectionId: 'section-training-root',
                      tooltip: 'View and manage mandatory training records'
                    };
                  }
                  // Employment Gaps
                  if (blocker.gate?.includes('gaps')) {
                    return { 
                      label: 'Review Gaps', 
                      tab: 'employment',
                      sectionId: 'section-employment-gaps',
                      tooltip: 'Review unexplained employment history gaps'
                    };
                  }
                  // Spot check blockers
                  if (blocker.gate?.includes('spot_check') || blocker.gate?.includes('spot check')) {
                    return {
                      label: 'Open Spot Checks',
                      tab: 'spot_checks',
                      sectionId: 'section-spot-checks-root',
                      tooltip: 'Open spot checks and complete follow-up actions'
                    };
                  }
                  // Competency blockers
                  if (blocker.gate?.includes('competenc')) {
                    return {
                      label: 'Open Competencies',
                      tab: 'competencies',
                      sectionId: 'section-competencies-root',
                      tooltip: 'Open competency assessments and remediation actions'
                    };
                  }
                  // Document blockers: DBS, RTW, Identity, POA - use "Verify with Evidence"
                  if (blocker.gate?.includes('dbs') || blocker.gate?.includes('rtw') || 
                      blocker.gate?.includes('right_to_work') || blocker.gate?.includes('identity') || 
                      blocker.gate?.includes('poa') || blocker.gate?.includes('proof_of_address')) {
                    return { 
                      label: 'Verify with Evidence', 
                      tab: 'checklist',
                      sectionId: blocker.gate?.includes('dbs') ? 'section-dbs' :
                        blocker.gate?.includes('rtw') || blocker.gate?.includes('right_to_work') ? 'section-right_to_work' :
                        blocker.gate?.includes('identity') ? 'section-identity' :
                        blocker.gate?.includes('poa') || blocker.gate?.includes('proof_of_address') ? 'section-proof_of_address' :
                        null,
                      tooltip: 'Upload evidence and apply verification stamp'
                    };
                  }
                  // Default action
                  return { 
                    label: severity === 'PENDING' ? 'Verify' : 'View', 
                    tab: 'checklist',
                    sectionId: null,
                    tooltip: 'View and verify this requirement'
                  };
                };
                const action = getAction();

                return (
                  <div 
                    key={idx} 
                    className={cn(
                      "flex items-center justify-between px-4 py-3 hover:bg-gray-50",
                      severityConfig.bgColor
                    )}
                    data-testid={`blocker-item-${idx}`}
                    data-severity={severity}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center",
                        severityConfig.iconBg
                      )}>
                        <Icon className={cn("h-4 w-4", severityConfig.iconColor)} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{severityConfig.dot}</span>
                          <p className={cn("font-medium", severityConfig.textColor)}>
                            {blocker.label}
                          </p>
                          <Badge 
                            variant="outline" 
                            className={cn(
                              "text-[10px] px-1.5 py-0 h-4",
                              severity === 'CRITICAL' ? 'border-red-300 text-red-600' : 'border-amber-300 text-amber-600'
                            )}
                          >
                            {severityConfig.label}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500">
                          {severity === 'PENDING' 
                            ? 'Uploaded - awaiting admin verification'
                            : (gateData?.requirement || 'Required for promotion')
                          }
                        </p>
                      </div>
                    </div>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          {action.locked ? (
                            // Contract is locked until all other requirements complete
                            <Badge 
                              variant="outline" 
                              className="text-gray-500 border-gray-300 bg-gray-100 cursor-help"
                            >
                              <Lock className="h-3 w-3 mr-1" />
                              Locked
                              <Info className="h-3 w-3 ml-1 opacity-50" />
                            </Badge>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                // If this is a verification action and callback is provided, use it
                                if (action.label === 'Verify with Evidence' && onVerifyWithEvidence) {
                                  onVerifyWithEvidence(blocker.gate, gateData);
                                } else {
                                  if (onNavigateToItem) {
                                    onNavigateToItem(action.tab, action.sectionId || null);
                                  } else {
                                    onNavigateToTab?.(action.tab);
                                  }
                                }
                              }}
                              className={cn(
                                severity === 'CRITICAL' 
                                  ? "text-red-600 border-red-200 hover:bg-red-50"
                                  : "text-amber-600 border-amber-200 hover:bg-amber-50"
                              )}
                              data-testid={`action-btn-${blocker.gate}`}
                            >
                              {action.label}
                              <ChevronRight className="h-3.5 w-3.5 ml-1" />
                            </Button>
                          )}
                        </TooltipTrigger>
                        <TooltipContent side="left" className="max-w-xs">
                          <p>{action.tooltip}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* PROGRESS SUMMARY - ONE CARD */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="py-3 px-4 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-gray-700">
              PRE-EMPLOYMENT PROGRESS: {gatesPassed}/{totalGates} requirements complete ({gatesPercentage}%)
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchStatus}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="py-4">
          <Progress value={gatesPercentage} className="h-3 mb-4" />
          
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('compliance')}
            >
              <Eye className="h-4 w-4 mr-1" />
              View Full Compliance
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('training')}
            >
              <GraduationCap className="h-4 w-4 mr-1" />
              View Training
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onNavigateToTab?.('references')}
            >
              <Users className="h-4 w-4 mr-1" />
              View References
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
