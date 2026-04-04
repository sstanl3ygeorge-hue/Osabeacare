import { AuditTrailPanel } from '../../compliance';

/**
 * AuditTabContent - Displays employee audit trail
 * Wrapper around AuditTrailPanel for consistency
 */
export default function AuditTabContent({ employeeId }) {
  return (
    <div data-testid="audit-tab-content">
      <AuditTrailPanel employeeId={employeeId} />
    </div>
  );
}
