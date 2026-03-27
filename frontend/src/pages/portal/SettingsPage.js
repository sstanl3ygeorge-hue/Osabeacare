import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Settings, User, Shield, Bell } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
          Settings
        </h1>
        <p className="text-text-muted mt-1">Manage your account and preferences</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Profile */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Profile Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                {user?.picture ? (
                  <img src={user.picture} alt={user.name} className="w-16 h-16 rounded-2xl" />
                ) : (
                  <span className="text-primary font-heading font-bold text-2xl">
                    {user?.name?.charAt(0) || 'U'}
                  </span>
                )}
              </div>
              <div>
                <p className="font-heading font-semibold text-text-primary text-lg">{user?.name}</p>
                <p className="text-text-muted">{user?.email}</p>
              </div>
            </div>
            <div className="pt-4 border-t border-[#E4E8EB] space-y-3">
              <div className="flex justify-between">
                <span className="text-text-muted">Role</span>
                <span className="font-medium text-text-primary capitalize">{user?.role?.replace('_', ' ')}</span>
              </div>
              {user?.branch && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Branch</span>
                  <span className="font-medium text-text-primary">{user.branch}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-text-muted">User ID</span>
                <span className="font-medium text-text-primary">{user?.user_id}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Permissions */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Permissions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {user?.role === 'super_admin' && (
              <>
                <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                  <div className="w-8 h-8 bg-success/10 rounded-lg flex items-center justify-center">
                    <Shield className="h-4 w-4 text-success" />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Full Access</p>
                    <p className="text-sm text-text-muted">Manage all system settings and users</p>
                  </div>
                </div>
              </>
            )}
            {(user?.role === 'admin' || user?.role === 'super_admin') && (
              <>
                <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                  <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                    <User className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Employee Management</p>
                    <p className="text-sm text-text-muted">Create and manage employee records</p>
                  </div>
                </div>
              </>
            )}
            {user?.role === 'branch_manager' && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center">
                  <User className="h-4 w-4 text-info" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Branch Access</p>
                  <p className="text-sm text-text-muted">View and manage branch employees</p>
                </div>
              </div>
            )}
            {user?.role === 'employee' && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center">
                  <User className="h-4 w-4 text-info" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Employee Access</p>
                  <p className="text-sm text-text-muted">View and upload your own documents</p>
                </div>
              </div>
            )}
            {user?.role === 'auditor' && (
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="w-8 h-8 bg-warning/10 rounded-lg flex items-center justify-center">
                  <Settings className="h-4 w-4 text-warning" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">Read-Only Access</p>
                  <p className="text-sm text-text-muted">View compliance data for auditing purposes</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Notifications (placeholder) */}
        <Card className="border-[#E4E8EB] shadow-sm lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Notification Preferences
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-text-muted">
              Notification settings will be available in a future update. You'll be able to configure email alerts for document requests, policy assignments, and expiring documents.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
