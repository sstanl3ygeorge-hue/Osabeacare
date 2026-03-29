import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, X, Check, AlertCircle, Loader2, File, Image } from 'lucide-react';
import { Button } from './button';
import { cn } from '../../lib/utils';

/**
 * FileUploader - Reusable drag-and-drop file upload component
 * 
 * Features:
 * - Click to upload
 * - Drag and drop on desktop
 * - Multiple file support
 * - Upload progress
 * - File validation (type, size)
 * - Mobile-safe (tap upload still primary)
 * - Clear error messages
 * 
 * @param {function} onUpload - Callback when file(s) are ready to upload. Receives File or File[]
 * @param {function} onUploadComplete - Callback when upload succeeds
 * @param {function} onUploadError - Callback when upload fails
 * @param {boolean} multiple - Allow multiple file selection
 * @param {string[]} acceptedTypes - Accepted MIME types (default: PDF, JPG, PNG)
 * @param {number} maxSizeBytes - Max file size in bytes (default: 10MB)
 * @param {string} uploadEndpoint - API endpoint for upload (if provided, component handles upload)
 * @param {object} uploadHeaders - Headers for the upload request
 * @param {object} uploadData - Additional form data to send with upload
 * @param {string} uploadFieldName - Form field name for file (default: 'file')
 * @param {boolean} disabled - Disable the uploader
 * @param {string} className - Additional CSS classes
 * @param {string} label - Custom label text
 * @param {string} description - Custom description text
 * @param {boolean} compact - Use compact mode (smaller height)
 * @param {boolean} showPreview - Show file preview before upload
 */
export function FileUploader({
  onUpload,
  onUploadComplete,
  onUploadError,
  multiple = false,
  acceptedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'],
  maxSizeBytes = 10 * 1024 * 1024, // 10MB default
  uploadEndpoint,
  uploadHeaders = {},
  uploadData = {},
  uploadFieldName = 'file',
  disabled = false,
  className,
  label,
  description,
  compact = false,
  showPreview = true
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploadStatus, setUploadStatus] = useState({}); // 'pending' | 'uploading' | 'success' | 'error'
  const [errors, setErrors] = useState([]);
  const fileInputRef = useRef(null);

  // File type display mapping
  const fileTypeLabels = {
    'application/pdf': 'PDF',
    'image/jpeg': 'JPG',
    'image/jpg': 'JPG',
    'image/png': 'PNG',
    'image/webp': 'WEBP',
    'image/gif': 'GIF'
  };

  // Get file extension from MIME type
  const getAcceptString = () => {
    const extensions = acceptedTypes.map(type => {
      switch (type) {
        case 'application/pdf': return '.pdf';
        case 'image/jpeg': return '.jpg,.jpeg';
        case 'image/jpg': return '.jpg,.jpeg';
        case 'image/png': return '.png';
        case 'image/webp': return '.webp';
        case 'image/gif': return '.gif';
        default: return '';
      }
    });
    return extensions.filter(Boolean).join(',');
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Validate file
  const validateFile = (file) => {
    const errors = [];
    
    // Check file type
    if (!acceptedTypes.includes(file.type)) {
      const allowedTypes = acceptedTypes.map(t => fileTypeLabels[t] || t).join(', ');
      errors.push(`Invalid file type. Allowed: ${allowedTypes}`);
    }
    
    // Check file size
    if (file.size > maxSizeBytes) {
      errors.push(`File too large. Maximum size: ${formatFileSize(maxSizeBytes)}`);
    }
    
    // Check for safe filename
    const dangerousChars = /[<>:"/\\|?*]/;
    if (dangerousChars.test(file.name)) {
      errors.push('Filename contains invalid characters');
    }
    
    return errors;
  };

  // Process files (validate and add to selected)
  const processFiles = useCallback((files) => {
    const fileArray = Array.from(files);
    const newErrors = [];
    const validFiles = [];
    
    fileArray.forEach(file => {
      const fileErrors = validateFile(file);
      if (fileErrors.length > 0) {
        newErrors.push(`${file.name}: ${fileErrors.join(', ')}`);
      } else {
        validFiles.push(file);
      }
    });
    
    setErrors(newErrors);
    
    if (validFiles.length > 0) {
      if (multiple) {
        setSelectedFiles(prev => [...prev, ...validFiles]);
      } else {
        setSelectedFiles(validFiles.slice(0, 1));
      }
      
      // If onUpload callback provided and no endpoint, call it
      if (onUpload && !uploadEndpoint) {
        onUpload(multiple ? validFiles : validFiles[0]);
      }
    }
  }, [multiple, acceptedTypes, maxSizeBytes, onUpload, uploadEndpoint]);

  // Handle drag events
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    if (disabled) return;
    
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      processFiles(files);
    }
  };

  // Handle click to upload
  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Handle file input change
  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFiles(files);
    }
    // Reset input value so same file can be selected again
    e.target.value = '';
  };

  // Remove a selected file
  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[index];
      return newProgress;
    });
    setUploadStatus(prev => {
      const newStatus = { ...prev };
      delete newStatus[index];
      return newStatus;
    });
  };

  // Upload files (if endpoint provided)
  const uploadFiles = async () => {
    if (!uploadEndpoint || selectedFiles.length === 0) return;
    
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      setUploadStatus(prev => ({ ...prev, [i]: 'uploading' }));
      setUploadProgress(prev => ({ ...prev, [i]: 0 }));
      
      try {
        const formData = new FormData();
        formData.append(uploadFieldName, file);
        
        // Add additional data
        Object.entries(uploadData).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            formData.append(key, value);
          }
        });
        
        const response = await fetch(uploadEndpoint, {
          method: 'POST',
          headers: uploadHeaders,
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Upload failed');
        }
        
        setUploadProgress(prev => ({ ...prev, [i]: 100 }));
        setUploadStatus(prev => ({ ...prev, [i]: 'success' }));
        
        if (onUploadComplete) {
          const responseData = await response.json().catch(() => ({}));
          onUploadComplete(file, responseData);
        }
      } catch (error) {
        setUploadStatus(prev => ({ ...prev, [i]: 'error' }));
        setErrors(prev => [...prev, `${file.name}: ${error.message}`]);
        if (onUploadError) {
          onUploadError(file, error);
        }
      }
    }
  };

  // Clear all files
  const clearFiles = () => {
    setSelectedFiles([]);
    setUploadProgress({});
    setUploadStatus({});
    setErrors([]);
  };

  // Get file icon
  const getFileIcon = (file) => {
    if (file.type.startsWith('image/')) {
      return <Image className="h-5 w-5 text-blue-500" />;
    }
    if (file.type === 'application/pdf') {
      return <FileText className="h-5 w-5 text-red-500" />;
    }
    return <File className="h-5 w-5 text-gray-500" />;
  };

  return (
    <div className={cn("w-full", className)}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={getAcceptString()}
        multiple={multiple}
        onChange={handleFileInputChange}
        disabled={disabled}
        data-testid="file-uploader-input"
      />
      
      {/* Drop zone */}
      <div
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          "relative border-2 border-dashed rounded-xl transition-all cursor-pointer",
          compact ? "p-4" : "p-6",
          isDragOver && !disabled
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-gray-300 hover:border-primary/50 hover:bg-gray-50",
          disabled && "opacity-50 cursor-not-allowed bg-gray-100",
          selectedFiles.length > 0 && showPreview && "border-solid border-primary/30"
        )}
        data-testid="file-uploader-dropzone"
      >
        {/* Drag overlay */}
        {isDragOver && !disabled && (
          <div className="absolute inset-0 bg-primary/10 rounded-xl flex items-center justify-center z-10">
            <div className="text-center">
              <Upload className="h-10 w-10 text-primary mx-auto mb-2 animate-bounce" />
              <p className="text-primary font-semibold">Drop files here</p>
            </div>
          </div>
        )}
        
        {/* Default state */}
        {selectedFiles.length === 0 && (
          <div className={cn("text-center", isDragOver && "opacity-0")}>
            <Upload className={cn(
              "mx-auto text-gray-400",
              compact ? "h-8 w-8 mb-2" : "h-12 w-12 mb-3"
            )} />
            <p className={cn(
              "font-medium text-text-primary",
              compact ? "text-sm" : "text-base"
            )}>
              {label || (multiple ? 'Drop files here or click to upload' : 'Drop file here or click to upload')}
            </p>
            <p className={cn(
              "text-text-muted mt-1",
              compact ? "text-xs" : "text-sm"
            )}>
              {description || `Supports: ${acceptedTypes.map(t => fileTypeLabels[t] || t).join(', ')} (max ${formatFileSize(maxSizeBytes)})`}
            </p>
          </div>
        )}
        
        {/* Selected files preview */}
        {selectedFiles.length > 0 && showPreview && (
          <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className={cn(
                  "flex items-center gap-3 p-3 bg-white rounded-lg border",
                  uploadStatus[index] === 'success' && "border-green-200 bg-green-50",
                  uploadStatus[index] === 'error' && "border-red-200 bg-red-50",
                  uploadStatus[index] === 'uploading' && "border-blue-200 bg-blue-50"
                )}
              >
                {/* File icon / thumbnail */}
                <div className="flex-shrink-0">
                  {file.type.startsWith('image/') ? (
                    <img
                      src={URL.createObjectURL(file)}
                      alt={file.name}
                      className="h-10 w-10 object-cover rounded"
                    />
                  ) : (
                    getFileIcon(file)
                  )}
                </div>
                
                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-text-muted">
                    {formatFileSize(file.size)}
                  </p>
                  
                  {/* Progress bar */}
                  {uploadStatus[index] === 'uploading' && (
                    <div className="mt-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${uploadProgress[index] || 0}%` }}
                      />
                    </div>
                  )}
                </div>
                
                {/* Status / Actions */}
                <div className="flex-shrink-0">
                  {uploadStatus[index] === 'uploading' && (
                    <Loader2 className="h-5 w-5 text-primary animate-spin" />
                  )}
                  {uploadStatus[index] === 'success' && (
                    <Check className="h-5 w-5 text-green-500" />
                  )}
                  {uploadStatus[index] === 'error' && (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                  {!uploadStatus[index] && (
                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="p-1 hover:bg-gray-100 rounded-full transition-colors"
                    >
                      <X className="h-4 w-4 text-gray-500" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            
            {/* Add more / Clear buttons */}
            <div className="flex items-center gap-2 pt-2">
              {multiple && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleClick}
                  className="text-xs"
                >
                  <Upload className="h-3 w-3 mr-1" />
                  Add More
                </Button>
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={clearFiles}
                className="text-xs text-text-muted"
              >
                Clear All
              </Button>
              
              {/* Upload button if endpoint provided */}
              {uploadEndpoint && selectedFiles.some((_, i) => !uploadStatus[i]) && (
                <Button
                  type="button"
                  size="sm"
                  onClick={uploadFiles}
                  className="ml-auto"
                  disabled={disabled}
                >
                  <Upload className="h-3 w-3 mr-1" />
                  Upload {selectedFiles.filter((_, i) => !uploadStatus[i]).length} file(s)
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Error messages */}
      {errors.length > 0 && (
        <div className="mt-2 space-y-1">
          {errors.map((error, index) => (
            <div
              key={index}
              className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-2 rounded-lg"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setErrors(prev => prev.filter((_, i) => i !== index))}
                className="ml-auto p-0.5 hover:bg-red-100 rounded"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Inline variant - smaller, for use within forms
 */
export function FileUploaderInline({
  onFileSelect,
  selectedFile,
  onClear,
  acceptedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'],
  maxSizeBytes = 10 * 1024 * 1024,
  disabled = false,
  placeholder = 'Choose file or drag here',
  error,
  className
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const fileInputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const validateFile = (file) => {
    if (!acceptedTypes.includes(file.type)) {
      return 'Invalid file type';
    }
    if (file.size > maxSizeBytes) {
      return `File too large (max ${formatFileSize(maxSizeBytes)})`;
    }
    return null;
  };

  const handleFile = (file) => {
    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    onFileSelect(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  };

  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = '';
  };

  const getAcceptString = () => {
    return acceptedTypes.map(type => {
      switch (type) {
        case 'application/pdf': return '.pdf';
        case 'image/jpeg': case 'image/jpg': return '.jpg,.jpeg';
        case 'image/png': return '.png';
        default: return '';
      }
    }).filter(Boolean).join(',');
  };

  return (
    <div className={className}>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={getAcceptString()}
        onChange={handleChange}
        disabled={disabled}
      />
      
      <div
        onClick={() => !disabled && fileInputRef.current?.click()}
        onDragEnter={(e) => { e.preventDefault(); !disabled && setIsDragOver(true); }}
        onDragLeave={(e) => { e.preventDefault(); setIsDragOver(false); }}
        onDragOver={(e) => { e.preventDefault(); !disabled && setIsDragOver(true); }}
        onDrop={handleDrop}
        className={cn(
          "flex items-center gap-3 p-3 border-2 border-dashed rounded-lg cursor-pointer transition-all",
          isDragOver ? "border-primary bg-primary/5" : "border-gray-300 hover:border-primary/50",
          disabled && "opacity-50 cursor-not-allowed",
          selectedFile && "border-solid border-green-300 bg-green-50",
          (error || validationError) && "border-red-300 bg-red-50"
        )}
      >
        {selectedFile ? (
          <>
            <FileText className="h-5 w-5 text-green-600 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">{selectedFile.name}</p>
              <p className="text-xs text-text-muted">{formatFileSize(selectedFile.size)}</p>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onClear?.(); }}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="h-4 w-4 text-gray-500" />
            </button>
          </>
        ) : (
          <>
            <Upload className={cn("h-5 w-5 flex-shrink-0", isDragOver ? "text-primary" : "text-gray-400")} />
            <span className="text-sm text-text-muted">{placeholder}</span>
          </>
        )}
      </div>
      
      {(error || validationError) && (
        <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {error || validationError}
        </p>
      )}
    </div>
  );
}

export default FileUploader;
