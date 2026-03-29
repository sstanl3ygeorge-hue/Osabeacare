import React from 'react';
import { cn } from '../../lib/utils';
import { Button } from './button';
import { StatusBadge, ExpiryBadge } from './status-badge';
import {
  Eye,
  Download,
  Upload,
  Edit,
  Trash2,
  CheckCircle,
  MoreVertical,
  FileText,
  GraduationCap,
  Shield,
  AlertTriangle,
  ChevronRight
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './dropdown-menu';

/**
 * RequirementRow - Unified row component for documents, training, and compliance items
 * 
 * @param {string} title - Item title/name
 * @param {string} subtitle - Secondary text (e.g., completion date, file name)
 * @param {string} status - Status string for badge
 * @param {string} type - 'document' | 'training' | 'form' | 'acknowledgement'
 * @param {object} expiry - { date, daysUntilExpiry, status }
 * @param {array} badges - Additional badges to show [{ label, variant }]
 * @param {array} actions - Action buttons [{ icon, label, onClick, variant }]
 * @param {function} onView - View action handler
 * @param {function} onEdit - Edit action handler
 * @param {function} onUpload - Upload action handler
 * @param {function} onDownload - Download action handler
 * @param {function} onDelete - Delete action handler
 * @param {function} onVerify - Verify action handler
 * @param {boolean} verified - Whether item is verified
 * @param {string} verifiedBy - Who verified it
 * @param {boolean} hasEvidence - Whether item has evidence files
 * @param {number} fileCount - Number of files
 * @param {boolean} isRequired - Whether item is required
 * @param {boolean} isOptional - Whether item is optional
 * @param {boolean} isExpanded - Whether row is expanded (for collapsible rows)
 * @param {function} onToggleExpand - Toggle expand handler
 */
export const RequirementRow = ({
  title,
  subtitle,
  status,
  type = 'document',
  expiry,
  badges = [],
  actions = [],
  onView,
  onEdit,
  onUpload,
  onDownload,
  onDelete,
  onVerify,
  verified,
  verifiedBy,
  hasEvidence,
  fileCount,
  isRequired,
  isOptional,
  isExpanded,
  onToggleExpand,
  children,
  className
}) => {
  // Type icons
  const typeIcons = {
    document: FileText,
    training: GraduationCap,
    form: FileText,
    acknowledgement: CheckCircle
  };
  
  const TypeIcon = typeIcons[type] || FileText;
  
  // Build action buttons
  const renderActions = () => {
    const buttonActions = [];
    
    if (onView && hasEvidence) {
      buttonActions.push(
        <Button
          key="view"
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0 rounded-lg"
          onClick={onView}
          title="View"
        >
          <Eye className="h-4 w-4" />
        </Button>
      );
    }
    
    if (onDownload && hasEvidence) {
      buttonActions.push(
        <Button
          key="download"
          size="sm"
          variant="ghost"
          className="h-8 w-8 p-0 rounded-lg"
          onClick={onDownload}
          title="Download"
        >
          <Download className="h-4 w-4" />
        </Button>
      );
    }
    
    // Additional custom actions
    actions.forEach((action, idx) => {
      const ActionIcon = action.icon;
      buttonActions.push(
        <Button
          key={`action-${idx}`}
          size="sm"
          variant={action.variant || 'ghost'}
          className="h-8 w-8 p-0 rounded-lg"
          onClick={action.onClick}
          title={action.label}
        >
          <ActionIcon className="h-4 w-4" />
        </Button>
      );
    });
    
    // Dropdown menu for additional actions
    const menuActions = [];
    if (onEdit) menuActions.push({ icon: Edit, label: 'Edit', onClick: onEdit });
    if (onUpload) menuActions.push({ icon: Upload, label: 'Upload', onClick: onUpload });
    if (onVerify && !verified) menuActions.push({ icon: Shield, label: 'Verify', onClick: onVerify, className: 'text-green-600' });
    if (onDelete) menuActions.push({ icon: Trash2, label: 'Delete', onClick: onDelete, className: 'text-red-600' });
    
    if (menuActions.length > 0) {
      buttonActions.push(
        <DropdownMenu key="menu">
          <DropdownMenuTrigger asChild>
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0 rounded-lg">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {menuActions.map((action, idx) => {
              const MenuIcon = action.icon;
              return (
                <DropdownMenuItem 
                  key={idx} 
                  onClick={action.onClick}
                  className={action.className}
                >
                  <MenuIcon className="h-4 w-4 mr-2" />
                  {action.label}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      );
    }
    
    return buttonActions;
  };
  
  return (
    <div className={cn(
      'p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]',
      className
    )}>
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left section: Icon, Title, Badges */}
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            {onToggleExpand && (
              <button
                onClick={onToggleExpand}
                className="p-1 hover:bg-gray-200 rounded"
              >
                <ChevronRight className={cn(
                  'h-4 w-4 transition-transform',
                  isExpanded && 'rotate-90'
                )} />
              </button>
            )}
            
            <TypeIcon className="h-4 w-4 text-text-muted" />
            
            <span className="font-medium text-text-primary">{title}</span>
            
            {/* Badges */}
            {isRequired && (
              <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary font-medium">
                Required
              </span>
            )}
            {isOptional && (
              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 font-medium">
                Optional
              </span>
            )}
            {verified && (
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 font-medium flex items-center gap-1">
                <Shield className="h-3 w-3" />
                Verified
              </span>
            )}
            {fileCount > 1 && (
              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">
                {fileCount} files
              </span>
            )}
            {badges.map((badge, idx) => (
              <StatusBadge 
                key={idx} 
                status={badge.variant || badge.status} 
                label={badge.label}
                size="sm"
              />
            ))}
          </div>
          
          {/* Subtitle */}
          {subtitle && (
            <p className="text-sm text-text-muted mt-1 ml-6">{subtitle}</p>
          )}
          
          {/* Verified by info */}
          {verified && verifiedBy && (
            <p className="text-xs text-text-muted mt-1 ml-6">
              Verified by {verifiedBy}
            </p>
          )}
        </div>
        
        {/* Right section: Expiry, Status, Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Expiry badge */}
          {expiry && expiry.date && (
            <ExpiryBadge
              status={expiry.status}
              daysUntilExpiry={expiry.daysUntilExpiry}
              expiryDate={expiry.date}
            />
          )}
          
          {/* Status badge */}
          {status && (
            <StatusBadge status={status} />
          )}
          
          {/* Actions */}
          <div className="flex items-center gap-1">
            {renderActions()}
          </div>
        </div>
      </div>
      
      {/* Expanded content */}
      {isExpanded && children && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {children}
        </div>
      )}
    </div>
  );
};

/**
 * TrainingRow - Specialized row for training records
 */
export const TrainingRow = ({
  record,
  onView,
  onDownload,
  onVerify,
  onUnverify,
  onCorrect,
  ...props
}) => {
  const hasEvidence = record.certificate_url || (record.evidence_files && record.evidence_files.length > 0);
  
  // Build expiry info from computed status
  const expiry = record.expiry_date ? {
    date: record.expiry_date,
    daysUntilExpiry: record.days_until_expiry,
    status: record.renewal_status || record.computed_status
  } : null;
  
  return (
    <RequirementRow
      title={record.training_name}
      subtitle={record.completion_date ? `Completed: ${new Date(record.completion_date).toLocaleDateString()}` : null}
      status={record.status}
      type="training"
      expiry={expiry}
      verified={record.verified}
      verifiedBy={record.verified_by}
      hasEvidence={hasEvidence}
      onView={hasEvidence ? onView : undefined}
      onDownload={hasEvidence ? onDownload : undefined}
      onVerify={!record.verified ? onVerify : undefined}
      actions={[
        ...(record.verified ? [{ icon: Shield, label: 'Remove Verification', onClick: onUnverify }] : []),
        ...(onCorrect ? [{ icon: Edit, label: 'Correct', onClick: onCorrect }] : [])
      ]}
      badges={[
        ...(record.mandatory ? [{ label: 'Mandatory', variant: 'warning' }] : [])
      ]}
      {...props}
    />
  );
};

/**
 * DocumentRow - Specialized row for documents
 */
export const DocumentRow = ({
  document,
  onView,
  onDownload,
  onUpload,
  onVerify,
  onDelete,
  ...props
}) => {
  const hasEvidence = document.file_url || document.files?.length > 0;
  
  const expiry = document.expiry_date ? {
    date: document.expiry_date,
    daysUntilExpiry: document.days_until_expiry,
    status: document.expiry_status?.status
  } : null;
  
  return (
    <RequirementRow
      title={document.document_label || document.name}
      subtitle={document.original_filename}
      status={document.status}
      type="document"
      expiry={expiry}
      verified={document.verified}
      verifiedBy={document.verified_by}
      hasEvidence={hasEvidence}
      fileCount={document.files?.length}
      isRequired={document.required}
      onView={hasEvidence ? onView : undefined}
      onDownload={hasEvidence ? onDownload : undefined}
      onUpload={onUpload}
      onVerify={!document.verified && hasEvidence ? onVerify : undefined}
      onDelete={onDelete}
      {...props}
    />
  );
};

export default RequirementRow;
