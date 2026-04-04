import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  Shield, CheckCircle, XCircle, Loader2, RefreshCw, 
  FileText, Stamp, ClipboardList, AlertTriangle,
  ChevronRight
} from 'lucide-react';
import { toast } from 'sonner';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GATE_CONFIG = {
  interview_completed: {
    icon: FileText,
    color: 'blue',
    link: '#compliance' // Link to interview section
  },
  contract_signed: {
    icon: FileText,
    color: 'purple',
    link: '#policies' // Link to agreements tab
  },
  verification_stamps_complete: {
    icon: Stamp,
    color: 'amber',
    link: '#compliance' // Link to compliance tab
  },
  induction_complete: {
    icon: ClipboardList,
    color: 'green',
    link: '#training' // Link to induction section
  }
};

export default function PreEmploymentGatesPanel({ employeeId, onNavigate, onRefresh }) {
  const [gates, setGates] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchGates = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/pre-employment-gates`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setGates(response.data);
    } catch (error) {
      console.error('Failed to fetch pre-employment gates:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchGates();
    }
  }, [employeeId]);

  const handleNavigate = (gateKey) => {
    const config = GATE_CONFIG[gateKey];
    if (config?.link && onNavigate) {
      onNavigate(config.link);
    }
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-6 flex justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (!gates) return null;

  const { gates: gateData, gates_passed, total_gates, all_gates_passed, blockers } = gates;
  const progressPercent = Math.round((gates_passed / total_gates) * 100);
  const activeBlockers = blockers?.filter(b => b !== null) || [];

  return (
    <Card 
      className={`border shadow-sm ${
        all_gates_passed 
          ? 'border-green-200 bg-green-50/30' 
          : activeBlockers.length > 0 
            ? 'border-amber-200 bg-amber-50/30' 
            : 'border-[#E4E8EB]'
      }`}
      data-testid="pre-employment-gates-panel"
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="font-heading text-base flex items-center gap-2">
            <Shield className={`h-5 w-5 ${all_gates_passed ? 'text-green-600' : 'text-amber-600'}`} />
            Pre-Employment Gates
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge className={all_gates_passed ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}>
              {gates_passed}/{total_gates} Complete
            </Badge>
            <Button variant="ghost" size="sm" onClick={fetchGates} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-3">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 rounded-full ${
                all_gates_passed ? 'bg-green-500' : 'bg-amber-500'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        {/* Gates List */}
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(gateData).map(([key, gate]) => {
            const config = GATE_CONFIG[key];
            const Icon = config?.icon || Shield;
            
            return (
              <div
                key={key}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  gate.passed 
                    ? 'bg-green-50 border-green-200 hover:border-green-300' 
                    : 'bg-gray-50 border-gray-200 hover:border-gray-300 hover:bg-gray-100'
                }`}
                onClick={() => handleNavigate(key)}
                data-testid={`gate-${key}`}
              >
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-lg ${
                    gate.passed ? 'bg-green-100' : 'bg-gray-200'
                  }`}>
                    {gate.passed ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <Icon className={`h-4 w-4 text-gray-400`} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate ${
                      gate.passed ? 'text-green-800' : 'text-gray-700'
                    }`}>
                      {gate.label}
                    </p>
                    {gate.detail && gate.passed && (
                      <p className="text-[10px] text-gray-500 truncate">
                        {gate.detail.completed_at ? formatBackendDate(gate.detail.completed_at) : 
                         gate.detail.verified_at ? formatBackendDate(gate.detail.verified_at) : ''}
                      </p>
                    )}
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Blockers Alert */}
        {activeBlockers.length > 0 && (
          <div className="mt-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800">
                  Action Required Before Work Can Begin
                </p>
                <ul className="mt-1 space-y-0.5">
                  {activeBlockers.map((blocker, idx) => (
                    <li key={idx} className="text-xs text-amber-700 flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-amber-400" />
                      {blocker.message}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* All Complete Message */}
        {all_gates_passed && (
          <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <p className="text-sm font-medium text-green-800">
                All pre-employment checks complete - ready for work assignment
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
