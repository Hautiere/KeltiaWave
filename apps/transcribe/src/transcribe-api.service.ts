import { HttpClient, HttpErrorResponse, HttpEvent, HttpEventType, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, filter, map } from 'rxjs';

export type TranscribeLanguage = 'br' | 'cy';
export type TranscribeMode = 'fast' | 'quality';
export interface TranscribeResult {
  filename: string;
  text: string;
  segments?: Array<{ id: number; start: number; end: number; text: string }>;
  metrics?: Record<string, unknown>;
}
export interface TranscribeProgress { progress: number; result?: TranscribeResult; }
export interface TranscriptionEstimate {
  estimated_seconds: number;
  real_time_factor: number;
  sample_count: number;
  source: 'server-calibration' | 'server-default';
}

@Injectable({ providedIn: 'root' })
export class TranscribeApiService {
  private readonly base = '';
  constructor(private readonly http: HttpClient) {}

  estimate(language: TranscribeLanguage, mode: TranscribeMode, durationSeconds: number): Observable<TranscriptionEstimate> {
    const params = new URLSearchParams({
      lang: language,
      mode,
      duration_seconds: String(durationSeconds),
    });
    return this.http.get<TranscriptionEstimate>(`${this.base}/api/transcribe/estimate?${params}`);
  }

  transcribe(file: File, language: TranscribeLanguage, mode: TranscribeMode): Observable<TranscribeProgress> {
    const endpoint = language === 'cy'
      ? mode === 'fast' ? '/api/transcribe/transcribe_w2v_wel_metrics' : '/api/transcribe/transcribe_whisper_wel_metrics'
      : mode === 'quality'
        ? '/api/transcribe/transcribe_whisper_bre_metrics'
        : '/api/transcribe/transcribe_vosk_bre_metrics_v2?clean=false&include_words=false';
    const form = new FormData();
    form.append('audio_file', file, file.name);
    const request = new HttpRequest('POST', `${this.base}${endpoint}`, form, { reportProgress: true });
    return this.http.request<TranscribeResult>(request).pipe(
      filter((event: HttpEvent<TranscribeResult>) => event.type === HttpEventType.UploadProgress || event.type === HttpEventType.Response),
      map(event => event.type === HttpEventType.UploadProgress
        ? { progress: event.total ? Math.round(event.loaded * 100 / event.total) : 0 }
        : { progress: 100, result: event.body || undefined }),
    );
  }

  formatError(error: unknown): string {
    const http = error as HttpErrorResponse;
    return String(http?.error?.detail || http?.message || 'Le service Transcribe est indisponible.');
  }
}
