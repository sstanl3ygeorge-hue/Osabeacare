import { AlertCircle, ArrowRight, CheckCircle2, Clock3 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

const ACTION_STYLES = {
  critical: {
    card: 'border-red-200 bg-red-50/70',
    iconWrap: 'bg-red-100',
    icon: 'text-red-600',
    badge: 'bg-red-100 text-red-700',
    button: 'bg-red-600 hover:bg-red-700',
    Icon: AlertCircle,
  },
  high: {
    card: 'border-amber-200 bg-amber-50/70',
    iconWrap: 'bg-amber-100',
    icon: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-700',
    button: 'bg-amber-600 hover:bg-amber-700',
    Icon: Clock3,
  },
  medium: {
    card: 'border-blue-200 bg-blue-50/70',
    iconWrap: 'bg-blue-100',
    icon: 'text-blue-600',
    badge: 'bg-blue-100 text-blue-700',
    button: 'bg-blue-600 hover:bg-blue-700',
    Icon: ArrowRight,
  },
  success: {
    card: 'border-green-200 bg-green-50/70',
    iconWrap: 'bg-green-100',
    icon: 'text-green-600',
    badge: 'bg-green-100 text-green-700',
    button: 'bg-green-600 hover:bg-green-700',
    Icon: CheckCircle2,
  },
};

export default function NextActionCard({ action, onPrimaryAction, secondaryAction }) {
  if (!action) return null;
  const style = ACTION_STYLES[action.level] || ACTION_STYLES.medium;
  const Icon = style.Icon;

  return (
    <Card className={`border shadow-sm ${style.card}`} data-testid="next-action-card">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${style.iconWrap}`}>
            <Icon className={`h-5 w-5 ${style.icon}`} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-lg text-slate-900">{action.title}</CardTitle>
              <Badge className={style.badge}>Next action</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-600">{action.description}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button className={`w-full sm:w-auto ${style.button}`} onClick={() => onPrimaryAction?.(action)}>
            {action.primaryLabel}
          </Button>
          {secondaryAction ? (
            <Button variant="outline" className="w-full sm:w-auto" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
