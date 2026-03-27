import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { toast } from 'sonner';
import { GraduationCap, Plus, CheckCircle, Clock, AlertTriangle, Loader2 } from 'lucide-react';

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

export default function TrainingPage() {
  const [training, setTraining] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { token, isAuditor } = useAuth();

  const [newRecord, setNewRecord] = useState({
    employee_id: '',
    training_name: '',
    mandatory: true,
    status: 'not_started'
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
      await axios.post(`${API}/training-records`, newRecord, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Training record added');
      setAddOpen(false);
      setNewRecord({ employee_id: '', training_name: '', mandatory: true, status: 'not_started' });
      fetchData();
    } catch (error) {
      toast.error('Failed to add training record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getEmployeeName = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId);
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  const completed = training.filter(t => t.status === 'completed').length;
  const inProgress = training.filter(t => t.status === 'in_progress').length;
  const overdue = training.filter(t => t.status === 'expired' || t.status === 'renewal_due').length;

  return (
    <div className="space-y-6" data-testid="training-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Training Matrix
          </h1>
          <p className="text-text-muted mt-1">Track employee training and certifications</p>
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
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-success/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{completed}</p>
              <p className="text-sm text-text-muted">Completed</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-info/10 rounded-xl flex items-center justify-center">
              <Clock className="h-6 w-6 text-info" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{inProgress}</p>
              <p className="text-sm text-text-muted">In Progress</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-warning/10 rounded-xl flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{overdue}</p>
              <p className="text-sm text-text-muted">Overdue/Renewal</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Training Records */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Training Records</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : training.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No training records yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Training</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden md:table-cell">Type</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden lg:table-cell">Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {training.map((record) => (
                    <tr key={record.id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA]">
                      <td className="p-4 font-medium text-text-primary">{getEmployeeName(record.employee_id)}</td>
                      <td className="p-4 text-text-primary">{record.training_name}</td>
                      <td className="p-4 hidden md:table-cell">
                        <span className={`text-sm ${record.mandatory ? 'text-error' : 'text-text-muted'}`}>
                          {record.mandatory ? 'Mandatory' : 'Optional'}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className={`status-chip ${
                          record.status === 'completed' ? 'status-success' :
                          record.status === 'in_progress' ? 'status-info' :
                          record.status === 'expired' ? 'status-error' :
                          'status-neutral'
                        }`}>
                          {record.status?.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-4 text-text-muted text-sm hidden lg:table-cell">
                        {record.completion_date ? new Date(record.completion_date).toLocaleDateString() : '-'}
                      </td>
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
