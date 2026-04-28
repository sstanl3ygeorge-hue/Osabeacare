import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { 
  AlertTriangle, 
  Plus,
  Search,
  Filter,
  Calendar,
  User,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  MessageSquare,
  ChevronRight,
  AlertCircle
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Label } from "../../components/ui/label";
import { Progress } from '../../components/ui/progress';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const COMPLAINT_STATUSES = [
  { value: 'received', label: 'Received', color: 'bg-gray-100 text-gray-800', icon: Clock },
  { value: 'investigating', label: 'Investigating', color: 'bg-blue-100 text-blue-800', icon: Search },
  { value: 'awaiting_response', label: 'Awaiting Response', color: 'bg-amber-100 text-amber-800', icon: MessageSquare },
  { value: 'resolved', label: 'Resolved', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
  { value: 'closed', label: 'Closed', color: 'bg-gray-100 text-gray-800', icon: XCircle },
];

const SEVERITY_LEVELS = [
  { value: 'low', label: 'Low', color: 'bg-green-100 text-green-800' },
  { value: 'medium', label: 'Medium', color: 'bg-amber-100 text-amber-800' },
  { value: 'high', label: 'High', color: 'bg-red-100 text-red-800' },
  { value: 'critical', label: 'Critical', color: 'bg-red-200 text-red-900' },
];

const COMPLAINT_CATEGORIES = [
  'Staff Conduct',
  'Quality of Care',
  'Communication',
  'Timeliness',
  'Safety Concern',
  'Medication Error',
  'Documentation',
  'Privacy/Confidentiality',
  'Equipment/Environment',
  'Other'
];

const ComplaintsHandlingPage = () => {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [newNote, setNewNote] = useState('');
  
  const [newComplaint, setNewComplaint] = useState({
    complainant_name: '',
    complainant_relationship: '',
    complainant_contact: '',
    employee_id: '',
    category: '',
    severity: 'medium',
    title: '',
    description: '',
    date_received: new Date().toISOString().split('T')[0],
    date_of_incident: '',
    desired_outcome: ''
  });
  
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchComplaints();
    fetchStats();
    fetchEmployees();
  }, []);

  const fetchComplaints = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/complaints`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setComplaints(response.data.complaints || []);
    } catch (error) {
      console.error('Failed to fetch complaints:', error);
      setComplaints([]);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/complaints/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchEmployees = async () => {
    try {
      const response = await axios.get(`${API}/staff/employees`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmployees(response.data || []);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    }
  };

  const handleSubmitComplaint = async () => {
    try {
      await axios.post(`${API}/complaints`, newComplaint, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowAddDialog(false);
      setNewComplaint({
        complainant_name: '',
        complainant_relationship: '',
        complainant_contact: '',
        employee_id: '',
        category: '',
        severity: 'medium',
        title: '',
        description: '',
        date_received: new Date().toISOString().split('T')[0],
        date_of_incident: '',
        desired_outcome: ''
      });
      fetchComplaints();
      fetchStats();
    } catch (error) {
      console.error('Failed to submit complaint:', error);
    }
  };

  const handleUpdateStatus = async (complaintId, newStatus) => {
    try {
      await axios.patch(`${API}/complaints/${complaintId}/status`, 
        { status: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchComplaints();
      fetchStats();
      if (selectedComplaint?.id === complaintId) {
        setSelectedComplaint({ ...selectedComplaint, status: newStatus });
      }
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const handleAddNote = async () => {
    if (!selectedComplaint || !newNote.trim()) return;
    
    try {
      await axios.post(`${API}/complaints/${selectedComplaint.id}/notes`, 
        { note: newNote },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setNewNote('');
      // Refresh the complaint details
      const response = await axios.get(`${API}/complaints/${selectedComplaint.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedComplaint(response.data);
    } catch (error) {
      console.error('Failed to add note:', error);
    }
  };

  const filteredComplaints = complaints.filter(item => {
    const matchesSearch = !searchTerm || 
      item.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.complainant_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.reference_number?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusStyle = (status) => {
    const found = COMPLAINT_STATUSES.find(s => s.value === status);
    return found ? found.color : 'bg-gray-100 text-gray-800';
  };

  const getSeverityStyle = (severity) => {
    const found = SEVERITY_LEVELS.find(s => s.value === severity);
    return found ? found.color : 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status) => {
    const found = COMPLAINT_STATUSES.find(s => s.value === status);
    const Icon = found?.icon || Clock;
    return <Icon className="w-4 h-4" />;
  };

  return (
    <div className="p-6 space-y-6" data-testid="complaints-handling-page">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Complaints Handling</h1>
          <p className="text-gray-500 mt-1">CQC-compliant complaints management and resolution tracking</p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button data-testid="log-complaint-btn">
              <Plus className="w-4 h-4 mr-2" /> Log Complaint
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Log New Complaint</DialogTitle>
              <DialogDescription>
                Record complaint details for investigation and resolution
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Complainant Name *</Label>
                  <Input
                    value={newComplaint.complainant_name}
                    onChange={(e) => setNewComplaint({...newComplaint, complainant_name: e.target.value})}
                    placeholder="Name of person making complaint"
                  />
                </div>
                <div>
                  <Label>Relationship to Service User</Label>
                  <Select 
                    value={newComplaint.complainant_relationship} 
                    onValueChange={(v) => setNewComplaint({...newComplaint, complainant_relationship: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select relationship" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="service_user">Service User</SelectItem>
                      <SelectItem value="family">Family Member</SelectItem>
                      <SelectItem value="carer">Carer</SelectItem>
                      <SelectItem value="advocate">Advocate</SelectItem>
                      <SelectItem value="professional">Healthcare Professional</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Contact Details</Label>
                  <Input
                    value={newComplaint.complainant_contact}
                    onChange={(e) => setNewComplaint({...newComplaint, complainant_contact: e.target.value})}
                    placeholder="Phone or email"
                  />
                </div>
                <div>
                  <Label>Staff Member Involved</Label>
                  <Select 
                    value={newComplaint.employee_id} 
                    onValueChange={(v) => setNewComplaint({...newComplaint, employee_id: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select employee" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unknown">Unknown/Not Specified</SelectItem>
                      {employees.map(emp => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Category *</Label>
                  <Select 
                    value={newComplaint.category} 
                    onValueChange={(v) => setNewComplaint({...newComplaint, category: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {COMPLAINT_CATEGORIES.map(cat => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Severity</Label>
                  <Select 
                    value={newComplaint.severity} 
                    onValueChange={(v) => setNewComplaint({...newComplaint, severity: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SEVERITY_LEVELS.map(level => (
                        <SelectItem key={level.value} value={level.value}>{level.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div>
                <Label>Complaint Title *</Label>
                <Input
                  value={newComplaint.title}
                  onChange={(e) => setNewComplaint({...newComplaint, title: e.target.value})}
                  placeholder="Brief summary of the complaint"
                />
              </div>
              
              <div>
                <Label>Full Description *</Label>
                <Textarea
                  value={newComplaint.description}
                  onChange={(e) => setNewComplaint({...newComplaint, description: e.target.value})}
                  placeholder="Detailed description of the complaint..."
                  rows={4}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Date Received</Label>
                  <Input
                    type="date"
                    value={newComplaint.date_received}
                    onChange={(e) => setNewComplaint({...newComplaint, date_received: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Date of Incident</Label>
                  <Input
                    type="date"
                    value={newComplaint.date_of_incident}
                    onChange={(e) => setNewComplaint({...newComplaint, date_of_incident: e.target.value})}
                  />
                </div>
              </div>
              
              <div>
                <Label>Desired Outcome</Label>
                <Textarea
                  value={newComplaint.desired_outcome}
                  onChange={(e) => setNewComplaint({...newComplaint, desired_outcome: e.target.value})}
                  placeholder="What outcome does the complainant want?"
                  rows={2}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleSubmitComplaint} data-testid="submit-complaint-btn">
                Log Complaint
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Complaints</p>
                  <p className="text-2xl font-bold">{stats.total || 0}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-gray-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Open</p>
                  <p className="text-2xl font-bold text-amber-600">{stats.open || 0}</p>
                </div>
                <Clock className="w-8 h-8 text-amber-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Investigating</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.investigating || 0}</p>
                </div>
                <Search className="w-8 h-8 text-blue-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Resolved</p>
                  <p className="text-2xl font-bold text-green-600">{stats.resolved || 0}</p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-green-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Avg Resolution (days)</p>
                  <p className="text-2xl font-bold">{stats.avg_resolution_days?.toFixed(1) || '-'}</p>
                </div>
                <Calendar className="w-8 h-8 text-purple-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            className="pl-10"
            placeholder="Search complaints..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-48">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {COMPLAINT_STATUSES.map(status => (
              <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Complaints List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading complaints...</div>
        ) : filteredComplaints.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <CheckCircle2 className="w-12 h-12 mx-auto text-green-300 mb-4" />
              <p className="text-gray-500">No complaints recorded</p>
              <p className="text-sm text-gray-400 mt-1">Click "Log Complaint" to record a new complaint</p>
            </CardContent>
          </Card>
        ) : (
          filteredComplaints.map((item) => (
            <Card 
              key={item.id} 
              className="hover:shadow-md transition-shadow cursor-pointer" 
              data-testid={`complaint-item-${item.id}`}
              onClick={() => {
                setSelectedComplaint(item);
                setShowDetailsDialog(true);
              }}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-mono text-gray-500">{item.reference_number}</span>
                      <Badge className={getStatusStyle(item.status)}>
                        {getStatusIcon(item.status)}
                        <span className="ml-1">{item.status}</span>
                      </Badge>
                      <Badge className={getSeverityStyle(item.severity)}>
                        {item.severity}
                      </Badge>
                      <Badge variant="outline">{item.category}</Badge>
                    </div>
                    <h3 className="font-semibold text-lg">{item.title}</h3>
                    <p className="text-gray-600 mt-1 line-clamp-2">{item.description}</p>
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        {item.complainant_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(item.date_received).toLocaleDateString()}
                      </span>
                      {item.employee_name && (
                        <span className="flex items-center gap-1">
                          <AlertCircle className="w-4 h-4" />
                          Staff: {item.employee_name}
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedComplaint && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <span>{selectedComplaint.reference_number}</span>
                  <Badge className={getStatusStyle(selectedComplaint.status)}>
                    {selectedComplaint.status}
                  </Badge>
                </DialogTitle>
                <DialogDescription>{selectedComplaint.title}</DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                {/* Status Actions */}
                <div className="flex gap-2 flex-wrap">
                  {COMPLAINT_STATUSES.filter(s => s.value !== selectedComplaint.status).map(status => (
                    <Button 
                      key={status.value}
                      variant="outline" 
                      size="sm"
                      onClick={() => handleUpdateStatus(selectedComplaint.id, status.value)}
                    >
                      Mark as {status.label}
                    </Button>
                  ))}
                </div>
                
                {/* Details */}
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Complainant:</span>
                      <span className="ml-2 font-medium">{selectedComplaint.complainant_name}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Relationship:</span>
                      <span className="ml-2 font-medium">{selectedComplaint.complainant_relationship}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Date Received:</span>
                      <span className="ml-2 font-medium">{new Date(selectedComplaint.date_received).toLocaleDateString()}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Severity:</span>
                      <Badge className={`ml-2 ${getSeverityStyle(selectedComplaint.severity)}`}>
                        {selectedComplaint.severity}
                      </Badge>
                    </div>
                  </div>
                  
                  <div>
                    <span className="text-gray-500 text-sm">Description:</span>
                    <p className="mt-1">{selectedComplaint.description}</p>
                  </div>
                  
                  {selectedComplaint.desired_outcome && (
                    <div>
                      <span className="text-gray-500 text-sm">Desired Outcome:</span>
                      <p className="mt-1">{selectedComplaint.desired_outcome}</p>
                    </div>
                  )}
                </div>
                
                {/* Notes/Timeline */}
                <div>
                  <h4 className="font-semibold mb-2">Investigation Notes</h4>
                  <div className="space-y-2 mb-3">
                    {(selectedComplaint.notes || []).map((note, idx) => (
                      <div key={idx} className="bg-blue-50 p-3 rounded-lg text-sm">
                        <p>{note.text}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {note.created_by} - {new Date(note.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex gap-2">
                    <Input 
                      placeholder="Add investigation note..."
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                    />
                    <Button onClick={handleAddNote}>Add Note</Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ComplaintsHandlingPage;

