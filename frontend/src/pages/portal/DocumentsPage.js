import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import { FileText, Search, Filter, Loader2, CheckCircle, Clock, XCircle } from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusColors = {
  not_started: 'status-neutral',
  requested: 'status-info',
  uploaded: 'status-info',
  under_review: 'status-warning',
  approved: 'status-success',
  rejected: 'status-error',
  expired: 'status-error'
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [search, setSearch] = useState('');
  const { token, isAuditor } = useAuth();

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (categoryFilter) params.append('category', categoryFilter);
      
      const [docsRes, empsRes] = await Promise.all([
        axios.get(`${API}/employee-documents?${params}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setDocuments(docsRes.data);
      setEmployees(empsRes.data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token, statusFilter, categoryFilter]);

  const handleUpdateStatus = async (docId, status) => {
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

  const getEmployeeName = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId);
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  const filteredDocuments = documents.filter(doc => {
    if (search) {
      const empName = getEmployeeName(doc.employee_id).toLowerCase();
      const docName = (doc.document_type_name || '').toLowerCase();
      return empName.includes(search.toLowerCase()) || docName.includes(search.toLowerCase());
    }
    return true;
  });

  const categories = [...new Set(documents.map(d => d.category).filter(Boolean))];

  const pendingReview = documents.filter(d => d.status === 'uploaded').length;
  const approved = documents.filter(d => d.status === 'approved').length;
  const missing = documents.filter(d => d.status === 'not_started' || d.status === 'requested').length;

  return (
    <div className="space-y-6" data-testid="documents-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
          Document Centre
        </h1>
        <p className="text-text-muted mt-1">Manage and review employee documents</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-warning/10 rounded-xl flex items-center justify-center">
              <Clock className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{pendingReview}</p>
              <p className="text-sm text-text-muted">Awaiting Review</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-success/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{approved}</p>
              <p className="text-sm text-text-muted">Verified</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-error/10 rounded-xl flex items-center justify-center">
              <XCircle className="h-6 w-6 text-error" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{missing}</p>
              <p className="text-sm text-text-muted">Missing</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <Input
                placeholder="Search by employee or document..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 rounded-xl border-[#E4E8EB]"
                data-testid="docs-search"
              />
            </div>
            <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-40 rounded-xl" data-testid="docs-status-filter">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="not_started">Not Started</SelectItem>
                <SelectItem value="requested">Requested</SelectItem>
                <SelectItem value="uploaded">Awaiting Review</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="approved">Verified</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Select value={categoryFilter || "all"} onValueChange={(v) => setCategoryFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-40 rounded-xl" data-testid="docs-category-filter">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No documents found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Document</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden md:table-cell">Category</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden lg:table-cell">Uploaded</th>
                    {!isAuditor() && <th className="text-left p-4 font-medium text-text-muted text-sm">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA]">
                      <td className="p-4">
                        <p className="font-medium text-text-primary">{doc.document_type_name}</p>
                        {doc.original_filename && (
                          <p className="text-sm text-text-muted">{doc.original_filename}</p>
                        )}
                      </td>
                      <td className="p-4 text-text-primary">{getEmployeeName(doc.employee_id)}</td>
                      <td className="p-4 text-text-muted hidden md:table-cell">{doc.category}</td>
                      <td className="p-4">
                        <span className={`status-chip ${statusColors[doc.status]}`}>
                          {doc.status?.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-4 text-text-muted text-sm hidden lg:table-cell">
                        {formatBackendDate(doc.uploaded_at, { fallback: '-' })}
                      </td>
                      {!isAuditor() && (
                        <td className="p-4">
                          {doc.status === 'uploaded' && (
                            <div className="flex gap-2">
                              <Button 
                                size="sm" 
                                onClick={() => handleUpdateStatus(doc.id, 'approved')}
                                className="bg-success hover:bg-success/90 text-white rounded-lg"
                                data-testid={`approve-${doc.id}`}
                              >
                                Approve
                              </Button>
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => handleUpdateStatus(doc.id, 'rejected')}
                                className="text-error border-error hover:bg-error/10 rounded-lg"
                                data-testid={`reject-${doc.id}`}
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
    </div>
  );
}
