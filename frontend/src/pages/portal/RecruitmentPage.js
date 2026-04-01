import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
import { Search, Users, UserPlus, Filter, Loader2, ChevronRight, CheckCircle, Clock, FileText, User, ArrowRight } from 'lucide-react';
import EmployeeAvatar from '../../components/portal/EmployeeAvatar';
import { StageIdentityBadge } from '../../components/compliance';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusLabels = {
  new: 'New Application',
  screening: 'Under Review',
  interview: 'Interview Stage',
  compliance_review: 'Awaiting Approval'
};

const statusColors = {
  new: 'bg-blue-100 text-blue-800',
  screening: 'bg-purple-100 text-purple-800',
  interview: 'bg-amber-100 text-amber-800',
  compliance_review: 'bg-orange-100 text-orange-800'
};

export default function RecruitmentPage() {
  const navigate = useNavigate();
  const [pipeline, setPipeline] = useState(null);
  const [applicants, setApplicants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [selectedApplicant, setSelectedApplicant] = useState(null);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const { token, user } = useAuth();

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

  const fetchApplicants = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter) params.append('status', statusFilter);
      
      const response = await axios.get(`${API}/recruitment/applicants?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setApplicants(response.data);
    } catch (error) {
      console.error('Failed to fetch applicants:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipeline();
    fetchApplicants();
  }, [token, search, statusFilter]);

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
        `${selectedApplicant.first_name} ${selectedApplicant.last_name} has been approved! Employee code: ${response.data.employee_code}`,
        { duration: 5000 }
      );
      
      setApprovalDialogOpen(false);
      setSelectedApplicant(null);
      setApprovalNotes('');
      fetchPipeline();
      fetchApplicants();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve recruitment');
    } finally {
      setIsApproving(false);
    }
  };

  const canApprove = user?.role === 'super_admin' || user?.role === 'admin';

  return (
    <div className="space-y-6" data-testid="recruitment-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Recruitment Pipeline</h1>
          <p className="text-text-muted mt-1">
            {pipeline?.summary?.total_applicants || 0} applicants awaiting recruitment approval
          </p>
          <p className="text-xs text-text-muted/70 mt-0.5">
            Applicants appear here until recruitment is approved. After approval, they move to Staff.
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
              className={`cursor-pointer hover:shadow-md transition-shadow ${
                statusFilter === stage.status ? 'ring-2 ring-brand-primary' : ''
              }`}
              onClick={() => setStatusFilter(statusFilter === stage.status ? '' : stage.status)}
              data-testid={`pipeline-stage-${stage.status}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-muted">{stage.label}</span>
                  <Badge variant="secondary" className={statusColors[stage.status]}>
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
                <SelectItem value="new">New Applications</SelectItem>
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
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">Applicants</Badge>
            Recruitment Pipeline
          </CardTitle>
          <CardDescription>
            People awaiting recruitment approval. Once approved, they move to Staff with an employee code assigned.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-brand-primary" />
            </div>
          ) : applicants.length === 0 ? (
            <div className="text-center py-8 text-text-muted">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No applicants found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {applicants.map((applicant) => (
                <div
                  key={applicant.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border-default hover:bg-bg-subtle transition-colors"
                  data-testid={`applicant-row-${applicant.id}`}
                >
                  <div className="flex items-center gap-4">
                    <EmployeeAvatar
                      firstName={applicant.first_name}
                      lastName={applicant.last_name}
                      size="md"
                    />
                    <div>
                      <Link
                        to={`/portal/employees/${applicant.id}`}
                        className="font-medium text-text-primary hover:text-brand-primary"
                      >
                        {applicant.first_name} {applicant.last_name}
                      </Link>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className={statusColors[applicant.status]}>
                          {statusLabels[applicant.status]}
                        </Badge>
                        <span className="text-sm text-text-muted">{applicant.role}</span>
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
                    <StageIdentityBadge 
                      stageIdentity={applicant.person_stage || applicant.stage_identity || 'applicant'} 
                      size="sm" 
                    />
                    
                    {applicant.recruitment_approved ? (
                      <Badge className="bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Recruitment Approved
                      </Badge>
                    ) : canApprove ? (
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedApplicant(applicant);
                          setApprovalDialogOpen(true);
                        }}
                        data-testid={`approve-btn-${applicant.id}`}
                        className="bg-primary hover:bg-primary-hover"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve Recruitment
                      </Button>
                    ) : (
                      <Badge variant="outline" className="text-amber-600 border-amber-300">
                        <Clock className="w-3 h-3 mr-1" />
                        Awaiting Approval
                      </Badge>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/portal/employees/${applicant.id}`)}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Approval Dialog */}
      <Dialog open={approvalDialogOpen} onOpenChange={setApprovalDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-primary" />
              Approve Recruitment
            </DialogTitle>
            <DialogDescription className="text-left">
              <p className="mb-3">This action will:</p>
              <ul className="list-disc ml-4 space-y-1 text-sm">
                <li>Assign an official employee code</li>
                <li>Move this person from <strong>Applicant</strong> to <strong>Staff</strong> stage</li>
                <li>Enable them for work assignment once checks are verified</li>
              </ul>
              <p className="mt-3 text-amber-700 bg-amber-50 p-2 rounded text-sm">
                Ensure all recruitment checks (references, DBS, right to work, interview) are complete before approving.
              </p>
            </DialogDescription>
          </DialogHeader>
          
          {selectedApplicant && (
            <div className="py-4">
              <div className="flex items-center gap-3 mb-4 p-3 bg-bg-subtle rounded-lg">
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
                  <Badge variant="outline" className="bg-blue-50 text-blue-600 border-blue-200 text-[10px] mt-1">
                    Applicant → Staff
                  </Badge>
                </div>
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
              data-testid="confirm-approve-btn"
              className="bg-primary hover:bg-primary-hover"
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
    </div>
  );
}
