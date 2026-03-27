import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Button } from '../ui/button';
import { Plus, Trash2 } from 'lucide-react';

export default function FormFieldRenderer({
  field,
  value,
  onChange,
  disabled = false,
  employeeRole = null, // 'Healthcare Assistant' or 'Nurse'
  className = ""
}) {
  // Check role-based visibility
  if (field.role_restriction) {
    if (field.role_restriction === 'nurse_only' && employeeRole !== 'Nurse') {
      return null;
    }
    if (field.role_restriction === 'hca_only' && employeeRole === 'Nurse') {
      return null;
    }
  }

  const renderField = () => {
    switch (field.type) {
      case 'text':
      case 'email':
      case 'date':
      case 'number':
        return (
          <Input
            type={field.type}
            value={value || ''}
            onChange={(e) => onChange(field.name, e.target.value)}
            disabled={disabled}
            placeholder={field.placeholder || ''}
            className="rounded-xl"
            required={field.required}
            data-testid={`field-${field.name}`}
          />
        );

      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => onChange(field.name, e.target.value)}
            disabled={disabled}
            placeholder={field.placeholder || ''}
            className="rounded-xl"
            rows={field.rows || 3}
            required={field.required}
            data-testid={`field-${field.name}`}
          />
        );

      case 'select':
        return (
          <Select
            value={value || ''}
            onValueChange={(v) => onChange(field.name, v)}
            disabled={disabled}
          >
            <SelectTrigger className="rounded-xl" data-testid={`field-${field.name}`}>
              <SelectValue placeholder={field.placeholder || 'Select an option'} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'checkbox':
        return (
          <div className="flex items-start space-x-3">
            <Checkbox
              id={field.name}
              checked={value === true || value === 'true'}
              onCheckedChange={(checked) => onChange(field.name, checked)}
              disabled={disabled}
              data-testid={`field-${field.name}`}
            />
            <label 
              htmlFor={field.name} 
              className="text-sm text-text-primary cursor-pointer leading-relaxed"
            >
              {field.checkbox_label || field.label}
              {field.required && <span className="text-error ml-1">*</span>}
            </label>
          </div>
        );

      case 'multiselect':
        const selectedValues = Array.isArray(value) ? value : [];
        return (
          <div className="space-y-2">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {field.options?.map((option) => (
                <div key={option} className="flex items-center space-x-2">
                  <Checkbox
                    id={`${field.name}-${option}`}
                    checked={selectedValues.includes(option)}
                    onCheckedChange={(checked) => {
                      const newValues = checked
                        ? [...selectedValues, option]
                        : selectedValues.filter((v) => v !== option);
                      onChange(field.name, newValues);
                    }}
                    disabled={disabled}
                  />
                  <label 
                    htmlFor={`${field.name}-${option}`}
                    className="text-sm text-text-primary cursor-pointer"
                  >
                    {option}
                  </label>
                </div>
              ))}
            </div>
          </div>
        );

      case 'rating':
        const maxRating = field.max || 5;
        return (
          <div className="flex gap-2">
            {Array.from({ length: maxRating }, (_, i) => i + 1).map((rating) => (
              <button
                key={rating}
                type="button"
                onClick={() => !disabled && onChange(field.name, rating)}
                disabled={disabled}
                className={`w-10 h-10 rounded-lg border-2 font-medium transition-colors ${
                  value === rating
                    ? 'bg-primary border-primary text-white'
                    : 'border-[#E4E8EB] text-text-muted hover:border-primary/50'
                } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                data-testid={`field-${field.name}-${rating}`}
              >
                {rating}
              </button>
            ))}
          </div>
        );

      case 'competency':
        const competencyOptions = ['Competent', 'Needs Support', 'Not Competent'];
        return (
          <div className="flex flex-wrap gap-2">
            {competencyOptions.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => !disabled && onChange(field.name, option)}
                disabled={disabled}
                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  value === option
                    ? option === 'Competent'
                      ? 'bg-success border-success text-white'
                      : option === 'Needs Support'
                      ? 'bg-warning border-warning text-white'
                      : 'bg-error border-error text-white'
                    : 'border-[#E4E8EB] text-text-muted hover:border-primary/50'
                } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
              >
                {option}
              </button>
            ))}
          </div>
        );

      case 'outcome':
        const outcomeOptions = field.options || ['Fit to Work', 'Needs Supervision', 'Not Fit'];
        return (
          <div className="flex flex-wrap gap-2">
            {outcomeOptions.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => !disabled && onChange(field.name, option)}
                disabled={disabled}
                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  value === option
                    ? 'bg-primary border-primary text-white'
                    : 'border-[#E4E8EB] text-text-muted hover:border-primary/50'
                } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
              >
                {option}
              </button>
            ))}
          </div>
        );

      case 'repeatable':
        const items = Array.isArray(value) ? value : [];
        const addItem = () => {
          const newItem = {};
          field.fields?.forEach((f) => (newItem[f.name] = ''));
          onChange(field.name, [...items, newItem]);
        };
        const removeItem = (index) => {
          const newItems = items.filter((_, i) => i !== index);
          onChange(field.name, newItems);
        };
        const updateItem = (index, fieldName, fieldValue) => {
          const newItems = [...items];
          newItems[index] = { ...newItems[index], [fieldName]: fieldValue };
          onChange(field.name, newItems);
        };

        return (
          <div className="space-y-4">
            {items.map((item, index) => (
              <div 
                key={index} 
                className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] space-y-3"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-text-muted">
                    {field.item_label || 'Entry'} {index + 1}
                  </span>
                  {!disabled && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeItem(index)}
                      className="text-error hover:bg-error/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {field.fields?.map((subField) => (
                    <div key={subField.name} className={subField.full_width ? 'sm:col-span-2' : ''}>
                      <Label className="text-xs text-text-muted mb-1">
                        {subField.label}
                        {subField.required && <span className="text-error ml-1">*</span>}
                      </Label>
                      {subField.type === 'textarea' ? (
                        <Textarea
                          value={item[subField.name] || ''}
                          onChange={(e) => updateItem(index, subField.name, e.target.value)}
                          disabled={disabled}
                          className="rounded-xl"
                          rows={2}
                        />
                      ) : (
                        <Input
                          type={subField.type || 'text'}
                          value={item[subField.name] || ''}
                          onChange={(e) => updateItem(index, subField.name, e.target.value)}
                          disabled={disabled}
                          className="rounded-xl"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {!disabled && (
              <Button
                type="button"
                variant="outline"
                onClick={addItem}
                className="rounded-xl w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add {field.item_label || 'Entry'}
              </Button>
            )}
          </div>
        );

      case 'section_header':
        return (
          <div className="border-b border-[#E4E8EB] pb-2">
            <h3 className="font-heading font-semibold text-text-primary text-lg">
              {field.label}
            </h3>
            {field.description && (
              <p className="text-sm text-text-muted mt-1">{field.description}</p>
            )}
          </div>
        );

      case 'info_box':
        return (
          <div className={`p-4 rounded-xl ${
            field.variant === 'warning' ? 'bg-warning/10 border border-warning/20' :
            field.variant === 'error' ? 'bg-error/10 border border-error/20' :
            field.variant === 'success' ? 'bg-success/10 border border-success/20' :
            'bg-info/10 border border-info/20'
          }`}>
            <p className="text-sm">{field.content}</p>
          </div>
        );

      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => onChange(field.name, e.target.value)}
            disabled={disabled}
            className="rounded-xl"
          />
        );
    }
  };

  // Don't render label for checkboxes (they have inline labels) or section headers
  if (field.type === 'checkbox' || field.type === 'section_header' || field.type === 'info_box') {
    return (
      <div className={className}>
        {renderField()}
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <Label htmlFor={field.name}>
        {field.label}
        {field.required && <span className="text-error ml-1">*</span>}
      </Label>
      {field.help_text && (
        <p className="text-xs text-text-muted">{field.help_text}</p>
      )}
      {renderField()}
    </div>
  );
}
