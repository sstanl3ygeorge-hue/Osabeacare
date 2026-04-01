import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Checkbox } from '../ui/checkbox';
import { Input } from '../ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  GraduationCap,
  Loader2,
  Clock,
  Shield,
  Upload,
  Eye,
  FileText,
  Calendar,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Filter,
  Search
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { formatBackendDate } from '../../lib/dateUtils';

const API = process.env.REACT_APP_BACKEND_URL;

// Status styling
const STATUS_STYLES = {
  current: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: CheckCircle2, label: 'Current' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: CheckCircle2, label: 'Completed' },
  expiring_soon: { bg: 'bg-amber-50', text: 'text-amber-700', icon: Clock, label: 'Renew Soon' },
  due_soon: { bg: 'bg-amber-50', text: 'text-amber-700', icon: Clock, label: 'Due Soon' },
  expired: { bg: 'bg-red-50', text: 'text-red-700', icon: AlertTriangle, label: 'Expired' },
  overdue: { bg: 'bg-red-50', text: 'text-red-700', icon: AlertTriangle, label: 'Overdue' },
  missing: { bg: 'bg-gray-100', text: 'text-gray-600', icon: XCircle, label: 'Missing' },
  pending: { bg: 'bg-blue-50', text: 'text-blue-700', icon: Clock, label: 'Pending' },
};

/**
 * TrainingMatrix - Comprehensive training requirements grid
 * 
 * Shows:
 * - All required training for the employee's role
 * - Current status of each training item
 * - Completion dates and expiry dates
 * - Work-blocking indicators
 * - Quick actions (upload cert, view evidence)
 */
export default function TrainingMatrix({
  employeeId,
  employeeName,
  role,
  onUploadCertificate,
  onViewCertificate,
  onRefresh
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [trainingData, setTrainingData] = useState(null);
  const [expandedRows, setExpandedRows] = useState({});
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showBlockersOnly, setShowBlockersOnly] = useState(false);
  
  // Fetch training matrix data
  const fetchTrainingMatrix = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/api/employees/${employeeId}/training/matrix`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTrainingData(response.data);
    } catch (err) {
      console.error('Error fetching training matrix:', err);
      // Fallback to training evaluation endpoint
      try {
        const evalResponse = await axios.get(
          `${API}/api/employees/${employeeId}/training`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setTrainingData({
          items: evalResponse.data.items || [],
          summary: {
            total: evalResponse.data.items?.length || 0,
            current: evalResponse.data.items?.filter(i => i.status === 'current').length || 0,
            expiring: evalResponse.data.items?.filter(i => i.status === 'expiring_soon' || i.status === 'due_soon').length || 0,
            missing: evalResponse.data.items?.filter(i => i.status === 'missing').length || 0,
            blockers: evalResponse.data.blockerCount || 0
          },
          overall: evalResponse.data.overall
        });
      } catch (fallbackErr) {
        toast.error('Failed to load training matrix');
      }
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    fetchTrainingMatrix();
  }, [fetchTrainingMatrix]);
  
  // Toggle row expansion
  const toggleRow = (code) => {
    setExpandedRows(prev => ({
      ...prev,
      [code]: !prev[code]
    }));
  };
  
  // Filter items
  const filteredItems = trainingData?.items?.filter(item => {
    // Status filter
    if (filterStatus !== 'all') {
      if (filterStatus === 'action_needed' && !['missing', 'expired', 'overdue', 'expiring_soon', 'due_soon'].includes(item.status)) {
        return false;
      } else if (filterStatus !== 'action_needed' && item.status !== filterStatus) {
        return false;
      }
    }
    
    // Blockers only
    if (showBlockersOnly && !item.blocker) {
      return false;
    }
    
    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return item.title?.toLowerCase().includes(query) || 
             item.code?.toLowerCase().includes(query);
    }
    
    return true;
  }) || [];
  
  // Calculate progress
  const progressPercent = trainingData?.summary?.total > 0
    ? Math.round((trainingData.summary.current / trainingData.summary.total) * 100)
    : 0;
  
  if (loading) {
    return (
      <Card className="border-dashed" data-testid="training-matrix-loading">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-gray-500">Loading training matrix...</span>
        </CardContent>
      </Card>
    );
  }
  
  if (!trainingData) {
    return (
      <Card data-testid="training-matrix-empty">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <GraduationCap className="h-12 w-12 text-gray-300 mb-4" />
          <p className="text-gray-500">No training requirements found</p>
          <p className="text-sm text-gray-400 mt-1">Training requirements will appear based on the employee's role</p>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card data-testid="training-matrix">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              Training Matrix
            </CardTitle>
            <CardDescription>
              {role ? `Required training for ${role}` : 'Employee training requirements'}
            </CardDescription>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              fetchTrainingMatrix();
              onRefresh?.();
            }}
            data-testid="refresh-training-matrix-btn"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-gray-900">{trainingData.summary?.total || 0}</p>
            <p className="text-xs text-gray-500">Total Required</p>
          </div>
          <div className="p-3 bg-emerald-50 rounded-lg">
            <p className="text-2xl font-bold text-emerald-700">{trainingData.summary?.current || 0}</p>
            <p className="text-xs text-emerald-600">Current</p>
          </div>
          <div className="p-3 bg-amber-50 rounded-lg">
            <p className="text-2xl font-bold text-amber-700">{trainingData.summary?.expiring || 0}</p>
            <p className="text-xs text-amber-600">Needs Renewal</p>
          </div>
          <div className="p-3 bg-red-50 rounded-lg">
            <p className="text-2xl font-bold text-red-700">{trainingData.summary?.missing || 0}</p>
            <p className="text-xs text-red-600">Missing</p>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">Completion Progress</span>
            <span className="text-sm font-medium">{progressPercent}%</span>
          </div>
          <Progress 
            value={progressPercent}
            className={cn(
              "h-2",
              progressPercent >= 80 ? "[&>div]:bg-emerald-500" :
              progressPercent >= 50 ? "[&>div]:bg-amber-500" :
              "[&>div]:bg-red-500"
            )}
          />
        </div>
        
        {/* Blockers Warning */}
        {trainingData.summary?.blockers > 0 && (
          <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <div>
              <p className="text-sm font-medium text-red-800">
                {trainingData.summary.blockers} work-blocking training item{trainingData.summary.blockers !== 1 ? 's' : ''} need attention
              </p>
              <p className="text-xs text-red-600">
                These must be completed before the employee can work
              </p>
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="pt-4">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search training..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              data-testid="training-matrix-search"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="h-10 px-3 rounded-md border border-input bg-background text-sm"
              data-testid="training-matrix-filter"
            >
              <option value="all">All Status</option>
              <option value="action_needed">Action Needed</option>
              <option value="current">Current</option>
              <option value="expiring_soon">Expiring Soon</option>
              <option value="missing">Missing</option>
              <option value="expired">Expired</option>
            </select>
            
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox
                checked={showBlockersOnly}
                onCheckedChange={setShowBlockersOnly}
                data-testid="blockers-only-checkbox"
              />
              <span className="text-gray-600">Blockers only</span>
            </label>
          </div>
        </div>
        
        {/* Training Matrix Table */}
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-50">
                <TableHead className="w-8"></TableHead>
                <TableHead>Training</TableHead>
                <TableHead className="text-center">Status</TableHead>
                <TableHead className="text-center hidden md:table-cell">Completed</TableHead>
                <TableHead className="text-center hidden md:table-cell">Expires</TableHead>
                <TableHead className="text-center">Evidence</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    No training items match your filters
                  </TableCell>
                </TableRow>
              ) : (
                filteredItems.map((item) => {
                  const statusStyle = STATUS_STYLES[item.status] || STATUS_STYLES.missing;
                  const StatusIcon = statusStyle.icon;
                  const isExpanded = expandedRows[item.code];
                  
                  return (
                    <>
                      <TableRow 
                        key={item.code}
                        className={cn(
                          "hover:bg-gray-50 transition-colors",
                          item.blocker && item.status !== 'current' && "bg-red-50/30"
                        )}
                        data-testid={`training-row-${item.code}`}
                      >
                        <TableCell className="w-8">
                          <button
                            onClick={() => toggleRow(item.code)}
                            className="p-1 hover:bg-gray-100 rounded"
                          >
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4 text-gray-400" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-gray-400" />
                            )}
                          </button>
                        </TableCell>
                        
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{item.title}</span>
                            {item.blocker && (
                              <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
                                Blocker
                              </Badge>
                            )}
                            {item.evidence_required && !item.verified && (
                              <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
                                Evidence Required
                              </Badge>
                            )}
                          </div>
                          {item.detail && item.status !== 'current' && (
                            <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                          )}
                        </TableCell>
                        
                        <TableCell className="text-center">
                          <Badge 
                            variant="outline"
                            className={cn("text-xs", statusStyle.bg, statusStyle.text)}
                          >
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {statusStyle.label}
                          </Badge>
                        </TableCell>
                        
                        <TableCell className="text-center hidden md:table-cell">
                          {item.completed_at ? (
                            <span className="text-sm text-gray-600">
                              {formatBackendDate(item.completed_at, { format: 'short' })}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </TableCell>
                        
                        <TableCell className="text-center hidden md:table-cell">
                          {item.expires_at ? (
                            <span className={cn(
                              "text-sm",
                              item.status === 'expired' ? "text-red-600 font-medium" :
                              item.status === 'expiring_soon' ? "text-amber-600" :
                              "text-gray-600"
                            )}>
                              {formatBackendDate(item.expires_at, { format: 'short' })}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </TableCell>
                        
                        <TableCell className="text-center">
                          {item.verified ? (
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                              <Shield className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                          ) : item.has_evidence ? (
                            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                              <FileText className="h-3 w-3 mr-1" />
                              Uploaded
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-100 text-gray-500">
                              None
                            </Badge>
                          )}
                        </TableCell>
                        
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {item.has_evidence && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0"
                                onClick={() => onViewCertificate?.(item.record_id, item.code)}
                                title="View Certificate"
                                data-testid={`view-cert-${item.code}`}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}
                            
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 p-0 text-primary"
                              onClick={() => onUploadCertificate?.(item.code, item.title)}
                              title="Upload Certificate"
                              data-testid={`upload-cert-${item.code}`}
                            >
                              <Upload className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                      
                      {/* Expanded Details Row */}
                      {isExpanded && (
                        <TableRow className="bg-gray-50/50">
                          <TableCell colSpan={7} className="py-3 px-6">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <p className="text-gray-500 text-xs">Training Code</p>
                                <p className="font-mono text-gray-700">{item.code}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 text-xs">Provider</p>
                                <p className="text-gray-700">{item.provider || '—'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 text-xs">Validity Period</p>
                                <p className="text-gray-700">{item.validity_days ? `${item.validity_days} days` : 'Lifetime'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 text-xs">Work Blocking</p>
                                <p className={cn(
                                  "font-medium",
                                  item.blocker ? "text-red-600" : "text-gray-600"
                                )}>
                                  {item.blocker ? 'Yes - Required' : 'No'}
                                </p>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
