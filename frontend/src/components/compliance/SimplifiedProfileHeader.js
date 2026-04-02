import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { AlertTriangle, CheckCircle, Clock, User, Briefcase } from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

/**
 * SimplifiedProfileHeader - Clean header for applicant/employee profile
 * 
 * Shows only:
 * - Name, reference, role, stage
 * - Progress percentage
 * - One concise blocker summary
 */
export default function SimplifiedProfileHeader({
  employee,
  complianceRequirements,
  isRecruitmentView = false
}) {
  if (!employee) return null;

  // Extract blocking items
  const blockingReasons = complianceRequirements?.statuses?.safety_blocking_reasons || [];
  const workReadiness = complianceRequirements?.work_readiness_3tier || {};
  const progress = complianceRequirements?.statuses?.overall_compliance?.percentage ?? employee.completion_percentage ?? 0;

  // Get stage display
  const isApplicant = employee.person_stage === 'applicant';
  const stageBadge = isApplicant 
    ? { label: 'Applicant', color: 'bg-blue-100 text-blue-800 border-blue-200' }
    : { label: 'Staff', color: 'bg-green-100 text-green-800 border-green-200' };

  // Get recruitment stage
  const recruitmentStage = employee.recruitment_stage || employee.status || 'unknown';
  const recruitmentLabel = recruitmentStage.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5" data-testid="simplified-profile-header">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Left: Basic Info */}
        <div className="flex items-center gap-4">
          {/* Avatar */}
          <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
            <span className="text-primary font-bold text-lg">
              {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
            </span>
          </div>
          
          {/* Name and Details */}
          <div>
            <h1 className="text-xl font-bold text-gray-900" data-testid="employee-name">
              {employee.first_name} {employee.last_name}
            </h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-600 flex-wrap">
              <span className="font-medium">{employee.employee_code || employee.applicant_reference || '-'}</span>
              <span className="text-gray-300">•</span>
              <span className="flex items-center gap-1">
                <Briefcase className="h-3.5 w-3.5" />
                {employee.role || 'No role assigned'}
              </span>
            </div>
            
            {/* Badges Row */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <Badge className={`text-xs ${stageBadge.color}`}>
                {stageBadge.label}
              </Badge>
              <Badge variant="outline" className="text-xs bg-gray-50 text-gray-700">
                {recruitmentLabel}
              </Badge>
              {employee.recruitment_approved && (
                <Badge className="text-xs bg-green-100 text-green-800">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Approved
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Right: Progress */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Progress</p>
            <p className="text-2xl font-bold text-gray-900">{Math.round(progress)}%</p>
          </div>
          <Progress value={progress} className="w-24 h-2" />
        </div>
      </div>

      {/* Blocker Summary - One concise line */}
      {blockingReasons.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg" data-testid="blocker-summary">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">
                {blockingReasons.length} blocking item{blockingReasons.length !== 1 ? 's' : ''}
              </p>
              <p className="text-xs text-red-600 mt-0.5">
                {blockingReasons.slice(0, 3).join(' • ')}
                {blockingReasons.length > 3 && ` +${blockingReasons.length - 3} more`}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
