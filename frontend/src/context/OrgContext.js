import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';
import API_BASE from '../utils/apiBase';

const API = API_BASE;

const OrgContext = createContext(null);

export function OrgProvider({ children }) {
  const { token } = useAuth();
  const [orgSettings, setOrgSettings] = useState({
    organisation_name: 'Osabea Healthcare Solutions',
    service_type: 'adults_only',
    loading: true
  });

  useEffect(() => {
    const fetchOrgSettings = async () => {
      if (!token) return;
      
      try {
        const response = await axios.get(`${API}/org-settings`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setOrgSettings({
          ...response.data,
          loading: false
        });
      } catch (error) {
        console.error('Failed to fetch org settings:', error);
        setOrgSettings(prev => ({ ...prev, loading: false }));
      }
    };

    fetchOrgSettings();
  }, [token]);

  const updateOrgSettings = async (updates) => {
    try {
      const response = await axios.put(
        `${API}/org-settings`,
        updates,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setOrgSettings({
        ...response.data,
        loading: false
      });
      return { success: true };
    } catch (error) {
      console.error('Failed to update org settings:', error);
      return { success: false, error: error.response?.data?.detail || 'Failed to update settings' };
    }
  };

  return (
    <OrgContext.Provider value={{ 
      orgSettings, 
      orgName: orgSettings.organisation_name,
      serviceType: orgSettings.service_type,
      updateOrgSettings,
      isLoading: orgSettings.loading
    }}>
      {children}
    </OrgContext.Provider>
  );
}

export function useOrg() {
  const context = useContext(OrgContext);
  if (!context) {
    // Return default values if used outside provider (e.g., public pages)
    return {
      orgSettings: { organisation_name: 'Osabea Healthcare Solutions', service_type: 'adults_only' },
      orgName: 'Osabea Healthcare Solutions',
      serviceType: 'adults_only',
      updateOrgSettings: () => {},
      isLoading: false
    };
  }
  return context;
}

export default OrgContext;

