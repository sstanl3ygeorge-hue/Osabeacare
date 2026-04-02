import { useState } from 'react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { CheckCircle, XCircle, Clock, AlertTriangle, Loader2, Shield } from 'lucide-react';

/**
 * RecruitmentApprovalCard - Clean approval checklist
 * 
 * Shows:
 * - Status: Awaiting approval / Approved
 * - Checklist of required items
 * - Approve button (disabled until all requirements met)
 */
export default function RecruitmentApprovalCard({
  employee,
  complianceFile,
  complianceRequirements,
  onApprove,
  isApproving = false
}) {
  if (!employee) return null;

  // Already approved
  if (employee.recruitment_approved) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-4" data-testid="approval-card-approved">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-green-800">Recruitment Approved</h3>
            <p className="text-sm text-green-600">
              Approved on {employee.recruitment_approved_at ? new Date(employee.recruitment_approved_at).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Extract requirements from compliance file
  const sections = complianceFile?.sections || {};
  
  // Define approval requirements with their statuses
  const approvalRequirements = [
    {
      key: 'right_to_work',
      label: 'Right to Work verified',
      check: () => {
        const rtw = sections.right_to_work;
        if (!rtw) return false;
        // Check if there's a verified check
        const checkRow = rtw.rows?.find(r => r.row_type === 'check');
        return checkRow?.is_verified === true;
      }
    },
    {
      key: 'identity',
      label: 'Identity verified',
      check: () => {
        const identity = sections.identity;
        if (!identity) return false;
        const checkRow = identity.rows?.find(r => r.row_type === 'check');
        return checkRow?.is_verified === true;
      }
    },
    {
      key: 'dbs',
      label: 'DBS verified',
      check: () => {
        const dbs = sections.dbs;
        if (!dbs) return false;
        const checkRow = dbs.rows?.find(r => r.row_type === 'check');
        return checkRow?.is_verified === true;
      }
    },
    {
      key: 'references',
      label: '2 references verified',
      check: () => {
        const refs = sections.references;
        if (!refs) return false;
        const verifiedRefs = refs.rows?.filter(r => r.is_verified)?.length || 0;
        return verifiedRefs >= 2;
      }
    },
    {
      key: 'proof_of_address',
      label: 'Proof of address verified',
      check: () => {
        const poa = sections.proof_of_address;
        if (!poa) return false;
        const checkRow = poa.rows?.find(r => r.row_type === 'check');
        return checkRow?.is_verified === true;
      }
    }
  ];

  // Evaluate each requirement
  const evaluatedRequirements = approvalRequirements.map(req => ({
    ...req,
    completed: req.check()
  }));

  const completedCount = evaluatedRequirements.filter(r => r.completed).length;
  const allComplete = completedCount === evaluatedRequirements.length;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5" data-testid="approval-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
            <Shield className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Recruitment Approval</h3>
            <p className="text-sm text-gray-500">
              Status: <span className="font-medium text-amber-600">Awaiting approval</span>
            </p>
          </div>
        </div>
        <Badge className={`${allComplete ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
          {completedCount}/{evaluatedRequirements.length} complete
        </Badge>
      </div>

      {/* Requirements Checklist */}
      <div className="space-y-2 mb-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Required before approval:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {evaluatedRequirements.map((req) => (
            <div 
              key={req.key}
              className={`flex items-center gap-2 p-2 rounded-lg ${
                req.completed ? 'bg-green-50' : 'bg-gray-50'
              }`}
            >
              {req.completed ? (
                <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-gray-400 flex-shrink-0" />
              )}
              <span className={`text-sm ${req.completed ? 'text-green-800' : 'text-gray-600'}`}>
                {req.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Approve Button */}
      <Button
        onClick={onApprove}
        disabled={!allComplete || isApproving}
        className={`w-full ${allComplete ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-300 cursor-not-allowed'}`}
        data-testid="approve-recruitment-btn"
      >
        {isApproving ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Approving...
          </>
        ) : (
          <>
            <CheckCircle className="h-4 w-4 mr-2" />
            Approve Recruitment
          </>
        )}
      </Button>

      {!allComplete && (
        <p className="text-xs text-gray-500 text-center mt-2">
          Complete all requirements above to enable approval
        </p>
      )}
    </div>
  );
}
