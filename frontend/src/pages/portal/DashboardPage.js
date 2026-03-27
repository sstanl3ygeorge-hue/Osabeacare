import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import {
  Users, UserPlus, Clock, AlertTriangle, FileX, ShieldAlert,
  FileCheck, CalendarClock, ArrowRight, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState([]);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, employeesRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees?limit=5`, { headers: { Authorization: `Bearer ${token}` } })
        ]);
        setStats(statsRes.data);
        setEmployees(employeesRes.data.slice(0, 5));
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const statCards = [
    { label: 'Total Employees', value: stats?.total_employees || 0, icon: Users, color: 'bg-primary' },
    { label: 'Applicants', value: stats?.total_applicants || 0, icon: UserPlus, color: 'bg-secondary' },
    { label: 'Onboarding', value: stats?.onboarding_in_progress || 0, icon: Clock, color: 'bg-info' },
    { label: 'Missing Documents', value: stats?.missing_urgent_documents || 0, icon: FileX, color: 'bg-warning', alert: true },
    { label: 'Unsigned Policies', value: stats?.unsigned_policies || 0, icon: FileCheck, color: 'bg-error', alert: true },
    { label: 'DBS Pending', value: stats?.dbs_pending || 0, icon: ShieldAlert, color: 'bg-warning' },
    { label: 'RTW Missing', value: stats?.rtw_missing || 0, icon: AlertTriangle, color: 'bg-error' },
    { label: 'Expiring (30 days)', value: stats?.expiring_30_days || 0, icon: CalendarClock, color: 'bg-warning' },
  ];

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
          Compliance Dashboard
        </h1>
        <p className="text-text-muted mt-1">Overview of employee compliance status</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, idx) => (
          <Card key={idx} className="border-[#E4E8EB] shadow-sm" data-testid={`stat-card-${idx}`}>
            <CardContent className="p-4 lg:p-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-text-muted">{stat.label}</p>
                  <p className={`text-2xl lg:text-3xl font-heading font-bold mt-1 ${stat.alert && stat.value > 0 ? 'text-warning' : 'text-text-primary'}`}>
                    {stat.value}
                  </p>
                </div>
                <div className={`w-10 h-10 ${stat.color} rounded-xl flex items-center justify-center`}>
                  <stat.icon className="h-5 w-5 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions & Recent Employees */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to="/portal/employees" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-add-employee">
                <UserPlus className="mr-2 h-4 w-4" />
                Add New Employee
              </Button>
            </Link>
            <Link to="/portal/documents" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-documents">
                <FileCheck className="mr-2 h-4 w-4" />
                Review Documents
              </Button>
            </Link>
            <Link to="/portal/compliance-centre" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-compliance">
                <FileCheck className="mr-2 h-4 w-4" />
                Compliance Centre
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Employees */}
        <Card className="lg:col-span-2 border-[#E4E8EB] shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-lg">Recent Employees</CardTitle>
            <Link to="/portal/employees">
              <Button variant="ghost" size="sm" className="text-primary" data-testid="view-all-employees">
                View all
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {employees.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No employees yet</p>
                <Link to="/portal/employees">
                  <Button className="mt-4 bg-primary hover:bg-primary-hover text-white rounded-xl">
                    Add your first employee
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {employees.map((emp) => (
                  <Link
                    key={emp.id}
                    to={`/portal/employees/${emp.id}`}
                    className="flex items-center justify-between p-3 rounded-xl hover:bg-[#F8FAFA] transition-colors"
                    data-testid={`employee-row-${emp.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
                        <span className="text-primary font-medium">
                          {emp.first_name?.charAt(0)}{emp.last_name?.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                        <p className="text-sm text-text-muted">{emp.employee_code} · {emp.role}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right hidden sm:block">
                        <p className="text-sm font-medium text-text-primary">{emp.completion_percentage}%</p>
                        <p className="text-xs text-text-muted">Complete</p>
                      </div>
                      <span className={`status-chip ${
                        emp.status === 'active' ? 'status-success' :
                        emp.status === 'onboarding' ? 'status-info' :
                        'status-neutral'
                      }`}>
                        {emp.status}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      {(stats?.missing_urgent_documents > 0 || stats?.unsigned_policies > 0 || stats?.expiring_30_days > 0) && (
        <Card className="border-warning/30 bg-warning/5 shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2 text-warning">
              <AlertTriangle className="h-5 w-5" />
              Items Requiring Attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-3 gap-4">
              {stats?.missing_urgent_documents > 0 && (
                <div className="p-4 bg-white rounded-xl border border-[#E4E8EB]">
                  <p className="font-medium text-text-primary">{stats.missing_urgent_documents} missing documents</p>
                  <p className="text-sm text-text-muted">Require immediate action</p>
                </div>
              )}
              {stats?.unsigned_policies > 0 && (
                <div className="p-4 bg-white rounded-xl border border-[#E4E8EB]">
                  <p className="font-medium text-text-primary">{stats.unsigned_policies} unsigned policies</p>
                  <p className="text-sm text-text-muted">Awaiting acknowledgement</p>
                </div>
              )}
              {stats?.expiring_30_days > 0 && (
                <div className="p-4 bg-white rounded-xl border border-[#E4E8EB]">
                  <p className="font-medium text-text-primary">{stats.expiring_30_days} expiring soon</p>
                  <p className="text-sm text-text-muted">Within next 30 days</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
