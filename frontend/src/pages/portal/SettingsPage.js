import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../../components/ui/dialog';
import {
  Settings,
  User,
  Shield,
  Bell,
  Building2,
  Pencil,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const ORG_FIELDS = [
  { key: 'company_name',         label: 'Company name',          required: true,  placeholder: 'e.g. Osabea Healthcare Solutions LTD' },
  { key: 'company_address',      label: 'Company address',       required: true,  placeholder: 'Suite, Street, City, Postcode', multiline: true },
  { key: 'default_hourly_rate',  label: 'Default hourly rate (£)', required: true, placeholder: '12.98' },
  { key: 'default_sleep_in_rate',label: 'Default sleep-in rate (£)', required: false, placeholder: '40.00' },
  { key: 'registered_manager_name', label: 'Registered manager name', required: false, placeholder: 'e.g. Jane Smith' },
];

function fieldIsBlank(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  return false;
}

export default function SettingsPage() {
  const { user, token } = useAuth();
  const [orgSettings, setOrgSettings] = useState(null);
  const [loadingOrg, setLoadingOrg] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  const loadOrgSettings = async () => {
    setLoadingOrg(true);
    try {
      const res = await axios.get(`${API}/org-settings`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      setOrgSettings(res.data || {});
    } catch (err) {
      console.error('Failed to load org settings', err);
      toast.error('Could not load organisation settings');
      setOrgSettings({});
    } finally {
      setLoadingOrg(false);
    }
  };

  useEffect(() => {
    if (isAdmin) loadOrgSettings();
  }, [isAdmin]); // eslint-disable-line react-hooks/exhaustive-deps

  const openEdit = () => {
    const initial = {};
    ORG_FIELDS.forEach(f => {
      const v = orgSettings?.[f.key];
      initial[f.key] = v === null || v === undefined ? '' : String(v);
    });
    setForm(initial);
    setEditOpen(true);
  };

  const handleSave = async () => {
    // Client-side guard: required fields must not be blank.
    const blankRequired = ORG_FIELDS.filter(f => f.required && fieldIsBlank(form[f.key]));
    if (blankRequired.length) {
      toast.error(`Required: ${blankRequired.map(f => f.label).join(', ')}`);
      return;
    }
    setSaving(true);
    try {
      // Only send fields that have a non-empty value, so we never inadvertently
      // clear an optional field by submitting an empty string.
      const payload = {};
      ORG_FIELDS.forEach(f => {
        const v = form[f.key];
        if (typeof v === 'string' && v.trim() !== '') {
          payload[f.key] = v.trim();
        }
      });
      const res = await axios.put(`${API}/org-settings`, payload, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      setOrgSettings(res.data || orgSettings);
      toast.success('Organisation settings saved');
      setEditOpen(false);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message =
        (typeof detail === 'string' && detail) ||
        detail?.message ||
        err?.message ||
        'Failed to save settings';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const renderReadinessPill = () => {
    if (!orgSettings) return null;
    const missing = ORG_FIELDS.filter(f => f.required && fieldIsBlank(orgSettings[f.key]));
    if (missing.length === 0) {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
          data-testid="org-settings-readiness-ok"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Contract render: ready
        </span>
      );
    }
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800"
        data-testid="org-settings-readiness-missing"
        title={`Missing: ${missing.map(f => f.label).join(', ')}`}
      >
        <AlertTriangle className="h-3.5 w-3.5" />
        Required fields missing ({missing.length})
      </span>
    );
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-heading font-semibold text-text-primary">Settings</h1>
        <p className="text-text-muted mt-1">Manage your account preferences and system settings</p>
      </div>

      {/* Settings Cards */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* User Profile */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between py-2 border-b border-[#F0F2F4]">
              <span className="text-text-muted">Name</span>
              <span className="font-medium text-text-primary">{user?.name || 'Not set'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#F0F2F4]">
              <span className="text-text-muted">Email</span>
              <span className="font-medium text-text-primary">{user?.email || 'Not set'}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-text-muted">Role</span>
              <span className="font-medium text-text-primary capitalize">{user?.role?.replace('_', ' ') || 'Unknown'}</span>
            </div>
          </CardContent>
        </Card>

        {/* Access Level */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Access Level
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {user?.role === 'super_admin' && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-success/10 rounded-lg flex items-center justify-center">
                  <Shield className="h-4 w-4 text-success" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Full Access</p>
                  <p className="text-sm text-text-muted">Manage all system settings and users</p>
                </div>
              </div>
            )}
            {(user?.role === 'admin' || user?.role === 'super_admin') && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                  <User className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Employee Management</p>
                  <p className="text-sm text-text-muted">Create and manage employee records</p>
                </div>
              </div>
            )}
            {user?.role === 'branch_manager' && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-warning/10 rounded-lg flex items-center justify-center">
                  <User className="h-4 w-4 text-warning" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Branch Management</p>
                  <p className="text-sm text-text-muted">Manage branch employees and shifts</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* System Preferences */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Settings className="h-5 w-5 text-primary" />
              System Preferences
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-text-muted">System-wide preferences and configuration options.</p>
            <div className="mt-4 p-3 bg-[#F8FAFA] rounded-xl">
              <p className="text-sm text-text-muted">Additional settings will be available here in future updates.</p>
            </div>
          </CardContent>
        </Card>

        {/* Organisation Settings (admins only) */}
        {isAdmin && (
          <Card className="border-[#E4E8EB] shadow-sm lg:col-span-2" data-testid="org-settings-card">
            <CardHeader>
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-primary" />
                  Organisation Settings
                </CardTitle>
                <div className="flex items-center gap-3">
                  {!loadingOrg && renderReadinessPill()}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={openEdit}
                    disabled={loadingOrg}
                    className="h-8 text-xs rounded-lg"
                    data-testid="org-settings-edit-btn"
                  >
                    <Pencil className="h-3.5 w-3.5 mr-1.5" />
                    Edit
                  </Button>
                </div>
              </div>
              <p className="text-sm text-text-muted mt-1">
                These values appear on every contract and handbook generated by the system.
                Per-employee values still take precedence where set.
              </p>
            </CardHeader>
            <CardContent>
              {loadingOrg ? (
                <div className="flex items-center gap-2 text-text-muted text-sm py-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading…
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
                  {ORG_FIELDS.map(f => {
                    const value = orgSettings?.[f.key];
                    const blank = fieldIsBlank(value);
                    return (
                      <div
                        key={f.key}
                        className="flex flex-col py-2 border-b border-[#F0F2F4] last:border-0"
                        data-testid={`org-field-${f.key}`}
                      >
                        <span className="text-xs text-text-muted flex items-center gap-1.5">
                          {f.label}
                          {f.required && <span className="text-red-500">*</span>}
                        </span>
                        <span
                          className={`text-sm font-medium mt-0.5 ${
                            blank
                              ? f.required
                                ? 'text-red-600'
                                : 'text-text-muted italic'
                              : 'text-text-primary'
                          }`}
                        >
                          {blank ? (f.required ? 'Not set — required' : 'Not set') : String(value)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Notifications (placeholder) */}
        <Card className="border-[#E4E8EB] shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-text-muted">Notification preferences and alert settings.</p>
            <div className="mt-4 p-3 bg-[#F8FAFA] rounded-xl">
              <p className="text-sm text-text-muted">Configure email and in-app notifications (coming soon).</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Edit Org Settings dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[560px]" data-testid="org-settings-edit-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-primary" />
              Edit Organisation Settings
            </DialogTitle>
            <DialogDescription>
              Required fields cannot be cleared. Leave optional fields blank to keep
              their existing value.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {ORG_FIELDS.map(f => (
              <div key={f.key} className="space-y-1.5">
                <Label htmlFor={`org-${f.key}`} className="text-sm">
                  {f.label}
                  {f.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                {f.multiline ? (
                  <textarea
                    id={`org-${f.key}`}
                    rows={3}
                    placeholder={f.placeholder}
                    value={form[f.key] ?? ''}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    data-testid={`org-input-${f.key}`}
                  />
                ) : (
                  <Input
                    id={`org-${f.key}`}
                    placeholder={f.placeholder}
                    value={form[f.key] ?? ''}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                    data-testid={`org-input-${f.key}`}
                  />
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditOpen(false)}
              disabled={saving}
              data-testid="org-settings-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              data-testid="org-settings-save-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : null}
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
