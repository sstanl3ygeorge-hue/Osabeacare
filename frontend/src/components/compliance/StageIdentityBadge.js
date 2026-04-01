/**
 * StageIdentityBadge.js
 * 
 * Visual badge showing whether a person is an Applicant or Employee (Staff).
 * Used in employee lists, compliance headers, and profile pages.
 * 
 * Props:
 * - stageIdentity: "applicant" | "employee" (from person_stage field)
 * - size: "sm" | "md" | "lg" (default: "md")
 * - showIcon: boolean (default: true)
 * - className: additional CSS classes
 */

import { User, UserCheck } from 'lucide-react';

const STAGE_CONFIGS = {
  applicant: {
    label: 'Applicant',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
    borderColor: 'border-blue-200',
    icon: User,
  },
  employee: {
    label: 'Staff',
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
    borderColor: 'border-green-200',
    icon: UserCheck,
  },
};

const SIZE_CLASSES = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

const ICON_SIZES = {
  sm: 'h-3 w-3',
  md: 'h-3.5 w-3.5',
  lg: 'h-4 w-4',
};

export default function StageIdentityBadge({ 
  stageIdentity = 'applicant', 
  size = 'md', 
  showIcon = true,
  className = '' 
}) {
  const config = STAGE_CONFIGS[stageIdentity] || STAGE_CONFIGS.applicant;
  const Icon = config.icon;
  
  return (
    <span 
      className={`
        inline-flex items-center gap-1 rounded-lg font-medium border
        ${config.bgColor} ${config.textColor} ${config.borderColor}
        ${SIZE_CLASSES[size]}
        ${className}
      `}
      data-testid={`stage-badge-${stageIdentity}`}
    >
      {showIcon && <Icon className={ICON_SIZES[size]} />}
      {config.label}
    </span>
  );
}

// Export the configurations for external use
export { STAGE_CONFIGS };
