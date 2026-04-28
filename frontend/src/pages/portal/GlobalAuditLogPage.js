import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Loader2, ClipboardList } from 'lucide-react';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const RESOURCE_TYPE_OPTIONS = [
  'shift',
  'shift_attendance',
  'service_user_care_plan',
  'incident_log',
  'org_policy',
  'employee',
  'user',
  'agreement_submissions',
  'competency_record',
  'system',
];

function formatTimestamp(value) {
  if (!value) return '—';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString();
}

function summariseDetails(details) {
  if (!details || typeof details !== 'object') return '—';
  const entries = Object.entries(details)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .slice(0, 3)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v).slice(0, 40) : String(v).slice(0, 60)}`);
  return entries.join(' · ') || '—';
}

export default function GlobalAuditLogPage() {
  const { token } = useAuth();

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);

  const [resourceType, setResourceType] = useState('');
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 200 };
      if (resourceType) params.resource_type = resourceType;
      if (action.trim()) params.action = action.trim();
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await axios.get(`${API}/audit/global-log`, {
        headers: { Authorization: `Bearer ${token}` },
        params,
      });
      setLogs(res.data.logs || []);
      setTotal(res.data.count || 0);
    } catch (err) {
      setError('Failed to load audit log.');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [token, resourceType, action, dateFrom, dateTo]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleClear = () => {
    setResourceType('');
    setAction('');
    setDateFrom('');
    setDateTo('');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">Global Audit Log</h1>
      </div>

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            {/* Resource Type */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Resource Type</span>
              <Select value={resourceType} onValueChange={setResourceType}>
                <SelectTrigger className="w-48 rounded-xl">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All types</SelectItem>
                  {RESOURCE_TYPE_OPTIONS.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Action */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Action</span>
              <Input
                className="w-52 rounded-xl"
                placeholder="e.g. shift_attendance_approved"
                value={action}
                onChange={(e) => setAction(e.target.value)}
              />
            </div>

            {/* Date From */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Date From</span>
              <Input
                type="date"
                className="w-40 rounded-xl"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            {/* Date To */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Date To</span>
              <Input
                type="date"
                className="w-40 rounded-xl"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>

            <Button variant="outline" className="rounded-xl" onClick={handleClear}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium">
            {loading ? 'Loading…' : `${total} entries`}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : error ? (
            <div className="px-6 py-8 text-sm text-red-600">{error}</div>
          ) : logs.length === 0 ? (
            <div className="px-6 py-8 text-sm text-text-muted">No audit entries found for the selected filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table w-full text-sm">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Timestamp</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Actor</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Action</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Resource Type</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted whitespace-nowrap">Resource ID</th>
                    <th className="px-4 py-3 text-left font-medium text-text-muted">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr key={log.id || i} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-text-muted">
                        {formatTimestamp(log.timestamp)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {log.actor_name || log.user_id || '—'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="status-chip status-neutral font-mono text-xs">
                          {log.action || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-text-muted">
                        {log.resource_type || '—'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-text-muted">
                        {log.resource_id ? String(log.resource_id).slice(0, 16) + (String(log.resource_id).length > 16 ? '…' : '') : '—'}
                      </td>
                      <td className="px-4 py-3 text-text-muted text-xs max-w-xs truncate">
                        {summariseDetails(log.details)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

