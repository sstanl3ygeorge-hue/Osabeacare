/**
 * InlineDocumentViewer - Reusable modal for viewing PDF/image documents in-page.
 *
 * Fetches blobs from authenticated API endpoints and renders them inline
 * via <object>/<iframe> (PDF) or <img> (image). Handles loading, error,
 * Safari/iPhone fallback (download link), and blob URL cleanup on close.
 *
 * Props:
 *   open        - boolean controlling visibility
 *   onClose     - callback when modal is dismissed
 *   fetchUrl    - full URL to GET (with auth header); returns blob
 *   title       - dialog title
 *   token       - auth bearer token
 *   filename    - suggested download filename (optional)
 *   onFallback  - optional fallback action when the document cannot be loaded
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Loader2, Download, AlertTriangle, FileText, ExternalLink } from 'lucide-react';
import axios from 'axios';

// Detect Safari/iOS for fallback — they cannot render blob-URL PDFs in iframes
const isSafari = () => {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent;
  return /^((?!chrome|android).)*safari/i.test(ua) || /iPad|iPhone|iPod/.test(ua);
};

export default function InlineDocumentViewer({
  open,
  onClose,
  fetchUrl,
  title = 'Document',
  token,
  filename = 'document',
  fallbackLabel,
  onFallback,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);
  const [contentType, setContentType] = useState(null);
  const blobUrlRef = useRef(null);

  const revoke = useCallback(() => {
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
  }, []);

  // Fetch blob when dialog opens
  useEffect(() => {
    if (!open || !fetchUrl) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    revoke();

    (async () => {
      try {
        const resp = await axios.get(fetchUrl, {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob',
        });
        if (cancelled) return;

        const ct = resp.headers['content-type'] || 'application/octet-stream';
        const blob = new Blob([resp.data], { type: ct });
        const url = URL.createObjectURL(blob);
        blobUrlRef.current = url;
        setBlobUrl(url);
        setContentType(ct.split(';')[0].trim());
      } catch (err) {
        if (cancelled) return;
        let detail = 'Failed to load document';
        if (err.response?.data instanceof Blob) {
          try {
            const text = await err.response.data.text();
            const parsed = JSON.parse(text);
            if (parsed.detail) detail = parsed.detail;
          } catch (_) { /* keep default */ }
        } else if (err.response?.data?.detail) {
          detail = err.response.data.detail;
        }
        setError(detail);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [open, fetchUrl, token, revoke]);

  // Cleanup blob URL when closing
  const handleClose = () => {
    revoke();
    setBlobUrl(null);
    setContentType(null);
    setError(null);
    onClose();
  };

  // Unmount cleanup
  useEffect(() => revoke, [revoke]);

  const isPdf = contentType === 'application/pdf';
  const isImage = contentType?.startsWith('image/');
  const safariPdfFallback = isPdf && isSafari();

  const handleDownload = () => {
    if (!blobUrl) return;
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[92vh] flex flex-col" data-testid="inline-document-viewer">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5 text-primary flex-shrink-0" />
            <span className="truncate">{title}</span>
          </DialogTitle>
        </DialogHeader>

        {/* Preview area */}
        <div className="flex-1 min-h-[450px] overflow-auto bg-gray-100 rounded-lg relative">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-gray-500">Loading document…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3 px-6 text-center">
              <AlertTriangle className="h-12 w-12 text-amber-500" />
              <p className="font-medium">{error}</p>
              <Button variant="outline" size="sm" onClick={() => {
                revoke();
                setBlobUrl(null);
                setError(null);
                setLoading(true);
                // Re-trigger by toggling fetchUrl dependency isn't possible, so
                // just close & reopen. For now surface a retry.
                const refetch = async () => {
                  try {
                    const resp = await axios.get(fetchUrl, {
                      headers: { Authorization: `Bearer ${token}` },
                      responseType: 'blob',
                    });
                    const ct = resp.headers['content-type'] || 'application/octet-stream';
                    const blob = new Blob([resp.data], { type: ct });
                    const url = URL.createObjectURL(blob);
                    blobUrlRef.current = url;
                    setBlobUrl(url);
                    setContentType(ct.split(';')[0].trim());
                  } catch (_) {
                    setError('Retry failed. Try downloading instead.');
                  } finally {
                    setLoading(false);
                  }
                };
                refetch();
              }}>
                Retry
              </Button>
              {onFallback && (
                <Button variant="outline" size="sm" onClick={onFallback}>
                  {fallbackLabel || 'Use fallback view'}
                </Button>
              )}
            </div>
          ) : blobUrl && isPdf && !safariPdfFallback ? (
            <object
              data={blobUrl}
              type="application/pdf"
              className="w-full h-full min-h-[550px] rounded"
              title={title}
            >
              {/* Fallback if <object> fails */}
              <iframe
                src={blobUrl}
                className="w-full h-full min-h-[550px] rounded"
                title={title}
              />
            </object>
          ) : blobUrl && isImage ? (
            <div className="flex items-center justify-center p-4 h-full">
              <img
                src={blobUrl}
                alt={title}
                className="max-w-full max-h-[70vh] object-contain rounded shadow-lg"
              />
            </div>
          ) : blobUrl && safariPdfFallback ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
              <FileText className="h-16 w-16" />
              <p className="font-medium">PDF preview is not supported on this browser</p>
              <Button onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Download PDF
              </Button>
            </div>
          ) : blobUrl ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
              <FileText className="h-16 w-16" />
              <p className="font-medium">{filename}</p>
              <p className="text-sm">Preview not available for this file type</p>
              <Button onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Download to View
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>No document to display</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="gap-2 pt-3 border-t">
          {blobUrl && (
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          )}
          {blobUrl && (
            <Button variant="outline" size="sm" onClick={() => window.open(blobUrl, '_blank', 'noopener')}>
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in New Tab
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
