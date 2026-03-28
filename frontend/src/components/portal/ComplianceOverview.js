import { useMemo } from 'react';
import { Card, CardContent } from '../ui/card';
import { 
  Shield, ShieldCheck, FileCheck, CheckCircle,
  BookOpen, AlertTriangle, Clock, Users, CalendarClock
} from 'lucide-react';

/**
 * ComplianceOverview - Simplified Separated Status Model
 * 
 * Displays:
 * 1. Work Status - Can the employee safely start work?
 * 2. Recruitment File - Is the pre-employment record complete?
 * 3. Policies - Have assigned policies been acknowledged?
 * 4. Document Status - Are documents valid or expiring?
 * 5. Progress - Percentage (supporting info)
 */
export default function ComplianceOverview({ 
  employee, 
  policies,
  complianceRequirements,
  className = "" 
}) {
  // Extract statuses from backend
  const statuses = useMemo(() => {
    if (!complianceRequirements?.statuses) {
      return {
        start_status: { status: 'loading', label: 'Loading...', color: 'neutral' },
        recruitment_file: { status: 'loading', label: 'Loading...', color: 'neutral' },
        policies: { status: 'loading', label: 'Loading...', color: 'neutral' },
        document_status: { status: 'loading', label: 'Loading...', color: 'neutral' },
        overall_compliance: { percentage: 0 }
      };
    }
    return complianceRequirements.statuses;
  }, [complianceRequirements?.statuses]);

  // Extract missing blockers (start status items)
  const missingBlockers = useMemo(() => {
    return statuses.start_status?.missing || [];
  }, [statuses.start_status?.missing]);

  // Get color classes for status
  const getStatusColorClasses = (color) => {
    switch(color) {
      case 'success':
        return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: 'text-green-600' };
      case 'warning':
        return { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: 'text-amber-600' };
      case 'error':
        return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: 'text-red-600' };
      default:
        return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', icon: 'text-gray-500' };
    }
  };

  if (!complianceRequirements) {
    return (
      <Card className={`rounded-2xl border-[#E4E8EB] shadow-sm ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32 text-text-muted">
            Loading compliance data...
          </div>
        </CardContent>
      </Card>
    );
  }

  const startColors = getStatusColorClasses(statuses.start_status?.color);
  const recruitmentColors = getStatusColorClasses(statuses.recruitment_file?.color);
  const policiesColors = getStatusColorClasses(statuses.policies?.color);
  const docStatusColors = getStatusColorClasses(statuses.document_status?.color);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Primary Status Cards - Separated Model */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Work Status */}
        <Card className={`rounded-2xl border ${startColors.border} shadow-sm ${startColors.bg}`}>
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${startColors.bg} border ${startColors.border}`}>
                {statuses.start_status?.status === 'ready_to_work' ? (
                  <ShieldCheck className={`h-6 w-6 ${startColors.icon}`} />
                ) : statuses.start_status?.status === 'supervised_start_only' ? (
                  <Shield className={`h-6 w-6 ${startColors.icon}`} />
                ) : (
                  <AlertTriangle className={`h-6 w-6 ${startColors.icon}`} />
                )}
              </div>
              <div className="flex-1">
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Work Status</p>
                <p className={`text-lg font-semibold ${startColors.text} mt-0.5`}>
                  {statuses.start_status?.status === 'ready_to_work' ? 'Ready to Work' :
                   statuses.start_status?.status === 'supervised_start_only' ? 'Supervised Start' :
                   'Not Ready'}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Shows whether this employee can safely start work.
                </p>
                {statuses.start_status?.status !== 'ready_to_work' && (
                  <p className="text-xs mt-2">
                    <span className={startColors.text}>{statuses.start_status?.verified || 0}/{statuses.start_status?.total || 0}</span>
                    <span className="text-text-muted"> required items verified</span>
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recruitment File */}
        <Card className={`rounded-2xl border ${recruitmentColors.border} shadow-sm ${recruitmentColors.bg}`}>
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${recruitmentColors.bg} border ${recruitmentColors.border}`}>
                {statuses.recruitment_file?.status === 'complete' ? (
                  <FileCheck className={`h-6 w-6 ${recruitmentColors.icon}`} />
                ) : (
                  <Clock className={`h-6 w-6 ${recruitmentColors.icon}`} />
                )}
              </div>
              <div className="flex-1">
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Recruitment File</p>
                <p className={`text-lg font-semibold ${recruitmentColors.text} mt-0.5`}>
                  {statuses.recruitment_file?.status === 'complete' ? 'Complete' :
                   (statuses.recruitment_file?.complete || 0) / (statuses.recruitment_file?.total || 1) >= 0.8 ? 'Nearly Complete' :
                   'Incomplete'}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Shows whether the employee record is complete.
                </p>
                <p className="text-xs mt-2">
                  <span className={recruitmentColors.text}>{statuses.recruitment_file?.complete || 0}/{statuses.recruitment_file?.total || 0}</span>
                  <span className="text-text-muted"> items complete</span>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Policies */}
        <Card className={`rounded-2xl border ${policiesColors.border} shadow-sm ${policiesColors.bg}`}>
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${policiesColors.bg} border ${policiesColors.border}`}>
                {statuses.policies?.status === 'all_acknowledged' ? (
                  <CheckCircle className={`h-6 w-6 ${policiesColors.icon}`} />
                ) : statuses.policies?.status === 'policies_assigned' ? (
                  <BookOpen className={`h-6 w-6 ${policiesColors.icon}`} />
                ) : (
                  <BookOpen className={`h-6 w-6 ${policiesColors.icon}`} />
                )}
              </div>
              <div className="flex-1">
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Policies</p>
                <p className={`text-lg font-semibold ${policiesColors.text} mt-0.5`}>
                  {statuses.policies?.status === 'all_acknowledged' ? 'All Policies Acknowledged' :
                   statuses.policies?.status === 'no_policies' ? 'No Policies Assigned' :
                   `${statuses.policies?.acknowledged || 0} of ${statuses.policies?.assigned || 0} Acknowledged`}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Shows whether assigned policies have been read and acknowledged.
                </p>
                {statuses.policies?.assigned > 0 && (
                  <p className="text-xs mt-2">
                    <span className={policiesColors.text}>{statuses.policies?.acknowledged || 0}/{statuses.policies?.assigned || 0}</span>
                    <span className="text-text-muted"> acknowledged</span>
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Document Status Card */}
      {statuses.document_status && statuses.document_status.status !== 'no_expiry_tracked' && (
        <Card className={`rounded-2xl border ${docStatusColors.border} shadow-sm ${docStatusColors.bg}`}>
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${docStatusColors.bg} border ${docStatusColors.border}`}>
                <CalendarClock className={`h-6 w-6 ${docStatusColors.icon}`} />
              </div>
              <div className="flex-1">
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Document Status</p>
                <p className={`text-lg font-semibold ${docStatusColors.text} mt-0.5`}>
                  {statuses.document_status?.status === 'all_valid' ? 'All Valid' :
                   statuses.document_status?.status === 'expired' ? `${statuses.document_status?.expired_count} Expired` :
                   statuses.document_status?.status === 'expiring_soon' ? `${statuses.document_status?.expiring_soon_count} Expiring Soon` :
                   'No Expiry Dates'}
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Shows expiry status of documents with tracked dates.
                </p>
                {(statuses.document_status?.expired_count > 0 || statuses.document_status?.expiring_soon_count > 0) && (
                  <div className="flex gap-3 mt-2 text-xs">
                    {statuses.document_status?.expired_count > 0 && (
                      <span className="text-red-600">{statuses.document_status.expired_count} expired</span>
                    )}
                    {statuses.document_status?.expiring_soon_count > 0 && (
                      <span className="text-amber-600">{statuses.document_status.expiring_soon_count} expiring soon</span>
                    )}
                    {statuses.document_status?.valid_count > 0 && (
                      <span className="text-green-600">{statuses.document_status.valid_count} valid</span>
                    )}
                  </div>
                )}
                {statuses.document_status?.has_critical_expired && (
                  <p className="text-xs text-red-600 mt-2 font-medium">
                    Critical document expired - employee cannot work
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Progress - Supporting Info */}
      <Card className="rounded-2xl border-[#E4E8EB] shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Users className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Progress</p>
                <p className="text-lg font-semibold text-text-primary mt-0.5">
                  {statuses.overall_compliance?.percentage || 0}% Complete
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Shows how much of the employee record is complete.
                </p>
              </div>
            </div>
            <div className="w-32 h-3 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all ${
                  (statuses.overall_compliance?.percentage || 0) >= 80 ? 'bg-green-500' :
                  (statuses.overall_compliance?.percentage || 0) >= 50 ? 'bg-amber-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${statuses.overall_compliance?.percentage || 0}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Missing Blockers - Only show if not ready to work */}
      {missingBlockers.length > 0 && statuses.start_status?.status !== 'ready_to_work' && (
        <Card className="rounded-2xl border-red-200 shadow-sm bg-red-50">
          <CardContent className="p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-900">Missing Blockers</p>
                <p className="text-sm text-red-800 mt-1">
                  The following items are required before this employee can start work:
                </p>
                <ul className="mt-2 space-y-1">
                  {missingBlockers.map((item, idx) => (
                    <li key={idx} className="text-sm text-red-800 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                      {item.name}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
