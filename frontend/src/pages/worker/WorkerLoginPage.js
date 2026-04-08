import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { User, Lock, Loader2, ArrowLeft, Eye, EyeOff, Mail, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WorkerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sendingMagicLink, setSendingMagicLink] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [loginMethod, setLoginMethod] = useState('magic'); // 'magic' or 'password'

  const handleMagicLinkRequest = async (e) => {
    e.preventDefault();
    if (!email) {
      toast.error('Please enter your email address');
      return;
    }

    setSendingMagicLink(true);
    try {
      await axios.post(`${API}/worker/request-login`, { email });
      setMagicLinkSent(true);
      toast.success('Login link sent to your email!');
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to send login link. Please check your email address.';
      toast.error(message);
    } finally {
      setSendingMagicLink(false);
    }
  };

  const handlePasswordLogin = async (e) => {
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
      // If no password set, guide them to use magic link
      if (message.includes('No password set')) {
        toast.error('No password set yet. Use "Send Login Link" to access your account.');
        setLoginMethod('magic');
      } else {
        toast.error(message);
      }
    } finally {
      setLoading(false);
    }
  };

  if (magicLinkSent) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-0 shadow-2xl">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-slate-800 mb-2">Check Your Email</h2>
            <p className="text-slate-600 mb-6">
              We've sent a login link to <strong>{email}</strong>
            </p>
            <p className="text-sm text-slate-500 mb-6">
              Click the link in the email to access your portal. The link expires in 24 hours.
            </p>
            <Button 
              variant="outline" 
              onClick={() => setMagicLinkSent(false)}
              className="w-full"
            >
              Try a different email
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-0 shadow-2xl">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <User className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-slate-800">Worker Portal</CardTitle>
          <p className="text-sm text-slate-500 mt-2">
            Track your application and complete your onboarding
          </p>
        </CardHeader>
        <CardContent className="pt-4">
          {/* Login Method Tabs */}
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => setLoginMethod('magic')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                loginMethod === 'magic' 
                  ? 'bg-purple-100 text-purple-700 border-2 border-purple-300' 
                  : 'bg-slate-100 text-slate-600 border-2 border-transparent hover:bg-slate-200'
              }`}
            >
              <Mail className="h-4 w-4 inline mr-1" />
              Email Link
            </button>
            <button
              type="button"
              onClick={() => setLoginMethod('password')}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                loginMethod === 'password' 
                  ? 'bg-purple-100 text-purple-700 border-2 border-purple-300' 
                  : 'bg-slate-100 text-slate-600 border-2 border-transparent hover:bg-slate-200'
              }`}
            >
              <Lock className="h-4 w-4 inline mr-1" />
              Password
            </button>
          </div>

          {loginMethod === 'magic' ? (
            <form onSubmit={handleMagicLinkRequest} className="space-y-5">
              <div>
                <Label className="text-slate-700">Email Address</Label>
                <p className="text-xs text-slate-500 mb-2">
                  We'll send you a secure login link
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
              
              <Button 
                type="submit" 
                disabled={sendingMagicLink} 
                className="w-full h-12 text-base gap-2 bg-purple-600 hover:bg-purple-700"
                data-testid="worker-magic-link-submit"
              >
                {sendingMagicLink ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Mail className="h-5 w-5" />
                )}
                {sendingMagicLink ? 'Sending...' : 'Send Login Link'}
              </Button>
              
              <p className="text-xs text-center text-slate-500">
                No password required - we'll email you a secure link
              </p>
            </form>
          ) : (
            <form onSubmit={handlePasswordLogin} className="space-y-5">
              <div>
                <Label className="text-slate-700">Email Address</Label>
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
                <p className="text-xs text-slate-500 mt-1">
                  Don't have a password? Use "Email Link" tab instead
                </p>
              </div>
              
              <Button 
                type="submit" 
                disabled={loading} 
                className="w-full h-12 text-base gap-2 bg-purple-600 hover:bg-purple-700"
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
          )}
          
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
