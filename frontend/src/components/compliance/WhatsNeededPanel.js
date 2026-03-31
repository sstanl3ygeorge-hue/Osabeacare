import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  AlertTriangle, Send, ChevronRight, Shield, FileText, 
  GraduationCap, Clock
} from 'lucide-react';

/**
 * WhatsNeededPanel - Bottom panel showing missing/blocking items
 * 
 * Clear list of what's needed with "Request All Missing" button
 */
export default function WhatsNeededPanel({
  blockingItems = [],
  warningItems = [],
  missingItems = [],
  onRequestAll,
  onNavigateToItem,
  hasEmail = false,
  isAuditor = false
}) {
  const totalMissing = missingItems.length;
  const hasBlocking = blockingItems.length > 0;
  const hasWarnings = warningItems.length > 0;
  const hasMissing = totalMissing > 0;

  if (!hasBlocking && !hasWarnings && !hasMissing) {
    return null; // Nothing needed - don't show panel
  }

  // Icon for item type
  const getItemIcon = (item) => {
    if (item.section === 'training' || item.row_key?.includes('training')) {
      return <GraduationCap className="h-4 w-4 text-amber-500" />;
    }
    if (item.row_key?.includes('check') || item.row_key?.includes('verification')) {
      return <Shield className="h-4 w-4 text-red-500" />;
    }
    return <FileText className="h-4 w-4 text-gray-500" />;
  };

  return (
    <div className="mt-8 p-5 bg-white border border-gray-200 rounded-xl shadow-sm" data-testid="whats-needed-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-heading font-semibold text-text-primary flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          What's Needed
        </h3>
        {!isAuditor && hasEmail && totalMissing > 0 && (
          <Button
            variant="default"
            size="sm"
            onClick={onRequestAll}
            className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            data-testid="request-all-missing-btn"
          >
            <Send className="h-3.5 w-3.5 mr-1.5" />
            Request All Missing
          </Button>
        )}
      </div>

      {/* Blocking Items */}
      {hasBlocking && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-red-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            Blocking Work Readiness
          </h4>
          <ul className="space-y-2">
            {blockingItems.map((item, idx) => (
              <li 
                key={idx}
                className="flex items-center justify-between p-2.5 bg-red-50 border border-red-100 rounded-lg group hover:bg-red-100 transition-colors cursor-pointer"
                onClick={() => onNavigateToItem && onNavigateToItem(item)}
                data-testid={`blocking-item-${idx}`}
              >
                <div className="flex items-center gap-2.5">
                  {getItemIcon(item)}
                  <span className="text-sm text-red-900">{item.message}</span>
                </div>
                <ChevronRight className="h-4 w-4 text-red-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warning Items */}
      {hasWarnings && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Clock className="h-3 w-3 text-amber-500" />
            Warnings
          </h4>
          <ul className="space-y-2">
            {warningItems.map((item, idx) => (
              <li 
                key={idx}
                className="flex items-center justify-between p-2.5 bg-amber-50 border border-amber-100 rounded-lg group hover:bg-amber-100 transition-colors cursor-pointer"
                onClick={() => onNavigateToItem && onNavigateToItem(item)}
                data-testid={`warning-item-${idx}`}
              >
                <div className="flex items-center gap-2.5">
                  {getItemIcon(item)}
                  <span className="text-sm text-amber-900">{item.message}</span>
                </div>
                <ChevronRight className="h-4 w-4 text-amber-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Items (not blocking but need action) */}
      {hasMissing && !hasBlocking && (
        <div>
          <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <FileText className="h-3 w-3 text-gray-400" />
            Missing Items
          </h4>
          <ul className="space-y-2">
            {missingItems.slice(0, 5).map((item, idx) => (
              <li 
                key={idx}
                className="flex items-center justify-between p-2.5 bg-gray-50 border border-gray-100 rounded-lg group hover:bg-gray-100 transition-colors cursor-pointer"
                onClick={() => onNavigateToItem && onNavigateToItem(item)}
                data-testid={`missing-item-${idx}`}
              >
                <div className="flex items-center gap-2.5">
                  {getItemIcon(item)}
                  <span className="text-sm text-gray-700">{item.message || item.name}</span>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
              </li>
            ))}
            {missingItems.length > 5 && (
              <li className="text-xs text-text-muted text-center py-2">
                + {missingItems.length - 5} more items
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
