import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

export default function WorkerVerifyPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setError('No login token found. Please request a new login link.');
      return;
    }

    verifyToken(token);
  }, [searchParams]);

  const verifyToken = async (token) => {
    try {
      const response = await axios.post(`${API}/worker/verify-login`, { token });
      
      if (response.data.success && response.data.access_token) {
        // Store the worker token
        localStorage.setItem('workerToken', response.data.access_token);
        localStorage.setItem('workerEmployee', JSON.stringify(response.data.employee));
        
        setStatus('success');
        toast.success(`Welcome back, ${response.data.employee.name}!`);
        
        // Redirect to dashboard after brief delay
        setTimeout(() => {
          navigate('/worker/dashboard');
        }, 1500);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      setStatus('error');
      const message = error.response?.data?.detail || 'Login link is invalid or expired';
      setError(message);
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center">
        {status === 'verifying' && (
          <>
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Loader2 className="h-10 w-10 text-blue-600 animate-spin" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-800 mb-2">Verifying Your Login</h2>
            <p className="text-slate-600">Please wait while we log you in...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-800 mb-2">Login Successful!</h2>
            <p className="text-slate-600">Redirecting to your dashboard...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="h-10 w-10 text-red-600" />
            </div>
            <h2 className="text-2xl font-semibold text-slate-800 mb-2">Login Failed</h2>
            <p className="text-slate-600 mb-6">{error}</p>
            <button
              onClick={() => navigate('/worker/login')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Request New Login Link
            </button>
          </>
        )}
      </div>
    </div>
  );
}

