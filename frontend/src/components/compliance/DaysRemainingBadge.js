import { Badge } from '../ui/badge';
import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';

/**
 * DaysRemainingBadge — surfaces "days remaining" until an item expires or
 * needs follow-up, using the same colour rules everywhere (Tier 2 #6).
 *
 * Tone rules (single source of truth):
 *   • > 30 days remaining            ? green   "32d left"
 *   • 8–30 days remaining            ? amber   "12d left"
 *   • 1–7 days remaining             ? red     "5d left"
 *   • 0 / past expiry                ? red     "Overdue"
 *   • null / undefined               ? null    (renders nothing)
 *
 * Usage:
 *   <DaysRemainingBadge expiresAt={row.expires_at} />
 *   <DaysRemainingBadge daysUntil={42} label="Renewal" />
 */
export default function DaysRemainingBadge({
  expiresAt = null,
  daysUntil: daysUntilProp = null,
  label = null,
  className = '',
  testId = 'days-remaining-badge',
}) {
  const days = computeDays({ expiresAt, daysUntilProp });
  if (days === null) return null;

  const tone = pickTone(days);
  const Icon = tone.icon;
  return (
    <Badge
      variant="outline"
      className={`text-[10px] px-1.5 py-0 inline-flex items-center gap-1 ${tone.classes} ${className}`}
      data-testid={testId}
    >
      <Icon className="h-3 w-3" />
      {label ? `${label}: ` : ''}{tone.text(days)}
    </Badge>
  );
}

function computeDays({ expiresAt, daysUntilProp }) {
  if (Number.isFinite(daysUntilProp)) return Math.floor(daysUntilProp);
  if (!expiresAt) return null;
  const expiry = new Date(expiresAt);
  if (Number.isNaN(expiry.getTime())) return null;
  const ms = expiry.getTime() - Date.now();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function pickTone(days) {
  if (days < 0) {
    return {
      classes: 'bg-red-50 text-red-700 border-red-200',
      icon: AlertTriangle,
      text: () => 'Overdue',
    };
  }
  if (days <= 7) {
    return {
      classes: 'bg-red-50 text-red-700 border-red-200',
      icon: AlertTriangle,
      text: (d) => `${d}d left`,
    };
  }
  if (days <= 30) {
    return {
      classes: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: Clock,
      text: (d) => `${d}d left`,
    };
  }
  return {
    classes: 'bg-green-50 text-green-700 border-green-200',
    icon: CheckCircle2,
    text: (d) => `${d}d left`,
  };
}
