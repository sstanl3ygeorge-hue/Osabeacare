import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  Shield, ShieldCheck, ShieldAlert,
  GraduationCap, FileCheck, Fingerprint, BadgeCheck,
  ClipboardCheck, Pill, Calendar, Upload, Eye
} from 'lucide-react';

// Define the key compliance items
const COMPLIANCE_ITEMS = [
  { 
    id: 'safeguarding', 
    name: 'Safeguarding Training', 
    icon: Shield,
    trainingType: 'safeguarding',
    documentType: null,
    roleRequired: null
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
    roleRequired: 'Nurse'
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
    name: 'Induction', 
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

// CARE-FOCUSED STATUS CONFIG - Supportive language for healthcare context
const STATUS_CONFIG = {
  verified: {
    label: 'Checked & Approved',
    bgColor: 'bg-success/10',
    textColor: 'text-success',
    borderColor: 'border-success/20',
    dotColor: 'bg-success',
    priority: 1
  },
  evidence_uploaded: {
    label: 'Ready for Review',
    bgColor: 'bg-info/10',
    textColor: 'text-info',
    borderColor: 'border-info/20',
    dotColor: 'bg-info',
    priority: 2
  },
  expired: {
    label: 'Needs Updating',
    bgColor: 'bg-warning/10',
    textColor: 'text-warning',
    borderColor: 'border-warning/20',
    dotColor: 'bg-warning',
    priority: 3
  },
  missing: {
    label: 'Still Needed',
    bgColor: 'bg-error/10',
    textColor: 'text-error',
    borderColor: 'border-error/20',
    dotColor: 'bg-error',
    priority: 4
  },
  not_applicable: {
    label: 'N/A',
    bgColor: 'bg-gray-100',
    textColor: 'text-text-muted',
    borderColor: 'border-gray-200',
    dotColor: 'bg-gray-400',
    priority: 5
  }
};

export default function ComplianceOverview({ 
  employee, 
  documents, 
  training, 
  policies,
  generatedForms,
  onCompleteTraining,
  isAuditor = false,
  className = "" 
}) {
  // Calculate compliance status for each item using AUDIT-READY logic
  const complianceStatus = useMemo(() => {
    const now = new Date();
    
    return COMPLIANCE_ITEMS.map(item => {
      // Check if role-dependent item applies
      if (item.roleRequired && employee?.role !== item.roleRequired) {
        return {
          ...item,
          status: 'not_applicable',
          expiryDate: null,
          lastUpdated: null,
          hasEvidence: false,
          isVerified: false,
          details: `Only for ${item.roleRequired}s`
        };
      }
      
      let status = 'missing';
      let expiryDate = null;
      let lastUpdated = null;
      let hasEvidence = false;
      let isVerified = false;
      let details = null;
      
      // Check training records
      if (item.trainingType) {
        const searchTerms = [
          item.trainingType.replace(/_/g, ' '),
          item.trainingType.replace(/_/g, ''),
          item.name.toLowerCase()
        ];
        
        const trainingRecord = training.find(t => {
          const trainingName = (t.training_name || '').toLowerCase();
          const trainingType = (t.training_type || '').toLowerCase();
          return searchTerms.some(term => {
            const normalizedTerm = term.toLowerCase();
            return trainingName.includes(normalizedTerm) || 
                   normalizedTerm.includes(trainingName) ||
                   trainingType.includes(normalizedTerm);
          });
        });
        
        if (trainingRecord) {
          // Check if has certificate (evidence)
          hasEvidence = !!trainingRecord.certificate_url;
          isVerified = trainingRecord.verified === true;
          expiryDate = trainingRecord.expiry_date;
          lastUpdated = trainingRecord.completion_date || trainingRecord.updated_at;
          
          // Determine status based on evidence-first rules
          if (expiryDate && new Date(expiryDate) < now) {
            status = 'expired';
            details = 'Expired - renewal required';
          } else if (isVerified && hasEvidence) {
            status = 'verified';
          } else if (hasEvidence) {
            status = 'evidence_uploaded';
            details = 'Awaiting verification';
          } else if (trainingRecord.status === 'completed') {
            status = 'evidence_uploaded';
            details = 'Certificate needed';
          } else {
            status = 'missing';
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
          hasEvidence = !!doc.file_url;
          isVerified = doc.status === 'approved' || doc.verified === true;
          expiryDate = doc.expiry_date;
          lastUpdated = doc.reviewed_at || doc.uploaded_at;
          
          // Determine status
          if (expiryDate && new Date(expiryDate) < now) {
            status = 'expired';
            details = 'Document expired';
          } else if (isVerified && hasEvidence) {
            status = 'verified';
          } else if (hasEvidence) {
            status = 'evidence_uploaded';
            details = 'Awaiting verification';
          } else {
            status = 'missing';
          }
        }
      }
      
      // Check generated forms (for Induction)
      if (item.formTemplate) {
        const form = generatedForms?.find(f => 
          f.template_name?.toLowerCase().includes(item.formTemplate.toLowerCase())
        );
        
        if (form) {
          hasEvidence = !!form.pdf_url;
          isVerified = form.verified === true || form.status === 'signed_off';
          lastUpdated = form.signed_off_at || form.updated_at;
          
          if (isVerified && hasEvidence) {
            status = 'verified';
          } else if (hasEvidence) {
            status = 'evidence_uploaded';
            details = 'Awaiting verification';
          } else if (['completed', 'completed_imported', 'reviewed'].includes(form.status)) {
            status = 'evidence_uploaded';
            details = 'PDF needed';
          } else {
            status = 'missing';
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
        } else {
          hasEvidence = signedPolicies > 0;
          isVerified = signedPolicies === totalPolicies;
          
          if (isVerified) {
            status = 'verified';
            details = `${signedPolicies}/${totalPolicies} signed`;
          } else if (hasEvidence) {
            status = 'evidence_uploaded';
            details = `${signedPolicies}/${totalPolicies} signed`;
          } else {
            status = 'missing';
            details = `0/${totalPolicies} signed`;
          }
          
          if (policies?.length > 0) {
            const lastSigned = policies.filter(p => p.status === 'signed')
              .sort((a, b) => new Date(b.signed_at) - new Date(a.signed_at))[0];
            lastUpdated = lastSigned?.signed_at;
          }
        }
      }
      
      return {
        ...item,
        status,
        expiryDate,
        lastUpdated,
        hasEvidence,
        isVerified,
        details
      };
    });
  }, [employee, documents, training, policies, generatedForms]);
  
  // Calculate audit summary counts
  const summary = useMemo(() => {
    const applicable = complianceStatus.filter(c => c.status !== 'not_applicable');
    return {
      total: applicable.length,
      verified: complianceStatus.filter(c => c.status === 'verified').length,
      evidence_uploaded: complianceStatus.filter(c => c.status === 'evidence_uploaded').length,
      expired: complianceStatus.filter(c => c.status === 'expired').length,
      missing: complianceStatus.filter(c => c.status === 'missing').length
    };
  }, [complianceStatus]);

  // Group items by status for audit view
  const groupedItems = useMemo(() => {
    return {
      verified: complianceStatus.filter(c => c.status === 'verified'),
      needs_verification: complianceStatus.filter(c => c.status === 'evidence_uploaded'),
      missing: complianceStatus.filter(c => c.status === 'missing'),
      expired: complianceStatus.filter(c => c.status === 'expired'),
      not_applicable: complianceStatus.filter(c => c.status === 'not_applicable')
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

  const renderItem = (item) => {
    const config = STATUS_CONFIG[item.status];
    const Icon = item.icon;
    
    return (
      <div 
        key={item.id}
        className={`flex items-center justify-between p-3 rounded-xl border ${config.bgColor} ${config.borderColor}`}
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
        
        <div className="flex items-center gap-3">
          {/* Expiry date */}
          {item.expiryDate && item.status !== 'not_applicable' && (
            <div className="hidden sm:flex items-center gap-1 text-xs text-text-muted">
              <Calendar className="h-3 w-3" />
              <span>{formatDate(item.expiryDate)}</span>
            </div>
          )}
          
          {/* Action for missing training */}
          {item.trainingType && item.status === 'missing' && !isAuditor && onCompleteTraining && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onCompleteTraining(item)}
              className="text-xs h-7 rounded-lg"
              data-testid={`upload-training-${item.id}`}
            >
              <Upload className="h-3 w-3 mr-1" />
              Upload
            </Button>
          )}
          
          {/* Status Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${config.bgColor} min-w-[90px] justify-center`}>
            <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`}></span>
            <span className={`text-xs font-medium ${config.textColor}`}>
              {config.label}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card className={`border-[#E4E8EB] shadow-sm ${className}`} data-testid="compliance-overview">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Care Status
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Care Status Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-success/10 border border-success/20 rounded-xl text-center">
            <p className="text-2xl font-bold text-success">{summary.verified}</p>
            <p className="text-xs text-success font-medium">Checked & Approved</p>
          </div>
          <div className="p-3 bg-info/10 border border-info/20 rounded-xl text-center">
            <p className="text-2xl font-bold text-info">{summary.evidence_uploaded}</p>
            <p className="text-xs text-info font-medium">Ready for Review</p>
          </div>
          <div className="p-3 bg-error/10 border border-error/20 rounded-xl text-center">
            <p className="text-2xl font-bold text-error">{summary.missing}</p>
            <p className="text-xs text-error font-medium">Still Needed</p>
          </div>
          <div className="p-3 bg-warning/10 border border-warning/20 rounded-xl text-center">
            <p className="text-2xl font-bold text-warning">{summary.expired}</p>
            <p className="text-xs text-warning font-medium">Needs Updating</p>
          </div>
        </div>

        {/* Items grouped by status */}
        <div className="space-y-4">
          {/* Checked & Approved Items */}
          {groupedItems.verified.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-success mb-2 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Checked & Approved ({groupedItems.verified.length})
              </h4>
              <div className="space-y-2">
                {groupedItems.verified.map(renderItem)}
              </div>
            </div>
          )}

          {/* Ready for Review Items */}
          {groupedItems.needs_verification.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-info mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4" />
                Ready for Review ({groupedItems.needs_verification.length})
              </h4>
              <div className="space-y-2">
                {groupedItems.needs_verification.map(renderItem)}
              </div>
            </div>
          )}

          {/* Still Needed Items */}
          {groupedItems.missing.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-error mb-2 flex items-center gap-2">
                <Upload className="h-4 w-4" />
                Still Needed ({groupedItems.missing.length})
              </h4>
              <div className="space-y-2">
                {groupedItems.missing.map(renderItem)}
              </div>
            </div>
          )}

          {/* Needs Updating Items */}
          {groupedItems.expired.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-warning mb-2 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Needs Updating ({groupedItems.expired.length})
              </h4>
              <div className="space-y-2">
                {groupedItems.expired.map(renderItem)}
              </div>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div className="pt-4 border-t border-[#E4E8EB]">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-text-muted">Profile Progress</span>
            <span className="font-medium text-text-primary">
              {summary.verified}/{summary.total} approved
            </span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden flex">
            {summary.verified > 0 && (
              <div 
                className="h-full bg-success"
                style={{ width: `${(summary.verified / summary.total) * 100}%` }}
              />
            )}
            {summary.evidence_uploaded > 0 && (
              <div 
                className="h-full bg-info"
                style={{ width: `${(summary.evidence_uploaded / summary.total) * 100}%` }}
              />
            )}
            {summary.expired > 0 && (
              <div 
                className="h-full bg-warning"
                style={{ width: `${(summary.expired / summary.total) * 100}%` }}
              />
            )}
            {summary.missing > 0 && (
              <div 
                className="h-full bg-error"
                style={{ width: `${(summary.missing / summary.total) * 100}%` }}
              />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
