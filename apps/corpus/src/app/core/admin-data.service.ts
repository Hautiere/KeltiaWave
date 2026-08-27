import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { AuthService } from './auth.service';
import { API_BASE } from './constants';

export type SegmentStatus = 'pending' | 'approved' | 'rejected';

export interface AdminDataOverview {
  datasets: number;
  phrases: number;
  audios: number;
  approved: number;
  pending: number;
  rejected: number;
  phrases_without_audio: number;
  audios_without_text: number;
}

export interface AdminStorageInfo {
  backend: 's3' | 'local';
  bucket?: string | null;
  endpoint?: string | null;
  local_directory?: string | null;
}

export interface AdminDataset {
  name: string;
  phrases: number;
  audios: number;
  dataset_audios: number;
  user_audios: number;
  approved: number;
  pending: number;
  rejected: number;
  created_at: string;
}

export interface AdminSegment {
  id: number;
  phrase_id: number;
  texte: string;
  traduction_fr?: string | null;
  dataset: string;
  source?: string | null;
  domain?: string | null;
  status: SegmentStatus;
  origin: 'dataset' | 'user' | string;
  filename: string;
  audio_url: string;
  created_at: string;
  validated_at?: string | null;
  validated_by?: string | null;
  contributor_name?: string | null;
}

export interface DatasetCleanResult {
  dataset: string;
  dry_run: boolean;
  phrase_ids_without_audio: number[];
  missing_storage_audio_ids: number[];
  deleted_phrases: number;
  deleted_audios: number;
}

export interface DatasetClearResult {
  dataset: string;
  dry_run: boolean;
  audio_ids_to_delete: number[];
  protected_user_audio_ids: number[];
  phrase_ids_to_delete: number[];
  deleted_audios: number;
  deleted_phrases: number;
}

export interface DatasetImportResult {
  dataset: string;
  stats: Record<string, number>;
}

export interface AdminQualityReport {
  generated_at: string;
  phrases_without_audio: Array<{ id: number; texte: string; source?: string | null }>;
  empty_text_phrase_ids: number[];
  audios_without_text: Array<{ id: number; phrase_id: number; filename: string }>;
  duplicate_texts: string[];
  missing_storage_audio_ids: number[];
  storage_checked: boolean;
}

@Injectable({ providedIn: 'root' })
export class AdminDataService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly baseUrl = `${API_BASE}/admin-data`;

  overview() {
    return this.http.get<AdminDataOverview>(`${this.baseUrl}/overview`, { headers: this.auth.authHeaders });
  }

  storage() {
    return this.http.get<AdminStorageInfo>(`${this.baseUrl}/storage`, { headers: this.auth.authHeaders });
  }

  datasets() {
    return this.http.get<AdminDataset[]>(`${this.baseUrl}/datasets`, { headers: this.auth.authHeaders });
  }

  segments(params: { query?: string; dataset?: string; status?: string } = {}) {
    let httpParams = new HttpParams();
    if (params.query) httpParams = httpParams.set('query', params.query);
    if (params.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params.status) httpParams = httpParams.set('status', params.status);
    return this.http.get<AdminSegment[]>(`${this.baseUrl}/segments`, {
      headers: this.auth.authHeaders,
      params: httpParams,
    });
  }

  updateSegment(id: number, payload: Pick<AdminSegment, 'texte' | 'traduction_fr' | 'source' | 'domain' | 'status'>) {
    return this.http.patch<AdminSegment>(`${this.baseUrl}/segments/${id}`, payload, { headers: this.auth.authHeaders });
  }

  deleteSegmentAudio(id: number) {
    return this.http.delete<void>(`${this.baseUrl}/segments/${id}/audio`, { headers: this.auth.authHeaders });
  }

  exportDataset(name: string, params: { format?: 'csv' | 'json'; status?: SegmentStatus; includeUserData?: boolean } = {}) {
    let httpParams = new HttpParams();
    if (params.format) httpParams = httpParams.set('export_format', params.format);
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.includeUserData !== undefined) httpParams = httpParams.set('include_user_data', String(params.includeUserData));
    return this.http.get(`${this.baseUrl}/datasets/${encodeURIComponent(name)}/export`, {
      headers: this.auth.authHeaders,
      params: httpParams,
      responseType: 'blob',
    });
  }

  importDataset(payload: {
    metadata: File;
    audioArchive?: File | null;
    name: string;
    audioRoot?: string;
    langue?: string;
    author?: string;
    source?: string;
    initialStatus?: SegmentStatus;
  }) {
    const form = new FormData();
    form.append('metadata', payload.metadata);
    if (payload.audioArchive) form.append('audio_archive', payload.audioArchive);
    form.append('name', payload.name);
    form.append('audio_root', payload.audioRoot || 'audios');
    form.append('langue', payload.langue || 'br');
    form.append('author', payload.author || 'import-corpus');
    form.append('source', payload.source || payload.name);
    form.append('initial_status', payload.initialStatus || 'pending');
    return this.http.post<DatasetImportResult>(`${this.baseUrl}/datasets/import`, form, { headers: this.auth.authHeaders });
  }

  cleanDataset(name: string, payload: {
    dry_run?: boolean;
    remove_phrases_without_audio?: boolean;
    remove_missing_storage_audios?: boolean;
    include_legacy_imports?: boolean;
  } = {}) {
    return this.http.post<DatasetCleanResult>(`${this.baseUrl}/datasets/${encodeURIComponent(name)}/clean`, payload, { headers: this.auth.authHeaders });
  }

  clearDataset(name: string, payload: {
    dry_run?: boolean;
    delete_phrases_without_audio?: boolean;
    include_user_data?: boolean;
    include_legacy_imports?: boolean;
  } = {}) {
    return this.http.post<DatasetClearResult>(`${this.baseUrl}/datasets/${encodeURIComponent(name)}/clear`, payload, { headers: this.auth.authHeaders });
  }

  quality(checkStorage = false) {
    return this.http.get<AdminQualityReport>(`${this.baseUrl}/quality`, {
      headers: this.auth.authHeaders,
      params: { check_storage: String(checkStorage) },
    });
  }
}
