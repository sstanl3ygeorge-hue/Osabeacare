import { useState, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Slider } from '../ui/slider';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';
import { 
  X, Download, ZoomIn, ZoomOut, RotateCw,
  ChevronLeft, ChevronRight, Loader2, FileText, Image as ImageIcon,
  File, AlertCircle, Maximize2, Minimize2, ShieldCheck
} from 'lucide-react';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const FILE_TYPE_ICONS = {
  pdf: FileText,
  image: ImageIcon,
  other: File
};

const getFileType = (contentType, filename) => {
  if (contentType?.includes('pdf') || filename?.toLowerCase().endsWith('.pdf')) {
    return 'pdf';
  }
  if (contentType?.includes('image') || /\.(jpg|jpeg|png|gif|webp|svg|bmp)$/i.test(filename || '')) {
    return 'image';
  }
  return 'other';
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown size';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

export default function DocumentPreviewModal({ 
  isOpen, 
  onClose, 
  fileUrl, 
  fileName, 
  fileType: providedFileType,
  fileSize,
  token,
  onDownload,
  // Original/Stamped toggle support
  stampedFileUrl,
  // Stamp metadata for "Verified copy" badge
  verificationStampByName,
  verificationStampAt,
  // Multi-file support
  files = [],  // Array of {url, filename, content_type, file_id}
  initialFileIndex = 0
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);
  const [contentType, setContentType] = useState(null);
  const [actualFileSize, setActualFileSize] = useState(fileSize);
  
  // Original/Stamped toggle
  const [viewingStamped, setViewingStamped] = useState(!!stampedFileUrl);
  
  // Multi-file navigation state
  const [currentFileIndex, setCurrentFileIndex] = useState(initialFileIndex);
  
  // Get current file from array or use single file props
  const allFiles = files.length > 0 ? files : (fileUrl ? [{ url: fileUrl, filename: fileName, content_type: providedFileType }] : []);
  const currentFile = allFiles[currentFileIndex] || {};
  const baseFileUrl = currentFile.url || fileUrl;
  const activeFileUrl = (stampedFileUrl && viewingStamped) ? stampedFileUrl : baseFileUrl;
  const activeFileName = currentFile.filename || currentFile.file_label || fileName;
  const hasMultipleFiles = allFiles.length > 1;
  
  // Reset stamped toggle when prop changes
  useEffect(() => {
    setViewingStamped(!!stampedFileUrl);
  }, [stampedFileUrl]);

  // PDF specific state
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Determine file type
  const fileType = currentFile.content_type ? getFileType(currentFile.content_type, activeFileName) : (providedFileType || getFileType(contentType, activeFileName));
  const FileIcon = FILE_TYPE_ICONS[fileType] || File;

  // Navigate to next/previous file
  const goToNextFile = () => {
    if (currentFileIndex < allFiles.length - 1) {
      setCurrentFileIndex(currentFileIndex + 1);
    }
  };
  
  const goToPrevFile = () => {
    if (currentFileIndex > 0) {
      setCurrentFileIndex(currentFileIndex - 1);
    }
  };

  // Fetch file with authentication
  useEffect(() => {
    if (!isOpen || !activeFileUrl) return;
    
    let isMounted = true;
    setLoading(true);
    setError(null);
    setBlobUrl(null);
    setCurrentPage(1);
    setScale(1.0);
    setRotation(0);
    
    const fetchFile = async () => {
      try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const response = await fetch(activeFileUrl, { headers });
        
        if (!response.ok) {
          throw new Error(`Failed to load file: ${response.status}`);
        }
        
        const blob = await response.blob();
        const type = response.headers.get('content-type') || blob.type;
        
        if (isMounted) {
          setContentType(type);
          setActualFileSize(blob.size);
          setBlobUrl(URL.createObjectURL(blob));
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to load file:', err);
        if (isMounted) {
          setError(err.message || 'Failed to load file');
          setLoading(false);
        }
      }
    };
    
    fetchFile();
    
    return () => {
      isMounted = false;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [isOpen, activeFileUrl, token, currentFileIndex]);

  // Clean up blob URL on close
  useEffect(() => {
    if (!isOpen && blobUrl) {
      URL.revokeObjectURL(blobUrl);
      setBlobUrl(null);
    }
  }, [isOpen, blobUrl]);

  // PDF document load success
  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
  }, []);

  // PDF navigation
  const goToPrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const goToNextPage = () => setCurrentPage(prev => Math.min(prev + 1, numPages || 1));
  
  // Zoom controls
  const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const resetZoom = () => setScale(1.0);
  const fitToWidth = () => setScale(1.2);
  
  // Rotation
  const rotate = () => setRotation(prev => (prev + 90) % 360);
  
  // Download handler
  const handleDownload = () => {
    // When viewing stamped version, download from blob (correct version)
    if (viewingStamped && stampedFileUrl && blobUrl) {
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `stamped_${activeFileName || 'document'}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      return;
    }
    if (onDownload) {
      onDownload();
    } else if (blobUrl) {
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = activeFileName || 'document';
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
  };
  
  // Toggle fullscreen
  const toggleFullscreen = () => setIsFullscreen(prev => !prev);

  // Render PDF content
  const renderPdfContent = () => (
    <div className="flex flex-col h-full">
      {/* PDF Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
        {/* Page Navigation */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={goToPrevPage}
            disabled={currentPage <= 1}
            className="h-8 w-8 p-0"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium min-w-[80px] text-center">
            Page {currentPage} of {numPages || '?'}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={goToNextPage}
            disabled={currentPage >= (numPages || 1)}
            className="h-8 w-8 p-0"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="h-8 w-8 p-0"
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          
          <div className="w-24 hidden sm:block">
            <Slider
              value={[scale * 100]}
              onValueChange={([val]) => setScale(val / 100)}
              min={50}
              max={300}
              step={10}
              className="w-full"
            />
          </div>
          
          <span className="text-sm font-medium w-14 text-center">
            {Math.round(scale * 100)}%
          </span>
          
          <Button
            variant="outline"
            size="sm"
            onClick={zoomIn}
            disabled={scale >= 3}
            className="h-8 w-8 p-0"
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          
          <div className="h-4 w-px bg-gray-300 mx-1" />
          
          <Button
            variant="outline"
            size="sm"
            onClick={rotate}
            className="h-8 w-8 p-0"
            title="Rotate"
          >
            <RotateCw className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      {/* PDF Viewer */}
      <div className="flex-1 overflow-auto bg-gray-100 flex justify-center p-4">
        <Document
          file={blobUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          }
          error={
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-amber-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Preview unavailable
              </h3>
              <p className="text-gray-500 mb-6 max-w-md">
                This PDF cannot be displayed in the embedded viewer. You can still access the file using the options below.
              </p>
              <div className="flex gap-3">
                <Button variant="outline" onClick={handleDownload}>
                  <Download className="h-4 w-4 mr-2" />
                  Download File
                </Button>
              </div>
            </div>
          }
        >
          <Page
            pageNumber={currentPage}
            scale={scale}
            rotate={rotation}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            className="shadow-lg"
          />
        </Document>
      </div>
    </div>
  );

  // Render image content
  const renderImageContent = () => (
    <div className="flex flex-col h-full">
      {/* Image Toolbar */}
      <div className="flex items-center justify-center px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="h-8 w-8 p-0"
            title="Zoom out"
            data-testid="image-zoom-out"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          
          <span className="text-sm font-medium w-14 text-center">
            {Math.round(scale * 100)}%
          </span>
          
          <Button
            variant="outline"
            size="sm"
            onClick={zoomIn}
            disabled={scale >= 3}
            className="h-8 w-8 p-0"
            title="Zoom in"
            data-testid="image-zoom-in"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={resetZoom}
            className="h-8 px-2"
            data-testid="image-reset-zoom"
          >
            Reset
          </Button>
          
          <div className="h-4 w-px bg-gray-300 mx-1" />
          
          {/* Rotate Controls */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRotation(prev => (prev - 90 + 360) % 360)}
            className="h-8 w-8 p-0"
            title="Rotate left (-90°)"
            data-testid="image-rotate-left"
          >
            <RotateCw className="h-4 w-4 transform -scale-x-100" />
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRotation(prev => (prev + 90) % 360)}
            className="h-8 w-8 p-0"
            title="Rotate right (+90°)"
            data-testid="image-rotate-right"
          >
            <RotateCw className="h-4 w-4" />
          </Button>
          
          {rotation !== 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRotation(0)}
              className="h-8 px-2 text-xs text-gray-500"
              title="Reset rotation"
              data-testid="image-reset-rotation"
            >
              {rotation}°
            </Button>
          )}
        </div>
      </div>
      
      {/* Image Viewer */}
      <div className="flex-1 overflow-auto bg-gray-100 flex items-center justify-center p-4">
        <img
          src={blobUrl}
          alt={fileName}
          style={{ 
            transform: `scale(${scale}) rotate(${rotation}deg)`, 
            transformOrigin: 'center' 
          }}
          className="max-w-full max-h-full object-contain shadow-lg transition-transform duration-200"
          data-testid="image-preview"
        />
      </div>
    </div>
  );

  // Render unsupported file type
  const renderUnsupportedContent = () => (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <FileIcon className="h-10 w-10 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Preview not available
      </h3>
      <p className="text-gray-500 mb-1">
        {fileName || 'This file'} cannot be previewed in the browser.
      </p>
      <p className="text-sm text-gray-400 mb-6">
        {contentType && `File type: ${contentType}`}
        {actualFileSize && ` • ${formatFileSize(actualFileSize)}`}
      </p>
      <div className="flex gap-3">
        <Button onClick={handleDownload} className="bg-primary hover:bg-primary-hover text-white">
          <Download className="h-4 w-4 mr-2" />
          Download File
        </Button>
      </div>
    </div>
  );

  // Render error state - with fallback options to still access the file
  const renderError = () => (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="w-20 h-20 rounded-full bg-amber-50 flex items-center justify-center mb-4">
        <AlertCircle className="h-10 w-10 text-amber-500" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Preview unavailable
      </h3>
      <p className="text-gray-500 mb-2">
        {error || 'Unable to display this file in the browser.'}
      </p>
      <p className="text-sm text-gray-400 mb-6">
        Try downloading the file directly.
      </p>
      <div className="flex gap-3">
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>
    </div>
  );

  // Render loading state
  const renderLoading = () => (
    <div className="flex flex-col items-center justify-center h-full">
      <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
      <p className="text-gray-500">Loading document...</p>
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent 
        className={`
          p-0 gap-0 bg-white flex flex-col
          ${isFullscreen 
            ? 'max-w-[100vw] w-[100vw] h-[100vh] rounded-none' 
            : 'max-w-[98vw] w-[98vw] h-[96vh] rounded-xl'
          }
        `}
        data-testid="document-preview-modal"
      >
        {/* Accessibility: Hidden title and description for screen readers */}
        <VisuallyHidden>
          <DialogTitle>{activeFileName || 'Document Preview'}</DialogTitle>
          <DialogDescription>
            Preview of {activeFileName || 'document'}. Use the toolbar to navigate pages, zoom, and download.
          </DialogDescription>
        </VisuallyHidden>
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0 rounded-t-xl">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
              <FileIcon className="h-5 w-5 text-gray-600" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold text-gray-900 truncate" title={activeFileName}>
                {activeFileName || 'Document'}
              </h2>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className="uppercase">{fileType}</span>
                {actualFileSize && (
                  <>
                    <span>•</span>
                    <span>{formatFileSize(actualFileSize)}</span>
                  </>
                )}
                {/* Multi-file indicator */}
                {hasMultipleFiles && (
                  <>
                    <span>•</span>
                    <span className="text-primary font-medium">
                      File {currentFileIndex + 1} of {allFiles.length}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          
          {/* Original / Stamped toggle */}
          {stampedFileUrl && (
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5 gap-0.5 mr-3 shrink-0">
              <button
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  !viewingStamped
                    ? 'bg-white shadow-sm text-gray-900'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                onClick={() => setViewingStamped(false)}
              >
                Original
              </button>
              <button
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1 ${
                  viewingStamped
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                onClick={() => setViewingStamped(true)}
              >
                <ShieldCheck className="h-3 w-3" />
                Stamped
              </button>
            </div>
          )}

          {/* Verified copy badge — shown when viewing the stamped version */}
          {stampedFileUrl && viewingStamped && (
            <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5 mr-3 shrink-0">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <div className="flex flex-col leading-tight">
                <span className="text-xs font-semibold text-emerald-700">Verified copy</span>
                {(verificationStampByName || verificationStampAt) && (
                  <span className="text-[10px] text-emerald-600">
                    {verificationStampByName && `by ${verificationStampByName}`}
                    {verificationStampByName && verificationStampAt && ' · '}
                    {verificationStampAt && new Date(verificationStampAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Multi-file navigation */}
          {hasMultipleFiles && (
            <div className="flex items-center gap-1 mr-4">
              <Button
                variant="outline"
                size="sm"
                onClick={goToPrevFile}
                disabled={currentFileIndex === 0}
                className="h-8 px-3"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Prev
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={goToNextFile}
                disabled={currentFileIndex === allFiles.length - 1}
                className="h-8 px-3"
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
          
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="hidden sm:flex"
              disabled={loading || error}
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8 w-8 p-0"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Mobile Actions */}
        <div className="flex sm:hidden items-center justify-center gap-2 px-4 py-2 border-b border-gray-200 bg-gray-50">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={loading || error}
            className="flex-1"
          >
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          {loading && renderLoading()}
          {error && renderError()}
          {!loading && !error && fileType === 'pdf' && renderPdfContent()}
          {!loading && !error && fileType === 'image' && renderImageContent()}
          {!loading && !error && fileType === 'other' && renderUnsupportedContent()}
        </div>
      </DialogContent>
    </Dialog>
  );
}
