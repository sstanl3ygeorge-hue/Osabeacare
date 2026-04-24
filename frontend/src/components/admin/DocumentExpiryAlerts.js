import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { 
  FileText, AlertTriangle, Clock, ChevronRight, 
  Bell, Send, Loader2, RefreshCw, CheckCircle, Shield
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { format, parseISO, differenceInDays } from 'date-fns';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * DocumentExpiryAlerts - Dashboard component showing documents (DBS, RTW, Professional Registration) expiring soon
 */
export default function DocumentExpiryAlerts({ compact = false }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingReminders, setSendingReminders] = useState(false);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get(
        `${API}/api/admin/expiring-documents?days=30`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch document expiry alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAlerts();
  }, [token]);

  const handleSendAllReminders = async () => {
    setSendingReminders(true);
    try {
      const response = await axios.post(
        `${API}/api/admin/send-all-expiry-reminders`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(response.data.message || 'All expiry reminders sent successfully');
      fetchAlerts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reminders');
    } finally {
      setSendingReminders(false);
    }
  };

  if (loading) {
    return (
      <Card className="border border-slate-200">
        <CardContent className="py-8 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    );
  }

  if (!alerts || alerts.total_expiring === 0) {
    return compact ? null : (
      <Card className="border border-green-200 bg-green-50/50">
        <CardContent className="py-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <p className="font-medium text-green-800">All Documents Current</p>
            <p className="text-sm text-green-600">No document summary alerts in the next 30 days</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalExpiring = alerts.total_expiring || 0;
  const critical = alerts.critical || [];
  const warning = alerts.warning || [];
  const upcoming = alerts.upcoming || [];

  // Group by employee for display
  const groupByEmployee = (items) => {
    const grouped = {};
    items.forEach(item => {
      const key = item.employee_id;
      if (!grouped[key]) {
        grouped[key] = {
          employee_id: item.employee_id,
          employee_name: item.employee_name,
          documents: []
        };
      }
      grouped[key].documents.push(item);
    });
    return Object.values(grouped);
  };

  const formatDate = (dateStr) => {
    try {
      return format(parseISO(dateStr), 'dd MMM yyyy');
    } catch {
      return dateStr;
    }
  };

  const getDaysLeft = (dateStr) => {
    try {
      return differenceInDays(parseISO(dateStr), new Date());
    } catch {
      return 0;
    }
  };

  const getDocumentIcon = (docType) => {
    if (docType === 'dbs' || docType?.includes('dbs')) return <Shield className="h-4 w-4" />;
    if (docType === 'right_to_work' || docType?.includes('rtw')) return <FileText className="h-4 w-4" />;
    return <FileText className="h-4 w-4" />;
  };

  // Compact view for dashboard summary
  if (compact) {
    return (
      <div 
        onClick={() => navigate('/portal/compliance-centre?tab=documents')}
        className={cn(
          "p-4 rounded-xl transition-all cursor-pointer hover:shadow-md",
          critical.length > 0 ? "bg-red-100 border border-red-200" :
          warning.length > 0 ? "bg-amber-100 border border-amber-200" :
          "bg-blue-100 border border-blue-200"
        )}
        data-testid="document-expiry-compact"
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center",
            critical.length > 0 ? "bg-red-200" :
            warning.length > 0 ? "bg-amber-200" :
            "bg-blue-200"
          )}>
            <Shield className={cn(
              "h-5 w-5",
              critical.length > 0 ? "text-red-600" :
              warning.length > 0 ? "text-amber-600" :
              "text-blue-600"
            )} />
          </div>
          <div className="flex-1">
            <p className={cn(
              "text-2xl font-heading font-bold",
              critical.length > 0 ? "text-red-700" :
              warning.length > 0 ? "text-amber-700" :
              "text-blue-700"
            )}>
              {totalExpiring}
            </p>
            <p className={cn(
              "text-sm",
              critical.length > 0 ? "text-red-600" :
              warning.length > 0 ? "text-amber-600" :
              "text-blue-600"
            )}>
              Documents Expiring
            </p>
          </div>
          <ChevronRight className={cn(
            "h-4 w-4",
            critical.length > 0 ? "text-red-400" :
            warning.length > 0 ? "text-amber-400" :
            "text-blue-400"
          )} />
        </div>
        {critical.length > 0 && (
          <p className="text-xs text-red-500 mt-2">{critical.length} critical (under 7 days) - Open details</p>
        )}
      </div>
    );
  }

  // Full view
  return (
    <Card className="border-2 border-red-200 bg-red-50/30" data-testid="document-expiry-alerts">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
              <Shield className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                Document Summary Alerts
                <Badge className={cn(
                  "text-xs",
                  critical.length > 0 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                )}>
                  {totalExpiring} expiring
                </Badge>
              </CardTitle>
              <CardDescription>
                Summary view of DBS, Right to Work, and professional registrations expiring within 30 days
              </CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleSendAllReminders}
                    disabled={sendingReminders}
                  >
                    {sendingReminders ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    <span className="ml-1 hidden sm:inline">Send All Reminders</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  Send reminders from this summary view
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button variant="ghost" size="sm" onClick={fetchAlerts}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Critical (under 7 days) */}
        {critical.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <span className="text-sm font-semibold text-red-700">Critical - Under 7 Days ({critical.length})</span>
            </div>
            {groupByEmployee(critical).map((emp) => (
              <div 
                key={emp.employee_id}
                className="p-3 bg-red-100 border border-red-200 rounded-lg cursor-pointer hover:bg-red-150 transition-colors"
                onClick={() => navigate(`/portal/employees/${emp.employee_id}`)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-red-900">{emp.employee_name}</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {emp.documents.map((doc, idx) => (
                        <Badge key={idx} className="bg-red-200 text-red-800 text-xs flex items-center gap-1">
                          {getDocumentIcon(doc.document_type)}
                          {doc.document_name}
                          <span className="font-bold">({doc.days_until_expiry}d)</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-red-400" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Warning (7-14 days) */}
        {warning.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-600" />
              <span className="text-sm font-semibold text-amber-700">Warning - 7-14 Days ({warning.length})</span>
            </div>
            {groupByEmployee(warning).map((emp) => (
              <div 
                key={emp.employee_id}
                className="p-3 bg-amber-50 border border-amber-200 rounded-lg cursor-pointer hover:bg-amber-100 transition-colors"
                onClick={() => navigate(`/portal/employees/${emp.employee_id}`)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-amber-900">{emp.employee_name}</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {emp.documents.map((doc, idx) => (
                        <Badge key={idx} className="bg-amber-200 text-amber-800 text-xs flex items-center gap-1">
                          {getDocumentIcon(doc.document_type)}
                          {doc.document_name}
                          <span className="font-bold">({doc.days_until_expiry}d)</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-amber-400" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Upcoming (15-30 days) */}
        {upcoming.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-700">Upcoming - 15-30 Days ({upcoming.length})</span>
            </div>
            {groupByEmployee(upcoming).slice(0, 3).map((emp) => (
              <div 
                key={emp.employee_id}
                className="p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors"
                onClick={() => navigate(`/portal/employees/${emp.employee_id}`)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-blue-900">{emp.employee_name}</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {emp.documents.map((doc, idx) => (
                        <Badge key={idx} className="bg-blue-200 text-blue-800 text-xs flex items-center gap-1">
                          {getDocumentIcon(doc.document_type)}
                          {doc.document_name}
                          <span className="font-bold">({doc.days_until_expiry}d)</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-blue-400" />
                </div>
              </div>
            ))}
            {groupByEmployee(upcoming).length > 3 && (
              <p className="text-xs text-blue-600 text-center">
                + {groupByEmployee(upcoming).length - 3} more employees
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
