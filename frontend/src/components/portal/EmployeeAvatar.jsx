import { useState, useEffect } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * EmployeeAvatar - Displays employee profile photo with authenticated fetch
 * Falls back to initials if no photo or fetch fails
 */
export default function EmployeeAvatar({ 
  employeeId, 
  firstName, 
  lastName, 
  hasPhoto,
  token,
  size = 'md', // 'sm' | 'md' | 'lg'
  className = ''
}) {
  const [photoUrl, setPhotoUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-16 h-16 text-xl'
  };

  const initials = `${firstName?.charAt(0) || ''}${lastName?.charAt(0) || ''}`;

  useEffect(() => {
    let mounted = true;
    let blobUrl = null;

    const fetchPhoto = async () => {
      if (!hasPhoto || !employeeId || !token) {
        setPhotoUrl(null);
        return;
      }

      setLoading(true);
      setError(false);

      try {
        const response = await axios.get(
          `${API}/employees/${employeeId}/profile-photo/view`,
          { 
            headers: { Authorization: `Bearer ${token}` }, 
            responseType: 'blob',
            timeout: 10000
          }
        );
        
        if (mounted) {
          blobUrl = URL.createObjectURL(response.data);
          setPhotoUrl(blobUrl);
        }
      } catch (err) {
        if (mounted) {
          if (err?.response?.status !== 404) {
            console.error('Failed to fetch profile photo:', err);
            setError(true);
          }
          setPhotoUrl(null);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchPhoto();

    return () => {
      mounted = false;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [employeeId, hasPhoto, token]);

  // Show initials while loading, on error, or if no photo
  if (loading || error || !photoUrl) {
    return (
      <div 
        className={`bg-accent rounded-xl flex items-center justify-center ${sizeClasses[size]} ${className}`}
        data-testid={`employee-avatar-${employeeId}`}
      >
        <span className="text-primary font-medium">
          {initials}
        </span>
      </div>
    );
  }

  return (
    <img 
      src={photoUrl} 
      alt={`${firstName} ${lastName}`}
      className={`rounded-xl object-cover border border-[#E4E8EB] ${sizeClasses[size]} ${className}`}
      data-testid={`employee-avatar-${employeeId}`}
      onError={() => {
        setError(true);
        setPhotoUrl(null);
      }}
    />
  );
}
