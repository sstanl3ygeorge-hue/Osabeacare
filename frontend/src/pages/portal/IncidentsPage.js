import { Navigate } from 'react-router-dom';
import { toast } from 'sonner';

let notified = false;

export default function IncidentsPage() {
  if (!notified) {
    notified = true;
    toast.info('Incidents are now managed in Compliance Centre for consistent reportable incident handling.');
  }
  return <Navigate to="/portal/compliance-centre?tab=incidents" replace />;
}
