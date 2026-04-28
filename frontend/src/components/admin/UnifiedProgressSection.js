import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Loader2,
  RefreshCw,
  Shield,
  Upload,
  Mail,
  Info
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { SendReminderButton, RequestRenewalButton } from './AdminActionButtons';
import { ComplianceBreakdownCard, PROGRESS_METRICS } from '../compliance/LabeledProgressMetrics';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

/**
 * UnifiedProgressSection - Displays the single source of truth progress
 * Uses the /api/employees/{id}/unified-progress endpoint
 */
export default function UnifiedProgressSection({
  employeeId,
  employeeName,
  onNavigateToRequirement
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(null);
  
  const fetchProgress = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/unified-progress`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setProgress(response.data);
    } catch (err) {
      console.error('Error fetching unified progress:', err);
      if (err.response?.status !== 404) {
        toast.error('Failed to load progress');
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);
  
  if (loading) {
    return (
      <Card className="border-dashed" data-testid="unified-progress-loading">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-500">Loading progress...</span>
        </CardContent>
      </Card>
    );
  }
  
  if (!progress) return null;
  
  const {
    overall_percentage,
    completed_requirements,
    total_requirements,
    categories,
    blockers,
    is_work_ready
  } = progress;
  
  // Get priority blockers (critical first)
  const priorityBlockers = [...(blockers || [])].sort((a, b) => {
    if (a.includes('Expired')) return -1;
    if (b.includes('Expired')) return 1;
    if (a.includes('Reference')) return -1;
    if (b.includes('Reference')) return 1;
    return 0;
  });
  
  return (
    <Card 
      className={cn(
        "border-2 transition-colors",
        is_work_ready ? "border-emerald-200 bg-emerald-50/30" : "border-amber-200 bg-amber-50/30"
      )}
      data-testid="unified-progress-section"
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center",
              is_work_ready ? "bg-emerald-100" : "bg-amber-100"
            )}>
              {is_work_ready ? (
                <Shield className="h-5 w-5 text-emerald-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-600" />
              )}
            </div>
            <div>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <CardTitle className="text-lg flex items-center gap-2 cursor-help">
                      <span>✅</span> Ready to work
                      <Info className="h-4 w-4 text-slate-400" />
                    </CardTitle>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs bg-slate-900 text-white">
                    <p className="font-medium mb-1">Ready to work</p>
                    <p className="text-sm text-slate-300">
                      All requirements including documents, forms, training, induction, and competencies.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <CardDescription>
                {is_work_ready ? 'Cleared for work' : `${blockers?.length || 0} items blocking work readiness`}
              </CardDescription>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchProgress}
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
            
            {!is_work_ready && (
              <SendReminderButton
                employeeId={employeeId}
                employeeName={employeeName}
                onSuccess={fetchProgress}
                variant="outline"
                size="sm"
              />
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Main Progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-2xl font-bold text-gray-900">
              {overall_percentage}%
            </span>
          </div>
          <Progress 
            value={overall_percentage} 
            className={cn(
              "h-3",
              is_work_ready ? "[&>div]:bg-emerald-500" : "[&>div]:bg-amber-500"
            )}
          />
          <p className="text-xs text-gray-500 mt-1">
            {completed_requirements} of {total_requirements} requirements complete
          </p>
        </div>
        
        {/* Category Breakdown - Using ComplianceBreakdownCard */}
        <ComplianceBreakdownCard 
          categories={categories}
          totalCompleted={completed_requirements}
          totalRequired={total_requirements}
          className="border-0 p-0 bg-transparent"
        />
        
        {/* Blockers */}
        {priorityBlockers.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Items needing attention ({priorityBlockers.length})
            </p>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {priorityBlockers.slice(0, 8).map((blocker, idx) => {
                const isExpired = blocker.includes('Expired');
                const isReference = blocker.includes('Reference');
                
                return (
                  <div
                    key={idx}
                    className={cn(
                      "flex items-center justify-between p-2 rounded-lg border text-left",
                      isExpired ? "bg-red-50 border-red-200" : "bg-white border-gray-200"
                    )}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {isExpired ? (
                        <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-amber-500 flex-shrink-0" />
                      )}
                      <span className="text-sm text-gray-800 truncate">{blocker}</span>
                    </div>
                    
                    {/* Action buttons for specific blockers */}
                    {isExpired && (
                      <RequestRenewalButton
                        employeeId={employeeId}
                        employeeName={employeeName}
                        renewalType={blocker.toLowerCase().includes('dbs') ? 'dbs' : 
                                     blocker.toLowerCase().includes('training') ? 'training' : 'identity'}
                        itemName={blocker}
                        size="sm"
                        variant="ghost"
                      />
                    )}
                    
                    {!isExpired && !isReference && onNavigateToRequirement && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onNavigateToRequirement(blocker.toLowerCase().replace(/\s+/g, '_'))}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                );
              })}
              {priorityBlockers.length > 8 && (
                <p className="text-xs text-gray-500 text-center py-1">
                  + {priorityBlockers.length - 8} more
                </p>
              )}
            </div>
          </div>
        )}
        
        {/* Success state */}
        {is_work_ready && (
          <div className="flex items-center justify-center p-4 bg-emerald-100 rounded-lg">
            <CheckCircle className="h-5 w-5 text-emerald-600 mr-2" />
            <span className="font-medium text-emerald-700">All compliance requirements satisfied</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

