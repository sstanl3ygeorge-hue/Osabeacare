import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';
import {
  ArrowLeft, Upload, FileText, Mail, Phone, MapPin, Calendar,
  CheckCircle, Clock, AlertTriangle, XCircle, Loader2, FileCheck,
  GraduationCap, ClipboardList, History, User
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusIcons = {
  not_started: Clock,
  requested: Mail,
  uploaded: Upload,
  under_review: Clock,
  approved: CheckCircle,
  rejected: XCircle,
  expired: AlertTriangle,
  not_applicable: XCircle
};

const statusColors = {
  not_started: 'status-neutral',
  requested: 'status-info',
  uploaded: 'status-info',
  under_review: 'status-warning',
  approved: 'status-success',
  rejected: 'status-error',
  expired: 'status-error',
  not_applicable: 'status-neutral'
};

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const [employee, setEmployee] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const { token, isAuditor } = useAuth();

  const fetchData = async () => {
    try {
      const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/audit-logs?entity_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setEmployee(empRes.data);
      setDocuments(docsRes.data);
      setDocumentTypes(typesRes.data);
      setPolicies(policiesRes.data);
      setTraining(trainingRes.data);
      setAuditLogs(logsRes.data);
    } catch (error) {
      console.error('Failed to fetch employee data:', error);
      toast.error('Failed to load employee data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [employeeId, token]);

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedDocType || !uploadFile) {
      toast.error('Please select a document type and file');
      return;
    }
    
    setIsUploading(true);
    
    try {
      // First, create the document record
      const createRes = await axios.post(`${API}/employee-documents`, {
        employee_id: employeeId,
        document_type_id: selectedDocType
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      // Then upload the file
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      await axios.post(`${API}/employee-documents/${createRes.data.id}/upload`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Document uploaded successfully');
      setUploadDialogOpen(false);
      setSelectedDocType('');
      setUploadFile(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateDocumentStatus = async (docId, status) => {
    try {
      await axios.put(`${API}/employee-documents/${docId}`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Document ${status}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update document');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Employee not found</p>
        <Link to="/portal/employees">
          <Button className="mt-4">Back to Employees</Button>
        </Link>
      </div>
    );
  }

  const groupedDocs = documentTypes.reduce((acc, type) => {
    if (!acc[type.category]) acc[type.category] = [];
    const doc = documents.find(d => d.document_type_id === type.id);
    acc[type.category].push({ ...type, document: doc });
    return acc;
  }, {});

  return (
    <div className="space-y-6" data-testid="employee-profile">
      {/* Back Link */}
      <Link to="/portal/employees" className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors" data-testid="back-link">
        <ArrowLeft className="h-4 w-4" />
        Back to Employees
      </Link>

      {/* Header Card */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-start gap-6">
            <div className="flex items-start gap-4 flex-1">
              <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                <span className="text-primary font-heading font-bold text-xl">
                  {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
                </span>
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-text-primary">
                  {employee.first_name} {employee.last_name}
                </h1>
                <p className="text-text-muted">{employee.employee_code} · {employee.role}</p>
                <span className={`status-chip mt-2 ${
                  employee.status === 'active' ? 'status-success' :
                  employee.status === 'onboarding' ? 'status-info' :
                  'status-neutral'
                }`}>
                  {employee.status?.replace('_', ' ')}
                </span>
              </div>
            </div>

            <div className="flex flex-col items-end gap-4">
              <div className="text-right">
                <p className="text-sm text-text-muted">Compliance Score</p>
                <p className="text-3xl font-heading font-bold text-text-primary">{employee.completion_percentage}%</p>
              </div>
              <Progress value={employee.completion_percentage} className="w-32 h-2" />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#E4E8EB]">
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-text-muted" />
              <span className="text-sm text-text-primary">{employee.email}</span>
            </div>
            {employee.phone && (
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-text-muted" />
                <span className="text-sm text-text-primary">{employee.phone}</span>
              </div>
            )}
            <div className="flex items-center gap-3">
              <MapPin className="h-5 w-5 text-text-muted" />
              <span className="text-sm text-text-primary">{employee.branch}</span>
            </div>
            {employee.start_date && (
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-text-muted" />
                <span className="text-sm text-text-primary">Started: {employee.start_date}</span>
              </div>
            )}
          </div>

          {!isAuditor() && (
            <div className="flex flex-wrap gap-3 mt-6">
              <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="upload-doc-btn">
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Document
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="font-heading">Upload Document</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleUploadDocument} className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label>Document Type</Label>
                      <Select value={selectedDocType} onValueChange={setSelectedDocType}>
                        <SelectTrigger className="rounded-xl" data-testid="doc-type-select">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          {documentTypes.map((type) => (
                            <SelectItem key={type.id} value={type.id}>
                              {type.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>File</Label>
                      <Input
                        type="file"
                        onChange={(e) => setUploadFile(e.target.files[0])}
                        className="rounded-xl"
                        data-testid="doc-file-input"
                      />
                      <p className="text-xs text-text-muted">
                        Upload a clear copy of the document.
                      </p>
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <Button type="button" variant="outline" onClick={() => setUploadDialogOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isUploading} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="upload-submit">
                        {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl">
          <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <User className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="checklist" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <ClipboardList className="h-4 w-4 mr-2" />
            Checklist
          </TabsTrigger>
          <TabsTrigger value="documents" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileText className="h-4 w-4 mr-2" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="policies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileCheck className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          <TabsTrigger value="training" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <GraduationCap className="h-4 w-4 mr-2" />
            Training
          </TabsTrigger>
          <TabsTrigger value="audit" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <History className="h-4 w-4 mr-2" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Personal Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-text-muted">Full Name</p>
                    <p className="font-medium text-text-primary">{employee.first_name} {employee.last_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Employee ID</p>
                    <p className="font-medium text-text-primary">{employee.employee_code}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Role</p>
                    <p className="font-medium text-text-primary">{employee.role}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Branch</p>
                    <p className="font-medium text-text-primary">{employee.branch}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Email</p>
                    <p className="font-medium text-text-primary">{employee.email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Phone</p>
                    <p className="font-medium text-text-primary">{employee.phone || 'Not provided'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Compliance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Documents</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {documents.filter(d => d.status === 'approved').length}/{documentTypes.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Policies Signed</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {policies.filter(p => p.status === 'signed').length}/{policies.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Training Complete</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {training.filter(t => t.status === 'completed').length}/{training.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Missing Items</p>
                    <p className="text-2xl font-heading font-bold text-warning">
                      {documents.filter(d => d.status === 'not_started' || d.status === 'requested').length}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Checklist Tab */}
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              <div className="space-y-6">
                {Object.entries(groupedDocs).map(([category, items]) => (
                  <div key={category} className="space-y-3">
                    <h3 className="font-heading font-semibold text-text-primary">{category}</h3>
                    <div className="space-y-2">
                      {items.map((item) => {
                        const StatusIcon = statusIcons[item.document?.status || 'not_started'];
                        return (
                          <div key={item.id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-xl">
                            <div className="flex items-center gap-3">
                              <StatusIcon className={`h-5 w-5 ${
                                item.document?.status === 'approved' ? 'text-success' :
                                item.document?.status === 'rejected' || item.document?.status === 'expired' ? 'text-error' :
                                item.document?.status === 'uploaded' || item.document?.status === 'under_review' ? 'text-warning' :
                                'text-text-muted'
                              }`} />
                              <div>
                                <p className="font-medium text-text-primary">{item.name}</p>
                                {item.required_before_active && (
                                  <span className="text-xs text-error">Required</span>
                                )}
                              </div>
                            </div>
                            <span className={`status-chip ${statusColors[item.document?.status || 'not_started']}`}>
                              {(item.document?.status || 'not_started').replace('_', ' ')}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-0">
              {documents.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No documents uploaded yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Document</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Category</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Uploaded</th>
                        {!isAuditor() && <th className="text-left p-4 font-medium text-text-muted text-sm">Actions</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.id} className="border-b border-[#E4E8EB]">
                          <td className="p-4">
                            <p className="font-medium text-text-primary">{doc.document_type_name}</p>
                            {doc.original_filename && (
                              <p className="text-sm text-text-muted">{doc.original_filename}</p>
                            )}
                          </td>
                          <td className="p-4 text-text-muted">{doc.category}</td>
                          <td className="p-4">
                            <span className={`status-chip ${statusColors[doc.status]}`}>
                              {doc.status?.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="p-4 text-text-muted text-sm">
                            {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '-'}
                          </td>
                          {!isAuditor() && (
                            <td className="p-4">
                              {doc.status === 'uploaded' && (
                                <div className="flex gap-2">
                                  <Button 
                                    size="sm" 
                                    onClick={() => handleUpdateDocumentStatus(doc.id, 'approved')}
                                    className="bg-success hover:bg-success/90 text-white rounded-lg"
                                  >
                                    Approve
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => handleUpdateDocumentStatus(doc.id, 'rejected')}
                                    className="text-error border-error hover:bg-error/10 rounded-lg"
                                  >
                                    Reject
                                  </Button>
                                </div>
                              )}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policies Tab */}
        <TabsContent value="policies">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {policies.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No policies assigned yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {policies.map((policy) => (
                    <div key={policy.id} className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl">
                      <div>
                        <p className="font-medium text-text-primary">{policy.policy_title}</p>
                        <p className="text-sm text-text-muted">Assigned: {new Date(policy.assigned_at).toLocaleDateString()}</p>
                      </div>
                      <span className={`status-chip ${
                        policy.status === 'signed' ? 'status-success' :
                        policy.status === 'viewed' ? 'status-info' :
                        'status-neutral'
                      }`}>
                        {policy.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Training Tab */}
        <TabsContent value="training">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {training.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No training records yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {training.map((record) => (
                    <div key={record.id} className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl">
                      <div>
                        <p className="font-medium text-text-primary">{record.training_name}</p>
                        <p className="text-sm text-text-muted">
                          {record.mandatory ? 'Mandatory' : 'Optional'}
                          {record.completion_date && ` · Completed: ${new Date(record.completion_date).toLocaleDateString()}`}
                        </p>
                      </div>
                      <span className={`status-chip ${
                        record.status === 'completed' ? 'status-success' :
                        record.status === 'in_progress' ? 'status-info' :
                        record.status === 'expired' ? 'status-error' :
                        'status-neutral'
                      }`}>
                        {record.status?.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {auditLogs.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No activity recorded yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="flex items-start gap-4 p-4 bg-[#F8FAFA] rounded-xl">
                      <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center flex-shrink-0">
                        <History className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-text-primary">
                          {log.action?.replace('_', ' ')}
                        </p>
                        <p className="text-sm text-text-muted">
                          By {log.user_name || 'System'} · {new Date(log.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
