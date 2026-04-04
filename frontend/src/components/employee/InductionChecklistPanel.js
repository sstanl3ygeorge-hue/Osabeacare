import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  CheckCircle, Circle, Loader2, RefreshCw, FileText, 
  AlertTriangle, Clock, RotateCcw
} from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function InductionChecklistPanel({ employeeId, employeeName, isAuditor = false, onStatusChange }) {
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);

  const fetchChecklist = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/induction-checklist`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChecklist(response.data);
    } catch (error) {
      console.error('Failed to fetch induction checklist:', error);
      // Silently fail - may not have checklist yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchChecklist();
    }
  }, [employeeId]);

  const updateItem = async (itemName, newStatus) => {
    setUpdating(itemName);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.put(
        `${API}/employees/${employeeId}/induction-checklist`,
        { item_name: itemName, status: newStatus, notes: '' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${itemName} marked as ${newStatus}`);
      fetchChecklist();
      if (onStatusChange) {
        onStatusChange(response.data.overall_status);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update checklist');
    } finally {
      setUpdating(null);
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'completed') {
      return <Badge className="bg-green-100 text-green-700">Completed</Badge>;
    }
    return <Badge variant="outline" className="text-amber-600 border-amber-300">Pending</Badge>;
  };

  const getOverallStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-700">Completed</Badge>;
      case 'in_progress':
        return <Badge className="bg-blue-100 text-blue-700">In Progress</Badge>;
      default:
        return <Badge variant="outline" className="text-gray-500">Not Started</Badge>;
    }
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const items = checklist?.items || [];
  const completedCount = items.filter(i => i.status === 'completed').length;
  const mandatoryItems = items.filter(i => i.mandatory);
  const mandatoryCompleted = mandatoryItems.filter(i => i.status === 'completed').length;
  const overallStatus = checklist?.overall_status || 'pending';
  const progressPercent = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;

  return (
    <Card className="border-[#E4E8EB] shadow-sm" data-testid="induction-checklist-panel">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Induction Checklist
          </CardTitle>
          <div className="flex items-center gap-2">
            {getOverallStatusBadge(overallStatus)}
            <Button variant="ghost" size="sm" onClick={fetchChecklist} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Progress</span>
            <span className="font-medium">{completedCount}/{items.length} items ({progressPercent}%)</span>
          </div>
          <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 rounded-full ${
                overallStatus === 'completed' ? 'bg-green-500' : 
                overallStatus === 'in_progress' ? 'bg-blue-500' : 'bg-gray-300'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          
          {/* Mandatory Progress */}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-400" />
              Mandatory: {mandatoryCompleted}/{mandatoryItems.length}
            </span>
            {mandatoryCompleted < mandatoryItems.length && (
              <span className="text-amber-600 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {mandatoryItems.length - mandatoryCompleted} required items remaining
              </span>
            )}
          </div>
        </div>
        
        {overallStatus === 'completed' && checklist?.completed_at && (
          <p className="text-sm text-green-600 mt-3 flex items-center gap-1 bg-green-50 p-2 rounded-lg">
            <CheckCircle className="h-4 w-4" />
            Induction completed on {formatBackendDate(checklist.completed_at)}
          </p>
        )}
      </CardHeader>
      
      <CardContent>
        <div className="space-y-1">
          {items.map((item, idx) => (
            <div 
              key={idx}
              className={`flex items-center justify-between p-3 rounded-lg transition-colors ${
                item.status === 'completed' 
                  ? 'bg-green-50/50 border border-green-100' 
                  : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
              }`}
              data-testid={`induction-item-${idx}`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {/* Status Icon */}
                <div className={`flex-shrink-0 ${item.status === 'completed' ? 'text-green-600' : 'text-gray-300'}`}>
                  {item.status === 'completed' ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <Circle className="h-5 w-5" />
                  )}
                </div>
                
                {/* Item Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`font-medium ${item.status === 'completed' ? 'text-green-800' : 'text-gray-800'}`}>
                      {item.name}
                    </span>
                    {item.mandatory && (
                      <span className="text-[10px] text-red-600 bg-red-50 px-1.5 py-0.5 rounded font-medium">
                        REQUIRED
                      </span>
                    )}
                  </div>
                  {item.completed_at && (
                    <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatBackendDate(item.completed_at)}
                      {item.completed_by_name && <span>by {item.completed_by_name}</span>}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {!isAuditor && (
                  <>
                    {item.status !== 'completed' ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateItem(item.name, 'completed')}
                        disabled={updating === item.name}
                        className="h-8 px-3 text-xs rounded-lg hover:bg-green-50 hover:text-green-700 hover:border-green-300"
                        data-testid={`complete-item-${idx}`}
                      >
                        {updating === item.name ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <>
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Complete
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => updateItem(item.name, 'pending')}
                        disabled={updating === item.name}
                        className="h-8 px-2 text-xs text-gray-400 hover:text-gray-600"
                        title="Mark as pending"
                      >
                        {updating === item.name ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <RotateCcw className="h-3 w-3" />
                        )}
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {/* CQC Note */}
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
          <p className="text-xs text-blue-700">
            <strong>CQC Requirement:</strong> All mandatory induction items must be completed before an employee can work unsupervised. 
            Shadow shifts should be recorded as part of the induction process.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
