const RAW_API_BASE =
  process.env.REACT_APP_API_URL ||
  process.env.REACT_APP_API ||
  "https://api.osabeacares.co.uk/api";

const API_BASE = (() => {
  const normalized = String(RAW_API_BASE || "").trim().replace(/\/+$/, "");
  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
})();

export default API_BASE;
