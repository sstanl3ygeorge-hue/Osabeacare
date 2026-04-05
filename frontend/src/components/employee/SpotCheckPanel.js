import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Checkbox } from '../ui/checkbox';
import { formatBackendDate } from '../../lib/dateUtils';
import { 
  ClipboardCheck, Plus, Loader2, RefreshCw, AlertCircle, 
  CheckCircle, XCircle, Calendar, Eye, User, Download
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SPOT_CHECK_TYPES = [
  { value: 'observation', label: 'Direct Observation' },
  { value: 'document_review', label: 'Document Review' },
  { value: 'competency_check', label: 'Competency Check' },
  { value: 'medication_check', label: 'Medication Check' }
];

const SPOT_CHECK_AREAS = [
  { value: 'moving_handling', label: 'Moving & Handling' },
  { value: 'medication', label: 'Medication Administration' },
  { value: 'record_keeping', label: 'Record Keeping' },
  { value: 'communication', label: 'Communication' },
  { value: 'infection_control', label: 'Infection Control' },
  { value: 'dignity_respect', label: 'Dignity & Respect' },
  { value: 'safeguarding', label: 'Safeguarding' }
];

export default function SpotCheckPanel({ employeeId, employeeName, isAuditor = false, onRefresh }) {
  const [spotChecks, setSpotChecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    type: '',
    area: '',
    outcome: '',
    notes: '',
    follow_up_required: false,
    follow_up_date: ''
  });

  const fetchSpotChecks = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/spot-checks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSpotChecks(response.data.spot_checks || []);
    } catch (error) {
      console.error('Failed to fetch spot checks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchSpotChecks();
    }
  }, [employeeId]);

  const resetForm = () => {
    setFormData({
      type: '',
      area: '',
      outcome: '',
      notes: '',
      follow_up_required: false,
      follow_up_date: ''
    });
  };

  const handleSubmit = async () => {
    if (!formData.type || !formData.area || !formData.outcome) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/spot-checks`,
        { 
          ...formData, 
          employee_name: employeeName,
          follow_up_date: formData.follow_up_required ? formData.follow_up_date : null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Spot check recorded successfully');
      setShowDialog(false);
      resetForm();
      fetchSpotChecks();
      if (onRefresh) onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record spot check');
    } finally {
      setSubmitting(false);
    }
  };

  const [downloading, setDownloading] = useState(null);

  const handleDownloadPDF = async (checkId) => {
    try {
      setDownloading(checkId);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API}/employees/${employeeId}/spot-checks/${checkId}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `spot_check_${employeeName?.replace(/\s+/g, '_') || 'employee'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Spot check PDF downloaded');
    } catch (error) {
      console.error('PDF download failed:', error);
      toast.error('Failed to download PDF');
    } finally {
      setDownloading(null);
    }
  };

  const getOutcomeBadge = (outcome) => {
    switch(outcome) {
      case 'pass':
        return (
          <Badge className="bg-green-100 text-green-700">
            <CheckCircle className="h-3 w-3 mr-1" />
            Pass
          </Badge>
        );
      case 'needs_improvement':
        return (
          <Badge className="bg-amber-100 text-amber-700">
            <AlertCircle className="h-3 w-3 mr-1" />
            Needs Improvement
          </Badge>
        );
      case 'fail':
        return (
          <Badge className="bg-red-100 text-red-700">
            <XCircle className="h-3 w-3 mr-1" />
            Fail
          </Badge>
        );
      default:
        return <Badge variant="outline">{outcome}</Badge>;
    }
  };

  const getTypeLabel = (value) => SPOT_CHECK_TYPES.find(t => t.value === value)?.label || value;
  const getAreaLabel = (value) => SPOT_CHECK_AREAS.find(a => a.value === value)?.label || value;

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  // Calculate stats
  const passCount = spotChecks.filter(c => c.outcome === 'pass').length;
  const needsImprovementCount = spotChecks.filter(c => c.outcome === 'needs_improvement').length;
  const failCount = spotChecks.filter(c => c.outcome === 'fail').length;

  return (
    <>
      <Card className="border-[#E4E8EB] shadow-sm" data-testid="spot-check-panel">
        <CardHeader className="flex-row items-center justify-between flex-wrap gap-3">
          <div>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              Spot Checks
            </CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              CQC requires regular unannounced observations of work practice
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={fetchSpotChecks}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            {!isAuditor && (
              <Button 
                size="sm" 
                onClick={() => setShowDialog(true)} 
                className="gap-2"
                data-testid="record-spot-check-btn"
              >
                <Plus className="h-4 w-4" />
                Record Spot Check
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Summary Stats */}
          {spotChecks.length > 0 && (
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="p-3 bg-green-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-700">{passCount}</p>
                <p className="text-xs text-green-600">Passed</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-amber-700">{needsImprovementCount}</p>
                <p className="text-xs text-amber-600">Needs Work</p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-700">{failCount}</p>
                <p className="text-xs text-red-600">Failed</p>
              </div>
            </div>
          )}

          {spotChecks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <ClipboardCheck className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No spot checks recorded yet</p>
              <p className="text-xs mt-1">Record spot checks to demonstrate ongoing competency monitoring</p>
            </div>
          ) : (
            <div className="space-y-3">
              {spotChecks.map((check, idx) => (
                <div 
                  key={check.id || idx} 
                  className={`p-4 rounded-lg border ${
                    check.outcome === 'pass' ? 'bg-green-50/50 border-green-100' :
                    check.outcome === 'needs_improvement' ? 'bg-amber-50/50 border-amber-100' :
                    check.outcome === 'fail' ? 'bg-red-50/50 border-red-100' :
                    'bg-gray-50 border-gray-100'
                  }`}
                  data-testid={`spot-check-${idx}`}
                >
                  <div className="flex items-start justify-between flex-wrap gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-2">
                        <span className="font-medium text-gray-900">
                          {getTypeLabel(check.type)}
                        </span>
                        <span className="text-gray-400">-</span>
                        <span className="text-sm text-gray-600">
                          {getAreaLabel(check.area)}
                        </span>
                        {getOutcomeBadge(check.outcome)}
                      </div>
                      
                      {check.notes && (
                        <p className="text-sm text-gray-600 mt-1 bg-white/50 p-2 rounded">
                          {check.notes}
                        </p>
                      )}
                      
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {check.assessed_by_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatBackendDate(check.date)}
                        </span>
                        {check.follow_up_required && check.follow_up_date && (
                          <span className="text-amber-600 flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            Follow-up: {formatBackendDate(check.follow_up_date)}
                          </span>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownloadPDF(check.id)}
                      disabled={downloading === check.id}
                      className="rounded-lg shrink-0"
                      data-testid={`download-spot-check-${idx}`}
                    >
                      {downloading === check.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CQC Note */}
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <p className="text-xs text-blue-700">
              <strong>CQC Requirement:</strong> Spot checks should be conducted regularly (at least monthly) 
              to ensure care workers maintain competency and follow safe practices.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Add Spot Check Dialog */}
      <Dialog open={showDialog} onOpenChange={(open) => {
        if (!open) resetForm();
        setShowDialog(open);
      }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Record Spot Check</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Check Type <span className="text-red-500">*</span></Label>
              <Select 
                value={formData.type} 
                onValueChange={(v) => setFormData({...formData, type: v})}
              >
                <SelectTrigger data-testid="spot-check-type-select">
                  <SelectValue placeholder="Select type of check" />
                </SelectTrigger>
                <SelectContent>
                  {SPOT_CHECK_TYPES.map(t => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Area <span className="text-red-500">*</span></Label>
              <Select 
                value={formData.area} 
                onValueChange={(v) => setFormData({...formData, area: v})}
              >
                <SelectTrigger data-testid="spot-check-area-select">
                  <SelectValue placeholder="Select area assessed" />
                </SelectTrigger>
                <SelectContent>
                  {SPOT_CHECK_AREAS.map(a => (
                    <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Outcome <span className="text-red-500">*</span></Label>
              <Select 
                value={formData.outcome} 
                onValueChange={(v) => setFormData({...formData, outcome: v})}
              >
                <SelectTrigger data-testid="spot-check-outcome-select">
                  <SelectValue placeholder="Select outcome" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pass">
                    <span className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      Pass - Meets expected standards
                    </span>
                  </SelectItem>
                  <SelectItem value="needs_improvement">
                    <span className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-600" />
                      Needs Improvement - Minor issues identified
                    </span>
                  </SelectItem>
                  <SelectItem value="fail">
                    <span className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-600" />
                      Fail - Significant concerns
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Observations & Notes</Label>
              <Textarea
                rows={3}
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Describe what was observed, areas of concern, positive feedback..."
                data-testid="spot-check-notes-input"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="follow_up"
                checked={formData.follow_up_required}
                onCheckedChange={(checked) => setFormData({...formData, follow_up_required: checked})}
              />
              <Label htmlFor="follow_up" className="cursor-pointer">
                Follow-up required
              </Label>
            </div>

            {formData.follow_up_required && (
              <div>
                <Label>Follow-up Date</Label>
                <Input
                  type="date"
                  value={formData.follow_up_date}
                  onChange={(e) => setFormData({...formData, follow_up_date: e.target.value})}
                  data-testid="follow-up-date-input"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={submitting || !formData.type || !formData.area || !formData.outcome}
              data-testid="save-spot-check-btn"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Record Spot Check
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
