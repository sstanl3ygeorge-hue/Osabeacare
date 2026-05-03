import { Inbox } from 'lucide-react';

/**
 * EmptyState — shared empty-state helper for compliance surfaces (Tier 2 #9).
 *
 * Replaces ad-hoc divs scattered across panels (e.g. "No documents yet",
 * "No agreements found") so admin and worker dashboards present empty
 * collections in the same calm, instructive way.
 *
 * Usage:
 *   <EmptyState
 *     title="No agreements yet"
 *     description="Once the worker signs the contract it will appear here."
 *     icon={FileSignature}
 *     action={<Button size="sm">Send agreement</Button>}
 *   />
 */
export default function EmptyState({
  title = 'Nothing here yet',
  description = null,
  icon: Icon = Inbox,
  action = null,
  className = '',
  testId = 'empty-state',
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-8 px-4 rounded-lg border border-dashed border-gray-200 bg-gray-50/50 ${className}`}
      data-testid={testId}
    >
      <div className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center mb-3">
        <Icon className="h-5 w-5 text-gray-400" />
      </div>
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {description && (
        <p className="text-xs text-gray-500 mt-1 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
