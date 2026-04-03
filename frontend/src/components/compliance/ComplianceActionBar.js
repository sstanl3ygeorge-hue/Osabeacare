import { Button } from '../ui/button';
import { 
  Upload, Send, Download
} from 'lucide-react';

/**
 * ComplianceActionBar - Simplified toolbar for Compliance File
 * 
 * Actions (streamlined):
 * - Upload Evidence - Opens document uploader
 * - Request Documents - Bulk request via email
 * - Export File - Download compliance file (right-aligned)
 * 
 * Removed: Enter Check dropdown (moved to ApprovalStatusPanel/NextActionsPanel)
 */
export default function ComplianceActionBar({
  onUploadEvidence,
  onRequestMissing,
  onExport,
  missingCount = 0,
  hasEmail = false,
  isAuditor = false,
  isExporting = false
}) {

  if (isAuditor) {
    // Auditors only see Export
    return (
      <div className="flex items-center justify-end gap-2 p-3 bg-gray-50 border border-gray-200 rounded-xl mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={onExport}
          disabled={isExporting}
          className="h-8 text-sm rounded-lg"
          data-testid="export-compliance-file"
        >
          <Download className="h-4 w-4 mr-2" />
          Export File
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl mb-6" data-testid="compliance-action-bar">
      <div className="flex items-center gap-2">
        {/* Upload Evidence */}
        <Button
          variant="default"
          size="sm"
          onClick={onUploadEvidence}
          className="h-8 text-sm bg-primary hover:bg-primary-hover text-white rounded-lg"
          data-testid="action-upload-evidence"
        >
          <Upload className="h-4 w-4 mr-1.5" />
          Upload Evidence
        </Button>

        {/* Request Documents */}
        {hasEmail && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRequestMissing}
            disabled={missingCount === 0}
            className="h-8 text-sm border-slate-300 text-slate-700 hover:bg-white rounded-lg"
            data-testid="action-request-missing"
          >
            <Send className="h-4 w-4 mr-1.5" />
            Request Documents
            {missingCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-[10px] bg-slate-200 text-slate-700 rounded font-medium">
                {missingCount}
              </span>
            )}
          </Button>
        )}
      </div>

      {/* Export - Right aligned */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onExport}
        disabled={isExporting}
        className="h-8 text-sm text-slate-500 hover:text-slate-700 rounded-lg"
        data-testid="action-export-file"
      >
        <Download className="h-4 w-4 mr-1.5" />
        Export
      </Button>
    </div>
  );
}
