import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { 
  Upload, CheckCircle, XCircle, Loader2, AlertTriangle,
  ArrowLeft, FileText, Home, Clock, Shield, File
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function DocumentUploadPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const requestId = searchParams.get('request_id');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tokenData, setTokenData] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (token) {
      validateToken();
    } else {
      setError({ type: 'error', message: 'No upload token provided. Please use the link from your email.' });
      setLoading(false);
    }
  }, [token]);

  const validateToken = async () => {
    try {
      const response = await axios.get(`${API}/api/public/validate-upload-token`, {
        params: { token, request_id: requestId }
      });
      setTokenData(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired') || detail?.includes('invalid')) {
        setError({ type: 'expired', message: 'This upload link has expired or is no longer valid. Please contact your recruitment manager for a new link.' });
      } else if (detail?.includes('completed') || detail?.includes('submitted')) {
        setError({ type: 'already_done', message: 'This document has already been uploaded. If you need to upload a replacement, please contact your recruitment manager.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to validate upload link' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileSelect = (file) => {
    if (!file) return;
    
    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File is too large. Maximum size is 10MB.');
      return;
    }
    
    // Validate file type
    const allowedExtensions = tokenData?.allowed_extensions || ['.pdf', '.jpg', '.jpeg', '.png', '.webp'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      toast.error(`File type not allowed. Accepted formats: ${allowedExtensions.join(', ')}`);
      return;
    }
    
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || !token) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('token', token);
      formData.append('file', selectedFile);
      if (requestId) {
        formData.append('request_id', requestId);
      }
      
      const response = await axios.post(`${API}/api/public/upload-document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setUploaded(true);
      setUploadResult(response.data);
      toast.success('Document uploaded successfully!');
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(detail || 'Failed to upload document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="py-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
            <p className="text-slate-600">Validating your upload link...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error states
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="py-12 text-center">
            {error.type === 'expired' ? (
              <Clock className="h-16 w-16 text-amber-500 mx-auto mb-4" />
            ) : error.type === 'already_done' ? (
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            ) : (
              <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            )}
            <h2 className="text-xl font-semibold mb-2">
              {error.type === 'expired' ? 'Link Expired' : 
               error.type === 'already_done' ? 'Already Uploaded' : 'Unable to Load'}
            </h2>
            <p className="text-slate-600 mb-6">{error.message}</p>
            <Link to="/">
              <Button variant="outline" className="gap-2">
                <Home className="h-4 w-4" />
                Return to Homepage
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (uploaded && uploadResult) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-lg w-full border-green-200 bg-green-50/50">
          <CardContent className="py-12 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-semibold text-green-800 mb-2">Upload Successful!</h2>
            <p className="text-green-700 mb-6">{uploadResult.message}</p>
            
            <div className="bg-white rounded-xl p-6 text-left mb-6 border border-green-200">
              <h3 className="font-medium text-slate-700 mb-3">What happens next?</h3>
              <ul className="space-y-2">
                {uploadResult.next_steps?.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
            
            <p className="text-sm text-slate-500">
              You can close this page. You'll be contacted if we need anything else.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Upload form
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-slate-800">Osabea Healthcare</h1>
              <p className="text-xs text-slate-500">Secure Document Upload</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Card className="shadow-lg border-slate-200">
          <CardHeader className="text-center pb-2">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">Upload {tokenData?.requirement_name}</CardTitle>
            <CardDescription className="text-base mt-2">
              Hello <span className="font-medium text-slate-700">{tokenData?.person_name}</span>! 
              Please upload your document below.
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <p className="text-sm text-blue-800">
                <strong>Instructions:</strong> {tokenData?.instructions}
              </p>
              <p className="text-xs text-blue-600 mt-2">
                Maximum file size: {tokenData?.max_file_size_mb || 10}MB
              </p>
            </div>

            {/* Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                dragActive 
                  ? 'border-primary bg-primary/5' 
                  : selectedFile 
                    ? 'border-green-300 bg-green-50' 
                    : 'border-slate-200 hover:border-slate-300'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {selectedFile ? (
                <div className="space-y-3">
                  <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mx-auto">
                    <File className="h-7 w-7 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">{selectedFile.name}</p>
                    <p className="text-sm text-slate-500">{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedFile(null)}
                    className="text-slate-600"
                  >
                    Choose Different File
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mx-auto">
                    <Upload className="h-7 w-7 text-slate-400" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-slate-500">or click to browse</p>
                  </div>
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    accept={tokenData?.allowed_extensions?.join(',')}
                    onChange={(e) => handleFileSelect(e.target.files[0])}
                  />
                  <Button
                    variant="outline"
                    onClick={() => document.getElementById('file-upload').click()}
                    className="gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    Browse Files
                  </Button>
                </div>
              )}
            </div>

            {/* Accepted Formats */}
            <div className="text-center">
              <p className="text-xs text-slate-500">
                Accepted formats: {tokenData?.allowed_extensions?.join(', ')}
              </p>
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="w-full h-12 text-base gap-2"
              data-testid="upload-document-submit"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-5 w-5" />
                  Upload Document
                </>
              )}
            </Button>

            {/* Security Note */}
            <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl text-sm text-slate-600">
              <Shield className="h-5 w-5 text-slate-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-700">Secure Upload</p>
                <p>Your document is encrypted and transmitted securely. Only authorised personnel can view uploaded documents.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Need help? Contact us at <a href="mailto:recruitment@osabea.care" className="text-primary hover:underline">recruitment@osabea.care</a></p>
        </div>
      </div>
    </div>
  );
}
