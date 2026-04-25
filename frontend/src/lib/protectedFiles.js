import axios from 'axios';

export async function fetchProtectedFileBlob(url, token) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await axios.get(url, {
    headers,
    responseType: 'blob',
  });

  const contentType = response.headers['content-type'] || response.data?.type || 'application/octet-stream';
  const blob = new Blob([response.data], { type: contentType });
  const blobUrl = URL.createObjectURL(blob);

  return {
    blob,
    blobUrl,
    contentType,
  };
}

export function revokeBlobUrl(blobUrl) {
  if (blobUrl) {
    URL.revokeObjectURL(blobUrl);
  }
}

export function revokeBlobUrlLater(blobUrl, delayMs = 60000) {
  if (!blobUrl) return;
  window.setTimeout(() => revokeBlobUrl(blobUrl), delayMs);
}

export function downloadBlobUrl(blobUrl, filename = 'document') {
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function openBlobUrlInNewTab(blobUrl, fallbackName = 'document') {
  const openedWindow = window.open(blobUrl, '_blank', 'noopener,noreferrer');
  if (!openedWindow) {
    const link = document.createElement('a');
    link.href = blobUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.download = fallbackName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
}