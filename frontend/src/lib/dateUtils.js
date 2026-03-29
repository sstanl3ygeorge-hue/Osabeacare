/**
 * Date Utilities - SINGLE SOURCE OF TRUTH for date parsing and formatting
 * 
 * CANONICAL STORAGE RULES:
 * - expiry_date: YYYY-MM-DD string (date-only, no timezone)
 * - completion_date: YYYY-MM-DD string (date-only, no timezone)
 * - created_at, updated_at, verified_at: Full ISO with timezone
 * 
 * PARSING RULES:
 * - Date-only strings (YYYY-MM-DD) are treated as calendar dates, NOT local time
 * - Full ISO strings preserve their timezone
 * - Display uses consistent formatting across all pages
 */

/**
 * Parse a backend date value safely
 * Handles both YYYY-MM-DD and full ISO formats
 * 
 * @param {string|null} value - Date string from backend
 * @returns {Date|null} - Parsed Date object or null
 */
export function parseBackendDate(value) {
  if (!value) return null;
  
  try {
    // Handle date-only format: YYYY-MM-DD
    // CRITICAL: Parse as UTC to avoid timezone drift
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      // Split and create UTC date to avoid browser timezone interpretation
      const [year, month, day] = value.split('-').map(Number);
      return new Date(Date.UTC(year, month - 1, day));
    }
    
    // Handle full ISO format: 2026-03-28T02:07:30.467419+00:00
    if (typeof value === 'string' && value.includes('T')) {
      return new Date(value);
    }
    
    // Fallback: try native parsing
    const parsed = new Date(value);
    return isNaN(parsed.getTime()) ? null : parsed;
  } catch (e) {
    console.error('Date parsing error:', e, 'value:', value);
    return null;
  }
}

/**
 * Format a backend date for display
 * Uses consistent formatting across all pages
 * 
 * @param {string|null} value - Date string from backend
 * @param {object} options - Formatting options
 * @param {string} options.format - 'short' | 'medium' | 'long' | 'iso'
 * @param {string} options.fallback - Text to show if date is null
 * @returns {string} - Formatted date string
 */
export function formatBackendDate(value, options = {}) {
  const { format = 'medium', fallback = '-' } = options;
  
  if (!value) return fallback;
  
  const date = parseBackendDate(value);
  if (!date) return fallback;
  
  try {
    // For date-only values (YYYY-MM-DD), use UTC methods to avoid timezone shift
    const isDateOnly = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
    
    if (format === 'iso') {
      return isDateOnly ? value : date.toISOString().split('T')[0];
    }
    
    if (format === 'short') {
      // DD/MM/YY
      if (isDateOnly) {
        const day = String(date.getUTCDate()).padStart(2, '0');
        const month = String(date.getUTCMonth() + 1).padStart(2, '0');
        const year = String(date.getUTCFullYear()).slice(-2);
        return `${day}/${month}/${year}`;
      }
      return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: '2-digit' });
    }
    
    if (format === 'medium') {
      // DD MMM YYYY (e.g., 28 Mar 2026)
      if (isDateOnly) {
        const day = date.getUTCDate();
        const month = date.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' });
        const year = date.getUTCFullYear();
        return `${day} ${month} ${year}`;
      }
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }
    
    if (format === 'long') {
      // DD MMMM YYYY (e.g., 28 March 2026)
      if (isDateOnly) {
        const day = date.getUTCDate();
        const month = date.toLocaleString('en-GB', { month: 'long', timeZone: 'UTC' });
        const year = date.getUTCFullYear();
        return `${day} ${month} ${year}`;
      }
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    
    // Default: use browser locale
    if (isDateOnly) {
      // Use UTC values for date-only to prevent drift
      const day = date.getUTCDate();
      const month = date.getUTCMonth() + 1;
      const year = date.getUTCFullYear();
      return `${day}/${month}/${year}`;
    }
    return date.toLocaleDateString();
  } catch (e) {
    console.error('Date formatting error:', e, 'value:', value);
    return fallback;
  }
}

/**
 * Format a datetime value for display (includes time)
 * 
 * @param {string|null} value - ISO datetime string from backend
 * @param {object} options - Formatting options
 * @returns {string} - Formatted datetime string
 */
export function formatBackendDateTime(value, options = {}) {
  const { fallback = '-', includeTime = true } = options;
  
  if (!value) return fallback;
  
  const date = parseBackendDate(value);
  if (!date) return fallback;
  
  try {
    if (includeTime) {
      return date.toLocaleString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
    return formatBackendDate(value, { format: 'medium' });
  } catch (e) {
    console.error('DateTime formatting error:', e, 'value:', value);
    return fallback;
  }
}

/**
 * Check if a date-only string is in the past (expired)
 * NOTE: For status calculations, ALWAYS use backend-computed values
 * This is only for edge case display logic
 * 
 * @param {string} dateStr - YYYY-MM-DD date string
 * @returns {boolean}
 */
export function isDateInPast(dateStr) {
  if (!dateStr) return false;
  
  const date = parseBackendDate(dateStr);
  if (!date) return false;
  
  // Compare date-only (ignore time) using UTC
  const now = new Date();
  const todayUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const dateUTC = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  
  return dateUTC < todayUTC;
}

/**
 * Convert a date to YYYY-MM-DD format for backend storage
 * 
 * @param {Date|string} value - Date to convert
 * @returns {string|null} - YYYY-MM-DD string
 */
export function toBackendDateOnly(value) {
  if (!value) return null;
  
  try {
    let date;
    if (typeof value === 'string') {
      // If already in correct format, return as-is
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        return value;
      }
      date = new Date(value);
    } else {
      date = value;
    }
    
    if (isNaN(date.getTime())) return null;
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch (e) {
    console.error('Date conversion error:', e, 'value:', value);
    return null;
  }
}

export default {
  parseBackendDate,
  formatBackendDate,
  formatBackendDateTime,
  isDateInPast,
  toBackendDateOnly
};
