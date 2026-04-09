import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { 
  MessageSquare, 
  Star, 
  ThumbsUp, 
  ThumbsDown,
  Plus,
  Search,
  Filter,
  Calendar,
  User,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  TrendingUp
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Label } from "../../components/ui/label";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FEEDBACK_TYPES = [
  { value: 'compliment', label: 'Compliment', color: 'bg-green-100 text-green-800' },
  { value: 'suggestion', label: 'Suggestion', color: 'bg-blue-100 text-blue-800' },
  { value: 'concern', label: 'Concern', color: 'bg-amber-100 text-amber-800' },
  { value: 'complaint', label: 'Complaint', color: 'bg-red-100 text-red-800' },
];

const RATING_LABELS = {
  1: 'Poor',
  2: 'Fair',
  3: 'Good',
  4: 'Very Good',
  5: 'Excellent'
};

const ServiceUserFeedbackPage = () => {
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [serviceUsers, setServiceUsers] = useState([]);
  
  const [newFeedback, setNewFeedback] = useState({
    service_user_id: '',
    service_user_name: '',
    employee_id: '',
    feedback_type: 'compliment',
    rating: 5,
    title: '',
    description: '',
    date_received: new Date().toISOString().split('T')[0],
    recorded_by: ''
  });
  
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchFeedback();
    fetchStats();
    fetchEmployees();
    fetchServiceUsers();
  }, []);

  const fetchFeedback = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/service-user-feedback`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFeedback(response.data.feedback || []);
    } catch (error) {
      console.error('Failed to fetch feedback:', error);
      setFeedback([]);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/service-user-feedback/stats`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchEmployees = async () => {
    try {
      const response = await axios.get(`${API}/employees`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmployees(response.data || []);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    }
  };

  const fetchServiceUsers = async () => {
    try {
      const response = await axios.get(`${API}/service-users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setServiceUsers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch service users:', error);
    }
  };

  const handleSubmitFeedback = async () => {
    try {
      await axios.post(`${API}/service-user-feedback`, newFeedback, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowAddDialog(false);
      setNewFeedback({
        service_user_id: '',
        service_user_name: '',
        employee_id: '',
        feedback_type: 'compliment',
        rating: 5,
        title: '',
        description: '',
        date_received: new Date().toISOString().split('T')[0],
        recorded_by: ''
      });
      fetchFeedback();
      fetchStats();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const filteredFeedback = feedback.filter(item => {
    const matchesSearch = !searchTerm || 
      item.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.employee_name?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = filterType === 'all' || item.feedback_type === filterType;
    
    return matchesSearch && matchesType;
  });

  const renderStars = (rating) => {
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-4 h-4 ${star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`}
          />
        ))}
      </div>
    );
  };

  const getFeedbackTypeStyle = (type) => {
    const found = FEEDBACK_TYPES.find(t => t.value === type);
    return found ? found.color : 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6 space-y-6" data-testid="service-user-feedback-page">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Service User Feedback</h1>
          <p className="text-gray-500 mt-1">Record and track feedback from service users about staff performance</p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button data-testid="add-feedback-btn">
              <Plus className="w-4 h-4 mr-2" /> Record Feedback
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Record Service User Feedback</DialogTitle>
              <DialogDescription>
                Document feedback received from service users or their families
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Service User</Label>
                  <Select 
                    value={newFeedback.service_user_id} 
                    onValueChange={(v) => {
                      const su = serviceUsers.find(s => s.id === v);
                      setNewFeedback({
                        ...newFeedback, 
                        service_user_id: v,
                        service_user_name: su ? `${su.first_name} ${su.last_name}` : ''
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select service user" />
                    </SelectTrigger>
                    <SelectContent>
                      {serviceUsers.map(su => (
                        <SelectItem key={su.id} value={su.id}>
                          {su.first_name} {su.last_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Staff Member</Label>
                  <Select 
                    value={newFeedback.employee_id} 
                    onValueChange={(v) => setNewFeedback({...newFeedback, employee_id: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select employee" />
                    </SelectTrigger>
                    <SelectContent>
                      {employees.map(emp => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Feedback Type</Label>
                  <Select 
                    value={newFeedback.feedback_type} 
                    onValueChange={(v) => setNewFeedback({...newFeedback, feedback_type: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {FEEDBACK_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Rating</Label>
                  <div className="flex gap-1 pt-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setNewFeedback({...newFeedback, rating: star})}
                        className="focus:outline-none"
                      >
                        <Star
                          className={`w-6 h-6 cursor-pointer transition-colors ${
                            star <= newFeedback.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300 hover:text-yellow-200'
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              
              <div>
                <Label>Title</Label>
                <Input
                  value={newFeedback.title}
                  onChange={(e) => setNewFeedback({...newFeedback, title: e.target.value})}
                  placeholder="Brief summary of feedback"
                />
              </div>
              
              <div>
                <Label>Description</Label>
                <Textarea
                  value={newFeedback.description}
                  onChange={(e) => setNewFeedback({...newFeedback, description: e.target.value})}
                  placeholder="Full details of the feedback received..."
                  rows={4}
                />
              </div>
              
              <div>
                <Label>Date Received</Label>
                <Input
                  type="date"
                  value={newFeedback.date_received}
                  onChange={(e) => setNewFeedback({...newFeedback, date_received: e.target.value})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button onClick={handleSubmitFeedback} data-testid="submit-feedback-btn">
                Save Feedback
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Total Feedback</p>
                  <p className="text-2xl font-bold">{stats.total || 0}</p>
                </div>
                <MessageSquare className="w-8 h-8 text-blue-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Compliments</p>
                  <p className="text-2xl font-bold text-green-600">{stats.compliments || 0}</p>
                </div>
                <ThumbsUp className="w-8 h-8 text-green-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Concerns</p>
                  <p className="text-2xl font-bold text-amber-600">{stats.concerns || 0}</p>
                </div>
                <AlertCircle className="w-8 h-8 text-amber-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Complaints</p>
                  <p className="text-2xl font-bold text-red-600">{stats.complaints || 0}</p>
                </div>
                <ThumbsDown className="w-8 h-8 text-red-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">Avg Rating</p>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold">{stats.average_rating?.toFixed(1) || '-'}</p>
                    <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                  </div>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-500 opacity-20" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            className="pl-10"
            placeholder="Search feedback..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-48">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {FEEDBACK_TYPES.map(type => (
              <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Feedback List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading feedback...</div>
        ) : filteredFeedback.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <MessageSquare className="w-12 h-12 mx-auto text-gray-300 mb-4" />
              <p className="text-gray-500">No feedback recorded yet</p>
              <p className="text-sm text-gray-400 mt-1">Click "Record Feedback" to add service user feedback</p>
            </CardContent>
          </Card>
        ) : (
          filteredFeedback.map((item) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow" data-testid={`feedback-item-${item.id}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={getFeedbackTypeStyle(item.feedback_type)}>
                        {item.feedback_type}
                      </Badge>
                      {renderStars(item.rating)}
                      <span className="text-sm text-gray-500">
                        {new Date(item.date_received).toLocaleDateString()}
                      </span>
                    </div>
                    <h3 className="font-semibold text-lg">{item.title}</h3>
                    <p className="text-gray-600 mt-1">{item.description}</p>
                    <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <User className="w-4 h-4" />
                        Staff: {item.employee_name || 'Unknown'}
                      </span>
                      {item.service_user_name && (
                        <span className="flex items-center gap-1">
                          <MessageSquare className="w-4 h-4" />
                          From: {item.service_user_name}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default ServiceUserFeedbackPage;
