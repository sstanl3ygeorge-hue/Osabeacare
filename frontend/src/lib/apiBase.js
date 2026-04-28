const DEFAULT_API_ROOT = 'https://api.osabeacares.co.uk';

const normalizeRoot = (value) => {
  const raw = String(value || '').trim();
  const candidate = raw || DEFAULT_API_ROOT;
  let normalized = candidate.replace(/\/+$/, '');
  normalized = normalized.replace('://app.osabeacares.co.uk', '://api.osabeacares.co.uk');
  normalized = normalized.replace('://www.app.osabeacares.co.uk', '://api.osabeacares.co.uk');
  return normalized;
};

export const API_ROOT_URL = normalizeRoot(process.env.REACT_APP_BACKEND_URL);
export const API_BASE_URL = `${API_ROOT_URL}/api`;

export const toApiUrl = (path = '') => {
  if (!path) return API_BASE_URL;
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith('/api/')) return `${API_ROOT_URL}${path}`;
  if (path.startsWith('/')) return `${API_BASE_URL}${path}`;
  return `${API_BASE_URL}/${path}`;
};
