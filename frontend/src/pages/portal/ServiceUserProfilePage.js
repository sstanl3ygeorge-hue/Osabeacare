import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, User, FileText, ClipboardList, Heart, AlertTriangle,
  Pill, Stethoscope, CalendarCheck, Mail, Plus, Upload, Check,
  MoreVertical, Eye, Trash2, Edit, Phone, MapPin, Calendar,
  Building, UserCircle, Shield
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { toast } from 'sonner';
import FileUploader from '../../components/ui/file-uploader';
import { formatBackendDate, parseBackendDate } from '../../lib/dateUtils';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Tab configuration matching section structure
const TABS = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: '1_personal_referral', label: '1. Personal Info', icon: UserCircle },
  { id: '2_consent_contracts', label: '2. Consent', icon: Shield },
  { id: '3_assessments', label: '3. Assessments', icon: ClipboardList },
  { id: '4_care_plans', label: '4. Care Plans', icon: Heart },
  { id: '5_risk_assessments', label: '5. Risk Assessments', icon: AlertTriangle },
  { id: '6_monitoring', label: '6. Monitoring', icon: CalendarCheck },
  { id: '7_medication', label: '7. Medication', icon: Pill },
  { id: '8_health_visits', label: '8. Health Visits', icon: Stethoscope },
  { id: '9_reviews', label: '9. Reviews', icon: CalendarCheck },
  { id: '10_correspondence', label: '10. Letters', icon: Mail },
];

export default function ServiceUserProfilePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [serviceUser, setServiceUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [uploadSection, setUploadSection] = useState(null);
  const [sections, setSections] = useState([]);
  
  const [uploadForm, setUploadForm] = useState({
    title: '',
    document_type: '',
    notes: '',
    expiry_date: '',
    file_url: '',
    file_name: '',
  });
  
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    fetchServiceUser();
    fetchSections();
  }, [id]);

  const fetchServiceUser = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setServiceUser(data);
        setEditForm(data);
      } else {
        toast.error('Service user not found');
        navigate('/portal/service-users');
      }
    } catch (error) {
      console.error('Error fetching service user:', error);
      toast.error('Failed to load service user');
    } finally {
      setLoading(false);
    }
  };

  const fetchSections = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/sections`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSections(data);
      }
    } catch (error) {
      console.error('Error fetching sections:', error);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    
    if (!uploadForm.title || !uploadForm.file_url) {
      toast.error('Please provide a title and upload a file');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/${id}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          section_id: uploadSection,
          ...uploadForm
        })
      });

      if (response.ok) {
        toast.success('Document uploaded successfully');
        setShowUploadDialog(false);
        setUploadForm({
          title: '',
          document_type: '',
          notes: '',
          expiry_date: '',
          file_url: '',
          file_name: '',
        });
        fetchServiceUser();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to upload document');
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      toast.error('Failed to upload document');
    }
  };

  const handleVerifyDocument = async (documentId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/${id}/documents/${documentId}/verify`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Document verified');
        fetchServiceUser();
      }
    } catch (error) {
      toast.error('Failed to verify document');
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/${id}/documents/${documentId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Document deleted');
        fetchServiceUser();
      }
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const handleUpdateServiceUser = async (e) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/api/service-users/${id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });

      if (response.ok) {
        toast.success('Service user updated');
        setShowEditDialog(false);
        fetchServiceUser();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update');
      }
    } catch (error) {
      toast.error('Failed to update service user');
    }
  };

  const openUploadDialog = (sectionId) => {
    setUploadSection(sectionId);
    setShowUploadDialog(true);
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

  if (!serviceUser) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Service user not found</p>
        <Button onClick={() => navigate('/portal/service-users')} className="mt-4">
          Back to Service Users
        </Button>
      </div>
    );
  }

  const currentSection = serviceUser.sections?.[activeTab];

  return (
    <div className="space-y-6" data-testid="service-user-profile-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/portal/service-users')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-xl font-bold text-primary">
                {serviceUser.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{serviceUser.full_name}</h1>
              <div className="flex items-center gap-3 text-sm text-text-muted mt-1">
                <span className="font-mono">{serviceUser.service_user_code}</span>
                {serviceUser.date_of_birth && (
                  <span>{calculateAge(serviceUser.date_of_birth)} years old</span>
                )}
                {serviceUser.nhs_number && (
                  <span className="font-mono">NHS: {serviceUser.nhs_number}</span>
                )}
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            serviceUser.status === 'inactive' ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700'
          }`}>
            {serviceUser.status || 'Active'}
          </span>
          <Button variant="outline" onClick={() => setShowEditDialog(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Details
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 overflow-x-auto pb-2 border-b border-gray-200">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const docCount = tab.id !== 'overview' ? serviceUser.sections?.[tab.id]?.document_count || 0 : null;
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'text-text-muted hover:bg-gray-100'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {docCount !== null && docCount > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id ? 'bg-white/20' : 'bg-gray-200'
                }`}>
                  {docCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-xl border border-gray-100 p-6">
        {activeTab === 'overview' ? (
          <OverviewTab serviceUser={serviceUser} onOpenSection={setActiveTab} serviceUserId={id} />
        ) : (
          <SectionTab
            section={currentSection}
            sectionId={activeTab}
            onUpload={() => openUploadDialog(activeTab)}
            onVerify={handleVerifyDocument}
            onDelete={handleDeleteDocument}
          />
        )}
      </div>

      {/* Upload Document Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Upload Document</DialogTitle>
            <DialogDescription>
              Add a document to {serviceUser.sections?.[uploadSection]?.name || 'this section'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUploadDocument} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="doc_title">Document Title *</Label>
              <Input
                id="doc_title"
                value={uploadForm.title}
                onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                placeholder="e.g., Initial Care Assessment"
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_type">Document Type</Label>
              <Select
                value={uploadForm.document_type}
                onValueChange={(val) => setUploadForm({...uploadForm, document_type: val})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {serviceUser.sections?.[uploadSection]?.document_types?.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </SelectItem>
                  ))}
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Upload File *</Label>
              <FileUploader
                onUploadComplete={(url, fileName) => {
                  setUploadForm({...uploadForm, file_url: url, file_name: fileName});
                  toast.success('File uploaded');
                }}
                acceptedTypes={['application/pdf', 'image/*', '.doc', '.docx']}
              />
              {uploadForm.file_name && (
                <p className="text-sm text-green-600">Uploaded: {uploadForm.file_name}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_expiry">Expiry Date (optional)</Label>
              <Input
                id="doc_expiry"
                type="date"
                value={uploadForm.expiry_date}
                onChange={(e) => setUploadForm({...uploadForm, expiry_date: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_notes">Notes</Label>
              <Textarea
                id="doc_notes"
                value={uploadForm.notes}
                onChange={(e) => setUploadForm({...uploadForm, notes: e.target.value})}
                placeholder="Additional notes about this document"
                rows={3}
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setShowUploadDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={!uploadForm.file_url}>
                <Upload className="h-4 w-4 mr-2" />
                Upload Document
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Service User Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Service User Details</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdateServiceUser} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Full Name</Label>
                <Input
                  value={editForm.full_name || ''}
                  onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Date of Birth</Label>
                <Input
                  type="date"
                  value={editForm.date_of_birth || ''}
                  onChange={(e) => setEditForm({...editForm, date_of_birth: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>NHS Number</Label>
                <Input
                  value={editForm.nhs_number || ''}
                  onChange={(e) => setEditForm({...editForm, nhs_number: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={editForm.phone || ''}
                  onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={editForm.email || ''}
                  onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={editForm.status || 'active'}
                  onValueChange={(val) => setEditForm({...editForm, status: val})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">Address</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2 col-span-2">
                  <Label>Address Line 1</Label>
                  <Input
                    value={editForm.address_line_1 || ''}
                    onChange={(e) => setEditForm({...editForm, address_line_1: e.target.value})}
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Address Line 2</Label>
                  <Input
                    value={editForm.address_line_2 || ''}
                    onChange={(e) => setEditForm({...editForm, address_line_2: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input
                    value={editForm.city || ''}
                    onChange={(e) => setEditForm({...editForm, city: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Postcode</Label>
                  <Input
                    value={editForm.postcode || ''}
                    onChange={(e) => setEditForm({...editForm, postcode: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">Emergency Contact</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={editForm.emergency_contact_name || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={editForm.emergency_contact_phone || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_phone: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Relationship</Label>
                  <Input
                    value={editForm.emergency_contact_relationship || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_relationship: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">GP Details</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>GP Name</Label>
                  <Input
                    value={editForm.gp_name || ''}
                    onChange={(e) => setEditForm({...editForm, gp_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Surgery</Label>
                  <Input
                    value={editForm.gp_surgery || ''}
                    onChange={(e) => setEditForm({...editForm, gp_surgery: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={editForm.gp_phone || ''}
                    onChange={(e) => setEditForm({...editForm, gp_phone: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                rows={3}
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setShowEditDialog(false)}>
                Cancel
              </Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Overview Tab Component
function OverviewTab({ serviceUser, onOpenSection, serviceUserId }) {
  const encodedServiceUserId = encodeURIComponent(serviceUserId || '');
  return (
    <div className="space-y-6">
      {/* Quick Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Personal Info Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <User className="h-4 w-4" />
            Personal Information
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Date of Birth</span>
              <span className="text-text-primary">{serviceUser.date_of_birth || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">NHS Number</span>
              <span className="text-text-primary font-mono">{serviceUser.nhs_number || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Phone</span>
              <span className="text-text-primary">{serviceUser.phone || '-'}</span>
            </div>
          </div>
        </div>
        
        {/* Address Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Address
          </h3>
          <div className="text-sm text-text-primary space-y-1">
            {serviceUser.address_line_1 && <p>{serviceUser.address_line_1}</p>}
            {serviceUser.address_line_2 && <p>{serviceUser.address_line_2}</p>}
            {(serviceUser.city || serviceUser.postcode) && (
              <p>{[serviceUser.city, serviceUser.postcode].filter(Boolean).join(', ')}</p>
            )}
            {!serviceUser.address_line_1 && <p className="text-text-muted">No address recorded</p>}
          </div>
        </div>
        
        {/* Emergency Contact Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Phone className="h-4 w-4" />
            Emergency Contact
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Name</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Phone</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_phone || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Relationship</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_relationship || '-'}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* GP Details */}
      {(serviceUser.gp_name || serviceUser.gp_surgery) && (
        <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Building className="h-4 w-4" />
            GP Details
          </h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-text-muted">GP Name</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_name || '-'}</p>
            </div>
            <div>
              <span className="text-text-muted">Surgery</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_surgery || '-'}</p>
            </div>
            <div>
              <span className="text-text-muted">Phone</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_phone || '-'}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* File Sections Overview */}
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Care File Sections</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(serviceUser.sections || {}).map(([sectionId, section]) => (
            <button
              key={sectionId}
              onClick={() => onOpenSection(sectionId)}
              className="p-4 rounded-lg bg-white border border-gray-200 hover:border-primary hover:bg-primary/5 transition-all text-left"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-primary">
                  Section {section.section_number}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  section.document_count > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {section.document_count} docs
                </span>
              </div>
              <p className="text-sm font-medium text-text-primary truncate">{section.name}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Related Operational Records (read-only links) */}
      <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
        <h3 className="text-sm font-semibold text-text-primary mb-1">Related Operational Records</h3>
        <p className="text-xs text-text-muted mb-3">Opens filtered operational records for this service user.</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <a
            href={`/portal/compliance-centre?tab=incidents&service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Incidents
          </a>
          <a
            href={`/portal/shifts?service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Shifts
          </a>
          <a
            href={`/portal/feedback?service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Feedback
          </a>
        </div>
      </div>
      
      {/* Notes */}
      {serviceUser.notes && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-100">
          <h3 className="text-sm font-semibold text-text-primary mb-2">Notes</h3>
          <p className="text-sm text-text-muted whitespace-pre-wrap">{serviceUser.notes}</p>
        </div>
      )}
    </div>
  );
}

// Section Tab Component
function SectionTab({ section, sectionId, onUpload, onVerify, onDelete }) {
  if (!section) {
    return <p className="text-text-muted">Section not found</p>;
  }

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Section {section.section_number}: {section.name}
          </h2>
          <p className="text-sm text-text-muted">{section.description}</p>
        </div>
        <Button onClick={onUpload}>
          <Plus className="h-4 w-4 mr-2" />
          Add Document
        </Button>
      </div>
      
      {/* Document Types */}
      <div className="flex flex-wrap gap-2">
        {section.document_types?.map((type) => (
          <span key={type} className="px-2 py-1 rounded bg-gray-100 text-xs text-text-muted">
            {type.replace(/_/g, ' ')}
          </span>
        ))}
      </div>
      
      {/* Documents List */}
      {section.documents?.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-200">
          <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-sm font-medium text-text-primary mb-2">No Documents Yet</h3>
          <p className="text-xs text-text-muted mb-4">
            Upload documents for this section
          </p>
          <Button size="sm" onClick={onUpload}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Document
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {section.documents.map((doc) => (
            <div 
              key={doc.id}
              className="flex items-center justify-between p-4 rounded-lg bg-gray-50 border border-gray-100"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-white border border-gray-200">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">{doc.title}</p>
                  <div className="flex items-center gap-2 text-xs text-text-muted mt-1">
                    {doc.document_type && (
                      <span className="px-2 py-0.5 rounded bg-gray-200">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                    )}
                    <span>Uploaded {formatBackendDate(doc.uploaded_at)}</span>
                    {doc.expiry_date && (
                      <span className="text-amber-600">Expires {formatBackendDate(doc.expiry_date)}</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {doc.verified ? (
                  <span className="flex items-center gap-1 px-2 py-1 rounded bg-green-100 text-green-700 text-xs">
                    <Check className="h-3 w-3" />
                    Verified
                  </span>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => onVerify(doc.id)}>
                    <Check className="h-4 w-4 mr-1" />
                    Verify
                  </Button>
                )}
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => window.open(doc.file_url, '_blank')}>
                      <Eye className="h-4 w-4 mr-2" />
                      View Document
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => onDelete(doc.id)}
                      className="text-red-600"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
