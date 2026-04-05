import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { cn } from '../../lib/utils';

/**
 * Progress metric definitions with labels and tooltips
 */
export const PROGRESS_METRICS = {
  recruitment: {
    label: 'Recruitment Progress',
    shortLabel: 'Recruitment',
    tooltip: 'Documents + references + forms completed before promotion. Does not include training or induction.',
    color: 'blue',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-700',
    progressColor: '[&>div]:bg-blue-500',
    icon: '📋'
  },
  compliance: {
    label: 'Full Compliance',
    shortLabel: 'Compliance',
    tooltip: 'All requirements including documents, forms, training, induction, and competencies.',
    color: 'emerald',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    textColor: 'text-emerald-700',
    progressColor: '[&>div]:bg-emerald-500',
    icon: '✅'
  },
  workReadiness: {
    label: 'Work Readiness',
    shortLabel: 'Work Ready',
    tooltip: 'CQC work readiness calculation. Measures if employee can work safely today.',
    color: 'amber',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
    progressColor: '[&>div]:bg-amber-500',
    icon: '🟢'
  }
};

/**
 * LabeledProgressBadge - A badge showing progress with label and tooltip
 */
export function LabeledProgressBadge({ 
  metricType, 
  completed, 
  total, 
  percentage,
  showIcon = true,
  size = 'default' // 'sm' | 'default' | 'lg'
}) {
  const metric = PROGRESS_METRICS[metricType] || PROGRESS_METRICS.compliance;
  const pct = percentage ?? (total > 0 ? Math.round((completed / total) * 100) : 0);
  
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    default: 'text-sm px-3 py-1',
    lg: 'text-base px-4 py-1.5'
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            className={cn(
              metric.bgColor, 
              metric.borderColor, 
              metric.textColor,
              'border cursor-help flex items-center gap-1.5',
              sizeClasses[size]
            )}
          >
            {showIcon && <span>{metric.icon}</span>}
            <span className="font-medium">{metric.shortLabel}:</span>
            <span>{completed}/{total}</span>
            <span className="opacity-70">({pct}%)</span>
            <Info className="h-3 w-3 opacity-50" />
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs bg-slate-900 text-white">
          <p className="font-medium mb-1">{metric.label}</p>
          <p className="text-slate-300 text-xs">{metric.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * LabeledProgressCard - A card showing detailed progress with label and tooltip
 */
export function LabeledProgressCard({ 
  metricType, 
  completed, 
  total, 
  percentage,
  showBreakdown = false,
  categories = null,
  className
}) {
  const metric = PROGRESS_METRICS[metricType] || PROGRESS_METRICS.compliance;
  const pct = percentage ?? (total > 0 ? Math.round((completed / total) * 100) : 0);

  return (
    <div className={cn(
      'p-4 rounded-xl border',
      metric.bgColor,
      metric.borderColor,
      className
    )}>
      <div className="flex items-center justify-between mb-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 cursor-help">
                <span className="text-lg">{metric.icon}</span>
                <span className={cn('font-semibold', metric.textColor)}>
                  {metric.label}
                </span>
                <Info className={cn('h-4 w-4 opacity-50', metric.textColor)} />
              </div>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs bg-slate-900 text-white">
              <p>{metric.tooltip}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        <span className={cn('text-2xl font-bold', metric.textColor)}>
          {pct}%
        </span>
      </div>
      
      <Progress value={pct} className={cn('h-2 mb-2', metric.progressColor)} />
      
      <p className="text-sm text-slate-600">
        {completed} of {total} requirements complete
      </p>
      
      {showBreakdown && categories && (
        <div className="mt-3 pt-3 border-t border-slate-200/50 space-y-1">
          {Object.entries(categories).map(([key, value]) => {
            const catLabels = {
              documents: 'Documents',
              forms: 'Forms',
              training: 'Training',
              references: 'References',
              agreements: 'Agreements',
              induction: 'Induction'
            };
            const catPct = value.total > 0 ? Math.round((value.completed / value.total) * 100) : 0;
            const isComplete = value.completed >= value.total && value.total > 0;
            
            return (
              <div key={key} className="flex items-center justify-between text-xs">
                <span className={isComplete ? 'text-emerald-700' : 'text-slate-600'}>
                  {isComplete ? '✓' : '○'} {catLabels[key] || key}
                </span>
                <span className={isComplete ? 'text-emerald-700 font-medium' : 'text-slate-500'}>
                  {value.completed}/{value.total}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * ComplianceBreakdownCard - Shows the 6-category breakdown instead of "Care Status"
 */
export function ComplianceBreakdownCard({ categories, totalCompleted, totalRequired, className }) {
  const percentage = totalRequired > 0 ? Math.round((totalCompleted / totalRequired) * 100) : 0;
  
  const categoryConfig = {
    documents: { label: 'Documents', icon: '📄', color: 'text-blue-600' },
    forms: { label: 'Forms', icon: '📝', color: 'text-purple-600' },
    training: { label: 'Training', icon: '🎓', color: 'text-amber-600' },
    references: { label: 'References', icon: '👤', color: 'text-cyan-600' },
    agreements: { label: 'Agreements', icon: '✍️', color: 'text-pink-600' },
    induction: { label: 'Induction', icon: '📋', color: 'text-indigo-600' }
  };

  return (
    <div className={cn('p-4 rounded-xl border bg-white border-slate-200', className)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <span>📊</span>
          Compliance Breakdown
        </h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-help">
                Total: {totalCompleted}/{totalRequired} ({percentage}%)
                <Info className="h-3 w-3 ml-1 opacity-50" />
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="bg-slate-900 text-white">
              All requirements including documents, forms, training, references, agreements, and induction.
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      
      <div className="space-y-2">
        {Object.entries(categories || {}).map(([key, value]) => {
          const config = categoryConfig[key] || { label: key, icon: '•', color: 'text-slate-600' };
          const catPct = value.total > 0 ? Math.round((value.completed / value.total) * 100) : 0;
          const isComplete = value.completed >= value.total && value.total > 0;
          
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-5 text-center">{config.icon}</span>
              <span className={cn('flex-1 text-sm', isComplete ? 'text-emerald-700' : 'text-slate-700')}>
                {config.label}
              </span>
              <div className="w-24">
                <Progress 
                  value={catPct} 
                  className={cn('h-1.5', isComplete ? '[&>div]:bg-emerald-500' : '[&>div]:bg-slate-400')} 
                />
              </div>
              <span className={cn(
                'text-sm font-medium w-12 text-right',
                isComplete ? 'text-emerald-600' : 'text-slate-600'
              )}>
                {value.completed}/{value.total}
              </span>
            </div>
          );
        })}
      </div>
      
      <div className="mt-4 pt-3 border-t border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Overall Progress</span>
          <span className="text-lg font-bold text-emerald-600">{percentage}%</span>
        </div>
        <Progress value={percentage} className="h-2 mt-1 [&>div]:bg-emerald-500" />
      </div>
    </div>
  );
}

export default LabeledProgressBadge;
