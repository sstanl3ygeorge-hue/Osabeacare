import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Button } from '../../components/ui/button';
import { Loader2, Bell } from 'lucide-react';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'warning', label: 'Warning' },
  { value: 'missing', label: 'Missing' },
  { value: 'safeguarding', label: 'Safeguarding' },
];

function formatDate(value) {
  if (!value) return '—';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

function severityClass(severity) {
  const normalized = String(severity || '').toLowerCase();
  if (normalized === 'urgent') return 'status-chip status-error';
  if (normalized === 'warning') return 'status-chip status-warning';
  if (normalized === 'missing') return 'status-chip status-neutral';
  if (normalized === 'safeguarding') return 'status-chip status-error';
  return 'status-chip status-neutral';
}

export default function ComplianceAlertsPage() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [counts, setCounts] = useState({ urgent: 0, warning: 0, missing: 0, safeguarding: 0 });
  const [severityFilter, setSeverityFilter] = useState('all');

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/compliance/alerts-summary`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 500 },
      });
      const payload = response.data || {};
      setAlerts(Array.isArray(payload.alerts) ? payload.alerts : []);
      setCounts(payload.counts || { urgent: 0, warning: 0, missing: 0, safeguarding: 0 });
    } catch (error) {
      console.error('Failed to load compliance alerts:', error);
      setAlerts([]);
      setCounts({ urgent: 0, warning: 0, missing: 0, safeguarding: 0 });
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const filteredAlerts = useMemo(() => {
    if (severityFilter === 'all') return alerts;
    return alerts.filter((row) => String(row.severity || '').toLowerCase() === severityFilter);
  }, [alerts, severityFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bell className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Compliance Alerts</h1>
          <p className="text-sm text-text-muted">Read-only cross-system alerts for urgent and missing actions.</p>
        </div>
      </div>

      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-[#E4E8EB] p-3 bg-[#F8FAFA]">
              <div className="text-xs text-text-muted">Urgent</div>
              <div className="text-lg font-semibold text-text-primary">{counts.urgent || 0}</div>
            </div>
            <div className="rounded-xl border border-[#E4E8EB] p-3 bg-[#F8FAFA]">
              <div className="text-xs text-text-muted">Warning</div>
              <div className="text-lg font-semibold text-text-primary">{counts.warning || 0}</div>
            </div>
            <div className="rounded-xl border border-[#E4E8EB] p-3 bg-[#F8FAFA]">
              <div className="text-xs text-text-muted">Missing</div>
              <div className="text-lg font-semibold text-text-primary">{counts.missing || 0}</div>
            </div>
            <div className="rounded-xl border border-[#E4E8EB] p-3 bg-[#F8FAFA]">
              <div className="text-xs text-text-muted">Safeguarding</div>
              <div className="text-lg font-semibold text-text-primary">{counts.safeguarding || 0}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">Alerts</CardTitle>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-full sm:w-48 rounded-xl">
              <SelectValue placeholder="Filter severity" />
            </SelectTrigger>
            <SelectContent>
              {FILTER_OPTIONS.map((item) => (
                <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="h-40 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="px-6 py-8 text-sm text-text-muted">No alerts for this filter.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table w-full text-sm">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="px-4 py-3 text-left font-medium text-text-muted">Alert</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Category</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Severity</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted">Entity</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Due / Expiry</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Source</th>
                    <th className="px-4 py-3 text-right font-medium text-text-muted whitespace-nowrap">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map((row, idx) => {
                    const dateValue = row.due_date || row.expiry_date;
                    return (
                      <tr key={`${row.source || 'src'}-${row.entity_id || idx}-${idx}`} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors">
                        <td className="px-4 py-3 text-text-primary">{row.title || 'Alert'}</td>
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">{row.category || '—'}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={severityClass(row.severity)}>{row.severity || '—'}</span>
                        </td>
                        <td className="px-4 py-3 text-text-muted">
                          <div className="font-medium text-text-primary">{row.entity_name || row.entity_id || '—'}</div>
                          <div className="text-xs">{row.entity_type || 'entity'} · {row.entity_id || '—'}</div>
                        </td>
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">{formatDate(dateValue)}</td>
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">{row.source || '—'}</td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <Button
                            variant="outline"
                            className="rounded-xl"
                            onClick={() => navigate(row.link_target || '/portal/compliance-centre')}
                          >
                            Open
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

