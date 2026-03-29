import React from 'react';
import { cn } from '../../lib/utils';
import { Card } from './card';
import { StatusBadge, ExpiryBadge } from './status-badge';
import { ProgressBar, ComplianceProgress } from './progress-bar';
import { 
  ArrowRight,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Users,
  Shield,
  Calendar
} from 'lucide-react';

/**
 * ComplianceCard - Reusable card for dashboard and employee summary views
 * 
 * @param {string} title - Card title
 * @param {number} value - Main numeric value
 * @param {string} subtitle - Description text
 * @param {string} variant - 'default' | 'success' | 'warning' | 'danger' | 'neutral'
 * @param {React.ReactNode} icon - Custom icon component
 * @param {function} onClick - Click handler
 * @param {boolean} clickable - Whether card is clickable
 * @param {string} actionText - Text shown when clickable (e.g., "View staff →")
 */
export const ComplianceCard = ({
  title,
  value,
  subtitle,
  variant = 'default',
  icon: CustomIcon,
  onClick,
  clickable,
  actionText,
  className
}) => {
  // Variant configuration
  const variantConfig = {
    default: {
      card: 'bg-white border-gray-200',
      icon: 'bg-gray-100',
      iconColor: 'text-gray-600',
      value: 'text-gray-700',
      subtitle: 'text-gray-500'
    },
    success: {
      card: 'bg-green-50 border-green-200',
      cardHover: 'hover:bg-green-100 hover:shadow-sm',
      icon: 'bg-green-100',
      iconColor: 'text-green-600',
      value: 'text-green-700',
      subtitle: 'text-green-600'
    },
    warning: {
      card: 'bg-amber-50 border-amber-200',
      cardHover: 'hover:bg-amber-100 hover:shadow-sm',
      icon: 'bg-amber-100',
      iconColor: 'text-amber-600',
      value: 'text-amber-700',
      subtitle: 'text-amber-600'
    },
    danger: {
      card: 'bg-red-50 border-red-200',
      cardHover: 'hover:bg-red-100 hover:shadow-md',
      icon: 'bg-red-100',
      iconColor: 'text-red-600',
      value: 'text-red-700',
      subtitle: 'text-red-600'
    },
    neutral: {
      card: 'bg-white border-gray-200',
      cardHover: 'hover:bg-gray-50 hover:shadow-sm',
      icon: 'bg-gray-100',
      iconColor: 'text-gray-400',
      value: 'text-gray-400',
      subtitle: 'text-gray-500'
    }
  };
  
  const config = variantConfig[variant] || variantConfig.default;
  const isClickable = clickable || (onClick && value > 0);
  
  // Default icons based on variant
  const DefaultIcon = variant === 'danger' ? AlertTriangle 
    : variant === 'warning' ? Clock 
    : variant === 'success' ? CheckCircle 
    : FileText;
  
  const Icon = CustomIcon || DefaultIcon;
  
  return (
    <div
      onClick={isClickable ? onClick : undefined}
      className={cn(
        'p-4 rounded-xl border transition-all',
        config.card,
        isClickable && config.cardHover,
        isClickable && 'cursor-pointer',
        className
      )}
      title={isClickable ? actionText : undefined}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', config.icon)}>
            <Icon className={cn('h-5 w-5', config.iconColor)} />
          </div>
          <div>
            <p className={cn('text-2xl font-heading font-bold', config.value)}>{value}</p>
            <p className={cn('text-sm', config.subtitle)}>{title}</p>
          </div>
        </div>
        {isClickable && <ArrowRight className={cn('h-4 w-4', config.iconColor)} />}
      </div>
      {subtitle && (
        <p className={cn('text-xs mt-2', config.subtitle)}>{subtitle}</p>
      )}
      {isClickable && actionText && (
        <p className={cn('text-xs mt-2', config.subtitle)}>{actionText}</p>
      )}
    </div>
  );
};

/**
 * StatCard - Smaller stat display card
 */
export const StatCard = ({
  title,
  value,
  icon: Icon,
  variant = 'default',
  onClick,
  className
}) => {
  const variantConfig = {
    default: { bg: 'bg-white', border: 'border-gray-200', text: 'text-gray-700' },
    success: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' },
    warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700' },
    danger: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700' }
  };
  
  const config = variantConfig[variant] || variantConfig.default;
  
  return (
    <div
      onClick={onClick}
      className={cn(
        'p-3 rounded-xl border flex items-center justify-between',
        config.bg,
        config.border,
        onClick && 'cursor-pointer hover:shadow-sm transition-all',
        className
      )}
    >
      <div className="flex items-center gap-2">
        {Icon && <Icon className={cn('h-4 w-4', config.text)} />}
        <span className={cn('text-sm', config.text)}>{title}</span>
      </div>
      <div className="flex items-center gap-1">
        <span className={cn('text-xl font-heading font-bold', config.text)}>{value}</span>
        {onClick && <ArrowRight className={cn('h-3 w-3', config.text)} />}
      </div>
    </div>
  );
};

/**
 * SummaryCard - Card showing summary with progress
 */
export const SummaryCard = ({
  title,
  completed,
  total,
  status,
  onClick,
  children,
  className
}) => {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  
  return (
    <Card 
      className={cn(
        'p-4',
        onClick && 'cursor-pointer hover:shadow-md transition-all',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-text-primary">{title}</h3>
        {status && <StatusBadge status={status} />}
      </div>
      <ComplianceProgress 
        completed={completed} 
        total={total}
        showFraction
      />
      {children}
    </Card>
  );
};

/**
 * AlertCard - Card for attention items
 */
export const AlertCard = ({
  title,
  count,
  severity = 'warning',
  items = [],
  onClick,
  className
}) => {
  const severityConfig = {
    low: { bg: 'bg-blue-50', border: 'border-blue-200', icon: Clock, iconColor: 'text-blue-600' },
    medium: { bg: 'bg-amber-50', border: 'border-amber-200', icon: AlertTriangle, iconColor: 'text-amber-600' },
    high: { bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle, iconColor: 'text-red-600' }
  };
  
  const config = severityConfig[severity] || severityConfig.medium;
  const Icon = config.icon;
  
  return (
    <div
      onClick={onClick}
      className={cn(
        'p-4 rounded-xl border',
        config.bg,
        config.border,
        onClick && 'cursor-pointer hover:shadow-md transition-all',
        className
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className={cn('h-5 w-5', config.iconColor)} />
        <span className="font-medium">{title}</span>
        <span className={cn('ml-auto text-xl font-bold', config.iconColor)}>{count}</span>
      </div>
      {items.length > 0 && (
        <ul className="text-sm text-text-muted space-y-1">
          {items.slice(0, 3).map((item, idx) => (
            <li key={idx} className="truncate">• {item}</li>
          ))}
          {items.length > 3 && (
            <li className="text-xs">+{items.length - 3} more</li>
          )}
        </ul>
      )}
    </div>
  );
};

export default ComplianceCard;
