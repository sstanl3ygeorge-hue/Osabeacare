import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { User, Lock, Loader2, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WorkerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Please enter your email and password');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/worker/login`, { 
        email, 
        password 
      });
      
      if (response.data.success && response.data.token) {
        // Store token and employee info
        localStorage.setItem('workerToken', response.data.token);
        localStorage.setItem('workerEmail', response.data.employee.email);
        localStorage.setItem('workerEmployeeId', response.data.employee.id);
        localStorage.setItem('workerName', `${response.data.employee.first_name} ${response.data.employee.last_name}`);
        
        toast.success('Login successful!');
        navigate('/worker/dashboard');
      } else {
        toast.error('Login failed. Please check your credentials.');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Invalid email or password';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-0 shadow-2xl">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <User className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-slate-800">Applicant Portal</CardTitle>
          <p className="text-sm text-slate-500 mt-2">
            Track your application and complete your onboarding
          </p>
        </CardHeader>
        <CardContent className="pt-4">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label className="text-slate-700">Email Address</Label>
              <p className="text-xs text-slate-500 mb-2">
                Use the email from your job application
              </p>
              <Input
                type="email"
                placeholder="your.email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 text-base"
                required
                data-testid="worker-email-input"
              />
            </div>
            
            <div>
              <Label className="text-slate-700">Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 text-base pr-10"
                  required
                  data-testid="worker-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>
            
            <Button 
              type="submit" 
              disabled={loading} 
              className="w-full h-12 text-base gap-2 bg-blue-600 hover:bg-blue-700"
              data-testid="worker-login-submit"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Lock className="h-5 w-5" />
              )}
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          
          <div className="mt-6 pt-6 border-t border-slate-100">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <p className="text-sm text-blue-800 font-medium">Default Password</p>
              <p className="text-lg text-blue-900 font-mono mt-1">Welcome123!</p>
              <p className="text-xs text-blue-600 mt-2">Use this password for your first login</p>
            </div>
          </div>
          
          <div className="mt-6 text-center space-y-2">
            <Link 
              to="/" 
              className="text-sm text-slate-500 hover:text-slate-700 inline-flex items-center gap-1"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to Homepage
            </Link>
            <span className="text-slate-300 mx-2">|</span>
            <Link 
              to="/portal/login" 
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              Admin/Staff Login
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
