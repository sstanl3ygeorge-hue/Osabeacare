import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../ui/collapsible';
import { 
  CheckCircle, XCircle, AlertTriangle, Clock, Upload, 
  ChevronDown, ChevronRight, Info, Loader2, GraduationCap,
  Calendar, Shield, Award, RefreshCw, FileText
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { format, differenceInDays, parseISO } from 'date-fns';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_ROOT_URL;

/**
 * MandatoryTrainingSection - Shows the 6 mandatory trainings that block promotion
 */
function MandatoryTrainingSection({ trainings, role, onUploadClick }) {
  const mandatoryTypes = [
    { id: 'safeguarding', name: 'Safeguarding', icon: '🛡️' },
    { id: 'manual_handling', name: 'Manual Handling', icon: '🏋️' },
    { id: 'fire_safety', name: 'Fire Safety', icon: '🔥' },
    { id: 'health_safety', name: 'Health & Safety', icon: '⚠️' },
    { id: 'basic_life_support', name: 'Basic Life Support', icon: '❤️' },
    { id: 'infection_control', name: 'Infection Control', icon: '🦠' },
  ];

  // Find matching training for each mandatory type
  const getMandatoryTrainingStatus = (typeId) => {
    const matches = trainings.filter(t => {
      const tId = (t.training_id || t.id || '').toLowerCase();
      const tName = (t.training_name || t.name || '').toLowerCase();
      return tId.includes(typeId) || tName.includes(typeId.replace('_', ' '));
    });
    
    if (matches.length === 0) return { status: 'missing', training: null };
    
    // Get the most recent valid training
    const validTraining = matches
      .filter(t => !isExpired(t))
      .sort((a, b) => new Date(b.completion_date) - new Date(a.completion_date))[0];
    
    if (validTraining) {
      return { status: 'complete', training: validTraining };
    }
    
    // All are expired - return most recent
    const mostRecent = matches.sort((a, b) => 
      new Date(b.expiry_date || b.completion_date) - new Date(a.expiry_date || a.completion_date)
    )[0];
    
    return { status: 'expired', training: mostRecent };
  };

  const isExpired = (training) => {
    if (!training?.expiry_date) return false;
    return new Date(training.expiry_date) < new Date();
  };

  const getDaysUntilExpiry = (training) => {
    if (!training?.expiry_date) return null;
    return differenceInDays(parseISO(training.expiry_date), new Date());
  };

  const completedCount = mandatoryTypes.filter(
    type => getMandatoryTrainingStatus(type.id).status === 'complete'
  ).length;

  return (
    <Card className="border-2 border-blue-200 bg-blue-50/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
              <Shield className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                Mandatory Training
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Badge className="bg-red-100 text-red-700 text-xs">BLOCKS</Badge>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs bg-slate-900 text-white">
                      <p>Missing or expired mandatory training blocks promotion to active employee status.</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </CardTitle>
              <CardDescription>
                {completedCount}/6 complete • Required for work readiness
              </CardDescription>
            </div>
          </div>
          <Badge className={cn(
            "text-lg px-3 py-1",
            completedCount === 6 ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          )}>
            {completedCount}/6
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {mandatoryTypes.map((type) => {
            const { status, training } = getMandatoryTrainingStatus(type.id);
            const daysLeft = training ? getDaysUntilExpiry(training) : null;
            
            return (
              <div
                key={type.id}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg border",
                  status === 'complete' ? "bg-green-50 border-green-200" :
                  status === 'expired' ? "bg-red-50 border-red-200" :
                  "bg-gray-50 border-gray-200"
                )}
                data-testid={`mandatory-training-${type.id}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{type.icon}</span>
                  <div>
                    <p className={cn(
                      "font-medium",
                      status === 'complete' ? "text-green-800" :
                      status === 'expired' ? "text-red-800" :
                      "text-gray-700"
                    )}>
                      {type.name}
                    </p>
                    {training && (
                      <p className="text-xs text-gray-500">
                        {training.training_name || training.name}
                        {training.completion_date && (
                          <> • Completed: {format(parseISO(training.completion_date), 'dd/MM/yyyy')}</>
                        )}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {status === 'complete' && (
                    <>
                      {daysLeft !== null && daysLeft <= 60 && (
                        <Badge className={cn(
                          "text-xs",
                          daysLeft <= 30 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                        )}>
                          {daysLeft} days left
                        </Badge>
                      )}
                      <Badge className="bg-green-100 text-green-700">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Complete
                      </Badge>
                    </>
                  )}
                  {status === 'expired' && (
                    <>
                      <Badge className="bg-red-100 text-red-700">
                        <XCircle className="h-3 w-3 mr-1" />
                        Expired
                      </Badge>
                      <Button size="sm" variant="outline" onClick={() => onUploadClick?.(type.id)}>
                        <Upload className="h-3 w-3 mr-1" />
                        Renew
                      </Button>
                    </>
                  )}
                  {status === 'missing' && (
                    <>
                      <Badge className="bg-gray-100 text-gray-600">
                        <Clock className="h-3 w-3 mr-1" />
                        Missing
                      </Badge>
                      <Button size="sm" onClick={() => onUploadClick?.(type.id)}>
                        <Upload className="h-3 w-3 mr-1" />
                        Upload
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * AdditionalTrainingSection - Shows bonus trainings (collapsible)
 */
function AdditionalTrainingSection({ trainings, onUploadClick }) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Filter out mandatory trainings
  const additionalTrainings = trainings.filter(t => !t.is_mandatory);
  
  if (additionalTrainings.length === 0) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return format(parseISO(dateStr), 'dd/MM/yyyy');
    } catch {
      return dateStr;
    }
  };

  return (
    <Card className="border border-slate-200">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-slate-50 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                  <Award className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    Additional Training
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <Badge className="bg-green-100 text-green-700 text-xs">BONUS</Badge>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs bg-slate-900 text-white">
                          <p>Additional qualifications and specialist skills. Does not block promotion.</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </CardTitle>
                  <CardDescription>
                    {additionalTrainings.length} additional qualifications
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="bg-purple-100 text-purple-700">
                  {additionalTrainings.length} items
                </Badge>
                {isOpen ? (
                  <ChevronDown className="h-5 w-5 text-gray-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {additionalTrainings.map((training, idx) => {
                const isExpired = training.expiry_date && new Date(training.expiry_date) < new Date();
                
                return (
                  <div
                    key={training.id || idx}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg border",
                      isExpired ? "bg-amber-50 border-amber-200" : "bg-white border-gray-200"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <GraduationCap className={cn(
                        "h-4 w-4",
                        isExpired ? "text-amber-500" : "text-purple-500"
                      )} />
                      <div>
                        <p className="font-medium text-gray-800 text-sm">
                          {training.training_name || training.name}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          {training.completion_date && (
                            <span>Completed: {formatDate(training.completion_date)}</span>
                          )}
                          {training.expiry_date && (
                            <span>• Expires: {formatDate(training.expiry_date)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {isExpired ? (
                      <Badge className="bg-amber-100 text-amber-700 text-xs">Expired</Badge>
                    ) : (
                      <Badge className="bg-green-100 text-green-700 text-xs">Valid</Badge>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

/**
 * BulkUploadSection - Handles multi-training certificate uploads
 */
function BulkUploadSection({ employeeId, onUploadComplete }) {
  const { token } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setExtractionResult(null);

    try {
      // Step 1: Upload and extract
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await axios.post(
        `${API}/employees/${employeeId}/training/intake/from-upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const { extraction } = uploadResponse.data;
      const proposedItems = extraction?.proposed_items || [];
      const newCount = extraction?.new_items ?? proposedItems.length;
      const updatedCount = extraction?.updated_items ?? 0;

      // Step 2: Auto-approve all new proposed items so they show on worker dashboard
      if (proposedItems.length > 0) {
        await axios.post(
          `${API}/employees/${employeeId}/training/proposed-items/review`,
          {
            items: proposedItems.map(item => ({
              item_id: item.id,
              approve: true,
              mapped_training_code: item.mapped_training_code,
              mapped_training_title: item.mapped_training_title || item.raw_course_title,
              completed_at: item.completed_at,
              expires_at: item.expires_at,
            })),
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }

      setExtractionResult({ newCount, updatedCount, totalCourses: extraction?.total_courses || 0 });

      if (newCount > 0 && updatedCount > 0) {
        toast.success(`${newCount} training record${newCount !== 1 ? 's' : ''} added, ${updatedCount} existing updated`);
      } else if (newCount > 0) {
        toast.success(`${newCount} training record${newCount !== 1 ? 's' : ''} extracted and saved`);
      } else if (updatedCount > 0) {
        toast.info(`No new trainings found — ${updatedCount} existing record${updatedCount !== 1 ? 's' : ''} updated with new certificate`);
      } else {
        toast.warning('Certificate scanned but no trainings could be identified. Check formatting or upload per-item.');
      }

      onUploadComplete?.();
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Failed to process certificate');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="border-dashed border-2 border-slate-300 bg-slate-50/50">
      <CardContent className="pt-6">
        <div className="text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Upload className="h-8 w-8 text-blue-600" />
          </div>
          
          <h3 className="font-semibold text-gray-800 mb-1">Bulk Upload Certificate</h3>
          <p className="text-sm text-gray-500 mb-4">
            Upload a training certificate - AI will extract ALL training items automatically.
            <br />
            <span className="text-xs text-gray-400">
              One certificate can contain multiple training records.
            </span>
          </p>
          
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
            <Button disabled={uploading} asChild>
              <span>
                {uploading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Select Certificate (PDF/JPG)
                  </>
                )}
              </span>
            </Button>
          </label>
        </div>
        
        {/* Extraction Result */}
        {extractionResult && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-green-700 font-medium mb-2">
              <CheckCircle className="h-4 w-4" />
              Extraction Complete
            </div>
            <div className="text-sm text-green-600 space-y-1">
              <p>Total courses detected: <strong>{extractionResult.totalCourses}</strong></p>
              <p>New records saved: <strong>{extractionResult.newCount}</strong></p>
              {extractionResult.updatedCount > 0 && (
                <p className="text-amber-600">
                  ⚠️ {extractionResult.updatedCount} duplicate{extractionResult.updatedCount !== 1 ? 's' : ''} detected — existing record{extractionResult.updatedCount !== 1 ? 's' : ''} updated with new certificate
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * EnhancedTrainingTab - Main component showing mandatory vs additional trainings
 */
export default function EnhancedTrainingTab({ employeeId, employeeRole, initialTrainings = [] }) {
  const { token } = useAuth();
  const [trainings, setTrainings] = useState(initialTrainings);
  const [loading, setLoading] = useState(false);

  const fetchTrainings = useCallback(async () => {
    if (!employeeId || !token) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/training-records`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setTrainings(response.data.trainings || response.data || []);
    } catch (error) {
      console.error('Failed to fetch trainings:', error);
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);

  useEffect(() => {
    if (initialTrainings.length === 0) {
      fetchTrainings();
    }
  }, [fetchTrainings, initialTrainings.length]);

  const handleUploadClick = (trainingType) => {
    // Open a file picker and upload directly to the per-requirement endpoint
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.jpg,.jpeg,.png,.webp';
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const formData = new FormData();
        formData.append('file', file);
        await axios.post(
          `${API}/employees/${employeeId}/training/${trainingType}/upload-certificate`,
          formData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'multipart/form-data',
            },
          }
        );
        toast.success('Certificate uploaded. Training record saved — awaiting verification.');
        fetchTrainings();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Upload failed');
      }
    };
    input.click();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-500">Loading training records...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-800">Training & Qualifications</h2>
          <p className="text-sm text-gray-500">
            Mandatory training must be complete for work readiness. Additional training is tracked but optional.
          </p>
        </div>
        <Button variant="outline" onClick={fetchTrainings} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Mandatory Training Section */}
      <MandatoryTrainingSection 
        trainings={trainings}
        role={employeeRole}
        onUploadClick={handleUploadClick}
      />

      {/* Bulk Upload Section */}
      <div data-testid="bulk-upload-section">
        <BulkUploadSection 
          employeeId={employeeId}
          onUploadComplete={fetchTrainings}
        />
      </div>

      {/* Additional Training Section */}
      <AdditionalTrainingSection 
        trainings={trainings}
        onUploadClick={handleUploadClick}
      />
    </div>
  );
}

