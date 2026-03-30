/**
 * Inspection Mode Context
 * 
 * REUSES:
 * - Existing AuditViewPage as primary inspection view
 * - Existing URL routing system
 * - Existing compliance data endpoints
 * 
 * NO NEW ENDPOINTS - This is a UI-only feature
 * 
 * Purpose: Toggle read-only mode for CQC inspections
 * - Hides edit/delete actions
 * - Shows inspection banner
 * - Enables print-friendly styling
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';

const InspectionModeContext = createContext();

export function InspectionModeProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const [isInspectionMode, setIsInspectionMode] = useState(false);
  
  // Check URL param on mount and whenever location changes
  useEffect(() => {
    const mode = searchParams.get('mode');
    setIsInspectionMode(mode === 'inspection');
  }, [searchParams, location.pathname]);
  
  // Toggle inspection mode via URL param
  const toggleInspectionMode = useCallback(() => {
    const newParams = new URLSearchParams(searchParams);
    if (isInspectionMode) {
      newParams.delete('mode');
    } else {
      newParams.set('mode', 'inspection');
    }
    setSearchParams(newParams, { replace: true });
  }, [isInspectionMode, searchParams, setSearchParams]);
  
  // Enable inspection mode
  const enableInspectionMode = useCallback(() => {
    const newParams = new URLSearchParams(searchParams);
    newParams.set('mode', 'inspection');
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);
  
  // Disable inspection mode
  const disableInspectionMode = useCallback(() => {
    const newParams = new URLSearchParams(searchParams);
    newParams.delete('mode');
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);
  
  return (
    <InspectionModeContext.Provider value={{
      isInspectionMode,
      toggleInspectionMode,
      enableInspectionMode,
      disableInspectionMode
    }}>
      {/* Add print-friendly class when in inspection mode */}
      <div className={isInspectionMode ? 'inspection-mode' : ''}>
        {children}
      </div>
    </InspectionModeContext.Provider>
  );
}

export function useInspectionMode() {
  const context = useContext(InspectionModeContext);
  if (!context) {
    // Return default values if used outside provider
    return {
      isInspectionMode: false,
      toggleInspectionMode: () => {},
      enableInspectionMode: () => {},
      disableInspectionMode: () => {}
    };
  }
  return context;
}

// HOC to hide elements in inspection mode
export function HideInInspection({ children }) {
  const { isInspectionMode } = useInspectionMode();
  if (isInspectionMode) return null;
  return <>{children}</>;
}
