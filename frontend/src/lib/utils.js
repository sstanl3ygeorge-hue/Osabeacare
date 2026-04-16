import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Safely extract a human-readable error message from an Axios error.
 * Handles string, array (422 validation), and object (409 blockers) detail formats.
 */
export function extractErrorMessage(error, fallback = 'An error occurred') {
  const detail = error?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join('; ');
  }
  if (typeof detail === 'object') return detail.message || detail.msg || JSON.stringify(detail);
  return String(detail);
}
