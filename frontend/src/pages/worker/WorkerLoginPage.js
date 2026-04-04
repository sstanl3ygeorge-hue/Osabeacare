import { useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Mail, Loader2, CheckCircle, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WorkerLoginPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) {
      toast.error('Please enter your email');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/worker/request-login`, { email });
      setSent(true);
      toast.success('Login link sent! Check your email');
    } catch (error) {
      toast.error('Failed to send login link. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-0 shadow-2xl">
          <CardContent className="py-12 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-semibold mb-2 text-slate-800">Check Your Email</h2>
            <p className="text-slate-600 mb-6">
              We've sent a login link to <strong className="text-slate-800">{email}</strong>
            </p>
            <div className="bg-slate-50 rounded-lg p-4 text-left space-y-2">
              <p className="text-sm text-slate-600">
                <span className="font-medium text-slate-700">1.</span> Open the email from Osabea Healthcare
              </p>
              <p className="text-sm text-slate-600">
                <span className="font-medium text-slate-700">2.</span> Click "Access My Dashboard"
              </p>
              <p className="text-sm text-slate-600">
                <span className="font-medium text-slate-700">3.</span> You'll be logged in automatically
              </p>
            </div>
            <p className="text-xs text-slate-500 mt-6">
              The link expires in 24 hours. If you don't see the email, check your spam folder.
            </p>
            <Button 
              variant="ghost" 
              className="mt-4 text-slate-600"
              onClick={() => setSent(false)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
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
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Mail className="h-8 w-8 text-white" />
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
            <Button 
              type="submit" 
              disabled={loading} 
              className="w-full h-12 text-base gap-2 bg-blue-600 hover:bg-blue-700"
              data-testid="worker-login-submit"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Mail className="h-5 w-5" />
              )}
              {loading ? 'Sending...' : 'Send Login Link'}
            </Button>
          </form>
          
          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              No password needed - we'll email you a secure link
            </p>
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
              to="/login" 
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
