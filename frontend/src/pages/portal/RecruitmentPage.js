import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Search, Users, Filter, Loader2, ChevronRight, CheckCircle, Clock, 
  AlertTriangle, User, XCircle, Shield, FileText, Briefcase,
  MoreHorizontal, Eye, UserCheck
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import EmployeeAvatar from '../../components/portal/EmployeeAvatar';
import { cn } from '../../lib/utils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Recruitment stage labels
const STAGE_LABELS = {
  new: 'New',
  screening: 'Screening',
  interview: 'Interview',
  compliance_review: 'Compliance Review'
};

// Stage colors
const STAGE_COLORS = {
  new: 'bg-blue-100 text-blue-800 border-blue-200',
  screening: 'bg-purple-100 text-purple-800 border-purple-200',
  interview: 'bg-amber-100 text-amber-800 border-amber-200',
  compliance_review: 'bg-orange-100 text-orange-800 border-orange-200'
};

export default function RecruitmentPage() {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  
  const [pipeline, setPipeline] = useState(null);
  const [applicants, setApplicants] = useState([]);
  const [approvalData, setApprovalData] = useState({}); // Cache approval checks
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  // Approval dialog state
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [blockersDialogOpen, setBlockersDialogOpen] = useState(false);
  const [selectedApplicant, setSelectedApplicant] = useState(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [loadingApprovalCheck, setLoadingApprovalCheck] = useState(null);

  const canApprove = user?.role === 'super_admin' || user?.role === 'admin';

  // Fetch pipeline summary
  const fetchPipeline = async () => {
    try {
      const response = await axios.get(`${API}/recruitment/pipeline`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPipeline(response.data);
    } catch (error) {
      console.error('Failed to fetch pipeline:', error);
    }
  };

  // Fetch applicants list
  const fetchApplicants = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter) params.append('status', statusFilter);
      
      const response = await axios.get(`${API}/recruitment/applicants?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setApplicants(response.data);
      
      // Fetch approval status for each applicant
      response.data.forEach(applicant => {
        if (!applicant.recruitment_approved) {
          fetchApprovalStatus(applicant.id);
        }
      });
    } catch (error) {
      console.error('Failed to fetch applicants:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch approval status for an applicant
  const fetchApprovalStatus = async (applicantId) => {
    try {
      const response = await axios.get(
        `${API}/employees/${applicantId}/recruitment-approval-check`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setApprovalData(prev => ({
        ...prev,
        [applicantId]: response.data
      }));
    } catch (error) {
      console.error(`Failed to fetch approval status for ${applicantId}:`, error);
    }
  };

  useEffect(() => {
    fetchPipeline();
    fetchApplicants();
  }, [token, search, statusFilter]);

  // Fetch approval status for all visible applicants
  useEffect(() => {
    if (applicants.length > 0) {
      applicants.forEach(applicant => {
        if (!approvalData[applicant.id]) {
          fetchApprovalStatus(applicant.id);
        }
      });
    }
  }, [applicants]);

  // Handle "Review Applicant" - navigate to recruitment context profile
  const handleReviewApplicant = (applicantId) => {
    navigate(`/portal/recruitment/${applicantId}`);
  };

  // Handle approval attempt
  const handleApprovalClick = async (applicant) => {
    setSelectedApplicant(applicant);
    setLoadingApprovalCheck(applicant.id);
    
    try {
      // Fetch fresh approval status
      const response = await axios.get(
        `${API}/employees/${applicant.id}/recruitment-approval-check`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const evaluation = response.data;
      setApprovalData(prev => ({ ...prev, [applicant.id]: evaluation }));
      
      if (evaluation.can_approve) {
        // Ready for approval - show confirmation dialog
        setApprovalDialogOpen(true);
      } else {
        // Not ready - show blockers dialog
        setBlockersDialogOpen(true);
      }
    } catch (error) {
      toast.error('Failed to check approval status');
    } finally {
      setLoadingApprovalCheck(null);
    }
  };

  // Execute approval
  const handleApproveRecruitment = async () => {
    if (!selectedApplicant) return;
    
    setIsApproving(true);
    try {
      const response = await axios.post(
        `${API}/employees/${selectedApplicant.id}/approve-recruitment`,
        { notes: approvalNotes },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(
        `${selectedApplicant.first_name} ${selectedApplicant.last_name} approved! Employee code: ${response.data.employee_code}`,
        { duration: 5000 }
      );
      
      setApprovalDialogOpen(false);
      setSelectedApplicant(null);
      setApprovalNotes('');
      
      // Redirect to the newly approved employee's profile
      navigate(`/portal/employees/${selectedApplicant.id}?tab=overview`);
      
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail.blockers) {
        setApprovalData(prev => ({
          ...prev,
          [selectedApplicant.id]: {
            ...prev[selectedApplicant.id],
            can_approve: false,
            blockers: detail.blockers
          }
        }));
        setApprovalDialogOpen(false);
        setBlockersDialogOpen(true);
        toast.error('Cannot approve - blockers exist');
      } else {
        toast.error(detail?.message || detail || 'Failed to approve recruitment');
      }
    } finally {
      setIsApproving(false);
    }
  };

  // Get approval summary for card display
  const getApprovalSummary = (applicantId) => {
    const data = approvalData[applicantId];
    if (!data) return null;
    
    return {
      canApprove: data.can_approve,
      blockerCount: data.blocker_count || 0,
      verifiedCount: data.verified_count || 0,
      requiredCount: data.required_count || 0
    };
  };

  return (
    <div className="space-y-6" data-testid="recruitment-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Recruitment Pipeline</h1>
          <p className="text-text-muted mt-1">
            {pipeline?.summary?.total_applicants || 0} applicants awaiting review and approval
          </p>
          <p className="text-xs text-text-muted/70 mt-0.5">
            Review applicants before approving. Once approved, they move to Staff.
          </p>
        </div>
        <Button onClick={() => navigate('/portal/employees')} variant="outline">
          <Users className="w-4 h-4 mr-2" />
          View Staff
        </Button>
      </div>

      {/* Pipeline Summary Cards */}
      {pipeline && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {pipeline.stages.map((stage) => (
            <Card 
              key={stage.status}
              className={cn(
                "cursor-pointer hover:shadow-md transition-shadow",
                statusFilter === stage.status && "ring-2 ring-primary"
              )}
              onClick={() => setStatusFilter(statusFilter === stage.status ? '' : stage.status)}
              data-testid={`pipeline-stage-${stage.status}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">{stage.label}</span>
                  <Badge variant="outline" className={STAGE_COLORS[stage.status]}>
                    {stage.applicants.length}
                  </Badge>
                </div>
                <div className="mt-2 text-2xl font-bold">
                  {stage.applicants.length}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-muted w-4 h-4" />
                <Input
                  placeholder="Search applicants..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                  data-testid="recruitment-search"
                />
              </div>
            </div>
            <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="All Stages" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="screening">Screening</SelectItem>
                <SelectItem value="interview">Interview</SelectItem>
                <SelectItem value="compliance_review">Compliance Review</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Applicants List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
              Applicants
            </Badge>
            Recruitment Pipeline
          </CardTitle>
          <CardDescription>
            Review each applicant's compliance status before approving for recruitment.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          ) : applicants.length === 0 ? (
            <div className="text-center py-8 text-text-muted">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No applicants found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {applicants.map((applicant) => {
                const approval = getApprovalSummary(applicant.id);
                const isLoadingApproval = loadingApprovalCheck === applicant.id;
                
                return (
                  <div
                    key={applicant.id}
                    className="p-4 rounded-xl border border-border-default hover:border-primary/30 hover:bg-bg-subtle/50 transition-all"
                    data-testid={`applicant-card-${applicant.id}`}
                  >
                    {/* Top Row: Name, Role, Stage */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <EmployeeAvatar
                          firstName={applicant.first_name}
                          lastName={applicant.last_name}
                          size="md"
                        />
                        <div>
                          <p className="font-semibold text-text-primary">
                            {applicant.first_name} {applicant.last_name}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {applicant.role || 'No role assigned'}
                            </Badge>
                            {applicant.applicant_reference && (
                              <span className="text-xs text-text-muted">
                                Ref: {applicant.applicant_reference}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {/* Stage Badge */}
                        <Badge 
                          variant="outline" 
                          className={cn("text-xs", STAGE_COLORS[applicant.status])}
                        >
                          {STAGE_LABELS[applicant.status] || applicant.status}
                        </Badge>
                        {/* Applicant Badge */}
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                          Applicant
                        </Badge>
                      </div>
                    </div>

                    {/* Middle Row: Quick Review Summary */}
                    <div className="mb-4 px-3 py-2 bg-gray-50 rounded-lg">
                      {approval ? (
                        <div className="flex items-center gap-4 text-sm">
                          {approval.canApprove ? (
                            <span className="flex items-center gap-1.5 text-emerald-600 font-medium">
                              <CheckCircle className="w-4 h-4" />
                              Ready for approval
                            </span>
                          ) : (
                            <span className="flex items-center gap-1.5 text-amber-600 font-medium">
                              <AlertTriangle className="w-4 h-4" />
                              Blocked by {approval.blockerCount} item{approval.blockerCount !== 1 ? 's' : ''}
                            </span>
                          )}
                          <span className="text-text-muted">
                            Progress: {approval.verifiedCount}/{approval.requiredCount}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-sm text-text-muted">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Loading approval status...
                        </div>
                      )}
                    </div>

                    {/* Bottom Row: Actions */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {/* PRIMARY: Review Applicant */}
                        <Button
                          onClick={() => handleReviewApplicant(applicant.id)}
                          className="bg-primary hover:bg-primary-hover"
                          data-testid={`review-applicant-btn-${applicant.id}`}
                        >
                          <Eye className="w-4 h-4 mr-2" />
                          Review Applicant
                        </Button>
                        
                        {/* SECONDARY: Approve Recruitment */}
                        {!applicant.recruitment_approved && canApprove && (
                          <Button
                            variant={approval?.canApprove ? "outline" : "ghost"}
                            className={cn(
                              approval?.canApprove 
                                ? "border-emerald-300 text-emerald-700 hover:bg-emerald-50" 
                                : "text-gray-500"
                            )}
                            onClick={() => handleApprovalClick(applicant)}
                            disabled={isLoadingApproval}
                            data-testid={`approve-btn-${applicant.id}`}
                          >
                            {isLoadingApproval ? (
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            ) : approval?.canApprove ? (
                              <CheckCircle className="w-4 h-4 mr-2" />
                            ) : (
                              <Shield className="w-4 h-4 mr-2" />
                            )}
                            {approval?.canApprove ? 'Approve Recruitment' : 'View Blockers'}
                          </Button>
                        )}
                        
                        {applicant.recruitment_approved && (
                          <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            Approved
                          </Badge>
                        )}
                      </div>

                      {/* Overflow Menu */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleReviewApplicant(applicant.id)}>
                            <Eye className="w-4 h-4 mr-2" />
                            Review Full Profile
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            onClick={() => navigate(`/portal/recruitment/${applicant.id}?tab=checklist`)}
                          >
                            <FileText className="w-4 h-4 mr-2" />
                            View Compliance File
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => navigate(`/portal/recruitment/${applicant.id}?tab=recruitment`)}
                          >
                            <Briefcase className="w-4 h-4 mr-2" />
                            View Recruitment Record
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Approval Confirmation Dialog */}
      <Dialog open={approvalDialogOpen} onOpenChange={setApprovalDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="approval-confirm-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-emerald-600" />
              Approve for Recruitment?
            </DialogTitle>
            <DialogDescription className="text-left">
              This will transition <strong>{selectedApplicant?.first_name} {selectedApplicant?.last_name}</strong> from 
              Applicant to Employee status.
            </DialogDescription>
          </DialogHeader>
          
          {selectedApplicant && (
            <div className="py-4">
              <div className="flex items-center gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
                <EmployeeAvatar
                  firstName={selectedApplicant.first_name}
                  lastName={selectedApplicant.last_name}
                  size="md"
                />
                <div>
                  <p className="font-medium">
                    {selectedApplicant.first_name} {selectedApplicant.last_name}
                  </p>
                  <p className="text-sm text-text-muted">{selectedApplicant.role}</p>
                </div>
              </div>
              
              <div className="text-sm text-gray-600 mb-4 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <p className="font-medium text-emerald-800 mb-2">This action will:</p>
                <ul className="list-disc ml-4 space-y-1 text-emerald-700">
                  <li>Assign an official employee code</li>
                  <li>Move from <strong>Applicant</strong> to <strong>Employee</strong></li>
                  <li>Set status to <strong>Onboarding</strong></li>
                  <li>Enable employee actions and scheduling</li>
                </ul>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Approval Notes (optional)</label>
                <Textarea
                  placeholder="Add any notes about this recruitment decision..."
                  value={approvalNotes}
                  onChange={(e) => setApprovalNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setApprovalDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleApproveRecruitment} 
              disabled={isApproving}
              className="bg-emerald-600 hover:bg-emerald-700"
              data-testid="confirm-approve-recruitment-btn"
            >
              {isApproving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              Approve Recruitment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Blockers Dialog */}
      <Dialog open={blockersDialogOpen} onOpenChange={setBlockersDialogOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="blockers-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-700">
              <AlertTriangle className="h-5 w-5" />
              Cannot Approve - Blockers Exist
            </DialogTitle>
            <DialogDescription>
              The following items must be completed before recruitment approval.
            </DialogDescription>
          </DialogHeader>
          
          {selectedApplicant && approvalData[selectedApplicant.id] && (
            <div className="py-4">
              <div className="flex items-center gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
                <EmployeeAvatar
                  firstName={selectedApplicant.first_name}
                  lastName={selectedApplicant.last_name}
                  size="sm"
                />
                <div>
                  <p className="font-medium text-sm">
                    {selectedApplicant.first_name} {selectedApplicant.last_name}
                  </p>
                  <p className="text-xs text-text-muted">
                    {approvalData[selectedApplicant.id].verified_count} / {approvalData[selectedApplicant.id].required_count} verified
                  </p>
                </div>
              </div>
              
              <div className="max-h-64 overflow-y-auto space-y-2">
                {approvalData[selectedApplicant.id].blockers?.map((blocker, idx) => (
                  <div 
                    key={blocker.requirement_key || idx}
                    className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-100"
                  >
                    <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <XCircle className="w-3.5 h-3.5 text-red-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800 text-sm">{blocker.label}</p>
                      <p className="text-xs text-red-600">{blocker.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setBlockersDialogOpen(false)}>
              Close
            </Button>
            <Button 
              onClick={() => {
                setBlockersDialogOpen(false);
                if (selectedApplicant) {
                  navigate(`/portal/recruitment/${selectedApplicant.id}?tab=checklist`);
                }
              }}
              className="bg-primary hover:bg-primary-hover"
            >
              <Eye className="w-4 h-4 mr-2" />
              Review Compliance
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
