import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import InductionChecklistPanel from './InductionChecklistPanel';
import CompetencyRecordsPanel from './CompetencyRecordsPanel';
import { ClipboardList, Award } from 'lucide-react';

export default function HealthCompetencySection({ 
  employeeId, 
  employeeName,
  isAuditor = false,
  onRefresh 
}) {
  const [activeTab, setActiveTab] = useState('induction');

  return (
    <div className="space-y-4" data-testid="health-competency-section">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-4">
          <TabsTrigger value="induction" className="gap-2" data-testid="induction-tab">
            <ClipboardList className="h-4 w-4" />
            Induction
          </TabsTrigger>
          <TabsTrigger value="competency" className="gap-2" data-testid="competency-tab">
            <Award className="h-4 w-4" />
            Competencies
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="induction">
          <InductionChecklistPanel 
            employeeId={employeeId}
            employeeName={employeeName}
            isAuditor={isAuditor}
            onStatusChange={() => onRefresh && onRefresh()}
          />
        </TabsContent>
        
        <TabsContent value="competency">
          <CompetencyRecordsPanel 
            employeeId={employeeId}
            employeeName={employeeName}
            isAuditor={isAuditor}
            onRefresh={onRefresh}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
