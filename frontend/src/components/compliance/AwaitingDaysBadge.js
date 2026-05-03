import { Badge } from '../ui/badge';
import { Clock, AlertTriangle } from 'lucide-react';

/**
 * AwaitingDaysBadge — counts UP from a "sent" / "requested" / "submitted"
 * timestamp, telling admins how long an item has been waiting for the
 * other party to respond (Tier 3 #4 + #5).
 *
 * Distinct from DaysRemainingBadge (which counts DOWN to an expiry):
 *   • DaysRemainingBadge ? "12d left" (training expiry)
 *   • AwaitingDaysBadge  ? "Awaiting 12d" (chase context)
 *
 * Tone rules:
 *   • 0–3 days waiting           ? gray   "Awaiting 2d"
 *   • 4–13 days waiting          ? amber  "Awaiting 9d"
 *   • 14+ days waiting           ? red    "Awaiting 21d — chase"
 *   • null / undefined sentAt    ? null   (renders nothing)
 *
 * Usage:
 *   <AwaitingDaysBadge sentAt={ack.requested_at} />
 *   <AwaitingDaysBadge sentAt={ref.sent_at} label="Reference" />
 */
export default function AwaitingDaysBadge({
  sentAt = null,
  label = null,
  className = '',
  testId = 'awaiting-days-badge',
}) {
  const days = computeDays(sentAt);
  if (days === null) return null;

  const tone = pickTone(days);
  const Icon = tone.icon;
  const text = `${label ? `${label} ` : ''}Awaiting ${days}d${days >= 14 ? ' — chase' : ''}`;
  return (
    <Badge
      variant="outline"
      className={`text-[10px] px-1.5 py-0 inline-flex items-center gap-1 ${tone.classes} ${className}`}
      data-testid={testId}
    >
      <Icon className="h-3 w-3" />
      {text}
    </Badge>
  );
}

function computeDays(sentAt) {
  if (!sentAt) return null;
  const sent = new Date(sentAt);
  if (Number.isNaN(sent.getTime())) return null;
  const ms = Date.now() - sent.getTime();
  if (ms < 0) return 0;
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function pickTone(days) {
  if (days >= 14) {
    return {
      classes: 'bg-red-50 text-red-700 border-red-200',
      icon: AlertTriangle,
    };
  }
  if (days >= 4) {
    return {
      classes: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: Clock,
    };
  }
  return {
    classes: 'bg-gray-50 text-gray-600 border-gray-200',
    icon: Clock,
  };
}
