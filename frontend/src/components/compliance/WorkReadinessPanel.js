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
  Briefcase,
  Loader2,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  Clock,
  FileCheck,
  ShieldCheck,
  GraduationCap,
  FileText,
  Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';

const API = process.env.REACT_APP_BACKEND_URL;

// Category icons
const CATEGORY_ICONS = {
  agreement: FileText,
  form: FileCheck,
  competency: GraduationCap,
  document: ShieldCheck,
  expired_document: Calendar,
  training: GraduationCap,
  expiring_soon: Clock,
};

/**
 * WorkReadinessPanel - Controls work readiness gate (Gate 2)
 * 
 * Shows:
 * - Work readiness status (READY_TO_WORK / NOT_READY)
 * - Progress (verified_count / required_count)
 * - Blocker list by category
 * - Warnings (expiring documents)
 */
export default function WorkReadinessPanel({
  employeeId,
  employeeName,
  role,
  stageIdentity,
  recruitmentApproved,
  onNavigateToRequirement
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [evaluation, setEvaluation] = useState(null);
  const [blockerDialogOpen, setBlockerDialogOpen] = useState(false);
  
  // Fetch work readiness check
  const fetchWorkReadiness = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/api/employees/${employeeId}/work-readiness-check`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEvaluation(response.data);
    } catch (err) {
      console.error('Error fetching work readiness:', err);
      // Don't show toast for 404 - employee might not exist yet
      if (err.response?.status !== 404) {
        toast.error('Failed to load work readiness status');
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    fetchWorkReadiness();
  }, [fetchWorkReadiness]);
  
  // Handle blocker click - navigate to that section
  const handleBlockerClick = (blocker) => {
    if (onNavigateToRequirement) {
      onNavigateToRequirement(blocker.requirement_key, blocker.section);
    }
    setBlockerDialogOpen(false);
  };
  
  // Don't show for applicants (not yet approved for recruitment)
  if (stageIdentity === 'applicant' || !recruitmentApproved) {
    return null;
  }
  
  // Loading state
  if (loading) {
    return (
      <Card className="border-dashed" data-testid="work-readiness-panel-loading">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-500">Checking work readiness...</span>
        </CardContent>
      </Card>
    );
  }
  
  if (!evaluation) {
    return null;
  }
  
  const { 
    can_work,
    readiness_status,
    blockers, 
    blocker_count,
    warnings,
    warning_count,
    verified_count, 
    required_count,
    role_normalized
  } = evaluation;
  
  const progressPercent = required_count > 0 ? Math.round((verified_count / required_count) * 100) : 0;
  const isReady = can_work;
  
  // Group blockers by category
  const blockersByCategory = blockers?.reduce((acc, blocker) => {
    const cat = blocker.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(blocker);
    return acc;
  }, {}) || {};
  
  // Get status styling
  const getStatusStyle = () => {
    if (isReady) {
      return {
        cardClass: "border-emerald-200 bg-emerald-50/30",
        iconBg: "bg-emerald-100",
        iconColor: "text-emerald-600",
        bannerBg: "bg-emerald-100",
        bannerTextPrimary: "text-emerald-800",
        bannerTextSecondary: "text-emerald-600",
        progressColor: "[&>div]:bg-emerald-500"
      };
    }
    if (readiness_status === "READY_WITH_CONDITIONS") {
      return {
        cardClass: "border-amber-200 bg-amber-50/30",
        iconBg: "bg-amber-100",
        iconColor: "text-amber-600",
        bannerBg: "bg-amber-100",
        bannerTextPrimary: "text-amber-800",
        bannerTextSecondary: "text-amber-600",
        progressColor: "[&>div]:bg-amber-500"
      };
    }
    return {
      cardClass: "border-red-200 bg-red-50/30",
      iconBg: "bg-red-100",
      iconColor: "text-red-600",
      bannerBg: "bg-red-100",
      bannerTextPrimary: "text-red-800",
      bannerTextSecondary: "text-red-600",
      progressColor: "[&>div]:bg-red-500"
    };
  };
  
  const style = getStatusStyle();
  
  return (
    <>
      <Card 
        className={cn("border-2 transition-colors", style.cardClass)}
        data-testid="work-readiness-panel"
      >
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn("w-10 h-10 rounded-full flex items-center justify-center", style.iconBg)}>
                <Briefcase className={cn("h-5 w-5", style.iconColor)} />
              </div>
              <div>
                <CardTitle className="text-lg">Work Readiness</CardTitle>
                <CardDescription className="flex items-center gap-2 mt-0.5">
                  <Badge variant="outline" className="text-xs capitalize">
                    {role_normalized?.replace(/_/g, ' ') || role}
                  </Badge>
                  <Badge variant="outline" className="text-xs bg-teal-50 text-teal-700">
                    Employee
                  </Badge>
                </CardDescription>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchWorkReadiness}
              disabled={loading}
              data-testid="refresh-work-readiness-btn"
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Status Banner */}
          <div className={cn("p-3 rounded-lg flex items-center gap-3", style.bannerBg)}>
            {isReady ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className={cn("font-medium", style.bannerTextPrimary)}>Ready to Work</p>
                  <p className={cn("text-sm", style.bannerTextSecondary)}>All work requirements satisfied</p>
                </div>
              </>
            ) : readiness_status === "READY_WITH_CONDITIONS" ? (
              <>
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <div>
                  <p className={cn("font-medium", style.bannerTextPrimary)}>Ready with Conditions</p>
                  <p className={cn("text-sm", style.bannerTextSecondary)}>
                    {blocker_count} item{blocker_count !== 1 ? 's' : ''} need attention
                  </p>
                </div>
              </>
            ) : (
              <>
                <XCircle className="h-5 w-5 text-red-600" />
                <div>
                  <p className={cn("font-medium", style.bannerTextPrimary)}>Not Ready to Work</p>
                  <p className={cn("text-sm", style.bannerTextSecondary)}>
                    {blocker_count} blocking item{blocker_count !== 1 ? 's' : ''} must be resolved
                  </p>
                </div>
              </>
            )}
          </div>
          
          {/* Progress */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Readiness Progress</span>
              <span className="text-sm font-medium">
                {verified_count} / {required_count} requirements
              </span>
            </div>
            <Progress 
              value={progressPercent} 
              className={cn("h-2", style.progressColor)}
            />
            <p className="text-xs text-gray-500 mt-1">{progressPercent}% complete</p>
          </div>
          
          {/* Blockers Preview */}
          {!isReady && blockers && blockers.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Blocking Items:</p>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {blockers.slice(0, 6).map((blocker, idx) => {
                  const CategoryIcon = CATEGORY_ICONS[blocker.category] || AlertCircle;
                  return (
                    <button
                      key={blocker.requirement_key || idx}
                      className="w-full flex items-center justify-between p-2 rounded bg-white border border-red-100 hover:border-red-300 transition-colors text-left"
                      onClick={() => handleBlockerClick(blocker)}
                      data-testid={`work-blocker-${blocker.requirement_key}`}
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <div className="w-6 h-6 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
                          <CategoryIcon className="h-3.5 w-3.5 text-red-500" />
                        </div>
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
                  );
                })}
                {blockers.length > 6 && (
                  <p className="text-xs text-gray-500 text-center py-1">
                    + {blockers.length - 6} more blockers
                  </p>
                )}
              </div>
            </div>
          )}
          
          {/* Warnings (Expiring Soon) */}
          {warnings && warnings.length > 0 && (
            <div className="p-2 bg-amber-50 rounded-lg border border-amber-100">
              <p className="text-sm text-amber-700 flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                {warning_count} document{warning_count !== 1 ? 's' : ''} expiring soon
              </p>
              <div className="mt-1.5 space-y-1">
                {warnings.slice(0, 2).map((warning, idx) => (
                  <p key={idx} className="text-xs text-amber-600 ml-5">
                    {warning.label} - {warning.reason}
                  </p>
                ))}
              </div>
            </div>
          )}
        </CardContent>
        
        <CardFooter className="pt-0">
          {!isReady && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setBlockerDialogOpen(true)}
              data-testid="view-work-blockers-btn"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              View All Blockers ({blocker_count})
            </Button>
          )}
          {isReady && (
            <div className="w-full text-center">
              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                Cleared for Work
              </Badge>
            </div>
          )}
        </CardFooter>
      </Card>
      
      {/* Blockers Dialog */}
      <Dialog open={blockerDialogOpen} onOpenChange={setBlockerDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="work-blockers-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <Briefcase className="h-5 w-5" />
              Work Readiness Blockers
            </DialogTitle>
            <DialogDescription>
              The following {blocker_count} item{blocker_count !== 1 ? 's' : ''} must be resolved before starting work.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 max-h-80 overflow-y-auto space-y-4">
            {/* Group by category */}
            {Object.entries(blockersByCategory).map(([category, categoryBlockers]) => {
              const CategoryIcon = CATEGORY_ICONS[category] || AlertCircle;
              const categoryLabels = {
                agreement: 'Agreements',
                form: 'Forms',
                competency: 'Competencies',
                document: 'Documents',
                expired_document: 'Expired Documents',
                training: 'Training'
              };
              
              return (
                <div key={category}>
                  <p className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1.5">
                    <CategoryIcon className="h-4 w-4" />
                    {categoryLabels[category] || category}
                  </p>
                  <div className="space-y-2">
                    {categoryBlockers.map((blocker, idx) => (
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
                </div>
              );
            })}
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
