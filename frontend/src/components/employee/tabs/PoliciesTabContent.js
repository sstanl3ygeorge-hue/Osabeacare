import { useState } from 'react';
import axios from 'axios';
import { Card, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';
import { toast } from 'sonner';
import { 
  CheckCircle, Clock, Eye, Shield, XCircle, 
  RotateCcw, FileCheck, Download 
} from 'lucide-react';
import { formatBackendDate, formatBackendDateTime } from '../../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * PoliciesTabContent - Displays employee policy assignments
 * Handles viewing, acknowledging, and managing policy statuses
 */
export default function PoliciesTabContent({
  policies = [],
  token,
  isAuditor,
  isAdmin,
  onRefresh
}) {
  const [loading, setLoading] = useState({});

  // Handle policy view
  const handleViewPolicy = async (policy) => {
    setLoading(prev => ({ ...prev, [`view-${policy.id}`]: true }));
    try {
      // Mark as viewed if not already
      if (policy.status === 'assigned') {
        await axios.put(`${API}/policy-assignments/${policy.id}/view`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
      // Open policy file
      const response = await axios.get(`${API}/policies/${policy.policy_id}/file`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(response.data);
      window.open(url, '_blank');
      onRefresh?.();
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error('Policy document not found');
      } else {
        toast.error('Failed to open policy');
      }
    } finally {
      setLoading(prev => ({ ...prev, [`view-${policy.id}`]: false }));
    }
  };

  // Handle policy acknowledgement
  const handleAcknowledge = async (policy) => {
    const signerName = window.prompt('Type your full name to acknowledge this policy:');
    if (signerName === null) return;
    if (!signerName.trim()) {
      toast.error('Full name is required to acknowledge policy');
      return;
    }

    setLoading(prev => ({ ...prev, [`ack-${policy.id}`]: true }));
    try {
      await axios.put(`${API}/policy-assignments/${policy.id}/acknowledge`, {
        signer_name: signerName.trim()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Policy acknowledged successfully');
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to acknowledge policy');
    } finally {
      setLoading(prev => ({ ...prev, [`ack-${policy.id}`]: false }));
    }
  };

  // Handle admin review
  const handleAdminReview = async (policy) => {
    setLoading(prev => ({ ...prev, [`review-${policy.id}`]: true }));
    try {
      await axios.put(`${API}/policy-assignments/${policy.id}/admin-review`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Policy reviewed and approved');
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to review policy');
    } finally {
      setLoading(prev => ({ ...prev, [`review-${policy.id}`]: false }));
    }
  };

  // Handle unassign
  const handleUnassign = async (policy) => {
    if (!window.confirm('Remove this policy from the employee\'s active policy list?')) return;
    
    setLoading(prev => ({ ...prev, [`unassign-${policy.id}`]: true }));
    try {
      await axios.put(`${API}/policy-assignments/${policy.id}/unassign`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Policy unassigned');
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to unassign policy');
    } finally {
      setLoading(prev => ({ ...prev, [`unassign-${policy.id}`]: false }));
    }
  };

  // Handle withdraw
  const handleWithdraw = async (policy) => {
    if (!window.confirm('Withdraw this policy? The acknowledgement history will be preserved for audit purposes.')) return;
    
    setLoading(prev => ({ ...prev, [`withdraw-${policy.id}`]: true }));
    try {
      await axios.put(`${API}/policy-assignments/${policy.id}/withdraw`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Policy assignment withdrawn');
      onRefresh?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to withdraw policy');
    } finally {
      setLoading(prev => ({ ...prev, [`withdraw-${policy.id}`]: false }));
    }
  };

  const handleDownloadAcknowledgement = async (policy) => {
    setLoading(prev => ({ ...prev, [`pdf-${policy.id}`]: true }));
    try {
      const response = await axios.get(
        `${API}/policy-assignments/${policy.id}/acknowledgement-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${(policy.policy_title || 'policy').replace(/\s+/g, '_')}_acknowledgement.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export acknowledgement PDF');
    } finally {
      setLoading(prev => ({ ...prev, [`pdf-${policy.id}`]: false }));
    }
  };

  // Get policy card background class
  const getPolicyCardClass = (policy) => {
    if (policy.admin_reviewed) return 'bg-green-50 border-green-200';
    if (policy.status === 'acknowledged' || policy.status === 'signed') return 'bg-blue-50 border-blue-200';
    if (policy.status === 'viewed') return 'bg-amber-50 border-amber-200';
    return 'bg-[#F8FAFA] border-[#E4E8EB]';
  };

  // Get status badge class
  const getStatusBadgeClass = (policy) => {
    if (policy.admin_reviewed) return 'status-success';
    if (policy.status === 'acknowledged' || policy.status === 'signed') return 'bg-green-100 text-green-700 border-green-200';
    return 'bg-gray-100 text-gray-600 border-gray-200';
  };

  // Get status label
  const getStatusLabel = (policy) => {
    if (policy.admin_reviewed) return 'Reviewed & Approved';
    if (policy.status === 'acknowledged' || policy.status === 'signed') return 'Acknowledged';
    return 'Not Read';
  };

  return (
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardContent className="p-6">
        {/* Header with stats */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#E4E8EB]">
          <div>
            <h3 className="font-heading text-lg font-semibold text-text-primary">Assigned Policies</h3>
            <p className="text-sm text-text-muted">
              {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} of {policies.length} acknowledged
            </p>
            <p className="text-xs text-text-muted mt-1">
              Employees must read and acknowledge assigned policies.
            </p>
          </div>
          {policies.length > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                <Clock className="w-3 h-3" /> {policies.filter(p => p.status === 'assigned' || p.status === 'viewed').length} Not Read
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700">
                <CheckCircle className="w-3 h-3" /> {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} Acknowledged
              </span>
            </div>
          )}
        </div>

        {policies.length === 0 ? (
          <div className="text-center py-12 text-text-muted">
            <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No policies assigned yet</p>
            <p className="text-sm mt-1">Policies can be assigned from the Compliance Centre</p>
          </div>
        ) : (
          <div className="space-y-4">
            {policies.map((policy) => (
              <div 
                key={policy.id} 
                className={`p-4 rounded-xl border ${getPolicyCardClass(policy)}`}
                data-testid={`policy-card-${policy.id}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-text-primary">{policy.policy_title}</p>
                      <span className="text-xs px-2 py-0.5 bg-gray-200 rounded text-gray-600">
                        v{policy.policy_version || '1.0'}
                      </span>
                    </div>
                    <p className="text-sm text-text-muted mt-1">
                      Assigned: {formatBackendDate(policy.assigned_at)} 
                      {policy.assigned_by_name && ` by ${policy.assigned_by_name}`}
                    </p>
                    
                    {/* Signature Information Display */}
                    {(policy.status === 'acknowledged' || policy.status === 'signed') && (
                      <div className="mt-3 p-3 bg-white/80 rounded-lg border border-green-200">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Employee Acknowledgement</p>
                        <p className="text-sm font-medium text-green-800">
                          {policy.acknowledged_by_employee_name || policy.employee_name || 'Employee'}
                        </p>
                        <p className="text-xs text-green-600">
                          {policy.acknowledged_at ? formatBackendDateTime(policy.acknowledged_at) : 
                           policy.signed_at ? formatBackendDateTime(policy.signed_at) : ''}
                        </p>
                      </div>
                    )}
                    
                    {policy.admin_reviewed && (
                      <div className="mt-2 p-3 bg-white/80 rounded-lg border border-green-200">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Admin Review</p>
                        <p className="text-sm font-medium text-green-800">
                          {policy.admin_reviewed_by_name || 'Admin'}
                        </p>
                        <p className="text-xs text-green-600">
                          {policy.admin_reviewed_at ? formatBackendDateTime(policy.admin_reviewed_at) : ''}
                        </p>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex flex-col items-end gap-2">
                    {/* Status Badge */}
                    <span className={`status-chip ${getStatusBadgeClass(policy)}`}>
                      {getStatusLabel(policy)}
                    </span>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                      {/* View Policy Button */}
                      <Button
                        size="sm"
                        variant="outline"
                        className="rounded-lg text-xs"
                        onClick={() => handleViewPolicy(policy)}
                        disabled={loading[`view-${policy.id}`]}
                        data-testid={`view-policy-${policy.id}`}
                      >
                        <Eye className="w-3 h-3 mr-1" />
                        View Policy
                      </Button>
                      
                      {/* Acknowledge Button - only if not yet acknowledged */}
                      {policy.status !== 'acknowledged' && policy.status !== 'signed' && !isAuditor && (
                        <Button
                          size="sm"
                          className="rounded-lg text-xs bg-primary hover:bg-primary-hover text-white"
                          onClick={() => handleAcknowledge(policy)}
                          disabled={loading[`ack-${policy.id}`]}
                          data-testid={`acknowledge-policy-${policy.id}`}
                        >
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Mark as Read & Understood
                        </Button>
                      )}
                      
                      {/* Admin Review Button - only if acknowledged but not reviewed */}
                      {(policy.status === 'acknowledged' || policy.status === 'signed') && !policy.admin_reviewed && isAdmin && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-lg text-xs border-green-300 text-green-700 hover:bg-green-50"
                          onClick={() => handleAdminReview(policy)}
                          disabled={loading[`review-${policy.id}`]}
                          data-testid={`admin-review-policy-${policy.id}`}
                        >
                          <Shield className="w-3 h-3 mr-1" />
                          Reviewed and Approved
                        </Button>
                      )}

                      {(policy.status === 'acknowledged' || policy.status === 'signed' || policy.status === 'withdrawn') && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-lg text-xs"
                          onClick={() => handleDownloadAcknowledgement(policy)}
                          disabled={loading[`pdf-${policy.id}`]}
                          data-testid={`download-policy-ack-${policy.id}`}
                        >
                          <Download className="w-3 h-3 mr-1" />
                          Download Acknowledgement
                        </Button>
                      )}
                      
                      {/* Unassign Button - only for unacknowledged policies (admin/manager only) */}
                      {policy.status !== 'acknowledged' && policy.status !== 'signed' && 
                       policy.status !== 'unassigned' && policy.status !== 'withdrawn' && 
                       isAdmin && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-lg text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
                          onClick={() => handleUnassign(policy)}
                          disabled={loading[`unassign-${policy.id}`]}
                          data-testid={`unassign-policy-${policy.id}`}
                        >
                          <XCircle className="w-3 h-3 mr-1" />
                          Unassign
                        </Button>
                      )}
                      
                      {/* Withdraw Button - only for acknowledged policies (admin only) */}
                      {(policy.status === 'acknowledged' || policy.status === 'signed') && 
                       policy.status !== 'withdrawn' && isAdmin && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-lg text-xs border-red-300 text-red-700 hover:bg-red-50"
                          onClick={() => handleWithdraw(policy)}
                          disabled={loading[`withdraw-${policy.id}`]}
                          data-testid={`withdraw-policy-${policy.id}`}
                        >
                          <RotateCcw className="w-3 h-3 mr-1" />
                          Withdraw
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
