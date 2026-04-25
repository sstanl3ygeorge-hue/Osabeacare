import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Plus, CalendarClock } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function getBadgeVariant(nextDueAt) {
  if (!nextDueAt) return 'secondary';
  const due = new Date(nextDueAt);
  const now = new Date();
  if (Number.isNaN(due.getTime())) return 'secondary';
  return due < now ? 'destructive' : 'outline';
}

export default function AppraisalsPanel({ employeeId, employeeName = '' }) {
  const { token } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    appraisal_date: '',
    reviewer: '',
    notes: '',
    actions: '',
    next_due_at: '',
  });

  const headers = useMemo(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  const fetchItems = async () => {
    if (!employeeId || !token) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/appraisals`, { headers });
      setItems(response.data?.items || []);
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Failed to load appraisals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [employeeId, token]);

  const onCreate = async () => {
    if (!form.appraisal_date || !form.reviewer.trim()) {
      toast.error('Appraisal date and reviewer are required');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        appraisal_date: form.appraisal_date,
        reviewer: form.reviewer.trim(),
        notes: form.notes.trim() || null,
        actions: form.actions
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        next_due_at: form.next_due_at || null,
      };
      await axios.post(`${API}/employees/${employeeId}/appraisals`, payload, { headers });
      toast.success('Appraisal saved');
      setOpen(false);
      setForm({ appraisal_date: '', reviewer: '', notes: '', actions: '', next_due_at: '' });
      fetchItems();
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Failed to save appraisal');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="border-[#E4E8EB] shadow-sm" data-testid="appraisals-panel">
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div>
          <CardTitle className="font-heading text-lg">Appraisals</CardTitle>
          <p className="text-sm text-gray-600 mt-1">
            Minimal appraisal evidence for {employeeName || 'employee'}.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Appraisal
        </Button>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="text-sm text-gray-500">Loading appraisals...</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-gray-500">No appraisal records yet.</div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-lg border border-gray-200 p-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="text-sm font-medium text-gray-900">
                    {item.appraisal_date || 'No appraisal date'}
                  </div>
                  <Badge variant={getBadgeVariant(item.next_due_at)}>
                    {item.next_due_at ? `Next due: ${item.next_due_at}` : 'No next due date'}
                  </Badge>
                </div>
                <div className="text-sm text-gray-700 mt-1">Reviewer: {item.reviewer || 'N/A'}</div>
                {item.notes && <div className="text-sm text-gray-600 mt-2">{item.notes}</div>}
                {(item.actions || []).length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-sm text-gray-600">
                    {(item.actions || []).map((action, idx) => (
                      <li key={`${item.id}-action-${idx}`}>{action}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarClock className="h-5 w-5 text-teal-600" />
              Add Appraisal
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Appraisal Date *</Label>
              <Input
                type="date"
                value={form.appraisal_date}
                onChange={(e) => setForm({ ...form, appraisal_date: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Reviewer *</Label>
              <Input
                value={form.reviewer}
                onChange={(e) => setForm({ ...form, reviewer: e.target.value })}
                placeholder="Name or role"
              />
            </div>

            <div className="space-y-2">
              <Label>Next Due At</Label>
              <Input
                type="date"
                value={form.next_due_at}
                onChange={(e) => setForm({ ...form, next_due_at: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Summary notes"
              />
            </div>

            <div className="space-y-2">
              <Label>Actions (one per line)</Label>
              <Textarea
                value={form.actions}
                onChange={(e) => setForm({ ...form, actions: e.target.value })}
                placeholder="Action 1\nAction 2"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={onCreate} disabled={saving}>
                {saving ? 'Saving...' : 'Save Appraisal'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
