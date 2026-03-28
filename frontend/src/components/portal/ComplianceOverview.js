import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  Shield, ShieldCheck, ShieldAlert, CheckCircle,
  GraduationCap, FileCheck, Fingerprint, BadgeCheck,
  ClipboardCheck, Calendar, Upload, Eye, AlertTriangle,
  FileText, Clock, XCircle
} from 'lucide-react';

/**
 * ComplianceOverview - SINGLE SOURCE OF TRUTH
 * 
 * This component now uses complianceRequirements data directly from the backend.
 * No more hardcoded items - ensures Overview and What's Needed show the same data.
 */
export default function ComplianceOverview({ 
  employee, 
  documents, 
  training, 
  policies,
  generatedForms,
  complianceRequirements,  // SINGLE SOURCE OF TRUTH from backend
  onCompleteTraining,
  isAuditor = false,
  className = "" 
}) {
  // Use backend summary for accurate counts
  const summary = useMemo(() => {
    if (!complianceRequirements?.summary) {
      return {
        total: 0,
        verified: 0,
        completed: 0,
        missing: 0,
        readyForReview: 0
      };
    }
    
    const s = complianceRequirements.summary;
    return {
      total: s.total || 0,
      verified: s.verified || 0,
      completed: s.completed || 0,
      missing: s.missing || 0,
      readyForReview: (s.completed || 0) - (s.verified || 0)
    };
  }, [complianceRequirements?.summary]);

  // Group requirements by category from backend data
  const categorizedRequirements = useMemo(() => {
    if (!complianceRequirements?.requirements) return {};
    
    const grouped = {};
    complianceRequirements.requirements.forEach(req => {
      const category = req.category || 'Other';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(req);
    });
    
    return grouped;
  }, [complianceRequirements?.requirements]);

  // Category display names and order
  const CATEGORY_DISPLAY = {
    '1_Legal_Safety': { name: 'Legal & Safety', icon: Shield, color: 'text-red-600' },
    '2_Core_Training': { name: 'Core Training', icon: GraduationCap, color: 'text-blue-600' },
    '3_Role_Readiness': { name: 'Role Readiness', icon: ClipboardCheck, color: 'text-purple-600' },
    '4_Employment': { name: 'Employment', icon: FileCheck, color: 'text-green-600' },
    '5_Agreements': { name: 'Agreements', icon: BadgeCheck, color: 'text-amber-600' },
    '6_Admin': { name: 'Admin / Other', icon: FileText, color: 'text-gray-600' }
  };

  const categoryOrder = ['1_Legal_Safety', '2_Core_Training', '3_Role_Readiness', '4_Employment', '5_Agreements', '6_Admin'];

  // Get status badge for a requirement
  const getStatusBadge = (req) => {
    if (req.verified) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
          <CheckCircle className="h-3 w-3" />
          Approved
        </span>
      );
    }
    if (req.has_evidence) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
          <Clock className="h-3 w-3" />
          Ready for Review
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
        <AlertTriangle className="h-3 w-3" />
        Still Needed
      </span>
    );
  };

  // Calculate category stats
  const getCategoryStats = (categoryReqs) => {
    if (!categoryReqs || categoryReqs.length === 0) return { approved: 0, ready: 0, missing: 0 };
    
    return {
      approved: categoryReqs.filter(r => r.verified).length,
      ready: categoryReqs.filter(r => r.has_evidence && !r.verified).length,
      missing: categoryReqs.filter(r => !r.has_evidence).length
    };
  };

  if (!complianceRequirements) {
    return (
      <Card className={`rounded-2xl border-0 shadow-sm ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32 text-text-muted">
            Loading compliance data...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary Cards - SINGLE SOURCE OF TRUTH from backend */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="rounded-2xl border-0 shadow-sm bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-700 font-medium">Checked & Approved</p>
                <p className="text-2xl font-bold text-green-800">{summary.verified}/{summary.total}</p>
              </div>
              <ShieldCheck className="h-8 w-8 text-green-600 opacity-70" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="rounded-2xl border-0 shadow-sm bg-amber-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-amber-700 font-medium">Ready for Review</p>
                <p className="text-2xl font-bold text-amber-800">{summary.readyForReview}</p>
              </div>
              <Clock className="h-8 w-8 text-amber-600 opacity-70" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="rounded-2xl border-0 shadow-sm bg-gray-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-700 font-medium">Still Needed</p>
                <p className="text-2xl font-bold text-gray-800">{summary.missing}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-gray-500 opacity-70" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="rounded-2xl border-0 shadow-sm bg-blue-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-700 font-medium">Policies Signed</p>
                <p className="text-2xl font-bold text-blue-800">
                  {policies?.filter(p => p.signed).length || 0}/{policies?.length || 0}
                </p>
              </div>
              <BadgeCheck className="h-8 w-8 text-blue-600 opacity-70" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Category Overview - Using backend data */}
      <Card className="rounded-2xl border-0 shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="font-heading text-lg">Compliance by Category</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {categoryOrder.map(categoryKey => {
            const categoryReqs = categorizedRequirements[categoryKey] || [];
            if (categoryReqs.length === 0) return null;
            
            const categoryInfo = CATEGORY_DISPLAY[categoryKey] || { name: categoryKey, icon: FileText, color: 'text-gray-600' };
            const CategoryIcon = categoryInfo.icon;
            const stats = getCategoryStats(categoryReqs);
            
            return (
              <div key={categoryKey} className="border rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <CategoryIcon className={`h-5 w-5 ${categoryInfo.color}`} />
                    <span className="font-medium">{categoryInfo.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-green-600">{stats.approved} approved</span>
                    <span className="text-amber-600">{stats.ready} ready</span>
                    <span className="text-gray-500">{stats.missing} needed</span>
                  </div>
                </div>
                
                {/* Progress bar */}
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full flex">
                    <div 
                      className="bg-green-500 h-full transition-all" 
                      style={{ width: `${(stats.approved / categoryReqs.length) * 100}%` }}
                    />
                    <div 
                      className="bg-amber-400 h-full transition-all" 
                      style={{ width: `${(stats.ready / categoryReqs.length) * 100}%` }}
                    />
                  </div>
                </div>
                
                {/* Requirement list - compact */}
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {categoryReqs.map(req => (
                    <div key={req.id} className="flex items-center justify-between py-1 px-2 bg-gray-50 rounded-lg text-sm">
                      <span className="truncate flex-1">{req.name}</span>
                      {getStatusBadge(req)}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      {!isAuditor && summary.missing > 0 && (
        <Card className="rounded-2xl border-0 shadow-sm bg-amber-50 border-amber-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              <div className="flex-1">
                <p className="font-medium text-amber-800">
                  {summary.missing} requirement{summary.missing !== 1 ? 's' : ''} still needed
                </p>
                <p className="text-sm text-amber-700">
                  Use the "What's Needed" tab to upload documents and complete requirements.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
