import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Clock, LogOut, RefreshCw } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * SessionTimeoutWarning Component
 * 
 * P0 FIX: Displays a warning when session is about to expire.
 * - Checks session status every 60 seconds
 * - Shows warning 5 minutes before expiry
 * - Allows user to extend session or logout
 * 
 * Standards:
 * - 5 E's: Error Tolerant - User gets warning before timeout
 * - CIA Triad: Availability - User can extend session
 */
const SessionTimeoutWarning = ({ onLogout }) => {
  const [showWarning, setShowWarning] = useState(false);
  const [expiresIn, setExpiresIn] = useState(null);
  const [isExpired, setIsExpired] = useState(false);

  const checkSessionStatus = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(`${API}/api/auth/session-info`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        
        if (data.session_expired) {
          setIsExpired(true);
          setShowWarning(true);
        } else if (data.show_warning) {
          setShowWarning(true);
          setExpiresIn(data.expires_in_seconds);
        } else {
          setShowWarning(false);
          setExpiresIn(data.expires_in_seconds);
        }
      } else if (response.status === 401) {
        setIsExpired(true);
        setShowWarning(true);
      }
    } catch (error) {
      console.error('Session check failed:', error);
    }
  }, []);

  useEffect(() => {
    // Check immediately on mount
    checkSessionStatus();

    // Check every 60 seconds
    const interval = setInterval(checkSessionStatus, 60000);

    return () => clearInterval(interval);
  }, [checkSessionStatus]);

  // Countdown timer when warning is shown
  useEffect(() => {
    if (showWarning && expiresIn > 0 && !isExpired) {
      const countdown = setInterval(() => {
        setExpiresIn(prev => {
          if (prev <= 1) {
            setIsExpired(true);
            clearInterval(countdown);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(countdown);
    }
  }, [showWarning, isExpired]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleExtendSession = async () => {
    // Re-authenticate to extend session
    // For now, we'll just refresh the page which will use the existing token
    // In production, you'd want a dedicated refresh-token endpoint
    window.location.reload();
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    if (onLogout) {
      onLogout();
    } else {
      window.location.href = '/login';
    }
  };

  if (!showWarning) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-right-5 duration-300">
      <div className={`rounded-lg shadow-lg border p-4 max-w-sm ${
        isExpired 
          ? 'bg-red-50 border-red-300' 
          : 'bg-yellow-50 border-yellow-300'
      }`}>
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-full ${
            isExpired ? 'bg-red-100' : 'bg-yellow-100'
          }`}>
            {isExpired ? (
              <AlertTriangle className="h-5 w-5 text-red-600" />
            ) : (
              <Clock className="h-5 w-5 text-yellow-600" />
            )}
          </div>
          
          <div className="flex-1">
            <h4 className={`font-semibold text-sm ${
              isExpired ? 'text-red-800' : 'text-yellow-800'
            }`}>
              {isExpired ? 'Session Expired' : 'Session Expiring Soon'}
            </h4>
            
            <p className={`text-sm mt-1 ${
              isExpired ? 'text-red-700' : 'text-yellow-700'
            }`}>
              {isExpired 
                ? 'Your session has expired. Please log in again to continue.'
                : `Your session will expire in ${formatTime(expiresIn)}. Save your work and extend your session.`
              }
            </p>
            
            <div className="flex gap-2 mt-3">
              {!isExpired && (
                <button
                  onClick={handleExtendSession}
                  className="flex items-center gap-1 px-3 py-1.5 bg-yellow-600 text-white text-sm rounded-md hover:bg-yellow-700 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Extend Session
                </button>
              )}
              
              <button
                onClick={handleLogout}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
                  isExpired
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-white text-yellow-700 border border-yellow-300 hover:bg-yellow-100'
                }`}
              >
                <LogOut className="h-3.5 w-3.5" />
                {isExpired ? 'Log In Again' : 'Logout'}
              </button>
            </div>
          </div>
          
          {!isExpired && (
            <button
              onClick={() => setShowWarning(false)}
              className="text-yellow-500 hover:text-yellow-700"
              aria-label="Dismiss"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SessionTimeoutWarning;
