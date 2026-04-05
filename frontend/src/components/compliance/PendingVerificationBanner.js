import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import {
  AlertTriangle,
  Clock,
  FileText,
  CheckCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { cn } from '../../lib/utils';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * PendingVerificationBanner - Shows items awaiting admin verification
 * 
 * Displays at the top of employee profile when there are:
 * - Documents uploaded but not verified
 * - References received but not reviewed
 * - Forms submitted but not verified
 */
export default function PendingVerificationBanner({ 
  employeeId, 
  employeeName,
  onNavigateToItem 
}) {
  const { token } = useAuth();
  const [pendingItems, setPendingItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    fetchPendingItems();
  }, [employeeId]);

  const fetchPendingItems = async () => {
    try {
      const response = await axios.get(
        `${API}/api/employees/${employeeId}/pending-verifications`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setPendingItems(response.data.items || []);
    } catch (error) {
      console.error('Failed to fetch pending verifications:', error);
      setPendingItems([]);
    } finally {
      setLoading(false);
    }
  };

  // Format time ago
  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
    return date.toLocaleDateString('en-GB');
  };

  // Get icon for item type
  const getItemIcon = (type) => {
    switch (type) {
      case 'document':
        return <FileText className="h-4 w-4" />;
      case 'reference':
        return <CheckCircle className="h-4 w-4" />;
      case 'form':
        return <FileText className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  if (loading) return null;
  if (pendingItems.length === 0) return null;

  return (
    <Card className="border-amber-200 bg-amber-50/50 mb-4" data-testid="pending-verification-banner">
      <CardContent className="p-4">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <span className="font-semibold text-amber-800">
              PENDING VERIFICATION ({pendingItems.length})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm"
              className="bg-amber-100 border-amber-300 text-amber-800 hover:bg-amber-200"
              onClick={(e) => {
                e.stopPropagation();
                if (onNavigateToItem && pendingItems[0]) {
                  onNavigateToItem(pendingItems[0].tab || 'compliance');
                }
              }}
              data-testid="verify-all-btn"
            >
              Verify All
            </Button>
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-amber-600" />
            ) : (
              <ChevronDown className="h-4 w-4 text-amber-600" />
            )}
          </div>
        </div>

        {expanded && (
          <div className="mt-3 space-y-2">
            {pendingItems.map((item, idx) => (
              <div 
                key={idx}
                className={cn(
                  "flex items-center justify-between p-2 rounded-md bg-white border border-amber-100",
                  "hover:bg-amber-50 cursor-pointer transition-colors"
                )}
                onClick={() => onNavigateToItem?.(item.tab || 'compliance')}
                data-testid={`pending-item-${idx}`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-full bg-amber-100 text-amber-700">
                    {getItemIcon(item.type)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.name}</p>
                    <p className="text-xs text-gray-500">
                      Uploaded {formatTimeAgo(item.uploaded_at)}
                    </p>
                  </div>
                </div>
                <Badge 
                  className={cn(
                    "text-xs",
                    item.type === 'document' && "bg-blue-100 text-blue-700",
                    item.type === 'reference' && "bg-purple-100 text-purple-700",
                    item.type === 'form' && "bg-green-100 text-green-700"
                  )}
                >
                  {item.type === 'document' ? 'Document' : 
                   item.type === 'reference' ? 'Reference' : 'Form'}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
