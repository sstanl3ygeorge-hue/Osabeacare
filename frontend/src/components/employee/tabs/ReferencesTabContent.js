import ReferenceEmploymentComparison from '../ReferenceEmploymentComparison';
import { ReferencesPanel } from '../../compliance';

/**
 * ReferencesTabContent - Displays employee references
 * Includes reference-employment cross check and references panel
 */
export default function ReferencesTabContent({
  employeeId,
  onRefresh,
  onEditReference,
}) {
  return (
    <div data-testid="references-tab-content">
      <div className="mb-6">
        <ReferenceEmploymentComparison
          employeeId={employeeId}
          onRefresh={onRefresh}
        />
      </div>

      <ReferencesPanel
        employeeId={employeeId}
        onRefresh={onRefresh}
        onEditReference={onEditReference}
      />
    </div>
  );
}
