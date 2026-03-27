import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { 
  Shield, ShieldCheck, ShieldAlert, ShieldX,
  GraduationCap, FileCheck, Fingerprint, BadgeCheck,
  ClipboardCheck, Pill, Calendar, RefreshCw
} from 'lucide-react';

// Define the key compliance items
const COMPLIANCE_ITEMS = [
  { 
    id: 'safeguarding', 
    name: 'Safeguarding Training', 
    icon: Shield,
    trainingType: 'safeguarding',
    documentType: null,
    roleRequired: null // Required for all
  },
  { 
    id: 'manual_handling', 
    name: 'Manual Handling', 
    icon: GraduationCap,
    trainingType: 'manual_handling',
    documentType: null,
    roleRequired: null
  },
  { 
    id: 'infection_control', 
    name: 'Infection Control', 
    icon: ShieldCheck,
    trainingType: 'infection_control',
    documentType: null,
    roleRequired: null
  },
  { 
    id: 'basic_life_support', 
    name: 'Basic Life Support (BLS)', 
    icon: ShieldAlert,
    trainingType: 'basic_life_support',
    documentType: null,
    roleRequired: null
  },
  { 
    id: 'medication', 
    name: 'Medication Training', 
    icon: Pill,
    trainingType: 'medication',
    documentType: null,
    roleRequired: 'Nurse' // Only required for Nurses
  },
  { 
    id: 'dbs', 
    name: 'DBS Check', 
    icon: Fingerprint,
    trainingType: null,
    documentType: 'DBS',
    roleRequired: null
  },
  { 
    id: 'right_to_work', 
    name: 'Right to Work', 
    icon: BadgeCheck,
    trainingType: null,
    documentType: 'Right to Work',
    roleRequired: null
  },
  { 
    id: 'induction', 
    name: 'Induction Completed', 
    icon: ClipboardCheck,
    trainingType: 'induction',
    documentType: null,
    formTemplate: 'Induction',
    roleRequired: null
  },
  { 
    id: 'policies', 
    name: 'Policies Acknowledgement', 
    icon: FileCheck,
    trainingType: null,
    documentType: null,
    policyBased: true,
    roleRequired: null
  }
];

// Status configuration
const STATUS_CONFIG = {
  complete: {
    label: 'Complete',
    bgColor: 'bg-success/10',
    textColor: 'text-success',
    borderColor: 'border-success/20',
    dotColor: 'bg-success'
  },
  expiring: {
    label: 'Expiring',
    bgColor: 'bg-warning/10',
    textColor: 'text-warning',
    borderColor: 'border-warning/20',
    dotColor: 'bg-warning'
  },
  pending: {
    label: 'Pending',
    bgColor: 'bg-info/10',
    textColor: 'text-info',
    borderColor: 'border-info/20',
    dotColor: 'bg-info'
  },
  missing: {
    label: 'Missing',
    bgColor: 'bg-error/10',
    textColor: 'text-error',
    borderColor: 'border-error/20',
    dotColor: 'bg-error'
  },
  not_applicable: {
    label: 'N/A',
    bgColor: 'bg-gray-100',
    textColor: 'text-text-muted',
    borderColor: 'border-gray-200',
    dotColor: 'bg-gray-400'
  }
};

export default function ComplianceOverview({ 
  employee, 
  documents, 
  training, 
  policies,
  generatedForms,
  className = "" 
}) {
  // Calculate compliance status for each item
  const complianceStatus = useMemo(() => {
    const now = new Date();
    const thirtyDaysFromNow = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    
    return COMPLIANCE_ITEMS.map(item => {
      // Check if role-dependent item applies
      if (item.roleRequired && employee?.role !== item.roleRequired) {
        return {
          ...item,
          status: 'not_applicable',
          expiryDate: null,
          lastUpdated: null,
          details: `Only required for ${item.roleRequired}s`
        };
      }
      
      let status = 'missing';
      let expiryDate = null;
      let lastUpdated = null;
      let details = null;
      
      // Check training records
      if (item.trainingType) {
        const trainingRecord = training.find(t => 
          t.training_name?.toLowerCase().includes(item.trainingType.replace('_', ' ')) ||
          t.training_type?.toLowerCase().includes(item.trainingType.replace('_', ' '))
        );
        
        if (trainingRecord) {
          if (trainingRecord.status === 'completed') {
            status = 'complete';
            lastUpdated = trainingRecord.completion_date || trainingRecord.updated_at;
            expiryDate = trainingRecord.expiry_date;
            
            // Check if expiring soon
            if (expiryDate) {
              const expiry = new Date(expiryDate);
              if (expiry < now) {
                status = 'missing';
                details = 'Training expired';
              } else if (expiry < thirtyDaysFromNow) {
                status = 'expiring';
                details = 'Expires within 30 days';
              }
            }
          } else if (trainingRecord.status === 'in_progress' || trainingRecord.status === 'scheduled') {
            status = 'pending';
            details = trainingRecord.status === 'scheduled' ? 'Scheduled' : 'In progress';
            lastUpdated = trainingRecord.updated_at;
          }
        }
      }
      
      // Check document types (DBS, Right to Work)
      if (item.documentType) {
        const doc = documents.find(d => 
          d.document_type_name?.toLowerCase().includes(item.documentType.toLowerCase()) ||
          d.category?.toLowerCase().includes(item.documentType.toLowerCase())
        );
        
        if (doc) {
          if (doc.status === 'approved') {
            status = 'complete';
            lastUpdated = doc.reviewed_at || doc.uploaded_at;
            expiryDate = doc.expiry_date;
            
            // Check if expiring soon
            if (expiryDate) {
              const expiry = new Date(expiryDate);
              if (expiry < now) {
                status = 'missing';
                details = 'Document expired';
              } else if (expiry < thirtyDaysFromNow) {
                status = 'expiring';
                details = 'Expires within 30 days';
              }
            }
          } else if (doc.status === 'uploaded' || doc.status === 'under_review') {
            status = 'pending';
            details = 'Under review';
            lastUpdated = doc.uploaded_at;
          } else if (doc.status === 'rejected') {
            status = 'missing';
            details = 'Document rejected';
            lastUpdated = doc.reviewed_at;
          }
        }
      }
      
      // Check generated forms (for Induction)
      if (item.formTemplate) {
        const form = generatedForms?.find(f => 
          f.template_name?.toLowerCase().includes(item.formTemplate.toLowerCase())
        );
        
        if (form) {
          if (form.status === 'signed_off') {
            status = 'complete';
            lastUpdated = form.signed_off_at || form.updated_at;
          } else if (form.status === 'completed' || form.status === 'reviewed') {
            status = 'pending';
            details = 'Awaiting sign-off';
            lastUpdated = form.updated_at;
          } else if (['draft', 'sent', 'in_progress'].includes(form.status)) {
            status = 'pending';
            details = form.status === 'draft' ? 'Not started' : 'In progress';
            lastUpdated = form.updated_at;
          }
        }
      }
      
      // Check policies acknowledgement
      if (item.policyBased) {
        const totalPolicies = policies?.length || 0;
        const signedPolicies = policies?.filter(p => p.status === 'signed').length || 0;
        
        if (totalPolicies === 0) {
          status = 'not_applicable';
          details = 'No policies assigned';
        } else if (signedPolicies === totalPolicies) {
          status = 'complete';
          const lastSigned = policies.filter(p => p.status === 'signed')
            .sort((a, b) => new Date(b.signed_at) - new Date(a.signed_at))[0];
          lastUpdated = lastSigned?.signed_at;
          details = `${signedPolicies}/${totalPolicies} signed`;
        } else if (signedPolicies > 0) {
          status = 'pending';
          details = `${signedPolicies}/${totalPolicies} signed`;
          lastUpdated = policies.find(p => p.status === 'signed')?.signed_at;
        } else {
          status = 'missing';
          details = `0/${totalPolicies} signed`;
        }
      }
      
      return {
        ...item,
        status,
        expiryDate,
        lastUpdated,
        details
      };
    });
  }, [employee, documents, training, policies, generatedForms]);
  
  // Calculate summary counts
  const summary = useMemo(() => {
    const applicable = complianceStatus.filter(c => c.status !== 'not_applicable');
    return {
      total: applicable.length,
      complete: complianceStatus.filter(c => c.status === 'complete').length,
      expiring: complianceStatus.filter(c => c.status === 'expiring').length,
      pending: complianceStatus.filter(c => c.status === 'pending').length,
      missing: complianceStatus.filter(c => c.status === 'missing').length
    };
  }, [complianceStatus]);
  
  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return null;
    }
  };

  return (
    <Card className={`border-[#E4E8EB] shadow-sm ${className}`} data-testid="compliance-overview">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Training & Compliance Overview
          </CardTitle>
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-success"></span>
              {summary.complete}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-warning"></span>
              {summary.expiring}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-info"></span>
              {summary.pending}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-error"></span>
              {summary.missing}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {complianceStatus.map((item) => {
            const config = STATUS_CONFIG[item.status];
            const Icon = item.icon;
            
            return (
              <div 
                key={item.id}
                className={`flex items-center justify-between p-3 rounded-xl border ${config.bgColor} ${config.borderColor} transition-colors`}
                data-testid={`compliance-item-${item.id}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.bgColor}`}>
                    <Icon className={`h-4 w-4 ${config.textColor}`} />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary text-sm">{item.name}</p>
                    {item.details && (
                      <p className={`text-xs ${config.textColor}`}>{item.details}</p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  {/* Dates */}
                  <div className="text-right hidden sm:block">
                    {item.expiryDate && item.status !== 'not_applicable' && (
                      <div className="flex items-center gap-1 text-xs text-text-muted">
                        <Calendar className="h-3 w-3" />
                        <span>Exp: {formatDate(item.expiryDate)}</span>
                      </div>
                    )}
                    {item.lastUpdated && item.status !== 'not_applicable' && (
                      <div className="flex items-center gap-1 text-xs text-text-muted">
                        <RefreshCw className="h-3 w-3" />
                        <span>{formatDate(item.lastUpdated)}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Status Badge */}
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${config.bgColor} min-w-[85px] justify-center`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`}></span>
                    <span className={`text-xs font-medium ${config.textColor}`}>
                      {config.label}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Quick Summary Bar */}
        <div className="mt-4 pt-4 border-t border-[#E4E8EB]">
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-muted">Overall Compliance</span>
            <span className="font-medium text-text-primary">
              {summary.complete}/{summary.total} items complete
            </span>
          </div>
          <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden flex">
            {summary.complete > 0 && (
              <div 
                className="h-full bg-success transition-all"
                style={{ width: `${(summary.complete / summary.total) * 100}%` }}
              />
            )}
            {summary.expiring > 0 && (
              <div 
                className="h-full bg-warning transition-all"
                style={{ width: `${(summary.expiring / summary.total) * 100}%` }}
              />
            )}
            {summary.pending > 0 && (
              <div 
                className="h-full bg-info transition-all"
                style={{ width: `${(summary.pending / summary.total) * 100}%` }}
              />
            )}
            {summary.missing > 0 && (
              <div 
                className="h-full bg-error transition-all"
                style={{ width: `${(summary.missing / summary.total) * 100}%` }}
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
