import { forwardRef } from 'react';
import HealthCompetencySection from '../HealthCompetencySection';
import AuditReadyTrainingMatrix from '../../training/AuditReadyTrainingMatrix';

/**
 * TrainingTabContent - Displays employee training records and certifications
 * Includes induction/competency section and audit-ready training matrix
 */
const TrainingTabContent = forwardRef(function TrainingTabContent({
  employeeId,
  employeeName,
  employeeRole,
  isAuditor,
  onUploadCertificate,
  onViewCertificate,
  onRefresh
}, ref) {
  return (
    <div ref={ref} data-testid="training-tab-content">
      {/* Induction & Competency Section - CQC Requirement */}
      <div className="mb-6">
        <HealthCompetencySection
          employeeId={employeeId}
          employeeName={employeeName}
          isAuditor={isAuditor}
          onRefresh={onRefresh}
        />
      </div>
      
      {/* Audit-Ready Training Matrix - Complete training record with tabs */}
      <AuditReadyTrainingMatrix
        employeeId={employeeId}
        employeeName={employeeName}
        role={employeeRole}
        onUploadCertificate={onUploadCertificate}
        onViewCertificate={onViewCertificate}
        onRefresh={onRefresh}
      />
    </div>
  );
});

export default TrainingTabContent;
