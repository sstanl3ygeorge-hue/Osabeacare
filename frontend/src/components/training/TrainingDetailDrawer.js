import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '../ui/sheet';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../ui/tabs';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Download,
  Eye,
  Shield,
  Calendar,
  Clock,
  Building2,
  FileText,
  History,
  Upload,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { formatBackendDate } from '../../lib/dateUtils';

const API = process.env.REACT_APP_BACKEND_URL;

// Status styling
const STATUS_STYLES = {
  current: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  expiring_soon: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  expired: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
  missing: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200' },
  pending: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
};

/**
 * TrainingDetailDrawer - Shows full training record details
 * 
 * Opens when clicking a row in TrainingMatrix.
 * Displays:
 * - Training info (name, provider, dates, status)
 * - Certificate/evidence files with view/download
 * - Verification status and actions (admin only)
 * - History of changes
 */
export default function TrainingDetailDrawer({
  isOpen,
  onClose,
  trainingItem,
  employeeId,
  isAdmin = false,
  onUpdate
}) {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState('details');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [verifyNotes, setVerifyNotes] = useState('');
  
  // Fetch history when tab changes
  const fetchHistory = async () => {
    if (!trainingItem?.record_id) return;
    
    setHistoryLoading(true);
    try {
      const response = await axios.get(
        `${API}/api/training-records/${trainingItem.record_id}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setHistory(response.data || []);
    } catch (err) {
      console.error('Error fetching history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };
  
  // Handle tab change
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'history' && history.length === 0) {
      fetchHistory();
    }
  };
  
  // View certificate
  const handleViewCertificate = async () => {
    if (!trainingItem?.record_id) return;
    
    try {
      const response = await axios.get(
        `${API}/api/training-records/${trainingItem.record_id}/certificate/file`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (err) {
      toast.error('Failed to view certificate');
    }
  };
  
  // Download certificate
  const handleDownloadCertificate = async () => {
    if (!trainingItem?.record_id) return;
    
    try {
      const response = await axios.get(
        `${API}/api/training-records/${trainingItem.record_id}/certificate/download`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${trainingItem.code}_certificate.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success('Certificate downloaded');
    } catch (err) {
      toast.error('Failed to download certificate');
    }
  };
  
  // Verify training
  const handleVerify = async () => {
    if (!trainingItem?.record_id) return;
    
    setLoading(true);
    try {
      await axios.post(
        `${API}/api/training-records/${trainingItem.record_id}/verify`,
        { notes: verifyNotes },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Training verified');
      setVerifyNotes('');
      onUpdate?.();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify');
    } finally {
      setLoading(false);
    }
  };
  
  // Unverify training
  const handleUnverify = async () => {
    if (!trainingItem?.record_id) return;
    
    setLoading(true);
    try {
      await axios.post(
        `${API}/api/training-records/${trainingItem.record_id}/unverify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Verification removed');
      onUpdate?.();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unverify');
    } finally {
      setLoading(false);
    }
  };
  
  if (!trainingItem) return null;
  
  const statusStyle = STATUS_STYLES[trainingItem.status] || STATUS_STYLES.missing;
  
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto" data-testid="training-detail-drawer">
        <SheetHeader className="pb-4 border-b">
          <SheetTitle className="text-xl">{trainingItem.title}</SheetTitle>
          <SheetDescription className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              {trainingItem.code}
            </Badge>
            <Badge 
              variant="outline" 
              className={cn(statusStyle.bg, statusStyle.text, statusStyle.border)}
            >
              {trainingItem.status?.replace(/_/g, ' ')}
            </Badge>
            {trainingItem.verified && (
              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                <Shield className="h-3 w-3 mr-1" />
                Verified
              </Badge>
            )}
          </SheetDescription>
        </SheetHeader>
        
        <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="evidence">Evidence</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          
          {/* Details Tab */}
          <TabsContent value="details" className="mt-4 space-y-4">
            {/* Status Card */}
            <div className={cn("p-4 rounded-lg border", statusStyle.bg, statusStyle.border)}>
              <div className="flex items-center gap-3">
                {trainingItem.status === 'current' || trainingItem.status === 'completed' ? (
                  <CheckCircle2 className={cn("h-6 w-6", statusStyle.text)} />
                ) : trainingItem.status === 'expired' ? (
                  <XCircle className={cn("h-6 w-6", statusStyle.text)} />
                ) : trainingItem.status === 'expiring_soon' ? (
                  <AlertTriangle className={cn("h-6 w-6", statusStyle.text)} />
                ) : (
                  <Clock className={cn("h-6 w-6", statusStyle.text)} />
                )}
                <div>
                  <p className={cn("font-medium", statusStyle.text)}>
                    {trainingItem.status === 'current' ? 'Training Current' :
                     trainingItem.status === 'completed' ? 'Completed' :
                     trainingItem.status === 'expired' ? 'Training Expired' :
                     trainingItem.status === 'expiring_soon' ? 'Renewal Required Soon' :
                     'Training Not Completed'}
                  </p>
                  {trainingItem.detail && (
                    <p className={cn("text-sm", statusStyle.text, "opacity-80")}>
                      {trainingItem.detail}
                    </p>
                  )}
                </div>
              </div>
            </div>
            
            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4">
              {trainingItem.completed_at && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Completed</p>
                  <p className="font-medium flex items-center gap-1.5">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    {formatBackendDate(trainingItem.completed_at, { format: 'medium' })}
                  </p>
                </div>
              )}
              
              {trainingItem.expires_at && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Expires</p>
                  <p className={cn(
                    "font-medium flex items-center gap-1.5",
                    trainingItem.status === 'expired' ? 'text-red-600' :
                    trainingItem.status === 'expiring_soon' ? 'text-amber-600' : ''
                  )}>
                    <Clock className="h-4 w-4" />
                    {formatBackendDate(trainingItem.expires_at, { format: 'medium' })}
                  </p>
                </div>
              )}
              
              {trainingItem.provider && (
                <div className="p-3 bg-gray-50 rounded-lg col-span-2">
                  <p className="text-xs text-gray-500 mb-1">Provider</p>
                  <p className="font-medium flex items-center gap-1.5">
                    <Building2 className="h-4 w-4 text-gray-400" />
                    {trainingItem.provider}
                  </p>
                </div>
              )}
              
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Validity Period</p>
                <p className="font-medium">
                  {trainingItem.validity_days ? `${trainingItem.validity_days} days` : 'Lifetime'}
                </p>
              </div>
              
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Work Blocking</p>
                <p className={cn(
                  "font-medium",
                  trainingItem.blocker ? 'text-red-600' : 'text-gray-600'
                )}>
                  {trainingItem.blocker ? 'Yes - Required' : 'No'}
                </p>
              </div>
            </div>
            
            {/* Admin Verification Section */}
            {isAdmin && trainingItem.has_evidence && (
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="font-medium text-blue-800 mb-3">Admin Verification</p>
                
                {trainingItem.verified ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Shield className="h-5 w-5 text-emerald-600" />
                      <span className="text-emerald-700">Verified</span>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleUnverify}
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Remove Verification'}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Textarea
                      placeholder="Verification notes (optional)..."
                      value={verifyNotes}
                      onChange={(e) => setVerifyNotes(e.target.value)}
                      rows={2}
                      className="bg-white"
                    />
                    <Button
                      onClick={handleVerify}
                      disabled={loading}
                      className="w-full bg-emerald-600 hover:bg-emerald-700"
                    >
                      {loading ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Shield className="h-4 w-4 mr-2" />
                      )}
                      Verify Training
                    </Button>
                  </div>
                )}
              </div>
            )}
          </TabsContent>
          
          {/* Evidence Tab */}
          <TabsContent value="evidence" className="mt-4">
            {trainingItem.has_evidence ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded flex items-center justify-center">
                        <FileText className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium">Training Certificate</p>
                        <p className="text-sm text-gray-500">
                          {trainingItem.verified ? 'Verified' : 'Awaiting verification'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleViewCertificate}
                        data-testid="view-certificate-btn"
                      >
                        <Eye className="h-4 w-4 mr-1.5" />
                        View
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleDownloadCertificate}
                        data-testid="download-certificate-btn"
                      >
                        <Download className="h-4 w-4 mr-1.5" />
                        Download
                      </Button>
                    </div>
                  </div>
                </div>
                
                {trainingItem.verified && (
                  <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-emerald-600" />
                    <span className="text-emerald-700 text-sm">
                      Certificate verified by admin
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No certificate uploaded</p>
                <p className="text-sm mt-1">Upload a certificate to verify this training</p>
              </div>
            )}
          </TabsContent>
          
          {/* History Tab */}
          <TabsContent value="history" className="mt-4">
            {historyLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : history.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No history available</p>
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((item, idx) => (
                  <div 
                    key={item.id || idx}
                    className="p-3 bg-gray-50 rounded-lg border text-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">
                        {item.action?.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatBackendDate(item.created_at, { format: 'medium' })}
                      </span>
                    </div>
                    {item.performed_by_name && (
                      <p className="text-gray-600">By: {item.performed_by_name}</p>
                    )}
                    {item.notes && (
                      <p className="text-gray-500 mt-1">{item.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
        
        <SheetFooter className="mt-6 pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
