import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { handleOAuthCallback } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Use useRef to prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processCallback = async () => {
      const hash = window.location.hash;
      const sessionIdMatch = hash.match(/session_id=([^&]+)/);
      
      if (!sessionIdMatch) {
        toast.error('Authentication failed');
        navigate('/login');
        return;
      }

      const sessionId = sessionIdMatch[1];

      try {
        const user = await handleOAuthCallback(sessionId);
        toast.success(`Welcome, ${user.name}!`);
        // Clear the hash from URL and navigate to dashboard
        window.history.replaceState(null, '', '/portal/dashboard');
        navigate('/portal/dashboard', { state: { user }, replace: true });
      } catch (error) {
        console.error('OAuth callback error:', error);
        toast.error('Authentication failed. Please try again.');
        navigate('/login');
      }
    };

    processCallback();
  }, [handleOAuthCallback, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8FAFA]">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
        <p className="text-text-muted">Completing sign in...</p>
      </div>
    </div>
  );
}
