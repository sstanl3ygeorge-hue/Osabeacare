import React from 'react';
import { 
  ChevronRight,
  FileText,
  Upload,
  Send,
  ClipboardCheck,
  UserCheck,
  GraduationCap,
  Shield,
  Clock,
  AlertTriangle
} from 'lucide-react';

/**
 * NextActionsPanel - Dynamic, clickable list of next actions
 * 
 * Each item scrolls to the relevant compliance section when clicked.
 * Actions are derived from:
 * - Missing documents
 * - Pending reviews
 * - Unverified checks
 * - Expiring items
 */
export default function NextActionsPanel({
  // Action items - array of { type, label, description, sectionKey, priority, onClick }
  actions = [],
  // Maximum actions to show
  maxActions = 5,
  // Callback when action is clicked
  onActionClick
}) {
  if (!actions || actions.length === 0) {
    return null;
  }

  // Sort by priority (higher priority first)
  const sortedActions = [...actions].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  const visibleActions = sortedActions.slice(0, maxActions);
  const remainingCount = actions.length - maxActions;

  // Get icon based on action type
  const getActionIcon = (type) => {
    switch (type) {
      case 'upload':
        return <Upload className="h-4 w-4" />;
      case 'request':
        return <Send className="h-4 w-4" />;
      case 'verify':
      case 'record_check':
        return <ClipboardCheck className="h-4 w-4" />;
      case 'review':
        return <Clock className="h-4 w-4" />;
      case 'reference':
        return <UserCheck className="h-4 w-4" />;
      case 'training':
        return <GraduationCap className="h-4 w-4" />;
      case 'expiry':
        return <AlertTriangle className="h-4 w-4" />;
      case 'rtw':
        return <Shield className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  // Get color based on action type/priority
  const getActionColors = (type, priority) => {
    if (priority >= 3 || type === 'expiry') {
      return {
        bg: 'bg-red-50',
        border: 'border-red-200',
        icon: 'bg-red-100 text-red-600',
        text: 'text-red-800',
        hover: 'hover:bg-red-100 hover:border-red-300'
      };
    }
    if (priority >= 2 || type === 'review') {
      return {
        bg: 'bg-amber-50',
        border: 'border-amber-200',
        icon: 'bg-amber-100 text-amber-600',
        text: 'text-amber-800',
        hover: 'hover:bg-amber-100 hover:border-amber-300'
      };
    }
    if (type === 'training') {
      return {
        bg: 'bg-purple-50',
        border: 'border-purple-200',
        icon: 'bg-purple-100 text-purple-600',
        text: 'text-purple-800',
        hover: 'hover:bg-purple-100 hover:border-purple-300'
      };
    }
    if (type === 'reference') {
      return {
        bg: 'bg-orange-50',
        border: 'border-orange-200',
        icon: 'bg-orange-100 text-orange-600',
        text: 'text-orange-800',
        hover: 'hover:bg-orange-100 hover:border-orange-300'
      };
    }
    return {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'bg-blue-100 text-blue-600',
      text: 'text-blue-800',
      hover: 'hover:bg-blue-100 hover:border-blue-300'
    };
  };

  return (
    <div className="mb-6" data-testid="next-actions-panel">
      <div className="flex items-center gap-2 mb-3">
        <ChevronRight className="h-4 w-4 text-slate-500" />
        <h3 className="text-sm font-semibold text-slate-700">Next Actions</h3>
        <span className="text-xs text-slate-500">({actions.length})</span>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {visibleActions.map((action, idx) => {
          const colors = getActionColors(action.type, action.priority);
          
          return (
            <button
              key={action.id || idx}
              onClick={() => {
                if (action.onClick) {
                  action.onClick();
                } else if (onActionClick) {
                  onActionClick(action);
                }
              }}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all text-left group ${colors.bg} ${colors.border} ${colors.hover}`}
              data-testid={`next-action-${idx}`}
              data-section={action.sectionKey}
            >
              <div className={`p-2 rounded-lg ${colors.icon}`}>
                {getActionIcon(action.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${colors.text} group-hover:underline truncate`}>
                  {action.label}
                </p>
                {action.description && (
                  <p className="text-xs text-slate-500 truncate">
                    {action.description}
                  </p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 text-slate-400 group-hover:translate-x-0.5 transition-transform flex-shrink-0" />
            </button>
          );
        })}
      </div>
      
      {remainingCount > 0 && (
        <p className="text-xs text-slate-500 mt-2 text-center">
          + {remainingCount} more action{remainingCount !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
}
