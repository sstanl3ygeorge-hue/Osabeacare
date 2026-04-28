import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { 
  GraduationCap, AlertTriangle, Clock, ChevronRight, 
  Bell, Send, Loader2, RefreshCw, CheckCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { format, parseISO, differenceInDays } from 'date-fns';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_ROOT_URL;

/**
 * TrainingExpiryAlerts - Dashboard component showing training certificates expiring soon
 */
export default function TrainingExpiryAlerts({ compact = false }) {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingReminders, setSendingReminders] = useState(false);

  const fetchAlerts = async () => {
    try {
      const response = await axios.get(
        `${API}/api/admin/training-expiry-alerts?days=60`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch training expiry alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAlerts();
  }, [token]);

  const handleSendReminders = async () => {
    setSendingReminders(true);
    try {
      const response = await axios.post(
        `${API}/api/admin/training-expiry-reminders/send`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(response.data.message || 'Reminders sent successfully');
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
            <p className="font-medium text-green-800">All Training Current</p>
            <p className="text-sm text-green-600">No training summary alerts in the next 60 days</p>
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
          trainings: []
        };
      }
      grouped[key].trainings.push(item);
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

  if (compact) {
    // Compact view for dashboard cards
    return (
      <div 
        onClick={() => navigate('/portal/training?filter=expiring')}
        className={cn(
          "p-4 rounded-xl transition-all cursor-pointer hover:shadow-md",
          critical.length > 0 ? "bg-red-100 border border-red-200" :
          warning.length > 0 ? "bg-amber-100 border border-amber-200" :
          "bg-blue-100 border border-blue-200"
        )}
        data-testid="training-expiry-alert-card"
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center",
            critical.length > 0 ? "bg-red-200" :
            warning.length > 0 ? "bg-amber-200" :
            "bg-blue-200"
          )}>
            <GraduationCap className={cn(
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
              Training Expiring
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
          <p className="text-xs text-red-500 mt-2">{critical.length} critical (under 14 days) →</p>
        )}
      </div>
    );
  }

  // Full view
  return (
    <Card className="border-2 border-amber-200 bg-amber-50/30" data-testid="training-expiry-alerts">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                Training Summary Alerts
                <Badge className={cn(
                  "text-xs",
                  critical.length > 0 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                )}>
                  {totalExpiring} expiring
                </Badge>
              </CardTitle>
              <CardDescription>
                Summary view of training certificates expiring within 60 days
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
                    onClick={handleSendReminders}
                    disabled={sendingReminders}
                  >
                    {sendingReminders ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-1" />
                        Send Reminders
                      </>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                      <p>Send reminders from this summary view</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button variant="ghost" size="sm" onClick={fetchAlerts}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className={cn(
            "p-3 rounded-lg text-center",
            critical.length > 0 ? "bg-red-100 border border-red-200" : "bg-gray-50 border border-gray-200"
          )}>
            <p className={cn(
              "text-2xl font-bold",
              critical.length > 0 ? "text-red-700" : "text-gray-400"
            )}>
              {critical.length}
            </p>
            <p className={cn(
              "text-xs",
              critical.length > 0 ? "text-red-600" : "text-gray-500"
            )}>
              Critical (&lt;14 days)
            </p>
          </div>
          <div className={cn(
            "p-3 rounded-lg text-center",
            warning.length > 0 ? "bg-amber-100 border border-amber-200" : "bg-gray-50 border border-gray-200"
          )}>
            <p className={cn(
              "text-2xl font-bold",
              warning.length > 0 ? "text-amber-700" : "text-gray-400"
            )}>
              {warning.length}
            </p>
            <p className={cn(
              "text-xs",
              warning.length > 0 ? "text-amber-600" : "text-gray-500"
            )}>
              Warning (14-30 days)
            </p>
          </div>
          <div className={cn(
            "p-3 rounded-lg text-center",
            upcoming.length > 0 ? "bg-blue-100 border border-blue-200" : "bg-gray-50 border border-gray-200"
          )}>
            <p className={cn(
              "text-2xl font-bold",
              upcoming.length > 0 ? "text-blue-700" : "text-gray-400"
            )}>
              {upcoming.length}
            </p>
            <p className={cn(
              "text-xs",
              upcoming.length > 0 ? "text-blue-600" : "text-gray-500"
            )}>
              Upcoming (30-60 days)
            </p>
          </div>
        </div>

        {/* Critical Items List */}
        {critical.length > 0 && (
          <div className="space-y-2 mb-4">
            <h4 className="text-sm font-medium text-red-700 flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" />
              Urgent - Expiring within 14 days
            </h4>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {critical.slice(0, 5).map((item, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-2 bg-red-50 border border-red-100 rounded-lg text-sm cursor-pointer hover:bg-red-100"
                  onClick={() => navigate(`/portal/employees/${item.employee_id}?tab=training`)}
                >
                  <div>
                    <span className="font-medium text-red-800">{item.employee_name}</span>
                    <span className="text-red-600 mx-1">•</span>
                    <span className="text-red-700">{item.training_name}</span>
                  </div>
                  <Badge className="bg-red-200 text-red-800 text-xs">
                    {getDaysLeft(item.expiry_date)} days
                  </Badge>
                </div>
              ))}
              {critical.length > 5 && (
                <p className="text-xs text-red-500 text-center">
                  +{critical.length - 5} more critical items
                </p>
              )}
            </div>
          </div>
        )}

        {/* View All Button */}
        <Button 
          variant="outline" 
          className="w-full mt-2"
          onClick={() => navigate('/portal/training?filter=expiring')}
        >
          Open Training Details
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </CardContent>
    </Card>
  );
}

