import { useState } from 'react';
import { Button } from '../ui/button';
import { 
  Upload, Send, Shield, Download, ChevronDown
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';

/**
 * ComplianceActionBar - Global action buttons for Compliance File
 * 
 * Actions:
 * - Upload Evidence - Opens document uploader
 * - Request Missing Items - Bulk request via email
 * - Enter Check - Opens check dialog (RTW/DBS/Identity)
 * - Export File - Download compliance file
 */
export default function ComplianceActionBar({
  onUploadEvidence,
  onRequestMissing,
  onEnterCheck,
  onExport,
  missingCount = 0,
  hasEmail = false,
  isAuditor = false,
  isExporting = false
}) {
  // Check types for the Enter Check dropdown
  const checkTypes = [
    { key: 'right_to_work_check', label: 'Right to Work Check', icon: '🛂' },
    { key: 'dbs_status_check', label: 'DBS Status Check', icon: '🛡️' },
    { key: 'identity_verification', label: 'Identity Verification', icon: '🪪' },
    { key: 'address_verification', label: 'Address Verification', icon: '📍' }
  ];

  if (isAuditor) {
    // Auditors only see Export
    return (
      <div className="flex items-center justify-end gap-2 p-4 bg-gray-50 border border-gray-200 rounded-xl mb-6">
        <Button
          variant="outline"
          size="sm"
          onClick={onExport}
          disabled={isExporting}
          className="h-9 text-sm rounded-lg"
          data-testid="export-compliance-file"
        >
          <Download className="h-4 w-4 mr-2" />
          Export File
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between gap-3 p-4 bg-white border border-gray-200 rounded-xl mb-6 shadow-sm" data-testid="compliance-action-bar">
      <div className="flex items-center gap-2 flex-wrap">
        {/* Upload Evidence */}
        <Button
          variant="default"
          size="sm"
          onClick={onUploadEvidence}
          className="h-9 text-sm bg-primary hover:bg-primary-hover text-white rounded-lg"
          data-testid="action-upload-evidence"
        >
          <Upload className="h-4 w-4 mr-2" />
          Upload Evidence
        </Button>

        {/* Request Missing Items */}
        {hasEmail && missingCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRequestMissing}
            className="h-9 text-sm border-blue-200 text-blue-600 hover:bg-blue-50 rounded-lg"
            data-testid="action-request-missing"
          >
            <Send className="h-4 w-4 mr-2" />
            Request Missing Items
            {missingCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                {missingCount}
              </span>
            )}
          </Button>
        )}

        {/* Enter Check - Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-9 text-sm border-green-200 text-green-700 hover:bg-green-50 rounded-lg"
              data-testid="action-enter-check"
            >
              <Shield className="h-4 w-4 mr-2" />
              Enter Check
              <ChevronDown className="h-3 w-3 ml-1" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            {checkTypes.map((check) => (
              <DropdownMenuItem
                key={check.key}
                onClick={() => onEnterCheck && onEnterCheck(check.key)}
                className="cursor-pointer"
                data-testid={`enter-check-${check.key}`}
              >
                <span className="mr-2">{check.icon}</span>
                {check.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Export */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onExport}
        disabled={isExporting}
        className="h-9 text-sm text-text-muted hover:text-text-primary rounded-lg"
        data-testid="action-export-file"
      >
        <Download className="h-4 w-4 mr-2" />
        Export
      </Button>
    </div>
  );
}
