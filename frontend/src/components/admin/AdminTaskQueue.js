import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { 
  Loader2, FileText, Mail, Calendar, ClipboardCheck, 
  CheckCircle, AlertTriangle, Users, Shield, ChevronRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

export default function AdminTaskQueue() {
  const [tasks, setTasks] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/admin/task-queue`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    // Refresh every 5 minutes
    const interval = setInterval(fetchTasks, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const taskItems = [
    {
      key: 'pending_verifications',
      label: 'Documents pending verification',
      icon: FileText,
      color: 'blue',
      count: tasks?.summary?.pending_verifications || 0,
      link: '/portal/employees',
      priority: 'high'
    },
    {
      key: 'pending_references',
      label: 'References awaiting review',
      icon: Mail,
      color: 'purple',
      count: tasks?.summary?.pending_references || 0,
      link: '/portal/recruitment',
      priority: 'medium'
    },
    {
      key: 'expiring_documents',
      label: 'Documents expiring in 30 days',
      icon: Calendar,
      color: 'red',
      count: tasks?.summary?.expiring_documents || 0,
      link: '/portal/employees',
      priority: 'high'
    },
    {
      key: 'scheduled_tasks',
      label: 'Assessments / spot checks due this week',
      icon: ClipboardCheck,
      color: 'amber',
      count: tasks?.summary?.scheduled_tasks || 0,
      link: '/portal/employees',
      priority: 'medium'
    },
    {
      key: 'overdue_followups',
      label: 'Follow-ups overdue',
      icon: Shield,
      color: 'red',
      count: tasks?.summary?.overdue_followups || 0,
      link: '/portal/employees',
      priority: 'high'
    }
  ];

  const activeItems = taskItems.filter(item => item.count > 0);
  const totalTasks = activeItems.reduce((sum, item) => sum + item.count, 0);
  const highPriorityCount = activeItems.filter(i => i.priority === 'high').reduce((s, i) => s + i.count, 0);

  const getColorClasses = (color) => {
    const colors = {
      blue: { bg: 'bg-blue-100', text: 'text-blue-600', badge: 'bg-blue-100 text-blue-700' },
      purple: { bg: 'bg-purple-100', text: 'text-purple-600', badge: 'bg-purple-100 text-purple-700' },
      red: { bg: 'bg-red-100', text: 'text-red-600', badge: 'bg-red-100 text-red-700' },
      amber: { bg: 'bg-amber-100', text: 'text-amber-600', badge: 'bg-amber-100 text-amber-700' },
      orange: { bg: 'bg-orange-100', text: 'text-orange-600', badge: 'bg-orange-100 text-orange-700' },
      green: { bg: 'bg-green-100', text: 'text-green-600', badge: 'bg-green-100 text-green-700' }
    };
    return colors[color] || colors.blue;
  };

  return (
    <Card className="border-[#E4E8EB] shadow-sm" data-testid="admin-task-queue">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            {totalTasks > 0 ? (
              <AlertTriangle className="h-5 w-5 text-amber-600" />
            ) : (
              <CheckCircle className="h-5 w-5 text-green-600" />
            )}
            My Tasks
          </CardTitle>
          {totalTasks > 0 && (
            <div className="flex items-center gap-2">
              {highPriorityCount > 0 && (
                <Badge className="bg-red-100 text-red-700">
                  {highPriorityCount} urgent
                </Badge>
              )}
              <Badge className="bg-primary/10 text-primary">
                {totalTasks} total
              </Badge>
            </div>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Items requiring your attention
        </p>
      </CardHeader>
      <CardContent>
        {activeItems.length === 0 ? (
          <div className="text-center py-6 text-gray-500">
            <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
            <p className="font-medium text-green-700">All caught up!</p>
            <p className="text-xs mt-1">No pending tasks right now.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {activeItems.map((item) => {
              const Icon = item.icon;
              const colors = getColorClasses(item.color);
              
              return (
                <Link 
                  key={item.key} 
                  to={item.link} 
                  className="block group"
                  data-testid={`task-${item.key}`}
                >
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-transparent hover:border-gray-200">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${colors.bg}`}>
                        <Icon className={`h-4 w-4 ${colors.text}`} />
                      </div>
                      <div>
                        <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
                          {item.label}
                        </span>
                        {item.priority === 'high' && (
                          <span className="ml-2 text-[10px] text-red-600 bg-red-50 px-1.5 py-0.5 rounded font-medium">
                            URGENT
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={colors.badge}>
                        {item.count}
                      </Badge>
                      <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-gray-600" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

