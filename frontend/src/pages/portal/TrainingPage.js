import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { 
  GraduationCap, Plus, CheckCircle, Clock, AlertTriangle, Loader2, 
  MoreVertical, Edit, History, Filter, CalendarClock, ShieldCheck
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const mandatoryTraining = [
  'Safeguarding of Vulnerable Adults',
  'Health and Safety',
  'Moving and Handling',
  'Infection Control and Hygiene',
  'Medication Administration',
  'Food Hygiene, Nutrition and Hydration',
  'Covid 19',
  'First Aid Awareness'
];

const additionalTraining = [
  'Confidentiality',
  'Fire Safety',
  'Understanding Dementia',
  'Mental Health Awareness',
  'Pressure Care and Prevention Techniques',
  'Care Planning Process',
  'Deprivation of Liberty Safeguards',
  'Person Centred Care',
  'Dying, Death and Bereavement'
];

// Calculate expiry status
const getExpiryStatus = (expiryDate) => {
  if (!expiryDate) return null;
  
  const now = new Date();
  const expiry = new Date(expiryDate);
  const daysUntilExpiry = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
  
  if (daysUntilExpiry < 0) {
    return { status: 'expired', label: 'Expired', daysText: `${Math.abs(daysUntilExpiry)} days ago`, color: 'red' };
  } else if (daysUntilExpiry <= 30) {
    return { status: 'expiring_soon', label: 'Needs Renewal', daysText: `${daysUntilExpiry} days left`, color: 'amber' };
  } else {
    return { status: 'valid', label: 'Valid', daysText: `${daysUntilExpiry} days`, color: 'green' };
  }
};

export default function TrainingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [training, setTraining] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Initialize filter from URL params
  const [filter, setFilter] = useState(searchParams.get('filter') || 'all');
  const { token, isAuditor } = useAuth();

  // Sync filter to URL
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    if (filter && filter !== 'all') {
      newParams.set('filter', filter);
    } else {
      newParams.delete('filter');
    }
    setSearchParams(newParams, { replace: true });
  }, [filter]);


  // Correction modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [correction, setCorrection] = useState({ field: 'expiry_date', new_value: '', reason: '' });
  
  // History modal state
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyRecord, setHistoryRecord] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [newRecord, setNewRecord] = useState({
    employee_id: '',
    training_name: '',
    mandatory: true,
    status: 'not_started',
    expiry_date: ''
  });

  const fetchData = async () => {
    try {
      const [trainingRes, employeesRes] = await Promise.all([
        axios.get(`${API}/training-records`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setTraining(trainingRes.data);
      setEmployees(employeesRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const handleAddTraining = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      const payload = { ...newRecord };
      if (!payload.expiry_date) delete payload.expiry_date;
      
      await axios.post(`${API}/training-records`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Training record added');
      setAddOpen(false);
      setNewRecord({ employee_id: '', training_name: '', mandatory: true, status: 'not_started', expiry_date: '' });
      await fetchData();
    } catch (error) {
      toast.error('Failed to add training record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCorrection = async () => {
    if (!correction.reason || correction.reason.trim().length < 3) {
      toast.error('Please provide a reason for this correction (minimum 3 characters)');
      return;
    }
    if (!correction.new_value) {
      toast.error('Please enter the new value');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await axios.post(`${API}/training-records/${editingRecord.id}/correct`, {
        field: correction.field,
        old_value: editingRecord[correction.field],
        new_value: correction.new_value,
        reason: correction.reason.trim()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Training record corrected');
      setEditOpen(false);
      setEditingRecord(null);
      setCorrection({ field: 'expiry_date', new_value: '', reason: '' });
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to correct training record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewHistory = async (record) => {
    setHistoryRecord(record);
    setHistoryOpen(true);
    setHistoryLoading(true);
    
    try {
      const res = await axios.get(`${API}/training-records/${record.id}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistoryData(res.data.history || []);
    } catch (error) {
      toast.error('Failed to load history');
      setHistoryData([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const openEditModal = (record, field = 'expiry_date') => {
    setEditingRecord(record);
    setCorrection({ 
      field, 
      new_value: record[field] || '', 
      reason: '' 
    });
    setEditOpen(true);
  };

  const getEmployeeName = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId);
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  // Filter training records
  const filteredTraining = training.filter(record => {
    if (filter === 'all') return true;
    
    const expiryStatus = getExpiryStatus(record.expiry_date);
    if (!expiryStatus && (filter === 'expired' || filter === 'expiring_soon')) return false;
    if (!expiryStatus && filter === 'valid') return !record.expiry_date; // Show records without expiry
    
    return expiryStatus?.status === filter;
  });

  // Calculate stats
  const completed = training.filter(t => t.status === 'completed').length;
  const expired = training.filter(t => {
    const status = getExpiryStatus(t.expiry_date);
    return status?.status === 'expired';
  }).length;
  const expiringSoon = training.filter(t => {
    const status = getExpiryStatus(t.expiry_date);
    return status?.status === 'expiring_soon';
  }).length;
  const verified = training.filter(t => t.verified).length;

  return (
    <div className="space-y-6" data-testid="training-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Training Matrix
          </h1>
          <p className="text-text-muted mt-1">
            Track staff training, expiry dates, and renewals. Use filters to find risks quickly.
          </p>
        </div>
        
        {!isAuditor() && (
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="add-training-btn">
                <Plus className="mr-2 h-4 w-4" />
                Add Training
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="font-heading">Add Training Record</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddTraining} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Employee *</Label>
                  <Select value={newRecord.employee_id} onValueChange={(value) => setNewRecord({...newRecord, employee_id: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-employee">
                      <SelectValue placeholder="Select employee" />
                    </SelectTrigger>
                    <SelectContent>
                      {employees.map((emp) => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Training Course *</Label>
                  <Select value={newRecord.training_name} onValueChange={(value) => setNewRecord({...newRecord, training_name: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-name">
                      <SelectValue placeholder="Select training" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="header-mandatory" disabled className="font-semibold">
                        Mandatory Training
                      </SelectItem>
                      {mandatoryTraining.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                      <SelectItem value="header-additional" disabled className="font-semibold">
                        Additional Training
                      </SelectItem>
                      {additionalTraining.map((t) => (
                        <SelectItem key={t} value={t}>{t}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Expiry Date (optional)</Label>
                  <Input 
                    type="date" 
                    value={newRecord.expiry_date} 
                    onChange={(e) => setNewRecord({...newRecord, expiry_date: e.target.value})}
                    className="rounded-xl"
                    data-testid="training-expiry-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={newRecord.status} onValueChange={(value) => setNewRecord({...newRecord, status: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setAddOpen(false)} className="rounded-xl">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="training-submit">
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add Record'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{completed}</p>
              <p className="text-sm text-text-muted">Completed</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <ShieldCheck className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{verified}</p>
              <p className="text-sm text-text-muted">Verified</p>
            </div>
          </CardContent>
        </Card>
        <Card className={`border-[#E4E8EB] shadow-sm ${expiringSoon > 0 ? 'border-amber-200 bg-amber-50' : ''}`}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
              <CalendarClock className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-amber-700">{expiringSoon}</p>
              <p className="text-sm text-amber-600">Needs Renewal</p>
            </div>
          </CardContent>
        </Card>
        <Card className={`border-[#E4E8EB] shadow-sm ${expired > 0 ? 'border-red-200 bg-red-50' : ''}`}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-red-700">{expired}</p>
              <p className="text-sm text-red-600">Expired</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Filter className="h-4 w-4 text-text-muted" />
            <span className="text-sm text-text-muted">Filter:</span>
            <div className="flex flex-wrap gap-2">
              <Button 
                variant={filter === 'all' ? 'default' : 'outline'} 
                size="sm" 
                className="rounded-xl"
                onClick={() => setFilter('all')}
                data-testid="filter-all"
              >
                All Records
              </Button>
              <Button 
                variant={filter === 'expired' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'expired' ? 'bg-red-600 hover:bg-red-700' : 'text-red-600 border-red-200 hover:bg-red-50'}`}
                onClick={() => setFilter('expired')}
                data-testid="filter-expired"
              >
                Expired ({expired})
              </Button>
              <Button 
                variant={filter === 'expiring_soon' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'expiring_soon' ? 'bg-amber-600 hover:bg-amber-700' : 'text-amber-600 border-amber-200 hover:bg-amber-50'}`}
                onClick={() => setFilter('expiring_soon')}
                data-testid="filter-expiring"
              >
                Needs Renewal ({expiringSoon})
              </Button>
              <Button 
                variant={filter === 'valid' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'valid' ? 'bg-green-600 hover:bg-green-700' : 'text-green-600 border-green-200 hover:bg-green-50'}`}
                onClick={() => setFilter('valid')}
                data-testid="filter-valid"
              >
                Valid
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Training Records Table */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Training Records</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filteredTraining.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>{filter === 'all' ? 'No training records yet' : `No ${filter.replace('_', ' ')} training records`}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Training</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Expiry Date</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Renewal Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Verified</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm w-12">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTraining.map((record) => {
                    const expiryStatus = getExpiryStatus(record.expiry_date);
                    
                    return (
                      <tr key={record.id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA]" data-testid={`training-row-${record.id}`}>
                        <td className="p-4 font-medium text-text-primary">{getEmployeeName(record.employee_id)}</td>
                        <td className="p-4 text-text-primary">
                          <div>
                            {record.training_name}
                            {record.mandatory && (
                              <span className="ml-2 text-xs text-red-600 font-medium">Mandatory</span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            record.status === 'completed' ? 'bg-green-100 text-green-700' :
                            record.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {record.status?.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="p-4 text-text-muted text-sm">
                          {record.expiry_date ? new Date(record.expiry_date).toLocaleDateString() : '-'}
                        </td>
                        <td className="p-4">
                          {expiryStatus ? (
                            <div className="flex flex-col">
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium inline-block w-fit ${
                                expiryStatus.color === 'red' ? 'bg-red-100 text-red-700' :
                                expiryStatus.color === 'amber' ? 'bg-amber-100 text-amber-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {expiryStatus.label}
                              </span>
                              <span className="text-xs text-text-muted mt-1">{expiryStatus.daysText}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-text-muted">No expiry set</span>
                          )}
                        </td>
                        <td className="p-4">
                          {record.verified ? (
                            <div className="flex items-center gap-1">
                              <ShieldCheck className="h-4 w-4 text-green-600" />
                              <span className="text-xs text-green-600">Yes</span>
                            </div>
                          ) : (
                            <span className="text-xs text-text-muted">No</span>
                          )}
                        </td>
                        <td className="p-4">
                          {!isAuditor() && (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" data-testid={`training-actions-${record.id}`}>
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => openEditModal(record, 'expiry_date')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Expiry Date
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openEditModal(record, 'completion_date')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Completion Date
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openEditModal(record, 'status')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Status
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleViewHistory(record)}>
                                  <History className="mr-2 h-4 w-4" />
                                  View History
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit/Correction Modal */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Training Record</DialogTitle>
            <DialogDescription>
              Make a correction to this training record. All changes require a reason and are logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          {editingRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{editingRecord.training_name}</p>
                <p className="text-sm text-text-muted">{getEmployeeName(editingRecord.employee_id)}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Field to Edit</Label>
                <Select value={correction.field} onValueChange={(value) => setCorrection({...correction, field: value, new_value: editingRecord[value] || ''})}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expiry_date">Expiry Date</SelectItem>
                    <SelectItem value="completion_date">Completion Date</SelectItem>
                    <SelectItem value="status">Status</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Current Value</Label>
                <Input 
                  value={editingRecord[correction.field] || '(not set)'} 
                  disabled 
                  className="rounded-xl bg-gray-100"
                />
              </div>
              
              <div className="space-y-2">
                <Label>New Value *</Label>
                {correction.field === 'status' ? (
                  <Select value={correction.new_value} onValueChange={(value) => setCorrection({...correction, new_value: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="correction-new-value">
                      <SelectValue placeholder="Select new status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="renewal_due">Renewal Due</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input 
                    type="date" 
                    value={correction.new_value?.split('T')[0] || ''} 
                    onChange={(e) => setCorrection({...correction, new_value: e.target.value})}
                    className="rounded-xl"
                    data-testid="correction-new-value"
                  />
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Textarea 
                  placeholder="Explain why this correction is being made (required for audit trail)"
                  value={correction.reason}
                  onChange={(e) => setCorrection({...correction, reason: e.target.value})}
                  className="rounded-xl min-h-[80px]"
                  data-testid="correction-reason"
                />
                <p className="text-xs text-text-muted">This will be permanently recorded in the audit log</p>
              </div>
              
              {editingRecord.verified && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-700">
                    <AlertTriangle className="h-4 w-4 inline mr-2" />
                    This record has been verified. Corrections will be flagged in the audit log.
                  </p>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleCorrection} 
              disabled={isSubmitting || !correction.reason || !correction.new_value}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="correction-submit"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Correction'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Training Record History</DialogTitle>
          </DialogHeader>
          {historyRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{historyRecord.training_name}</p>
                <p className="text-sm text-text-muted">{getEmployeeName(historyRecord.employee_id)}</p>
              </div>
              
              {historyLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : historyData.length === 0 ? (
                <div className="text-center py-8 text-text-muted">
                  <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No correction history</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {historyData.map((entry, idx) => (
                    <div key={entry.id || idx} className="p-3 bg-white rounded-lg border border-[#E4E8EB]">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-text-primary">
                            {entry.action === 'training_correction' ? 'Correction' : entry.action?.replace('_', ' ')}
                          </p>
                          {entry.field_changed && (
                            <p className="text-sm text-text-muted">
                              <span className="font-medium">{entry.field_changed}</span>: {entry.old_value || '(empty)'} → {entry.new_value}
                            </p>
                          )}
                          {entry.reason && (
                            <p className="text-sm text-text-muted mt-1">
                              <span className="font-medium">Reason:</span> {entry.reason}
                            </p>
                          )}
                          {entry.was_verified_before_correction && (
                            <span className="inline-block mt-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">
                              Corrected after verification
                            </span>
                          )}
                        </div>
                        <div className="text-right text-xs text-text-muted">
                          <p>{entry.changed_by_name || 'System'}</p>
                          <p>{entry.created_at ? new Date(entry.created_at).toLocaleString() : ''}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
