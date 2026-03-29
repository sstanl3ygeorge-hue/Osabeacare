import React from 'react';
import { cn } from '../../lib/utils';

/**
 * ProgressBar - Single source of truth for progress visualization
 * 
 * @param {number} value - Current value
 * @param {number} max - Maximum value (default: 100)
 * @param {string} size - 'sm' | 'md' | 'lg' (default: 'md')
 * @param {string} variant - 'default' | 'success' | 'warning' | 'danger' | 'gradient'
 * @param {boolean} showLabel - Whether to show percentage label
 * @param {string} label - Custom label (overrides percentage)
 * @param {boolean} animate - Whether to animate the progress bar
 */
export const ProgressBar = ({
  value,
  max = 100,
  size = 'md',
  variant = 'default',
  showLabel = false,
  label,
  animate = false,
  className
}) => {
  // Calculate percentage
  const percentage = max > 0 ? Math.min(Math.round((value / max) * 100), 100) : 0;
  
  // Auto-determine variant based on percentage if not specified
  const computedVariant = variant === 'default' 
    ? percentage >= 80 ? 'success' 
      : percentage >= 50 ? 'warning' 
      : 'danger'
    : variant;
  
  // Size classes
  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4'
  };
  
  // Variant colors
  const variantClasses = {
    default: 'bg-primary',
    success: 'bg-green-500',
    warning: 'bg-amber-500',
    danger: 'bg-red-500',
    gradient: 'bg-gradient-to-r from-green-500 via-amber-500 to-red-500'
  };
  
  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-text-muted">
            {label || `${percentage}%`}
          </span>
          {!label && (
            <span className="text-sm font-medium">
              {value}/{max}
            </span>
          )}
        </div>
      )}
      <div className={cn(
        'w-full bg-gray-200 rounded-full overflow-hidden',
        sizeClasses[size]
      )}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            variantClasses[computedVariant],
            animate && 'animate-pulse'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

/**
 * ComplianceProgress - Specific progress bar for compliance percentage
 */
export const ComplianceProgress = ({
  completed,
  total,
  showFraction = true,
  size = 'md',
  className
}) => {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  
  // Determine color based on compliance level
  let variant = 'danger';
  if (percentage >= 100) variant = 'success';
  else if (percentage >= 80) variant = 'success';
  else if (percentage >= 50) variant = 'warning';
  
  return (
    <div className={cn('w-full', className)}>
      {showFraction && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-text-muted">Progress</span>
          <span className="text-sm font-medium">{completed}/{total} ({percentage}%)</span>
        </div>
      )}
      <ProgressBar 
        value={completed} 
        max={total} 
        variant={variant}
        size={size}
      />
    </div>
  );
};

/**
 * SegmentedProgress - Multi-segment progress (e.g., completed/pending/missing)
 */
export const SegmentedProgress = ({
  segments,
  total,
  size = 'md',
  showLegend = false,
  className
}) => {
  // segments: [{ value: 10, color: 'bg-green-500', label: 'Completed' }, ...]
  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4'
  };
  
  return (
    <div className={cn('w-full', className)}>
      <div className={cn(
        'w-full bg-gray-200 rounded-full overflow-hidden flex',
        sizeClasses[size]
      )}>
        {segments.map((segment, idx) => {
          const width = total > 0 ? (segment.value / total) * 100 : 0;
          return (
            <div
              key={idx}
              className={cn('h-full transition-all duration-500', segment.color)}
              style={{ width: `${width}%` }}
            />
          );
        })}
      </div>
      {showLegend && (
        <div className="flex flex-wrap gap-3 mt-2">
          {segments.map((segment, idx) => (
            <div key={idx} className="flex items-center gap-1.5 text-xs">
              <span className={cn('w-2 h-2 rounded-full', segment.color)} />
              <span className="text-text-muted">{segment.label}: {segment.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
