import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import EditReasonDialog from './EditReasonDialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import { Plus, Trash2, GripVertical } from 'lucide-react';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

/**
 * EditEmploymentHistoryDialog - Edit employment history with reason logging
 */
export default function EditEmploymentHistoryDialog({
  open,
  onClose,
  employeeId,
  currentHistory = [],
  onSuccess
}) {
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [jobs, setJobs] = useState([]);

  const normalizeJob = (job) => ({
    id: job.id || job._id || `temp_${Date.now()}_${Math.random()}`,
    employer: job.employer || job.company || job.employer_name || '',
    job_title: job.job_title || job.position || job.title || '',
    start_date: job.start_date || '',
    end_date: job.end_date || '',
    responsibilities: job.responsibilities || '',
    is_current: job.is_current || job.current || false
  });

  useEffect(() => {
    if (open) {
      // Initialize with current history or empty array
      setJobs(currentHistory.length > 0 ? currentHistory.map(normalizeJob) : [createEmptyJob()]);
    }
  }, [currentHistory, open]);

  const createEmptyJob = () => ({
    id: `temp_${Date.now()}`,
    employer: '',
    job_title: '',
    start_date: '',
    end_date: '',
    responsibilities: '',
    is_current: false
  });

  const handleJobChange = (index, field, value) => {
    const updated = [...jobs];
    updated[index] = { ...updated[index], [field]: value };
    
    // If marking as current, clear end_date and unmark others
    if (field === 'is_current' && value) {
      updated[index].end_date = '';
      updated.forEach((job, i) => {
        if (i !== index) job.is_current = false;
      });
    }
    
    setJobs(updated);
  };

  const addJob = () => {
    setJobs([...jobs, createEmptyJob()]);
  };

  const removeJob = (index) => {
    if (jobs.length === 1) {
      toast.error('At least one employment record is required');
      return;
    }
    setJobs(jobs.filter((_, i) => i !== index));
  };

  const handleSave = async (reason) => {
    // Validate
    for (const job of jobs) {
      if (!job.employer.trim()) {
        toast.error('Employer name is required for all positions');
        return;
      }
      if (!job.job_title.trim()) {
        toast.error('Job title is required for all positions');
        return;
      }
      if (!job.start_date) {
        toast.error('Start date is required for all positions');
        return;
      }
      if (!job.is_current && !job.end_date) {
        toast.error('End date is required for past positions');
        return;
      }
    }

    setIsLoading(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-history`,
        {
          employment_history: jobs.map(job => ({
            employer: job.employer,
            job_title: job.job_title,
            start_date: job.start_date,
            end_date: job.is_current ? null : job.end_date,
            responsibilities: job.responsibilities,
            is_current: job.is_current
          })),
          edit_reason: reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Employment history updated');
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update employment history');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <EditReasonDialog
      open={open}
      onClose={onClose}
      title="Edit Employment History"
      description="Add, edit, or remove employment records. Gaps will be auto-detected."
      onSave={handleSave}
      isLoading={isLoading}
    >
      <div className="space-y-4">
        {jobs.map((job, index) => (
          <div key={job.id || index} className="p-4 border border-gray-200 rounded-lg relative">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700">Position {index + 1}</span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeJob(index)}
                className="text-red-500 hover:text-red-700 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Employer *</Label>
                <Input
                  value={job.employer}
                  onChange={(e) => handleJobChange(index, 'employer', e.target.value)}
                  placeholder="Company name"
                  className="rounded-lg text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Job Title *</Label>
                <Input
                  value={job.job_title}
                  onChange={(e) => handleJobChange(index, 'job_title', e.target.value)}
                  placeholder="Your role"
                  className="rounded-lg text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Start Date *</Label>
                <Input
                  type="date"
                  value={job.start_date}
                  onChange={(e) => handleJobChange(index, 'start_date', e.target.value)}
                  className="rounded-lg text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">End Date {job.is_current ? '(Current)' : '*'}</Label>
                <Input
                  type="date"
                  value={job.end_date}
                  onChange={(e) => handleJobChange(index, 'end_date', e.target.value)}
                  disabled={job.is_current}
                  className="rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="mt-3 space-y-1">
              <Label className="text-xs">Responsibilities</Label>
              <Textarea
                value={job.responsibilities || ''}
                onChange={(e) => handleJobChange(index, 'responsibilities', e.target.value)}
                placeholder="Brief description of duties"
                className="rounded-lg text-sm min-h-[60px]"
              />
            </div>

            <div className="mt-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={job.is_current}
                  onChange={(e) => handleJobChange(index, 'is_current', e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-600">This is my current position</span>
              </label>
            </div>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          onClick={addJob}
          className="w-full rounded-lg"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Another Position
        </Button>
      </div>
    </EditReasonDialog>
  );
}

