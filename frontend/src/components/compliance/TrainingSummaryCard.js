import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  GraduationCap, CheckCircle, AlertTriangle, Clock, ChevronRight
} from 'lucide-react';

/**
 * TrainingSummaryCard - Compact training summary for Compliance File
 * 
 * Shows only summary stats + link to Training tab
 * Replaces detailed training rows in Compliance File
 */
export default function TrainingSummaryCard({
  completedCount = 0,
  totalCount = 0,
  expiringCount = 0,
  expiredCount = 0,
  onManageTraining,
  isAuditor = false
}) {
  const allComplete = completedCount === totalCount && totalCount > 0;
  const hasIssues = expiredCount > 0 || expiringCount > 0;
  
  // Determine status
  const getStatus = () => {
    if (expiredCount > 0) return { label: 'Expired', color: 'bg-red-100 text-red-700', icon: AlertTriangle };
    if (expiringCount > 0) return { label: 'Expiring Soon', color: 'bg-amber-100 text-amber-700', icon: Clock };
    if (allComplete) return { label: 'Complete', color: 'bg-green-100 text-green-700', icon: CheckCircle };
    return { label: 'In Progress', color: 'bg-blue-100 text-blue-700', icon: GraduationCap };
  };

  const status = getStatus();
  const StatusIcon = status.icon;

  return (
    <div 
      className="p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors cursor-pointer"
      onClick={onManageTraining}
      data-testid="training-summary-card"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
            expiredCount > 0 ? 'bg-red-100' :
            expiringCount > 0 ? 'bg-amber-100' :
            allComplete ? 'bg-green-100' : 'bg-blue-100'
          }`}>
            <GraduationCap className={`h-5 w-5 ${
              expiredCount > 0 ? 'text-red-600' :
              expiringCount > 0 ? 'text-amber-600' :
              allComplete ? 'text-green-600' : 'text-blue-600'
            }`} />
          </div>
          
          {/* Title and Stats */}
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-text-primary">Training Status</h4>
              <Badge className={`text-xs ${status.color}`}>
                <StatusIcon className="h-3 w-3 mr-1" />
                {status.label}
              </Badge>
            </div>
            <div className="flex items-center gap-3 mt-1 text-sm text-text-muted">
              <span className="flex items-center gap-1">
                <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                {completedCount}/{totalCount} completed
              </span>
              {expiringCount > 0 && (
                <span className="flex items-center gap-1 text-amber-600">
                  <Clock className="h-3.5 w-3.5" />
                  {expiringCount} expiring soon
                </span>
              )}
              {expiredCount > 0 && (
                <span className="flex items-center gap-1 text-red-600">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {expiredCount} expired
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-primary font-medium">Manage Training</span>
          <ChevronRight className="h-4 w-4 text-primary" />
        </div>
      </div>
    </div>
  );
}
