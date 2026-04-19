/**
 * CareCertificateInductionPanel
 *
 * Worker-facing Care Certificate induction dashboard.
 *
 * Shows all 15 Care Certificate standards grouped by completion type:
 *   - automatic  → evidence-driven, no worker action
 *   - hybrid     → worker fills a short form, admin signs off
 *   - manual     → shadow shift, awaiting manager action
 *
 * Hybrid items open an inline form modal; workers can save drafts or submit.
 */

import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─── Status badge ──────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  completed:          { label: 'Completed',           color: 'bg-green-100 text-green-800' },
  signed_off:         { label: 'Completed',           color: 'bg-green-100 text-green-800' },
  awaiting_signoff:   { label: 'Awaiting manager',    color: 'bg-amber-100 text-amber-800' },
  submitted:          { label: 'Awaiting manager',    color: 'bg-amber-100 text-amber-800' },
  returned:           { label: 'Returned – revise',   color: 'bg-red-100 text-red-800' },
  draft:              { label: 'Draft saved',          color: 'bg-blue-100 text-blue-800' },
  pending:            { label: 'Not started',          color: 'bg-slate-100 text-slate-600' },
  pending_evidence:   { label: 'Pending evidence',     color: 'bg-slate-100 text-slate-600' },
  awaiting_manager:   { label: 'Awaiting manager',    color: 'bg-amber-100 text-amber-800' },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

// ─── Form field renderers ──────────────────────────────────────────────────

function FormField({ field, value, onChange, disabled }) {
  const baseClass =
    'mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm ' +
    'focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 ' +
    (disabled ? 'bg-slate-50 cursor-not-allowed opacity-70' : '');

  // Soft word-count feedback for text/textarea fields
  const wordCount = (typeof value === 'string') ? value.trim().split(/\s+/).filter(Boolean).length : 0;
  const MIN_WORDS = 20;
  const isTooShort = !disabled && typeof value === 'string' && value.trim().length > 0 && wordCount < MIN_WORDS;

  if (field.type === 'textarea') {
    return (
      <div>
        <textarea
          className={baseClass}
          rows={4}
          maxLength={5000}
          disabled={disabled}
          placeholder={field.hint || ''}
          value={value || ''}
          onChange={e => onChange(field.key, e.target.value)}
        />
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-slate-400">Recommended: 2–4 sentences</span>
          {isTooShort && (
            <span className="text-xs text-amber-600">Try to add a little more detail</span>
          )}
        </div>
      </div>
    );
  }

  if (field.type === 'text') {
    return (
      <div>
        <input
          type="text"
          className={baseClass}
          maxLength={2000}
          disabled={disabled}
          placeholder={field.hint || ''}
          value={value || ''}
          onChange={e => onChange(field.key, e.target.value)}
        />
        {isTooShort && (
          <span className="text-xs text-amber-600 mt-1 block">Try to add a little more detail</span>
        )}
      </div>
    );
  }

  if (field.type === 'radio') {
    return (
      <div className="mt-1 space-y-2">
        {(field.options || []).map(opt => (
          <label key={opt.value} className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name={field.key}
              value={opt.value}
              disabled={disabled}
              checked={value === opt.value}
              onChange={() => onChange(field.key, opt.value)}
              className="mt-0.5 text-blue-600"
            />
            <span className="text-sm text-slate-700">{opt.label}</span>
          </label>
        ))}
      </div>
    );
  }

  if (field.type === 'checkboxes') {
    const selected = Array.isArray(value) ? value : [];
    return (
      <div className="mt-1 space-y-2">
        {(field.options || []).map(opt => (
          <label key={opt.value} className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              value={opt.value}
              disabled={disabled}
              checked={selected.includes(opt.value)}
              onChange={e => {
                const next = e.target.checked
                  ? [...selected, opt.value]
                  : selected.filter(v => v !== opt.value);
                onChange(field.key, next);
              }}
              className="mt-0.5 text-blue-600 rounded"
            />
            <span className="text-sm text-slate-700">{opt.label}</span>
          </label>
        ))}
      </div>
    );
  }

  return null;
}

// ─── Hybrid form modal ─────────────────────────────────────────────────────

function HybridFormModal({ formEntry, onClose, onSaved, onSubmitted }) {
  const [schema, setSchema] = useState(null);
  const [learningContent, setLearningContent] = useState(null);
  const [step, setStep] = useState('learning');
  const [formData, setFormData] = useState({});
  const [subStatus, setSubStatus] = useState(null);
  const [returnReason, setReturnReason] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const formId = formEntry.form_id;
  const isReadOnly = subStatus === 'submitted' || subStatus === 'signed_off';

  useEffect(() => {
    const token = localStorage.getItem('workerToken');
    axios.get(`${API}/worker/induction/forms/${formId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        setSchema(res.data.schema);
        setLearningContent(res.data.learning_content || null);
        setSubStatus(res.data.submission_status);
        setReturnReason(res.data.return_reason);
        const prefill = res.data.draft_data || res.data.submitted_data || {};
        setFormData(prefill);
      })
      .catch(() => toast.error('Could not load form.'))
      .finally(() => setLoading(false));
  }, [formId]);

  const handleChange = useCallback((key, val) => {
    setFormData(prev => ({ ...prev, [key]: val }));
  }, []);

  const hasLearningContent = learningContent && (
    learningContent.overview ||
    learningContent.expected_to_know?.length ||
    learningContent.guidance?.length ||
    learningContent.dos?.length ||
    learningContent.donts?.length
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(`${API}/worker/induction/forms/${formId}/save`, {
        data: formData,
        is_draft: true,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Draft saved.');
      setSubStatus('draft');
      onSaved && onSaved(formId);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save draft.');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      await axios.post(`${API}/worker/induction/forms/${formId}/submit`, {
        data: formData,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Form submitted for manager review.');
      setSubStatus('submitted');
      onSubmitted && onSubmitted(formId);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail && detail.errors) {
        detail.errors.forEach(e => toast.error(e));
      } else {
        toast.error(typeof detail === 'string' ? detail : 'Failed to submit form.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 overflow-y-auto py-10 px-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">
              Standard {formEntry.standard_number}
            </p>
            <h2 className="text-base font-semibold text-slate-900">{formEntry.title}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl font-bold leading-none">&times;</button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-6">
          {loading && <p className="text-sm text-slate-400">Loading form…</p>}

          {!loading && returnReason && subStatus === 'returned' && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4">
              <p className="text-sm font-semibold text-red-700 mb-1">Returned for correction</p>
              <p className="text-sm text-red-600">{returnReason}</p>
            </div>
          )}

          {!loading && subStatus === 'submitted' && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
              <p className="text-sm text-amber-700">This form is awaiting manager review. You cannot edit it right now.</p>
            </div>
          )}

          {!loading && subStatus === 'signed_off' && (
            <div className="rounded-lg bg-green-50 border border-green-200 p-3">
              <p className="text-sm text-green-700 font-medium">This standard has been signed off by your manager.</p>
            </div>
          )}

          {!loading && step === 'learning' && (
            <div className="space-y-4">
              {hasLearningContent ? (
                <>
                  {learningContent.overview && (
                    <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
                      <p className="text-sm font-semibold text-blue-900 mb-1">Before you answer</p>
                      <p className="text-sm text-blue-800">{learningContent.overview}</p>
                    </div>
                  )}
                  {learningContent.expected_to_know?.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 mb-2">What you are expected to know or do</h3>
                      <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
                        {learningContent.expected_to_know.map((item, idx) => <li key={idx}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                  {learningContent.guidance?.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900 mb-2">Practical guidance</h3>
                      <ul className="list-disc pl-5 space-y-1 text-sm text-slate-700">
                        {learningContent.guidance.map((item, idx) => <li key={idx}>{item}</li>)}
                      </ul>
                    </div>
                  )}
                  {(learningContent.dos?.length > 0 || learningContent.donts?.length > 0) && (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {learningContent.dos?.length > 0 && (
                        <div className="rounded-lg border border-green-100 bg-green-50 p-3">
                          <h3 className="text-sm font-semibold text-green-800 mb-2">Do</h3>
                          <ul className="list-disc pl-5 space-y-1 text-sm text-green-800">
                            {learningContent.dos.map((item, idx) => <li key={idx}>{item}</li>)}
                          </ul>
                        </div>
                      )}
                      {learningContent.donts?.length > 0 && (
                        <div className="rounded-lg border border-red-100 bg-red-50 p-3">
                          <h3 className="text-sm font-semibold text-red-800 mb-2">Do not</h3>
                          <ul className="list-disc pl-5 space-y-1 text-sm text-red-800">
                            {learningContent.donts.map((item, idx) => <li key={idx}>{item}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
                  <p className="text-sm text-slate-700">Read this standard carefully, then continue to the reflective questions.</p>
                </div>
              )}
            </div>
          )}

          {!loading && step === 'form' && schema && schema.fields && schema.fields.map(field => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-slate-900">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {field.hint && (
                <p className="text-xs text-slate-500 mt-0.5">{field.hint}</p>
              )}
              <FormField
                field={field}
                value={formData[field.key]}
                onChange={handleChange}
                disabled={isReadOnly}
              />
              {field.helper_text && (
                <p className="text-xs text-slate-400 mt-1.5 italic">{field.helper_text}</p>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        {!loading && step === 'learning' && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <button
              onClick={() => setStep('form')}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              Continue to questions
            </button>
          </div>
        )}
        {!loading && step === 'form' && !isReadOnly && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <button
              onClick={() => setStep('learning')}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50"
            >
              Back to guidance
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save draft'}
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? 'Submitting…' : 'Submit for review'}
            </button>
          </div>
        )}
        {!loading && step === 'form' && isReadOnly && (
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <button onClick={() => setStep('learning')} className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50">
              Back to guidance
            </button>
            <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50">
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main panel ────────────────────────────────────────────────────────────

export default function CareCertificateInductionPanel() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeForm, setActiveForm] = useState(null); // {form_id, standard_number, title}

  const fetchOverview = useCallback(() => {
    setLoading(true);
    const token = localStorage.getItem('workerToken');
    axios.get(`${API}/worker/induction/overview`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => setOverview(res.data))
      .catch(() => toast.error('Could not load induction status.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchOverview(); }, [fetchOverview]);

  const handleFormSaved = () => fetchOverview();
  const handleFormSubmitted = () => {
    setActiveForm(null);
    fetchOverview();
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-sm text-slate-400">Loading your induction…</div>
    );
  }

  if (!overview) return null;

  const { items = [], overall_status, completed: mandatory_completed, total: mandatory_total } = overview;

  const pct = mandatory_total > 0 ? Math.round((mandatory_completed / mandatory_total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Progress summary */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-slate-900">Care Certificate Progress</h2>
          <StatusBadge status={overall_status} />
        </div>
        <div className="flex items-center gap-3 mb-1">
          <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-blue-500 h-2.5 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-sm font-medium text-slate-700 shrink-0">{pct}%</span>
        </div>
        <p className="text-xs text-slate-500">{mandatory_completed} of {mandatory_total} mandatory standards complete</p>
      </div>

      {/* Items list */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide w-8">#</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Standard</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide hidden md:table-cell">Type</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wide">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map(item => {
              const displayStatus = item.submission_status || item.status || 'pending';
              const completionType = item.completion_type;

              // Determine worker action button
              let actionBtn = null;
              if (completionType === 'hybrid') {
                const wa = item.worker_action;
                if (wa === 'start_form') {
                  actionBtn = (
                    <button
                      onClick={() => setActiveForm(item)}
                      className="px-3 py-1 rounded-md text-xs font-medium text-white bg-blue-600 hover:bg-blue-700"
                    >
                      Start form
                    </button>
                  );
                } else if (wa === 'complete_form') {
                  actionBtn = (
                    <button
                      onClick={() => setActiveForm(item)}
                      className="px-3 py-1 rounded-md text-xs font-medium text-white bg-blue-600 hover:bg-blue-700"
                    >
                      Continue
                    </button>
                  );
                } else if (wa === 'resubmit') {
                  actionBtn = (
                    <button
                      onClick={() => setActiveForm(item)}
                      className="px-3 py-1 rounded-md text-xs font-medium text-white bg-red-600 hover:bg-red-700"
                    >
                      Revise &amp; resubmit
                    </button>
                  );
                } else if (wa === 'awaiting_review') {
                  actionBtn = (
                    <button
                      onClick={() => setActiveForm(item)}
                      className="px-3 py-1 rounded-md text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200"
                    >
                      View
                    </button>
                  );
                }
              }

              const typeLabel =
                completionType === 'hybrid' ? 'Self-assessment' :
                completionType === 'automatic' ? 'Training evidence' :
                completionType === 'manual' ? 'Manager sign-off' : completionType;

              return (
                <tr key={item.code} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-400 text-xs">{item.standard_number}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{item.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={displayStatus} /></td>
                  <td className="px-4 py-3 hidden md:table-cell text-slate-500 text-xs">{typeLabel}</td>
                  <td className="px-4 py-3 text-right">{actionBtn || '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Hybrid form modal */}
      {activeForm && (
        <HybridFormModal
          formEntry={activeForm}
          onClose={() => setActiveForm(null)}
          onSaved={handleFormSaved}
          onSubmitted={handleFormSubmitted}
        />
      )}
    </div>
  );
}
