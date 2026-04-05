import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Hook to fetch unified progress for an employee.
 * This is the SINGLE SOURCE OF TRUTH for progress data.
 * All components should use this hook instead of calculating their own progress.
 */
export function useUnifiedProgress(employeeId, token) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProgress = useCallback(async () => {
    if (!employeeId || !token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(
        `${API}/employees/${employeeId}/unified-progress`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setProgress(response.data);
    } catch (err) {
      console.error('Failed to fetch unified progress:', err);
      setError(err.response?.data?.detail || 'Failed to load progress');
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  return { progress, loading, error, refetch: fetchProgress };
}

/**
 * Helper function to get progress for a specific category
 */
export function getCategoryProgress(progress, category) {
  if (!progress?.categories?.[category]) {
    return { completed: 0, total: 0, percentage: 0 };
  }
  
  const cat = progress.categories[category];
  const percentage = cat.total > 0 
    ? Math.round((cat.completed / cat.total) * 100) 
    : 0;
  
  return {
    completed: cat.completed,
    total: cat.total,
    percentage
  };
}

/**
 * Format blockers as a readable list
 */
export function formatBlockers(blockers) {
  if (!blockers || blockers.length === 0) {
    return [];
  }
  return blockers.map((blocker, index) => ({
    id: index,
    name: blocker,
    priority: blocker.includes('Expired') ? 'critical' : 
              blocker.includes('Reference') ? 'high' : 'medium'
  }));
}

export default useUnifiedProgress;
