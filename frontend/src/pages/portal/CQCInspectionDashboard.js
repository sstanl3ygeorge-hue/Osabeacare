import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Users, 
  Shield, 
  Download,
  RefreshCw,
  ChevronRight,
  AlertCircle,
  XCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Risk level colors
const RISK_COLORS = {
  high: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', icon: XCircle },
  medium: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-300', icon: AlertCircle },
  low: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300', icon: CheckCircle2 }
};

const CQCInspectionDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [exporting, setExporting] = useState(false);
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/cqc/inspection-dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch CQC dashboard data:', error);
    }
    setLoading(false);
  };

  const exportPDF = async () => {
    setExporting(true);
    try {
      const response = await axios.get(`${API}/cqc/inspection-report/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `CQC_Inspection_Report_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to export PDF:', error);
    }
    setExporting(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="p-6 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
        <p className="text-gray-600">Unable to load CQC inspection data</p>
        <Button onClick={fetchDashboardData} className="mt-4">
          <RefreshCw className="w-4 h-4 mr-2" /> Retry
        </Button>
      </div>
    );
  }

  const { summary, cqc_domains, staff_breakdown, expiring_documents, training_gaps, risk_areas } = dashboardData;

  return (
    <div className="p-6 space-y-6" data-testid="cqc-inspection-dashboard">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CQC Inspection Dashboard</h1>
          <p className="text-gray-500 mt-1">Audit-ready compliance overview for CQC inspections</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchDashboardData}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button onClick={exportPDF} disabled={exporting}>
            <Download className="w-4 h-4 mr-2" />
            {exporting ? 'Exporting...' : 'Export PDF Report'}
          </Button>
        </div>
      </div>

      {/* Overall Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card data-testid="total-staff-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Staff</p>
                <p className="text-3xl font-bold">{summary?.total_staff || 0}</p>
              </div>
              <Users className="w-10 h-10 text-blue-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="work-ready-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Work Ready</p>
                <p className="text-3xl font-bold text-green-600">{summary?.work_ready || 0}</p>
                <p className="text-xs text-gray-400">{summary?.work_ready_percentage || 0}% of staff</p>
              </div>
              <CheckCircle2 className="w-10 h-10 text-green-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="pending-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">In Onboarding</p>
                <p className="text-3xl font-bold text-amber-600">{summary?.onboarding || 0}</p>
                <p className="text-xs text-gray-400">Pending compliance</p>
              </div>
              <Clock className="w-10 h-10 text-amber-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="critical-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Critical Issues</p>
                <p className="text-3xl font-bold text-red-600">{summary?.critical_issues || 0}</p>
                <p className="text-xs text-gray-400">Require immediate action</p>
              </div>
              <AlertTriangle className="w-10 h-10 text-red-500 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* CQC 5 Key Questions */}
      <Card data-testid="cqc-domains-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            CQC 5 Key Questions
          </CardTitle>
          <CardDescription>Assessment against CQC regulatory framework</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {cqc_domains?.map((domain) => {
              const riskStyle = RISK_COLORS[domain.risk_level] || RISK_COLORS.medium;
              const RiskIcon = riskStyle.icon;
              
              return (
                <div 
                  key={domain.name}
                  className={`p-4 rounded-lg border ${riskStyle.border} ${riskStyle.bg}`}
                  data-testid={`cqc-domain-${domain.name.toLowerCase()}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`font-semibold ${riskStyle.text}`}>{domain.name}</span>
                    <RiskIcon className={`w-5 h-5 ${riskStyle.text}`} />
                  </div>
                  <Progress value={domain.score} className="h-2 mb-2" />
                  <div className="flex justify-between text-sm">
                    <span className={riskStyle.text}>{domain.score}%</span>
                    <Badge variant={domain.risk_level === 'low' ? 'success' : domain.risk_level === 'high' ? 'destructive' : 'warning'}>
                      {domain.risk_level.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-xs mt-2 text-gray-600">{domain.summary}</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Staff Breakdown by Role */}
        <Card data-testid="staff-breakdown-card">
          <CardHeader>
            <CardTitle>Staff Compliance by Role</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {staff_breakdown?.map((role) => (
                <div key={role.role} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">{role.role}</p>
                    <p className="text-sm text-gray-500">{role.total} staff members</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm">
                        <span className="text-green-600 font-medium">{role.compliant}</span>
                        <span className="text-gray-400"> / {role.total}</span>
                      </p>
                      <p className="text-xs text-gray-500">compliant</p>
                    </div>
                    <div className="w-24">
                      <Progress value={(role.compliant / role.total) * 100} className="h-2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Risk Areas */}
        <Card data-testid="risk-areas-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Priority Risk Areas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {risk_areas?.map((area, idx) => {
                const riskStyle = RISK_COLORS[area.severity] || RISK_COLORS.medium;
                return (
                  <div 
                    key={idx} 
                    className={`p-3 rounded-lg border ${riskStyle.border} ${riskStyle.bg}`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className={`font-medium ${riskStyle.text}`}>{area.title}</p>
                        <p className="text-sm text-gray-600 mt-1">{area.description}</p>
                      </div>
                      <Badge variant={area.severity === 'high' ? 'destructive' : 'warning'}>
                        {area.affected_count} affected
                      </Badge>
                    </div>
                  </div>
                );
              })}
              {(!risk_areas || risk_areas.length === 0) && (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle2 className="w-12 h-12 mx-auto text-green-500 mb-2" />
                  <p>No critical risk areas identified</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Expiring Documents & Training Gaps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expiring Documents */}
        <Card data-testid="expiring-docs-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-500" />
              Expiring Documents (Next 30 Days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {expiring_documents?.map((doc, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <div>
                      <p className="font-medium text-sm">{doc.employee_name}</p>
                      <p className="text-xs text-gray-500">{doc.document_type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant={doc.days_until_expiry <= 7 ? 'destructive' : 'warning'}>
                      {doc.days_until_expiry} days
                    </Badge>
                  </div>
                </div>
              ))}
              {(!expiring_documents || expiring_documents.length === 0) && (
                <p className="text-center py-4 text-gray-500">No documents expiring soon</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Training Gaps */}
        <Card data-testid="training-gaps-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              Training Compliance Gaps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {training_gaps?.map((gap, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-red-800">{gap.training_name}</p>
                    <p className="text-sm text-red-600">
                      {gap.missing_count} staff missing this training
                    </p>
                  </div>
                  <Badge variant="destructive">{gap.compliance_rate}%</Badge>
                </div>
              ))}
              {(!training_gaps || training_gaps.length === 0) && (
                <div className="text-center py-4 text-gray-500">
                  <CheckCircle2 className="w-8 h-8 mx-auto text-green-500 mb-2" />
                  <p>All mandatory training up to date</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-400">
        Last updated: {new Date().toLocaleString()}
      </div>
    </div>
  );
};

export default CQCInspectionDashboard;
