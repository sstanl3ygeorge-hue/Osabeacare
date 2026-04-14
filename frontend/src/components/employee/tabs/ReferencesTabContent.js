import { useEffect, useMemo, useState } from 'react';
import ReferenceEmploymentComparison from '../ReferenceEmploymentComparison';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Textarea } from '../../ui/textarea';
import { AlertTriangle, CheckCircle, Mail, Phone, Plus, Send, ShieldCheck, UserCheck, XCircle } from 'lucide-react';

const REFERENCE_STATUS_OPTIONS = ['pending', 'requested', 'received', 'verified', 'rejected'];

const REFERENCE_STATUS_STYLES = {
  pending: 'bg-gray-100 text-gray-600 border-gray-200',
  requested: 'bg-amber-100 text-amber-700 border-amber-200',
  received: 'bg-blue-100 text-blue-700 border-blue-200',
  verified: 'bg-green-100 text-green-700 border-green-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
};

function normalizeReferenceStatus(status, verified) {
  if (verified || status === 'verified') return 'verified';
  if (status === 'requested' || status === 'sent' || status === 'awaiting_response') return 'requested';
  if (status === 'received' || status === 'response_received' || status === 'reviewed') return 'received';
  if (status === 'rejected') return 'rejected';
  return 'pending';
}

function buildInitialReferences(employee) {
  const seededReferences = [];
  const legacyReferences = [employee?.reference_1, employee?.reference_2].filter(Boolean);
  const arrayReferences = Array.isArray(employee?.references) ? employee.references : [];
  const sourceReferences = arrayReferences.length > 0 ? arrayReferences : legacyReferences;

  sourceReferences.forEach((reference, index) => {
    if (!reference) return;
    seededReferences.push({
      id: reference.id || `seed-${index + 1}`,
      name: reference.name || reference.referee_name || '',
      relationship: reference.relationship || reference.referee_relationship || '',
      email: reference.email || reference.referee_email || '',
      phone: reference.phone || reference.referee_phone || '',
      status: normalizeReferenceStatus(reference.status || employee?.[`reference_${index + 1}_status`], reference.verified),
      rejectionReason: reference.rejection_reason || '',
    });
  });

  return seededReferences;
}

/**
 * ReferencesTabContent - Displays employee references
 * Includes reference-employment cross check and references panel
 */
export default function ReferencesTabContent({ 
  employeeId, 
  onRefresh,
  onEditReference,
  employee,
}) {
  const seededReferences = useMemo(() => buildInitialReferences(employee), [employee]);
  const [references, setReferences] = useState([]);
  const [addReferenceOpen, setAddReferenceOpen] = useState(false);
  const [rejectReferenceOpen, setRejectReferenceOpen] = useState(false);
  const [selectedReferenceId, setSelectedReferenceId] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [referenceDraft, setReferenceDraft] = useState({
    name: '',
    relationship: '',
    email: '',
    phone: '',
    status: 'pending',
  });

  useEffect(() => {
    setReferences(seededReferences);
  }, [employeeId, seededReferences]);

  const referencesVerified =
    references.length >= 2 &&
    references.every(reference => reference.status === 'verified');

  const referencesStatusBlockers = [
    references.length < 2 ? 'Add at least 2 references' : null,
    ...references
      .filter(reference => reference.status !== 'verified')
      .map(reference => `${reference.name || 'Reference'} not yet verified`),
  ].filter(Boolean);

  const verifiedCount = references.filter(reference => reference.status === 'verified').length;
  const requestedCount = references.filter(reference => reference.status === 'requested').length;
  const receivedCount = references.filter(reference => reference.status === 'received').length;

  const updateReferenceStatus = (referenceId, status, options = {}) => {
    setReferences(currentReferences =>
      currentReferences.map(reference =>
        reference.id === referenceId
          ? {
              ...reference,
              status,
              rejectionReason: status === 'rejected' ? options.reason || reference.rejectionReason || '' : '',
            }
          : reference
      )
    );
  };

  const handleAddReference = () => {
    if (!referenceDraft.name.trim() || !referenceDraft.relationship.trim()) {
      return;
    }

    if (!referenceDraft.email.trim() && !referenceDraft.phone.trim()) {
      return;
    }

    setReferences(currentReferences => [
      ...currentReferences,
      {
        id: `local-${Date.now()}`,
        name: referenceDraft.name.trim(),
        relationship: referenceDraft.relationship.trim(),
        email: referenceDraft.email.trim(),
        phone: referenceDraft.phone.trim(),
        status: referenceDraft.status,
        rejectionReason: '',
      },
    ]);
    setReferenceDraft({ name: '', relationship: '', email: '', phone: '', status: 'pending' });
    setAddReferenceOpen(false);
  };

  const openRejectDialog = (referenceId) => {
    setSelectedReferenceId(referenceId);
    setRejectionReason('');
    setRejectReferenceOpen(true);
  };

  const handleRejectReference = () => {
    if (!rejectionReason.trim()) {
      return;
    }

    updateReferenceStatus(selectedReferenceId, 'rejected', { reason: rejectionReason.trim() });
    setRejectReferenceOpen(false);
    setSelectedReferenceId(null);
    setRejectionReason('');
  };

  return (
    <div data-testid="references-tab-content">
      <div className="mb-6 space-y-6">
        <div className={`rounded-xl border p-4 ${referencesVerified ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`mt-0.5 ${referencesVerified ? 'text-green-600' : 'text-amber-600'}`}>
                {referencesVerified ? <CheckCircle className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
              </div>
              <div>
                <p className={`font-medium ${referencesVerified ? 'text-green-800' : 'text-amber-800'}`}>
                  References Status: {referencesVerified ? 'Complete' : 'Incomplete'}
                </p>
                {referencesVerified ? (
                  <p className="mt-1 text-sm text-green-700">
                    Two or more references are present and every reference is verified.
                  </p>
                ) : (
                  <>
                    <p className="mt-1 text-sm text-amber-700">
                      Hiring remains blocked until all required references are verified.
                    </p>
                    {referencesStatusBlockers.length > 0 && (
                      <p className="mt-1 text-sm text-amber-700">
                        Blockers: {referencesStatusBlockers.join(' · ')}
                      </p>
                    )}
                  </>
                )}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setAddReferenceOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add Reference
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
            <p className="text-xs text-text-muted">Total references</p>
            <p className="mt-2 text-lg font-semibold text-gray-900">{references.length}</p>
          </div>
          <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
            <p className="text-xs text-text-muted">Verified</p>
            <p className="mt-2 text-lg font-semibold text-gray-900">{verifiedCount}</p>
          </div>
          <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
            <p className="text-xs text-text-muted">Requested</p>
            <p className="mt-2 text-lg font-semibold text-gray-900">{requestedCount}</p>
          </div>
          <div className="rounded-xl border border-[#E4E8EB] bg-white p-3 shadow-sm">
            <p className="text-xs text-text-muted">Received</p>
            <p className="mt-2 text-lg font-semibold text-gray-900">{receivedCount}</p>
          </div>
        </div>

        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-lg">
              <span>Reference Tracking</span>
              <Badge variant="outline" className={referencesVerified ? REFERENCE_STATUS_STYLES.verified : REFERENCE_STATUS_STYLES.requested}>
                {referencesVerified ? 'Ready' : 'Needs action'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {references.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center">
                <p className="font-medium text-gray-700">No references added yet</p>
                <p className="mt-1 text-sm text-gray-500">Add at least two references before progressing the applicant.</p>
              </div>
            ) : (
              references.map((reference, index) => (
                <div key={reference.id} className="rounded-xl border border-[#E4E8EB] bg-white p-4 shadow-sm">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-900">Reference {index + 1}: {reference.name}</p>
                        <Badge variant="outline" className={REFERENCE_STATUS_STYLES[reference.status]}>
                          {reference.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">Relationship: {reference.relationship || 'Not provided'}</p>
                      <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-600">
                        {reference.email && (
                          <span className="inline-flex items-center gap-1">
                            <Mail className="h-3.5 w-3.5" />
                            {reference.email}
                          </span>
                        )}
                        {reference.phone && (
                          <span className="inline-flex items-center gap-1">
                            <Phone className="h-3.5 w-3.5" />
                            {reference.phone}
                          </span>
                        )}
                      </div>
                      {reference.rejectionReason && reference.status === 'rejected' && (
                        <p className="mt-2 text-sm text-red-600">Rejection reason: {reference.rejectionReason}</p>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {(reference.status === 'pending' || reference.status === 'rejected') && (
                        <Button size="sm" variant="outline" onClick={() => updateReferenceStatus(reference.id, 'requested')}>
                          <Send className="mr-2 h-4 w-4" />
                          Mark Requested
                        </Button>
                      )}
                      {reference.status === 'requested' && (
                        <Button size="sm" variant="outline" onClick={() => updateReferenceStatus(reference.id, 'received')}>
                          <UserCheck className="mr-2 h-4 w-4" />
                          Mark Received
                        </Button>
                      )}
                      {reference.status === 'received' && (
                        <Button size="sm" variant="outline" onClick={() => updateReferenceStatus(reference.id, 'verified')}>
                          <ShieldCheck className="mr-2 h-4 w-4" />
                          Verify Reference
                        </Button>
                      )}
                      {reference.status !== 'verified' && (
                        <Button size="sm" variant="outline" onClick={() => openRejectDialog(reference.id)}>
                          <XCircle className="mr-2 h-4 w-4" />
                          Reject Reference
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reference-Employment Cross Check - CQC Requirement */}
      <div className="mb-6">
        <ReferenceEmploymentComparison 
          employeeId={employeeId}
          onRefresh={onRefresh}
        />
      </div>

      <Dialog open={addReferenceOpen} onOpenChange={setAddReferenceOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Add Reference</DialogTitle>
            <DialogDescription>
              Add a referee and set the current reference status for admin tracking.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={referenceDraft.name}
                onChange={(event) => setReferenceDraft((currentDraft) => ({ ...currentDraft, name: event.target.value }))}
                placeholder="Referee full name"
              />
            </div>
            <div className="space-y-2">
              <Label>Relationship *</Label>
              <Input
                value={referenceDraft.relationship}
                onChange={(event) => setReferenceDraft((currentDraft) => ({ ...currentDraft, relationship: event.target.value }))}
                placeholder="Line manager, supervisor, colleague"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={referenceDraft.email}
                  onChange={(event) => setReferenceDraft((currentDraft) => ({ ...currentDraft, email: event.target.value }))}
                  placeholder="name@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={referenceDraft.phone}
                  onChange={(event) => setReferenceDraft((currentDraft) => ({ ...currentDraft, phone: event.target.value }))}
                  placeholder="07123 456789"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={referenceDraft.status}
                onValueChange={(value) => setReferenceDraft((currentDraft) => ({ ...currentDraft, status: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {REFERENCE_STATUS_OPTIONS.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddReferenceOpen(false)}>Cancel</Button>
            <Button
              onClick={handleAddReference}
              disabled={
                !referenceDraft.name.trim() ||
                !referenceDraft.relationship.trim() ||
                (!referenceDraft.email.trim() && !referenceDraft.phone.trim())
              }
            >
              Add Reference
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={rejectReferenceOpen} onOpenChange={setRejectReferenceOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Reject Reference</DialogTitle>
            <DialogDescription>
              Record why this reference cannot be accepted.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label>Reason *</Label>
            <Textarea
              value={rejectionReason}
              onChange={(event) => setRejectionReason(event.target.value)}
              placeholder="Explain why this reference was rejected"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectReferenceOpen(false)}>Cancel</Button>
            <Button onClick={handleRejectReference} disabled={!rejectionReason.trim()}>
              Save Rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
