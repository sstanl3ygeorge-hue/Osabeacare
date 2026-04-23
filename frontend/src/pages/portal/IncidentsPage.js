import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { AlertTriangle, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_OPTIONS = ['open', 'under_review', 'closed'];

function toLocalDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export default function IncidentsPage() {
  const token = localStorage.getItem('token');
  const [loading, setLoading] = useState(true);
  const [incidents, setIncidents] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    incident_type: 'incident',
    title: '',
    description: '',
    date_occurred: '',
    location: '',
    related_shift_id: '',
  });

  const headers = { Authorization: `Bearer ${token}` };

  const fetchIncidents = async () => {
    try {
      setLoading(true);
      const params = statusFilter === 'all' ? {} : { status: statusFilter === 'under_review' ? 'investigating' : statusFilter };
      const res = await axios.get(`${API}/compliance/incidents`, { headers, params });
      setIncidents(res.data || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [statusFilter]);

  const handleCreate = async () => {
    if (!form.title || !form.description || !form.date_occurred) {
      toast.error('Title, description and date/time are required');
      return;
    }
    setSaving(true);
    try {
      await axios.post(
        `${API}/compliance/incidents`,
        {
          incident_type: form.incident_type,
          title: form.title,
          description: form.description,
          date_occurred: new Date(form.date_occurred).toISOString(),
          location: form.location || null,
          related_shift_id: form.related_shift_id || null,
        },
        { headers }
      );
      toast.success('Incident created');
      setShowCreate(false);
      setForm({
        incident_type: 'incident',
        title: '',
        description: '',
        date_occurred: '',
        location: '',
        related_shift_id: '',
      });
      fetchIncidents();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create incident');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (incident, nextStatus) => {
    try {
      await axios.put(
        `${API}/compliance/incidents/${incident.id}`,
        { status: nextStatus === 'under_review' ? 'investigating' : nextStatus },
        { headers }
      );
      toast.success('Incident status updated');
      if (selected?.id === incident.id) {
        setSelected({ ...selected, status: nextStatus === 'under_review' ? 'investigating' : nextStatus });
      }
      fetchIncidents();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update incident');
    }
  };

  const handleAddNote = async () => {
    if (!selected?.id || !note.trim()) return;
    try {
      await axios.post(`${API}/compliance/incidents/${selected.id}/notes`, { note: note.trim() }, { headers });
      const detail = await axios.get(`${API}/compliance/incidents`, { headers, params: { status: selected.status } });
      const refreshed = (detail.data || []).find((x) => x.id === selected.id) || selected;
      setSelected(refreshed);
      setNote('');
      fetchIncidents();
      toast.success('Note added');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add note');
    }
  };

  return (
    <div className="space-y-6" data-testid="incidents-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Incidents</h1>
          <p className="text-sm text-slate-600 mt-1">Review and close worker-submitted incident reports.</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Log Incident
        </Button>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Incident register</CardTitle>
          <div className="w-48">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>{status}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 flex items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
            </div>
          ) : incidents.length === 0 ? (
            <p className="text-sm text-slate-600">No incidents found.</p>
          ) : (
            <div className="space-y-3">
              {incidents.map((incident) => {
                const label = incident.status === 'investigating' ? 'under_review' : incident.status;
                return (
                  <div
                    key={incident.id}
                    className="rounded-lg border border-slate-200 p-3 cursor-pointer hover:bg-slate-50"
                    onClick={() => {
                      setSelected(incident);
                      setShowDetail(true);
                    }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-slate-900">{incident.reference_number} — {incident.title}</p>
                        <p className="mt-1 text-xs text-slate-600">{toLocalDateTime(incident.date_occurred)} • {incident.location || 'No location'}</p>
                        <p className="mt-1 text-xs text-slate-600 line-clamp-2">{incident.description}</p>
                      </div>
                      <Badge className={
                        label === 'closed'
                          ? 'bg-green-100 text-green-700'
                          : label === 'under_review'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-blue-100 text-blue-700'
                      }>
                        {label}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Log incident</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Type</Label>
              <Select value={form.incident_type} onValueChange={(v) => setForm((prev) => ({ ...prev, incident_type: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="incident">Incident</SelectItem>
                  <SelectItem value="near_miss">Near miss</SelectItem>
                  <SelectItem value="concern">Concern</SelectItem>
                  <SelectItem value="safeguarding">Safeguarding concern</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Title</Label>
              <Input value={form.title} onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))} />
            </div>
            <div>
              <Label>Date/time occurred</Label>
              <Input type="datetime-local" value={form.date_occurred} onChange={(e) => setForm((prev) => ({ ...prev, date_occurred: e.target.value }))} />
            </div>
            <div>
              <Label>Location</Label>
              <Input value={form.location} onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))} />
            </div>
            <div>
              <Label>Related shift ID (optional)</Label>
              <Input value={form.related_shift_id} onChange={(e) => setForm((prev) => ({ ...prev, related_shift_id: e.target.value }))} />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={4} value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{selected?.reference_number || 'Incident detail'}</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-medium text-slate-900">{selected.title}</p>
                <p className="text-xs text-slate-600 mt-1">{toLocalDateTime(selected.date_occurred)} • {selected.location || 'No location'}</p>
                <p className="text-sm text-slate-700 mt-2">{selected.description}</p>
                {selected.action_taken ? <p className="text-xs text-slate-600 mt-2">Action taken: {selected.action_taken}</p> : null}
              </div>

              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.filter((s) => s !== (selected.status === 'investigating' ? 'under_review' : selected.status)).map((status) => (
                  <Button key={status} variant="outline" size="sm" onClick={() => handleStatusChange(selected, status)}>
                    Mark {status}
                  </Button>
                ))}
              </div>

              <div className="space-y-2">
                <Label>Follow-up note</Label>
                <div className="flex gap-2">
                  <Textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
                </div>
                <Button size="sm" onClick={handleAddNote}>Add note</Button>
              </div>

              {(selected.notes || []).length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-900">Timeline</p>
                  {(selected.notes || []).slice().reverse().map((item) => (
                    <div key={item.id || `${item.created_at}-${item.text}`} className="rounded-md border border-slate-200 p-2">
                      <p className="text-sm text-slate-700">{item.text}</p>
                      <p className="text-xs text-slate-500 mt-1">{item.author_email || item.author_id || item.author_type || 'system'} • {toLocalDateTime(item.created_at)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

