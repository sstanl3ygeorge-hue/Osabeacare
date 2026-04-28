import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, Search, Users, FileText, Calendar, Phone, MapPin, 
  MoreVertical, Eye, Edit, ChevronRight, User
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { parseBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';

const API_URL = API_BASE;

export default function ServiceUsersPage() {
  const navigate = useNavigate();
  const [serviceUsers, setServiceUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newServiceUser, setNewServiceUser] = useState({
    full_name: '',
    date_of_birth: '',
    nhs_number: '',
    address_line_1: '',
    city: '',
    postcode: '',
    phone: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
  });

  useEffect(() => {
    fetchServiceUsers();
  }, [statusFilter, searchQuery]);

  const fetchServiceUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      let url = `${API_URL}/api/service-users?`;
      if (statusFilter) url += `status=${statusFilter}&`;
      if (searchQuery) url += `search=${encodeURIComponent(searchQuery)}&`;
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setServiceUsers(data);
      }
    } catch (error) {
      console.error('Error fetching service users:', error);
      toast.error('Failed to load service users');
    } finally {
      setLoading(false);
    }
  };

  const handleAddServiceUser = async (e) => {
    e.preventDefault();
    
    if (!newServiceUser.full_name.trim()) {
      toast.error('Full name is required');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newServiceUser)
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Service user created: ${result.service_user_code}`);
        setShowAddDialog(false);
        setNewServiceUser({
          full_name: '',
          date_of_birth: '',
          nhs_number: '',
          address_line_1: '',
          city: '',
          postcode: '',
          phone: '',
          emergency_contact_name: '',
          emergency_contact_phone: '',
        });
        fetchServiceUsers();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create service user');
      }
    } catch (error) {
      console.error('Error creating service user:', error);
      toast.error('Failed to create service user');
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      active: 'bg-green-100 text-green-700',
      inactive: 'bg-gray-100 text-gray-600',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.inactive}`}>
        {status || 'Active'}
      </span>
    );
  };

  // HARDENING: Use parseBackendDate for safe age calculation
  const calculateAge = (dob) => {
    if (!dob) return null;
    const birth = parseBackendDate(dob);
    if (!birth) return null;
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="service-users-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Service Users</h1>
          <p className="text-sm text-text-muted mt-1">
            Manage care records for people receiving services
          </p>
        </div>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button data-testid="add-service-user-btn">
              <Plus className="h-4 w-4 mr-2" />
              Add Service User
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add New Service User</DialogTitle>
              <DialogDescription>
                Create a new service user record. You can add more details later.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddServiceUser} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name *</Label>
                <Input
                  id="full_name"
                  value={newServiceUser.full_name}
                  onChange={(e) => setNewServiceUser({...newServiceUser, full_name: e.target.value})}
                  placeholder="Enter full name"
                  required
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date_of_birth">Date of Birth</Label>
                  <Input
                    id="date_of_birth"
                    type="date"
                    value={newServiceUser.date_of_birth}
                    onChange={(e) => setNewServiceUser({...newServiceUser, date_of_birth: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nhs_number">NHS Number</Label>
                  <Input
                    id="nhs_number"
                    value={newServiceUser.nhs_number}
                    onChange={(e) => setNewServiceUser({...newServiceUser, nhs_number: e.target.value})}
                    placeholder="000 000 0000"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={newServiceUser.address_line_1}
                  onChange={(e) => setNewServiceUser({...newServiceUser, address_line_1: e.target.value})}
                  placeholder="Address line 1"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    value={newServiceUser.city}
                    onChange={(e) => setNewServiceUser({...newServiceUser, city: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="postcode">Postcode</Label>
                  <Input
                    id="postcode"
                    value={newServiceUser.postcode}
                    onChange={(e) => setNewServiceUser({...newServiceUser, postcode: e.target.value})}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={newServiceUser.phone}
                  onChange={(e) => setNewServiceUser({...newServiceUser, phone: e.target.value})}
                  placeholder="Phone number"
                />
              </div>
              
              <div className="pt-4 border-t">
                <p className="text-sm font-medium text-text-primary mb-3">Emergency Contact</p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emergency_name">Name</Label>
                    <Input
                      id="emergency_name"
                      value={newServiceUser.emergency_contact_name}
                      onChange={(e) => setNewServiceUser({...newServiceUser, emergency_contact_name: e.target.value})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emergency_phone">Phone</Label>
                    <Input
                      id="emergency_phone"
                      value={newServiceUser.emergency_contact_phone}
                      onChange={(e) => setNewServiceUser({...newServiceUser, emergency_contact_phone: e.target.value})}
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowAddDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit">Create Service User</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <Input
            placeholder="Search by name, NHS number, or postcode..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-200 text-sm bg-white"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white border border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">{serviceUsers.length}</p>
              <p className="text-xs text-text-muted">Total Service Users</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100">
              <User className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">
                {serviceUsers.filter(su => su.status === 'active' || !su.status).length}
              </p>
              <p className="text-xs text-text-muted">Active</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">
                {serviceUsers.reduce((sum, su) => sum + (su.total_documents || 0), 0)}
              </p>
              <p className="text-xs text-text-muted">Total Documents</p>
            </div>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white border border-gray-100">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-100">
              <Calendar className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-text-primary">10</p>
              <p className="text-xs text-text-muted">File Sections</p>
            </div>
          </div>
        </div>
      </div>

      {/* Service Users List */}
      {serviceUsers.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
          <Users className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">No Service Users Yet</h3>
          <p className="text-sm text-text-muted mb-4">
            Get started by adding your first service user
          </p>
          <Button onClick={() => setShowAddDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Service User
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Service User
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    NHS Number
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Location
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Documents
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {serviceUsers.map((su) => (
                  <tr 
                    key={su.id} 
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/portal/service-users/${su.id}`)}
                    data-testid={`service-user-row-${su.id}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-semibold text-primary">
                            {su.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-text-primary">{su.full_name}</p>
                          <p className="text-xs text-text-muted">
                            {su.service_user_code}
                            {su.date_of_birth && ` • ${calculateAge(su.date_of_birth)} years old`}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-text-primary font-mono">
                        {su.nhs_number || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-sm text-text-muted">
                        <MapPin className="h-3 w-3" />
                        {su.postcode || su.city || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <FileText className="h-4 w-4 text-text-muted" />
                        <span className="text-sm font-medium text-text-primary">
                          {su.total_documents || 0}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(su.status)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/portal/service-users/${su.id}`)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => navigate(`/portal/service-users/${su.id}`)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Profile
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => navigate(`/portal/service-users/${su.id}?edit=true`)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Edit Details
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

