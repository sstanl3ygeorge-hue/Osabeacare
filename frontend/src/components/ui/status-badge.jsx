import React from 'react';
import { cn } from '../../lib/utils';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  Shield,
  Eye,
  HelpCircle
} from 'lucide-react';

/**
 * StatusBadge - Single source of truth for status styling across the app
 * 
 * @param {string} status - One of: valid, expired, pending, supervised, ready, 
 *                          needs_renewal, verified, missing, blocked, current,
 *                          completed, in_progress, not_started, expiring_soon
 * @param {string} label - Optional custom label (defaults to formatted status)
 * @param {string} size - 'sm' | 'md' | 'lg' (default: 'sm')
 * @param {boolean} showIcon - Whether to show status icon (default: false)
 * @param {string} className - Additional classes
 * @param {string} variant - 'badge' | 'pill' | 'dot' (default: 'badge')
 */
export const StatusBadge = ({ 
  status, 
  label, 
  size = 'sm', 
  showIcon = false,
  className,
  variant = 'badge'
}) => {
  // Normalize status to lowercase
  const normalizedStatus = (status || '').toLowerCase().replace(/[\s_-]+/g, '_');
  
  // Status configuration - SINGLE SOURCE OF TRUTH
  const statusConfig = {
    // GREEN statuses - positive/complete
    valid: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Valid' },
    verified: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: Shield, label: 'Verified' },
    ready: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Ready' },
    work_ready: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Ready to Work' },
    fully_compliant: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Fully Compliant' },
    completed: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Completed' },
    current: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Current' },
    approved: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Approved' },
    checked_approved: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle, label: 'Checked & Approved' },
    
    // AMBER statuses - warning/attention needed
    pending: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Pending' },
    supervised: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: Eye, label: 'Supervised' },
    supervised_start: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: Eye, label: 'Supervised Start' },
    needs_renewal: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: AlertTriangle, label: 'Needs Renewal' },
    expiring: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: AlertTriangle, label: 'Expiring' },
    expiring_soon: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: AlertTriangle, label: 'Expiring Soon' },
    review_due_soon: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Review Due Soon' },
    in_progress: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200', icon: Clock, label: 'In Progress' },
    ready_for_review: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200', icon: Eye, label: 'Ready for Review' },
    under_review: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200', icon: Eye, label: 'Under Review' },
    certificate_only: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', icon: AlertTriangle, label: 'Certificate Only' },
    
    // RED statuses - critical/blocked
    expired: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Expired' },
    missing: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Missing' },
    blocked: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Blocked' },
    not_ready: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Not Ready' },
    review_overdue: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Review Overdue' },
    overdue: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Overdue' },
    rejected: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', icon: XCircle, label: 'Rejected' },
    
    // GRAY statuses - neutral/not started
    not_started: { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-200', icon: HelpCircle, label: 'Not Started' },
    unknown: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200', icon: HelpCircle, label: 'Unknown' },
    no_expiry: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200', icon: CheckCircle, label: 'No Expiry' },
  };
  
  // Get config or fallback
  const config = statusConfig[normalizedStatus] || statusConfig.unknown;
  const Icon = config.icon;
  const displayLabel = label || config.label;
  
  // Size classes
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  };
  
  // Variant classes
  const variantClasses = {
    badge: 'rounded font-medium',
    pill: 'rounded-full font-medium',
    dot: 'rounded-full font-medium flex items-center gap-1.5'
  };
  
  if (variant === 'dot') {
    return (
      <span className={cn(
        'inline-flex items-center gap-1.5',
        sizeClasses[size],
        config.text,
        className
      )}>
        <span className={cn('w-2 h-2 rounded-full', config.bg.replace('100', '500'))} />
        {displayLabel}
      </span>
    );
  }
  
  return (
    <span className={cn(
      'inline-flex items-center gap-1',
      sizeClasses[size],
      variantClasses[variant],
      config.bg,
      config.text,
      className
    )}>
      {showIcon && <Icon className={cn(size === 'sm' ? 'h-3 w-3' : size === 'md' ? 'h-4 w-4' : 'h-5 w-5')} />}
      {displayLabel}
    </span>
  );
};

/**
 * ExpiryBadge - Shows expiry status with days remaining
 */
export const ExpiryBadge = ({
  status,
  daysUntilExpiry,
  expiryDate,
  size = 'sm',
  className
}) => {
  // Determine status from days if not provided
  let computedStatus = status;
  if (!computedStatus && daysUntilExpiry !== undefined) {
    if (daysUntilExpiry < 0) computedStatus = 'expired';
    else if (daysUntilExpiry <= 30) computedStatus = 'expiring_soon';
    else computedStatus = 'valid';
  }
  
  // Build label
  let label;
  if (daysUntilExpiry !== undefined && daysUntilExpiry !== null) {
    if (daysUntilExpiry < 0) {
      label = `Expired (${Math.abs(daysUntilExpiry)}d ago)`;
    } else if (daysUntilExpiry === 0) {
      label = 'Expires today';
    } else {
      label = `${daysUntilExpiry}d left`;
    }
  } else if (expiryDate) {
    label = `Expires: ${new Date(expiryDate).toLocaleDateString()}`;
  }
  
  return (
    <StatusBadge 
      status={computedStatus} 
      label={label}
      size={size}
      className={className}
    />
  );
};

/**
 * WorkReadinessBadge - Specific badge for work readiness status
 */
export const WorkReadinessBadge = ({ status, className }) => {
  const statusMap = {
    'work_ready': 'ready',
    'fully_compliant': 'ready',
    'supervised_start': 'supervised',
    'not_ready': 'not_ready',
    'blocked': 'blocked'
  };
  
  const labelMap = {
    'work_ready': 'Ready to Work',
    'fully_compliant': 'Ready to Work',
    'supervised_start': 'Supervised Start',
    'not_ready': 'Not Ready',
    'blocked': 'Blocked'
  };
  
  return (
    <StatusBadge 
      status={statusMap[status] || status}
      label={labelMap[status]}
      showIcon
      className={className}
    />
  );
};

export default StatusBadge;
