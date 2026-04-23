import { Bell, RefreshCw, LogOut } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

export default function DashboardHeader({
  orgName,
  workerName,
  subtitle,
  progressLabel,
  unreadCount = 0,
  onRefresh,
  onToggleNotifications,
  onLogout,
}) {
  return (
    <div className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{orgName}</p>
          <h1 className="truncate text-xl font-semibold text-slate-900">Welcome, {workerName}</h1>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
          {progressLabel ? <p className="mt-1 text-xs text-slate-500">{progressLabel}</p> : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="Refresh dashboard">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onToggleNotifications} aria-label="Notifications" className="relative">
            <Bell className="h-4 w-4" />
            {unreadCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-semibold text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            ) : null}
          </Button>
          <Button variant="outline" size="sm" onClick={onLogout} className="gap-1">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
