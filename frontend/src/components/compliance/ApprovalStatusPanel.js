import React from 'react';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  ChevronRight,
  FileText,
  Send,
  ClipboardCheck,
  XCircle
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

/**
 * ApprovalStatusPanel - Single authoritative status block for compliance approval
 * 
 * Displays:
 * 1. Overall status (ready/not ready)
 * 2. Blocker count
 * 3. Pending review count
 * 4. Top 3 blockers
 * 5. Action buttons
 * 
 * Replaces: Applicant Stage, Not Ready to Work, Blocking Requirements panels
 */
export default function ApprovalStatusPanel({
  // Status data
  isReady = false,
  blockers = [],
  pendingReviewCount = 0,
  missingCount = 0,
  
  // Flags
  isApplicant = false,
  canApprove = false,
  isApproving = false,
  
  // Actions
  onReviewPending,
  onRequestMissing,
  onRecordVerification,
  onApprove,
  onBlockerClick,
  
  // Employee info
  employeeName = ''
}) {
  const blockerCount = blockers.length;
  const hasBlockers = blockerCount > 0;
  const hasPending = pendingReviewCount > 0;
  const hasMissing = missingCount > 0;
  
  // Determine overall status
  const status = isReady ? 'ready' : hasBlockers ? 'blocked' : hasPending ? 'pending' : 'ready';
  
  return (
    <div className="mb-6" data-testid="approval-status-panel">
      {/* Main Status Block */}
      <div className={`p-4 rounded-xl border-2 ${
        status === 'ready' ? 'border-green-300 bg-gradient-to-r from-green-50 to-emerald-50' :
        status === 'blocked' ? 'border-red-300 bg-gradient-to-r from-red-50 to-rose-50' :
        'border-amber-300 bg-gradient-to-r from-amber-50 to-yellow-50'
      }`}>
        {/* Status Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
              status === 'ready' ? 'bg-green-100' :
              status === 'blocked' ? 'bg-red-100' : 'bg-amber-100'
            }`}>
              {status === 'ready' ? (
                <CheckCircle className="h-6 w-6 text-green-600" />
              ) : status === 'blocked' ? (
                <XCircle className="h-6 w-6 text-red-600" />
              ) : (
                <Clock className="h-6 w-6 text-amber-600" />
              )}
            </div>
            <div>
              <h3 className={`text-lg font-semibold ${
                status === 'ready' ? 'text-green-900' :
                status === 'blocked' ? 'text-red-900' : 'text-amber-900'
              }`}>
                {status === 'ready' ? 'Ready for Recruitment Approval' :
                 status === 'blocked' ? 'Not ready for recruitment approval' : 'Awaiting admin review'}
              </h3>
              <p className={`text-sm ${
                status === 'ready' ? 'text-green-700' :
                status === 'blocked' ? 'text-red-700' : 'text-amber-700'
              }`}>
                {status === 'ready' 
                  ? `${employeeName || 'This person'} can be approved for work`
                  : status === 'blocked'
                  ? `${blockerCount} blocker${blockerCount !== 1 ? 's' : ''} must be resolved`
                  : `${pendingReviewCount} item${pendingReviewCount !== 1 ? 's' : ''} awaiting review`}
              </p>
            </div>
          </div>
          
          {/* Status Badges */}
          <div className="flex items-center gap-2">
            {hasBlockers && (
              <Badge className="bg-red-100 text-red-700 border-red-200 text-xs font-semibold">
                {blockerCount} Blocker{blockerCount !== 1 ? 's' : ''}
              </Badge>
            )}
            {hasPending && (
              <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-xs font-semibold">
                {pendingReviewCount} Pending
              </Badge>
            )}
            {hasMissing && (
              <Badge className="bg-gray-100 text-gray-600 border-gray-200 text-xs font-semibold">
                {missingCount} Missing
              </Badge>
            )}
          </div>
        </div>
        
        {/* Top 3 Blockers - Clickable */}
        {hasBlockers && (
          <div className="mb-4 space-y-2">
            <p className="text-xs font-semibold text-red-800 uppercase tracking-wide">
              Top Blockers
            </p>
            <div className="space-y-1.5">
              {blockers.slice(0, 3).map((blocker, idx) => {
                // Parse blocker info if it's an object
                const blockerText = typeof blocker === 'string' ? blocker : blocker.message || blocker.code || 'Unknown blocker';
                const blockerType = typeof blocker === 'object' ? blocker.type : 'hard_block';
                
                return (
                  <button
                    key={idx}
                    onClick={() => onBlockerClick && onBlockerClick(blocker)}
                    className={`w-full flex items-center gap-2 p-2 rounded-lg text-left transition-all ${
                      blockerType === 'hard_block' 
                        ? 'bg-red-100 hover:bg-red-200 border border-red-200' 
                        : 'bg-amber-100 hover:bg-amber-200 border border-amber-200'
                    }`}
                    data-testid={`blocker-${idx}`}
                  >
                    <AlertTriangle className={`h-4 w-4 flex-shrink-0 ${
                      blockerType === 'hard_block' ? 'text-red-600' : 'text-amber-600'
                    }`} />
                    <span className={`text-sm font-medium flex-1 truncate ${
                      blockerType === 'hard_block' ? 'text-red-800' : 'text-amber-800'
                    }`}>
                      {blockerText}
                    </span>
                    <ChevronRight className={`h-4 w-4 ${
                      blockerType === 'hard_block' ? 'text-red-400' : 'text-amber-400'
                    }`} />
                  </button>
                );
              })}
              {blockers.length > 3 && (
                <p className="text-xs text-red-600 pl-2">
                  + {blockers.length - 3} more blocker{blockers.length - 3 !== 1 ? 's' : ''}
                </p>
              )}
            </div>
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {hasPending && onReviewPending && (
            <Button
              size="sm"
              variant="outline"
              onClick={onReviewPending}
              className="bg-white border-amber-300 text-amber-700 hover:bg-amber-50 hover:text-amber-800"
              data-testid="review-pending-btn"
            >
              <Clock className="h-4 w-4 mr-1.5" />
              Review Pending ({pendingReviewCount})
            </Button>
          )}
          
          {hasMissing && onRequestMissing && (
            <Button
              size="sm"
              variant="outline"
              onClick={onRequestMissing}
              className="bg-white border-gray-300 text-gray-700 hover:bg-gray-50"
              data-testid="request-missing-btn"
            >
              <Send className="h-4 w-4 mr-1.5" />
              Request Missing ({missingCount})
            </Button>
          )}
          
          {onRecordVerification && (
            <Button
              size="sm"
              variant="outline"
              onClick={onRecordVerification}
              className="bg-white border-indigo-300 text-indigo-700 hover:bg-indigo-50"
              data-testid="record-verification-btn"
            >
              <ClipboardCheck className="h-4 w-4 mr-1.5" />
              Record Verification
            </Button>
          )}
          
          {/* Approve Button - Only for applicants who can be approved */}
          {isApplicant && canApprove && onApprove && (
            <Button
              size="sm"
              onClick={onApprove}
              disabled={!isReady || isApproving}
              className={`ml-auto ${
                isReady 
                  ? 'bg-green-600 hover:bg-green-700 text-white' 
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              data-testid="approve-btn"
            >
              {isApproving ? (
                <>Processing...</>
              ) : (
                <>
                  <Shield className="h-4 w-4 mr-1.5" />
                  {isReady ? 'Approve to Onboarding' : 'Cannot Approve'}
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
