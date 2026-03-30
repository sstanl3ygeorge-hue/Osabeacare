/**
 * Inspection Banner Component
 * 
 * Displays a banner at the top when inspection mode is active.
 * Provides quick exit button and visual indication of read-only state.
 */

import { useInspectionMode } from '../../context/InspectionModeContext';
import { Eye, X, Printer } from 'lucide-react';

export function InspectionBanner() {
  const { isInspectionMode, disableInspectionMode } = useInspectionMode();
  
  if (!isInspectionMode) return null;
  
  const handlePrint = () => {
    window.print();
  };
  
  return (
    <div className="inspection-banner" data-testid="inspection-banner">
      <Eye className="h-4 w-4" />
      <span>INSPECTION MODE — Read-only view for CQC compliance review</span>
      <button 
        className="exit-btn print-include"
        onClick={handlePrint}
        title="Print this page"
      >
        <Printer className="h-3 w-3 inline mr-1" />
        Print
      </button>
      <button 
        className="exit-btn"
        onClick={disableInspectionMode}
        data-testid="exit-inspection-mode"
      >
        <X className="h-3 w-3 inline mr-1" />
        Exit
      </button>
    </div>
  );
}
