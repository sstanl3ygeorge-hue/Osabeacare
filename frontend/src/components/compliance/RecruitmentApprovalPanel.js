import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Shield,
  Loader2,
  UserCheck,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  Clock,
  ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * RecruitmentApprovalPanel - Controls recruitment approval gate
 * 
 * Shows:
 * - Approval readiness status
 * - Progress (verified_count / required_count)
 * - Blocker list with navigation
 * - Approve button (if ready)
 * - Blocker details (if not ready)
 */
export default function RecruitmentApprovalPanel({
  employeeId,
  employeeName,
  role,
  stageIdentity,
  onApprovalSuccess,
  onNavigateToRequirement
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [blockerDialogOpen, setBlockerDialogOpen] = useState(false);
  
  // Fetch approval check
  const fetchApprovalCheck = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/recruitment-approval-check`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEvaluation(response.data);
    } catch (err) {
      console.error('Error fetching approval check:', err);
      toast.error('Failed to load approval status');
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    fetchApprovalCheck();
  }, [fetchApprovalCheck]);
  
  // Handle approval
  const handleApprove = async () => {
    setApproving(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/approve-recruitment`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Recruitment approved successfully!');
      setConfirmDialogOpen(false);
      
      // Call success callback with updated employee data
      onApprovalSuccess && onApprovalSuccess(response.data);
      
    } catch (err) {
      console.error('Error approving recruitment:', err);
      const detail = err.response?.data?.detail;
      
      if (typeof detail === 'object' && detail.blockers) {
        // Update evaluation with blockers
        setEvaluation(prev => ({
          ...prev,
          can_approve: false,
          blockers: detail.blockers,
          blocker_count: detail.blockers.length,
          verified_count: detail.verified_count,
          required_count: detail.required_count
        }));
        setConfirmDialogOpen(false);
        setBlockerDialogOpen(true);
        toast.error('Cannot approve - blockers exist');
      } else {
        toast.error(detail?.message || detail || 'Failed to approve recruitment');
      }
    } finally {
      setApproving(false);
    }
  };
  
  // Handle blocker click - navigate to that section
  const handleBlockerClick = (blocker) => {
    if (onNavigateToRequirement) {
      onNavigateToRequirement(blocker.requirement_key, blocker.section);
    }
    setBlockerDialogOpen(false);
  };
  
  // Don't show for employees (already approved)
  if (stageIdentity === 'employee' || evaluation?.recruitment_approved) {
    return null;
  }
  
  // Loading state
  if (loading) {
    return (
      <Card className="border-dashed" data-testid="approval-panel-loading">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-teal-600" />
          <span className="ml-2 text-gray-500">Checking approval status...</span>
        </CardContent>
      </Card>
    );
  }
  
  if (!evaluation) {
    return null;
  }
  
  const { 
    can_approve, 
    blockers, 
    blocker_count,
    warnings,
    warning_count,
    verified_count, 
    required_count,
    role_normalized
  } = evaluation;
  
  const progressPercent = required_count > 0 ? Math.round((verified_count / required_count) * 100) : 0;
  const isReady = can_approve;
  
  return (
    <>
      <Card 
        className={cn(
          "border-2 transition-colors",
          isReady ? "border-emerald-200 bg-emerald-50/30" : "border-amber-200 bg-amber-50/30"
        )}
        data-testid="recruitment-approval-panel"
      >
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center",
                isReady ? "bg-emerald-100" : "bg-amber-100"
              )}>
                {isReady ? (
                  <Shield className="h-5 w-5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                )}
              </div>
              <div>
                <CardTitle className="text-lg">Recruitment Approval</CardTitle>
                <CardDescription className="flex items-center gap-2 mt-0.5">
                  <Badge variant="outline" className="text-xs capitalize">
                    {role_normalized?.replace(/_/g, ' ') || role}
                  </Badge>
                  <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700">
                    Applicant
                  </Badge>
                </CardDescription>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchApprovalCheck}
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Status Banner */}
          <div className={cn(
            "p-3 rounded-lg flex items-center gap-3",
            isReady ? "bg-emerald-100" : "bg-amber-100"
          )}>
            {isReady ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="font-medium text-emerald-800">Ready for Recruitment Approval</p>
                  <p className="text-sm text-emerald-600">All required items verified</p>
                </div>
              </>
            ) : (
              <>
                <Clock className="h-5 w-5 text-amber-600" />
                <div>
                  <p className="font-medium text-amber-800">
                    Blocked by {blocker_count} item{blocker_count !== 1 ? 's' : ''}
                  </p>
                  <p className="text-sm text-amber-600">Complete required items to approve</p>
                </div>
              </>
            )}
          </div>
          
          {/* Recruitment Approval Progress */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Recruitment Readiness</span>
              <span className="text-sm font-medium">
                {verified_count} / {required_count} key items verified
              </span>
            </div>
            <Progress 
              value={progressPercent} 
              className={cn(
                "h-2",
                isReady ? "[&>div]:bg-emerald-500" : "[&>div]:bg-amber-500"
              )}
            />
            <p className="text-xs text-gray-500 mt-1">
              {progressPercent}% ready for recruitment approval
            </p>
          </div>
          
          {/* Blockers Preview */}
          {!isReady && blockers && blockers.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Items needing attention:</p>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {blockers.slice(0, 5).map((blocker, idx) => (
                  <button
                    key={blocker.requirement_key || idx}
                    className="w-full flex items-center justify-between p-2 rounded bg-white border border-red-100 hover:border-red-300 transition-colors text-left"
                    onClick={() => handleBlockerClick(blocker)}
                    data-testid={`blocker-${blocker.requirement_key}`}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                      <div className="min-w-0">
                        <span className="font-medium text-gray-800 text-sm block truncate">
                          {blocker.label}
                        </span>
                        <span className="text-xs text-red-500 block truncate">
                          {blocker.reason}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  </button>
                ))}
                {blockers.length > 5 && (
                  <p className="text-xs text-gray-500 text-center py-1">
                    + {blockers.length - 5} more blockers
                  </p>
                )}
              </div>
            </div>
          )}
          
          {/* Warnings */}
          {warnings && warnings.length > 0 && (
            <div className="p-2 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {warning_count} non-blocking item{warning_count !== 1 ? 's' : ''} pending
              </p>
            </div>
          )}
        </CardContent>
        
        <CardFooter className="pt-0">
          {isReady ? (
            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              onClick={() => setConfirmDialogOpen(true)}
              disabled={approving}
              data-testid="approve-recruitment-btn"
            >
              {approving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <UserCheck className="h-4 w-4 mr-2" />
              )}
              Approve to Onboarding
            </Button>
          ) : (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setBlockerDialogOpen(true)}
              data-testid="view-blockers-btn"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              View All Blockers ({blocker_count})
            </Button>
          )}
        </CardFooter>
      </Card>
      
      {/* Confirm Approval Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent data-testid="confirm-approval-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-emerald-600" />
              Approve to Onboarding?
            </DialogTitle>
            <DialogDescription>
              This will transition <strong>{employeeName}</strong> from Applicant to Employee status.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 space-y-3">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <ArrowRight className="h-5 w-5 text-gray-400" />
              <div className="text-sm">
                <p><span className="text-gray-500">Stage:</span> Applicant <ArrowRight className="inline h-3 w-3 mx-1" /> <strong className="text-emerald-600">Employee</strong></p>
                <p><span className="text-gray-500">Status:</span> Current <ArrowRight className="inline h-3 w-3 mx-1" /> <strong className="text-teal-600">Onboarding</strong></p>
              </div>
            </div>
            
            <div className="text-sm text-gray-600">
              <p>This action will:</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-gray-500">
                <li>Assign an employee code</li>
                <li>Set status to Onboarding</li>
                <li>Enable employee actions</li>
                <li>Record approval in audit log</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setConfirmDialogOpen(false)}
              disabled={approving}
            >
              Cancel
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={handleApprove}
              disabled={approving}
              data-testid="confirm-approve-btn"
            >
              {approving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4 mr-2" />
              )}
              Confirm Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Blockers Dialog */}
      <Dialog open={blockerDialogOpen} onOpenChange={setBlockerDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="blockers-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-700">
              <AlertTriangle className="h-5 w-5" />
              Cannot Approve Recruitment
            </DialogTitle>
            <DialogDescription>
              The following {blocker_count} item{blocker_count !== 1 ? 's' : ''} must be resolved before approval.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 max-h-80 overflow-y-auto space-y-2">
            {blockers?.map((blocker, idx) => (
              <button
                key={blocker.requirement_key || idx}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-red-50 border border-red-100 hover:border-red-300 transition-colors text-left"
                onClick={() => handleBlockerClick(blocker)}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                    <XCircle className="h-4 w-4 text-red-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800 truncate">{blocker.label}</p>
                    <p className="text-sm text-red-600">{blocker.reason}</p>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 text-gray-400 flex-shrink-0" />
              </button>
            ))}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setBlockerDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

