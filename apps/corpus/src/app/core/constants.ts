//frontend/src/app/core/constants.ts
export const API_BASE_URL = '/api';
export const API_BASE = '/api';
export const AUDIOS_ENDPOINT = `${API_BASE}/audios/`;    // ← slash final requis
export const STATIC_AUDIOS = '/static/audios/';

export function audioFileUrl(id: number): string {
  return `${API_BASE}/audios/${id}/file`;
}

// Legacy helper for old local records.
export function toAudioUrl(filename: string): string {
  if (filename.startsWith('s3://')) return '';
  const base = filename.startsWith('data/audios/')
    ? filename.replace('data/audios/', '')
    : filename;
  return `${STATIC_AUDIOS}${base}`;
}
