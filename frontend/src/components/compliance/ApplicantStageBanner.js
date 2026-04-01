/**
 * ApplicantStageBanner.js
 * 
 * Prominent warning banner shown on compliance page when viewing an applicant.
 * Indicates that recruitment approval is required before activation.
 * 
 * Props:
 * - employeeName: string - Name of the person
 * - status: string - Current recruitment status (screening, interview, etc.)
 * - onApprove: function - Called when admin clicks "Approve for Recruitment" (optional)
 * - canApprove: boolean - Whether the current user can approve (default: false)
 * - className: additional CSS classes
 */

import { AlertTriangle, UserCheck, ClipboardList, ArrowRight } from 'lucide-react';
import { Button } from '../ui/button';

const STATUS_LABELS = {
  new: 'Application Received',
  screening: 'Under Screening',
  interview: 'Interview Stage',
  compliance_review: 'Compliance Review',
};

export default function ApplicantStageBanner({ 
  employeeName,
  status = 'new',
  onApprove,
  canApprove = false,
  className = '' 
}) {
  const statusLabel = STATUS_LABELS[status] || status?.replace('_', ' ') || 'In Progress';
  
  return (
    <div 
      className={`
        mb-6 p-4 rounded-xl border-2 border-blue-300 bg-blue-50
        ${className}
      `}
      data-testid="applicant-stage-banner"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="h-5 w-5 text-blue-600" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-blue-900">
              Applicant Stage
            </h4>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-200 text-blue-800">
              {statusLabel}
            </span>
          </div>
          <p className="text-sm mt-1 text-blue-800">
            {employeeName ? `${employeeName} is` : 'This person is'} still in the recruitment pipeline. 
            Recruitment approval is required before they can be activated as staff.
          </p>
          
          {/* What's Required Section */}
          <div className="mt-3 p-3 bg-white/60 rounded-lg border border-blue-200">
            <p className="text-xs font-medium text-blue-900 mb-2 flex items-center gap-1.5">
              <ClipboardList className="h-3.5 w-3.5" />
              Before Recruitment Approval:
            </p>
            <ul className="text-xs text-blue-700 space-y-1 ml-5 list-disc">
              <li>Right to Work verified</li>
              <li>Identity verified</li>
              <li>DBS check verified</li>
              <li>2 references verified</li>
              <li>Proof of address (2 documents) verified</li>
            </ul>
          </div>
          
          {/* Approve Button (if allowed) */}
          {canApprove && onApprove && (
            <div className="mt-3 flex items-center gap-2">
              <Button
                size="sm"
                onClick={onApprove}
                className="bg-blue-600 hover:bg-blue-700 text-white"
                data-testid="approve-recruitment-btn"
              >
                <UserCheck className="h-4 w-4 mr-1.5" />
                Approve for Recruitment
                <ArrowRight className="h-4 w-4 ml-1.5" />
              </Button>
              <span className="text-xs text-blue-600">
                (Only if all requirements are verified)
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
