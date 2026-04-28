const DEFAULT_API_ROOT = 'https://api.osabeacares.co.uk';

const normalizeRoot = (value) => {
  const raw = String(value || '').trim();
  const candidate = raw || DEFAULT_API_ROOT;
  let normalized = candidate.replace(/\/+$/, '');
  normalized = normalized.replace('://app.osabeacares.co.uk', '://api.osabeacares.co.uk');
  normalized = normalized.replace('://www.app.osabeacares.co.uk', '://api.osabeacares.co.uk');
  return normalized;
};

import API_BASE from '../utils/apiBase';
export default API_BASE;
