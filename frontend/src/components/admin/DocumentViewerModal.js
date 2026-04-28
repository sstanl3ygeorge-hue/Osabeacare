/**
 * DocumentViewerModal - Display documents with metadata
 * 
 * Shows:
 * - Document preview (PDF/image)
 * - File name, upload date
 * - Verification status with stamp type
 * - Verifier name and date
 * - Download button
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { useAuth } from '../../context/AuthContext';
import { 
  Download, Loader2, FileText, Image, CheckCircle, 
  Clock, XCircle, Eye, Globe, FileCheck, ExternalLink,
  Calendar, User, Shield, AlertTriangle
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { cn } from '../../lib/utils';
import {
import { API_BASE_URL, API_ROOT_URL } from './';
  fetchProtectedFileBlob,
  downloadBlobUrl,
  openBlobUrlInNewTab,
  revokeBlobUrl,
} from '../../lib/protectedFiles';

const API = API_ROOT_URL;

const STAMP_LABELS = {
  'original_seen': { label: 'Original Seen', icon: Eye, color: 'bg-blue-100 text-blue-700' },
  'copy_verified': { label: 'Copy Verified', icon: FileCheck, color: 'bg-purple-100 text-purple-700' },
  'online_check': { label: 'Online Check', icon: Globe, color: 'bg-teal-100 text-teal-700' }
};

export default function DocumentViewerModal({ 
  open, 
  onClose, 
  document, 
  employeeId,
  employeeName,
  onVerify 
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [blobUrl, setBlobUrl] = useState(null);
  const [detectedContentType, setDetectedContentType] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open && document) {
      loadDocument();
    }
    return () => {
      revokeBlobUrl(blobUrl);
    };
  }, [open, document]);

  const loadDocument = async () => {
    if (!document?.file_url && !document?.url) {
      setError('No file URL available');
      return;
    }

    setLoading(true);
    setError(null);
    revokeBlobUrl(blobUrl);
    setBlobUrl(null);
    setDetectedContentType(null);

    try {
      const url = document.file_url || document.url;
      const { blobUrl: nextBlobUrl, contentType } = await fetchProtectedFileBlob(url, token);
      setDetectedContentType(contentType);
      setBlobUrl(nextBlobUrl);
    } catch (err) {
      console.error('Failed to load document:', err);
      setError('Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (blobUrl) {
      downloadBlobUrl(blobUrl, document?.original_filename || document?.document_type || 'document');
    }
  };

  const handleOpenInNewTab = () => {
    if (blobUrl) {
      openBlobUrlInNewTab(blobUrl, document?.original_filename || document?.document_type || 'document');
    }
  };

  const handleClose = () => {
    revokeBlobUrl(blobUrl);
    setBlobUrl(null);
    setDetectedContentType(null);
    setError(null);
    onClose();
  };

  const effectiveContentType = detectedContentType || document?.content_type || '';
  const isImage = effectiveContentType.startsWith('image/') || 
                  document?.file_url?.match(/\.(jpg|jpeg|png|gif|webp)$/i);
  const isPdf = effectiveContentType.includes('pdf') || effectiveContentType === 'application/pdf' ||
                document?.file_url?.match(/\.pdf$/i);

  const isVerified = document?.status === 'approved' || document?.status === 'verified' || document?.verified;
  const stampInfo = document?.verification_stamp ? STAMP_LABELS[document.verification_stamp] : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-[98vw] w-[98vw] h-[96vh] flex flex-col" data-testid="document-viewer-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            {document?.original_filename || document?.document_type || 'Document'}
          </DialogTitle>
        </DialogHeader>

        {/* Document Metadata */}
        <div className="flex flex-wrap items-center gap-3 py-2 border-b border-gray-200">
          {/* Verification Status */}
          {isVerified ? (
            <Badge className="bg-green-100 text-green-700 flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              Verified
            </Badge>
          ) : document?.status === 'uploaded' || document?.status === 'pending' ? (
            <Badge className="bg-amber-100 text-amber-700 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Pending Verification
            </Badge>
          ) : document?.status === 'rejected' ? (
            <Badge className="bg-red-100 text-red-700 flex items-center gap-1">
              <XCircle className="h-3 w-3" />
              Rejected
            </Badge>
          ) : (
            <Badge variant="outline">
              {document?.status || 'Unknown'}
            </Badge>
          )}

          {/* Stamp Type */}
          {stampInfo && (
            <Badge className={cn("flex items-center gap-1", stampInfo.color)}>
              <stampInfo.icon className="h-3 w-3" />
              {stampInfo.label}
            </Badge>
          )}

          {/* Upload Date */}
          {document?.uploaded_at && (
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Uploaded: {formatBackendDate(document.uploaded_at)}
            </span>
          )}

          {/* Verifier Info */}
          {document?.verified_by && (
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <User className="h-3 w-3" />
              Verified by: {document.verified_by_name || document.verified_by}
            </span>
          )}

          {/* Verification Date */}
          {document?.verified_at && (
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <Shield className="h-3 w-3" />
              on {formatBackendDate(document.verified_at)}
            </span>
          )}
        </div>

        {/* Document Preview Area */}
        <div className="flex-1 min-h-0 overflow-auto bg-gray-100 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <AlertTriangle className="h-12 w-12 mb-3 text-amber-500" />
              <p>{error}</p>
              <Button variant="outline" onClick={loadDocument} className="mt-3">
                Retry
              </Button>
            </div>
          ) : blobUrl ? (
            isImage ? (
              <div className="flex items-center justify-center p-4 h-full">
                <img 
                  src={blobUrl} 
                  alt={document?.original_filename || 'Document'} 
                  className="max-w-full max-h-full object-contain rounded shadow-lg"
                  data-testid="document-image"
                />
              </div>
            ) : isPdf ? (
              <iframe
                src={`${blobUrl}#toolbar=1&navpanes=1&scrollbar=1`}
                className="w-full h-full rounded"
                style={{ minHeight: '100%' }}
                title={document?.original_filename || 'Document'}
                data-testid="document-pdf"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <FileText className="h-16 w-16 mb-3" />
                <p className="font-medium">{document?.original_filename || 'Document'}</p>
                <p className="text-sm mt-1">Preview not available for this file type</p>
                <Button onClick={handleDownload} className="mt-4">
                  <Download className="h-4 w-4 mr-2" />
                  Download to View
                </Button>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <FileText className="h-16 w-16 mb-3" />
              <p>No document to display</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <DialogFooter className="gap-2 pt-4 border-t">
          {!isVerified && onVerify && (
            <Button 
              variant="outline" 
              onClick={() => { handleClose(); onVerify(document); }}
              className="text-primary border-primary"
              data-testid="verify-from-viewer-btn"
            >
              <Shield className="h-4 w-4 mr-2" />
              Verify with Evidence
            </Button>
          )}
          
          {blobUrl && (
            <Button 
              variant="outline" 
              onClick={handleDownload}
              data-testid="download-document-btn"
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          )}
          
          {blobUrl && (
            <Button 
              variant="outline" 
              onClick={handleOpenInNewTab}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in New Tab
            </Button>
          )}
          
          <Button variant="outline" onClick={handleClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

