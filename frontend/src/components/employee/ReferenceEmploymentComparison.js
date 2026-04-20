import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Users, CheckCircle, AlertTriangle, Building, Briefcase,
  Loader2, RefreshCw, Calendar, ChevronDown, ChevronUp,
  XCircle, Info,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ---------------------------------------------------------------------------
// Match-reason human labels
// ---------------------------------------------------------------------------
const MATCH_REASON_LABELS = {
  exact: 'Exact match',
  substring: 'Partial match',
  normalized: 'Matched ignoring common suffixes',
  none: 'No match',
};

// ---------------------------------------------------------------------------
// Per-reference compliance badge (three-tier NHS model)
// ---------------------------------------------------------------------------
function ComplianceStatusBadge({ status, isMostRecent }) {
  if (status === 'ok') {
    return (
      <Badge className="bg-green-100 text-green-800 text-[10px] flex items-center gap-0.5 shrink-0">
        <CheckCircle className="h-3 w-3" />
        Most recent employer
      </Badge>
    );
  }
  if (status === 'warning') {
    return (
      <Badge className="bg-amber-100 text-amber-800 text-[10px] flex items-center gap-0.5 shrink-0">
        <Info className="h-3 w-3" />
        Earlier employer
      </Badge>
    );
  }
  // alert
  return (
    <Badge className="bg-red-100 text-red-800 text-[10px] flex items-center gap-0.5 shrink-0">
      <XCircle className="h-3 w-3" />
      No employment match
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Card border / bg colour driven by compliance_status
// ---------------------------------------------------------------------------
function cardStyle(status) {
  if (status === 'ok') return 'bg-green-50 border-green-200';
  if (status === 'warning') return 'bg-amber-50 border-amber-200';
  return 'bg-red-50 border-red-200';
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function ReferenceEmploymentComparison({ employeeId, onRefresh }) {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const fetchComparison = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/employees/${employeeId}/reference-employment-comparison`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setComparison(response.data);
    } catch (error) {
      console.error('Failed to fetch comparison:', error);
      setComparison(null);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) fetchComparison();
  }, [employeeId]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- loading ---
  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-6 flex justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  // --- error ---
  if (loadError || !comparison) {
    return (
      <Card className="border-red-200 shadow-sm" data-testid="reference-employment-comparison">
        <CardContent className="py-6 text-center text-red-700">
          <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-red-500" />
          <p className="font-medium">Cannot assess reference-employment cross check</p>
          <p className="text-sm text-red-600 mt-1">
            Cross-check data unavailable. Treat this tab as blocked until it loads.
          </p>
          <Button variant="outline" size="sm" onClick={fetchComparison} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  // --- safe destructure with defaults — no crash if keys missing ---
  const {
    employment_history = [],
    references = [],
    comparison_summary = {},
    alert = {},
  } = comparison;

  const {
    has_discrepancy: hasDiscrepancy = false,
    highest_severity: highestSeverity = 'ok',
    total_references_declared: totalDeclared = 0,
    matched_references: matchedCount = 0,
    unmatched_references: unmatchedCount = 0,
    warning_references: warningCount = 0,
    employment_history_count: empHistCount = employment_history.length,
  } = comparison_summary;

  const alertCount = references.filter(r => r?.compliance_status === 'alert').length;

  // Header badge
  let headerBadge;
  if (!hasDiscrepancy) {
    headerBadge = (
      <Badge className="bg-green-100 text-green-700">
        <CheckCircle className="h-3 w-3 mr-1" />
        All matched
      </Badge>
    );
  } else if (highestSeverity === 'alert') {
    headerBadge = (
      <Badge className="bg-red-100 text-red-700">
        <XCircle className="h-3 w-3 mr-1" />
        {alertCount} unmatched
      </Badge>
    );
  } else {
    headerBadge = (
      <Badge className="bg-amber-100 text-amber-700">
        <Info className="h-3 w-3 mr-1" />
        {warningCount} earlier employer
      </Badge>
    );
  }

  return (
    <Card
      className={`border shadow-sm ${hasDiscrepancy ? (highestSeverity === 'alert' ? 'border-red-200' : 'border-amber-200') : 'border-[#E4E8EB]'}`}
      data-testid="reference-employment-comparison"
    >
      <CardHeader className="pb-2">
        {/* Collapsible header */}
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <CardTitle className="font-heading text-base flex items-center gap-2">
            <Users className={`h-5 w-5 ${hasDiscrepancy ? (highestSeverity === 'alert' ? 'text-red-600' : 'text-amber-600') : 'text-primary'}`} />
            Reference-Employment Cross Check
          </CardTitle>
          <div className="flex items-center gap-2">
            {headerBadge}
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {/* Alert banner */}
        {alert.show && alert.message && (
          <div className={`mt-2 p-2 rounded-lg border text-xs flex items-start gap-1 ${
            alert.level === 'alert'
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-amber-50 border-amber-200 text-amber-700'
          }`}>
            {alert.level === 'alert'
              ? <XCircle className="h-3 w-3 shrink-0 mt-0.5" />
              : <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
            }
            {alert.message}
          </div>
        )}
      </CardHeader>

      {expanded && (
        <CardContent className="pt-2">
          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="p-2 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-700">{empHistCount}</p>
              <p className="text-xs text-gray-500">Employment Records</p>
            </div>
            <div className="p-2 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-700">{totalDeclared}</p>
              <p className="text-xs text-gray-500">References Declared</p>
            </div>
            <div className={`p-2 rounded-lg text-center ${hasDiscrepancy ? 'bg-amber-50' : 'bg-green-50'}`}>
              <p className={`text-2xl font-bold ${hasDiscrepancy ? 'text-amber-700' : 'text-green-700'}`}>
                {matchedCount}
              </p>
              <p className={`text-xs ${hasDiscrepancy ? 'text-amber-600' : 'text-green-600'}`}>Matched</p>
            </div>
          </div>

          {/* Side-by-side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Employment history column */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Briefcase className="h-4 w-4" />
                Employment History
              </h4>
              <div className="space-y-2">
                {employment_history.length > 0 ? (
                  employment_history.map((emp, idx) => (
                    <div key={idx} className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="flex items-center justify-between gap-1">
                        <p className="font-medium text-sm text-gray-800">
                          {emp.employer_name || 'Unknown Employer'}
                        </p>
                        {emp.is_current && (
                          <Badge className="bg-blue-100 text-blue-700 text-[10px] shrink-0">Current</Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-600">{emp.position || 'Position not specified'}</p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                        <Calendar className="h-3 w-3" />
                        <span>
                          {emp.start_date || 'N/A'} – {emp.is_current ? 'Present' : (emp.end_date || 'N/A')}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500 italic p-2">No employment history recorded</p>
                )}
              </div>
            </div>

            {/* Declared references column */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Users className="h-4 w-4" />
                Declared References
              </h4>
              <div className="space-y-3">
                {references.length === 0 && (
                  <p className="text-xs text-gray-500 italic p-2">No references declared</p>
                )}
                {references.map((ref, idx) => {
                  if (!ref) return null;
                  const status = ref.compliance_status || 'alert';
                  const matchLabel = MATCH_REASON_LABELS[ref.match_reason] || MATCH_REASON_LABELS.none;
                  const hasName = Boolean(ref.name);

                  return (
                    <div key={idx} className={`p-3 rounded-lg border ${cardStyle(status)}`}>
                      {hasName ? (
                        <>
                          {/* Reference header row */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-medium text-sm text-gray-900 truncate">
                                Reference {ref.reference_num}: {ref.name}
                              </p>
                              <div className="flex items-center gap-1 text-xs text-gray-600 mt-0.5">
                                <Building className="h-3 w-3 shrink-0" />
                                <span className="truncate">
                                  {ref.organisation || ref.company || 'Organisation not specified'}
                                </span>
                              </div>
                            </div>
                            <ComplianceStatusBadge status={status} />
                          </div>

                          {/* Match reason pill */}
                          {ref.matches_employment_history && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                                <CheckCircle className="h-2.5 w-2.5" />
                                {matchLabel}
                              </span>
                              {ref.matching_employer?.employer_name &&
                                ref.matching_employer.employer_name.toLowerCase() !==
                                  (ref.organisation || ref.company || '').toLowerCase() && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                                  Matched to: {ref.matching_employer.employer_name}
                                </span>
                              )}
                            </div>
                          )}

                          {/* CQC investigation notice for warning / alert */}
                          {status === 'warning' && (
                            <div className="mt-2 p-1.5 bg-amber-100/60 rounded text-[10px] text-amber-800">
                              This reference is from an earlier employer, not the most recent.
                              NHS guidance requires this to be investigated and an explanation recorded.
                            </div>
                          )}
                          {status === 'alert' && (
                            <div className="mt-2 p-1.5 bg-red-100/60 rounded text-[10px] text-red-800">
                              This reference does not match any employer in the declared employment history.
                              Do not approve until an explanation has been obtained and documented.
                            </div>
                          )}

                          {/* Override reason (if present) */}
                          {ref.override_reason && (
                            <div className="mt-2 p-1.5 bg-blue-50 rounded text-[10px] text-blue-800 border border-blue-200">
                              Explanation recorded: {ref.override_reason}
                            </div>
                          )}

                          {/* Verification status chips */}
                          <div className="flex flex-wrap items-center gap-1.5 mt-2">
                            {ref.request_status && (
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                ref.request_status === 'verified'
                                  ? 'bg-green-100 text-green-700'
                                  : ref.request_status === 'sent'
                                  ? 'bg-blue-100 text-blue-700'
                                  : 'bg-gray-100 text-gray-600'
                              }`}>
                                {ref.request_status.replace(/_/g, ' ')}
                              </span>
                            )}
                            {ref.verified && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                                Verified
                              </span>
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="flex items-center gap-2 text-gray-400">
                          <XCircle className="h-4 w-4" />
                          <span className="text-sm">Reference {ref.reference_num} not declared</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Action items — only shown when there is something actionable */}
          {hasDiscrepancy && (
            <div className={`mt-4 p-3 rounded-lg border ${
              highestSeverity === 'alert'
                ? 'bg-red-50 border-red-200'
                : 'bg-amber-50 border-amber-200'
            }`}>
              <h5 className={`text-sm font-medium mb-2 ${
                highestSeverity === 'alert' ? 'text-red-800' : 'text-amber-800'
              }`}>
                Required Actions (NHS / CQC)
              </h5>
              <ul className={`space-y-1 text-xs ${
                highestSeverity === 'alert' ? 'text-red-700' : 'text-amber-700'
              }`}>
                {alertCount > 0 && (
                  <>
                    <li className="flex items-start gap-1">
                      <span className="w-1 h-1 rounded-full bg-red-400 mt-1.5 shrink-0" />
                      Obtain and document explanation for reference(s) not in declared employment history
                    </li>
                    <li className="flex items-start gap-1">
                      <span className="w-1 h-1 rounded-full bg-red-400 mt-1.5 shrink-0" />
                      Consider requesting a replacement reference from a known employer
                    </li>
                  </>
                )}
                {warningCount > 0 && (
                  <li className="flex items-start gap-1">
                    <span className="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                    Verify why reference is from an earlier employer; record explanation before approval
                  </li>
                )}
                <li className="flex items-start gap-1">
                  <span className="w-1 h-1 rounded-full bg-gray-400 mt-1.5 shrink-0" />
                  All discrepancies must be documented in the recruitment file per NHS reference guidance
                </li>
              </ul>
            </div>
          )}

          {/* Refresh */}
          <div className="mt-4 flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => { fetchComparison(); if (onRefresh) onRefresh(); }}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

      setLoading(true);
      setLoadError(false);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/reference-employment-comparison`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setComparison(response.data);
    } catch (error) {
      console.error('Failed to fetch comparison:', error);
      setComparison(null);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchComparison();
    }
  }, [employeeId]);

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-6 flex justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (loadError || !comparison) {
    return (
      <Card className="border-red-200 shadow-sm" data-testid="reference-employment-comparison">
        <CardContent className="py-6 text-center text-red-700">
          <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-red-500" />
          <p className="font-medium">Cannot assess reference-employment cross check</p>
          <p className="text-sm text-red-600 mt-1">Cross-check data unavailable. Treat this tab as blocked until it loads.</p>
          <Button variant="outline" size="sm" onClick={fetchComparison} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { employment_history = [], references = [], comparison_summary = {}, alert } = comparison;
  const hasDiscrepancy = comparison_summary?.has_discrepancy;

  return (
    <Card 
      className={`border shadow-sm ${
        hasDiscrepancy ? 'border-amber-200' : 'border-[#E4E8EB]'
      }`}
      data-testid="reference-employment-comparison"
    >
      <CardHeader className="pb-2">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <CardTitle className="font-heading text-base flex items-center gap-2">
            <Users className={`h-5 w-5 ${hasDiscrepancy ? 'text-amber-600' : 'text-primary'}`} />
            Reference-Employment Cross Check
          </CardTitle>
          <div className="flex items-center gap-2">
            {hasDiscrepancy ? (
              <Badge className="bg-amber-100 text-amber-700">
                <AlertTriangle className="h-3 w-3 mr-1" />
              {comparison_summary?.unmatched_references} Mismatch
              </Badge>
            ) : (
              <Badge className="bg-green-100 text-green-700">
                <CheckCircle className="h-3 w-3 mr-1" />
                Reviewed
              </Badge>
            )}
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        
        {/* Alert Banner */}
        {alert?.show && (
          <div className="mt-2 p-2 bg-amber-50 rounded-lg border border-amber-200">
            <p className="text-xs text-amber-700 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 flex-shrink-0" />
              {alert.message}
            </p>
          </div>
        )}
      </CardHeader>
      
      {expanded && (
        <CardContent className="pt-2">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="p-2 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-700">{employment_history.length}</p>
              <p className="text-xs text-gray-500">Employment Records</p>
            </div>
            <div className="p-2 bg-gray-50 rounded-lg text-center">
              <p className="text-2xl font-bold text-gray-700">{comparison_summary?.total_references_declared ?? 0}</p>
              <p className="text-xs text-gray-500">References Declared</p>
            </div>
            <div className={`p-2 rounded-lg text-center ${hasDiscrepancy ? 'bg-amber-50' : 'bg-green-50'}`}>
              <p className={`text-2xl font-bold ${hasDiscrepancy ? 'text-amber-700' : 'text-green-700'}`}>
                {comparison_summary?.references_matching_employment ?? 0}
              </p>
              <p className={`text-xs ${hasDiscrepancy ? 'text-amber-600' : 'text-green-600'}`}>Matched</p>
            </div>
          </div>

          {/* Side by Side Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Employment History */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Briefcase className="h-4 w-4" />
                Employment History
              </h4>
              <div className="space-y-2">
                {employment_history.length > 0 ? (
                  employment_history.map((emp, idx) => (
                    <div 
                      key={idx} 
                      className="p-2 bg-gray-50 rounded-lg border border-gray-100"
                    >
                      <p className="font-medium text-sm text-gray-800">{emp.employer_name || 'Unknown Employer'}</p>
                      <p className="text-xs text-gray-600">{emp.position || 'Position not specified'}</p>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                        <Calendar className="h-3 w-3" />
                        <span>
                          {emp.start_date || 'N/A'} - {emp.is_current ? 'Present' : (emp.end_date || 'N/A')}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-gray-500 italic p-2">No employment history recorded</p>
                )}
              </div>
            </div>

            {/* Declared References */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                <Users className="h-4 w-4" />
                Declared References
              </h4>
              <div className="space-y-2">
                {references.map((ref, idx) => (
                  <div 
                    key={idx} 
                    className={`p-2 rounded-lg border ${
                      ref.matches_employment_history 
                        ? 'bg-green-50 border-green-200' 
                        : ref.name 
                          ? 'bg-amber-50 border-amber-200' 
                          : 'bg-gray-50 border-gray-100'
                    }`}
                  >
                    {ref.name ? (
                      <>
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm text-gray-800">Reference {ref.reference_num}: {ref.name}</p>
                          {ref.matches_employment_history ? (
                            <Badge className="bg-green-100 text-green-700 text-[10px]">
                              <CheckCircle className="h-3 w-3 mr-0.5" />
                              Match
                            </Badge>
                          ) : (
                            <Badge className="bg-amber-100 text-amber-700 text-[10px]">
                              <AlertTriangle className="h-3 w-3 mr-0.5" />
                              No Match
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
                          <Building className="h-3 w-3" />
                          {ref.organisation || 'Organisation not specified'}
                        </div>
                        {ref.job_title && (
                          <p className="text-xs text-gray-500">{ref.job_title}</p>
                        )}
                        
                        {/* Match Details */}
                        {ref.matching_employer && (
                          <div className="mt-2 p-1.5 bg-green-100/50 rounded text-[10px] text-green-700">
                            Matches: {ref.matching_employer.employer_name}
                            {ref.match_reason === 'suffix_stripped' && (
                              <span className="ml-1 text-green-600 italic">(matched ignoring common suffixes)</span>
                            )}
                          </div>
                        )}
                        
                        {!ref.matches_employment_history && (
                          <div className="mt-2 p-1.5 bg-amber-100/50 rounded text-[10px] text-amber-700">
                            Not found in declared employment history - verify referee is from a recent employer
                          </div>
                        )}
                        
                        {/* Verification Status */}
                        <div className="flex items-center gap-2 mt-2">
                          {ref.request_status && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                              ref.request_status === 'verified' ? 'bg-green-100 text-green-700' :
                              ref.request_status === 'sent' ? 'bg-blue-100 text-blue-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {ref.request_status.replace(/_/g, ' ')}
                            </span>
                          )}
                          {ref.verified && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700">
                              Verified
                            </span>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="flex items-center gap-2 text-gray-400">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm">Reference {ref.reference_num} not declared</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Action Items */}
          {hasDiscrepancy && (
            <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <h5 className="text-sm font-medium text-amber-800 mb-2">Required Actions</h5>
              <ul className="space-y-1 text-xs text-amber-700">
                <li className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-amber-400" />
                  Verify that declared references are from recent employers
                </li>
                <li className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-amber-400" />
                  If reference is from an employer not in history, record explanation
                </li>
                <li className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-amber-400" />
                  Consider requesting alternative reference if no match found
                </li>
              </ul>
            </div>
          )}

          {/* Refresh Button */}
          <div className="mt-4 flex justify-end">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => {
                fetchComparison();
                if (onRefresh) onRefresh();
              }}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardContent>
      )}
    </Card>
  );
}
