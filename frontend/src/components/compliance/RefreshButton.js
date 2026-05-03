import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';

/**
 * RefreshButton — shared refresh control for compliance surfaces (Tier 2 #10).
 *
 * Centralises the spinner + accessible label pattern that was duplicated
 * across ConsolidatedStatusPanel, DualRowComplianceSection, NextActionsPanel
 * etc. Keeps the visual treatment identical wherever an admin or worker
 * triggers a manual refresh, so behaviour matches across the two
 * dashboards.
 *
 * Usage:
 *   <RefreshButton onRefresh={handleRefresh} loading={isLoading} />
 *   <RefreshButton onRefresh={handleRefresh} variant="outline" size="sm" label="Refresh" />
 */
export default function RefreshButton({
  onRefresh,
  loading = false,
  disabled = false,
  variant = 'ghost',
  size = 'sm',
  label = null,
  className = '',
  testId = 'refresh-button',
}) {
  const Icon = loading ? Loader2 : RefreshCw;
  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      disabled={disabled || loading}
      onClick={(e) => {
        e?.stopPropagation?.();
        if (!loading && typeof onRefresh === 'function') onRefresh();
      }}
      aria-label={label || 'Refresh'}
      className={className}
      data-testid={testId}
    >
      <Icon className={`h-4 w-4 ${loading ? 'animate-spin' : ''} ${label ? 'mr-1.5' : ''}`} />
      {label}
    </Button>
  );
}
