import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Shield, Search, AlertTriangle, CheckCircle, Clock, 
  FileText, Users, Calendar, RefreshCw, ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function DBSRegisterPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [register, setRegister] = useState([]);
  const [stats, setStats] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showNeedsAttention, setShowNeedsAttention] = useState(false);

  const token = localStorage.getItem('token');

  const fetchDBSRegister = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all') {
        params.append('status_filter', statusFilter);
      }
      if (showNeedsAttention) {
        params.append('needs_attention', 'true');
      }
      
      const res = await axios.get(`${API}/dbs-register?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRegister(res.data.register || []);
      setStats(res.data.stats || {});
    } catch (error) {
      toast.error('Failed to load DBS register');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDBSRegister();
  }, [statusFilter, showNeedsAttention]);

  // Filter by search term (client-side for responsiveness)
  const filteredRegister = register.filter(item => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      item.employee_name.toLowerCase().includes(search) ||
      item.role?.toLowerCase().includes(search) ||
      item.email?.toLowerCase().includes(search)
    );
  });

  const getStatusBadge = (item) => {
    const statusStyles = {
      current: 'bg-green-100 text-green-800 border-green-200',
      certificate_only: 'bg-amber-100 text-amber-800 border-amber-200',
      pending_verification: 'bg-blue-100 text-blue-800 border-blue-200',
      review_due_soon: 'bg-amber-100 text-amber-800 border-amber-200',
      review_overdue: 'bg-red-100 text-red-800 border-red-200',
      missing: 'bg-red-100 text-red-800 border-red-200'
    };

    return (
      <Badge className={`${statusStyles[item.dbs_status] || 'bg-gray-100 text-gray-800'} border`}>
        {item.dbs_status_label}
      </Badge>
    );
  };

  // HARDENING: Use shared date utility
  const formatDate = (dateStr) => {
    return formatBackendDate(dateStr, { fallback: '-' });
  };

  return (
    <div className="space-y-6" data-testid="dbs-register-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary flex items-center gap-2">
            <Shield className="h-7 w-7 text-primary" />
            DBS Register
          </h1>
          <p className="text-text-muted mt-1">
            Track DBS status, last checks, and upcoming review dates for all staff.
          </p>
        </div>
        <Button 
          variant="outline" 
          onClick={fetchDBSRegister}
          className="rounded-xl"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <Card className="border-[#E4E8EB]">
          <CardContent className="p-3 text-center">
            <Users className="h-5 w-5 mx-auto text-text-muted mb-1" />
            <p className="text-2xl font-bold text-text-primary">{stats.total || 0}</p>
            <p className="text-xs text-text-muted">Total Staff</p>
          </CardContent>
        </Card>
        <Card className="border-green-200 bg-green-50">
          <CardContent className="p-3 text-center">
            <CheckCircle className="h-5 w-5 mx-auto text-green-600 mb-1" />
            <p className="text-2xl font-bold text-green-700">{stats.current || 0}</p>
            <p className="text-xs text-green-600">Current</p>
          </CardContent>
        </Card>
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-3 text-center">
            <FileText className="h-5 w-5 mx-auto text-amber-600 mb-1" />
            <p className="text-2xl font-bold text-amber-700">{stats.certificate_only || 0}</p>
            <p className="text-xs text-amber-600">Cert Only</p>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="p-3 text-center">
            <Clock className="h-5 w-5 mx-auto text-blue-600 mb-1" />
            <p className="text-2xl font-bold text-blue-700">{stats.pending_verification || 0}</p>
            <p className="text-xs text-blue-600">Pending</p>
          </CardContent>
        </Card>
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-3 text-center">
            <AlertTriangle className="h-5 w-5 mx-auto text-amber-600 mb-1" />
            <p className="text-2xl font-bold text-amber-700">{stats.review_due_soon || 0}</p>
            <p className="text-xs text-amber-600">Due Soon</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-3 text-center">
            <AlertTriangle className="h-5 w-5 mx-auto text-red-600 mb-1" />
            <p className="text-2xl font-bold text-red-700">{stats.review_overdue || 0}</p>
            <p className="text-xs text-red-600">Overdue</p>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-3 text-center">
            <Shield className="h-5 w-5 mx-auto text-red-600 mb-1" />
            <p className="text-2xl font-bold text-red-700">{stats.missing || 0}</p>
            <p className="text-xs text-red-600">Missing</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-[#E4E8EB]">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <Input
                placeholder="Search by name, role, or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 rounded-xl"
                data-testid="dbs-search"
              />
            </div>
            
            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48 rounded-xl" data-testid="dbs-status-filter">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="current">Current & Verified</SelectItem>
                <SelectItem value="certificate_only">Certificate Only (Needs Verification)</SelectItem>
                <SelectItem value="pending_verification">Awaiting Verification</SelectItem>
                <SelectItem value="review_due_soon">Review Due Soon</SelectItem>
                <SelectItem value="review_overdue">Review Overdue</SelectItem>
                <SelectItem value="missing">Missing</SelectItem>
              </SelectContent>
            </Select>
            
            {/* Needs Attention Toggle */}
            <Button
              variant={showNeedsAttention ? 'default' : 'outline'}
              onClick={() => setShowNeedsAttention(!showNeedsAttention)}
              className="rounded-xl whitespace-nowrap"
              data-testid="needs-attention-filter"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Needs Attention ({stats.needs_attention || 0})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Register Table */}
      <Card className="border-[#E4E8EB]">
        <CardHeader className="border-b border-[#E4E8EB]">
          <CardTitle className="text-lg">Staff DBS Records</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : filteredRegister.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <Shield className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No staff found matching your criteria</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="dbs-register-table">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-gray-50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Employee</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Role</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">DBS Status</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Last DBS Check</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Next Review Due</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Details</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E4E8EB]">
                  {filteredRegister.map((item) => (
                    <tr 
                      key={item.employee_id} 
                      className={`hover:bg-gray-50 ${item.needs_attention ? 'bg-red-50/30' : ''}`}
                      data-testid={`dbs-row-${item.employee_id}`}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">{item.employee_name}</p>
                        <p className="text-xs text-text-muted">{item.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-text-primary">{item.role || '-'}</span>
                      </td>
                      <td className="px-4 py-3">
                        {getStatusBadge(item)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-text-primary">
                          {formatDate(item.last_dbs_check_date)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className={`text-sm ${
                            item.days_until_review != null && item.days_until_review < 0 ? 'text-red-600 font-medium' :
                            item.days_until_review != null && item.days_until_review <= 30 ? 'text-amber-600 font-medium' :
                            'text-text-primary'
                          }`}>
                            {item.next_dbs_review_due ? formatDate(item.next_dbs_review_due) : 'Not set'}
                          </span>
                          {item.days_until_review != null && item.days_until_review !== undefined && (
                            <span className={`text-xs ${
                              item.days_until_review < 0 ? 'text-red-500' :
                              item.days_until_review <= 30 ? 'text-amber-500' :
                              'text-text-muted'
                            }`}>
                              {item.days_until_review < 0 
                                ? `${Math.abs(item.days_until_review)} days overdue`
                                : `${item.days_until_review} days left`
                              }
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {item.certificate_on_file && (
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              item.certificate_verified ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                            }`}>
                              Cert {item.certificate_verified ? '✓' : ''}
                            </span>
                          )}
                          {item.update_service_active && (
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              item.update_service_verified ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                            }`}>
                              Update Svc {item.update_service_verified ? '✓' : ''}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => navigate(`/portal/employees/${item.employee_id}`)}
                          className="rounded-lg"
                          data-testid={`view-employee-${item.employee_id}`}
                        >
                          View
                          <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
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
