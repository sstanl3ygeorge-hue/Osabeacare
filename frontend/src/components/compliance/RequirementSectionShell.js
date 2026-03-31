import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { Badge } from '../ui/badge';

/**
 * RequirementSectionShell - Standard shell for all requirement sections
 * 
 * Provides consistent:
 * - Title row with blocking badge
 * - Summary line
 * - Action bar slot
 * - Toggle behavior
 * - Content area when open
 */
export default function RequirementSectionShell({
  title,
  summary,
  blockingLabel = null,
  isOpen,
  onToggle,
  actions,
  children,
  className = '',
  testId
}) {
  return (
    <section 
      className={`rounded-xl border bg-white shadow-sm overflow-hidden ${className}`}
      data-testid={testId || `section-${title.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {/* Header - Always visible */}
      <header 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-text-primary">{title}</h3>
            {blockingLabel && (
              <Badge className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 border border-red-200">
                <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                {blockingLabel}
              </Badge>
            )}
          </div>
          <p className="text-sm text-text-muted mt-0.5 truncate">{summary}</p>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {/* Action bar slot - stop propagation to prevent toggle */}
          {actions && (
            <div onClick={(e) => e.stopPropagation()}>
              {actions}
            </div>
          )}
          
          {/* Toggle chevron */}
          <button
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            aria-expanded={isOpen}
            aria-label={isOpen ? 'Collapse section' : 'Expand section'}
          >
            {isOpen ? (
              <ChevronUp className="h-5 w-5 text-text-muted" />
            ) : (
              <ChevronDown className="h-5 w-5 text-text-muted" />
            )}
          </button>
        </div>
      </header>

      {/* Content - Only when open */}
      {isOpen && (
        <div className="border-t border-gray-100 p-4 bg-gray-50/30">
          {children}
        </div>
      )}
    </section>
  );
}
