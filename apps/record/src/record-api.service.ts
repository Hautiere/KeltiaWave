import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom, timeout } from 'rxjs';

export type RecordLanguage = 'br' | 'cy';
export interface RecordResult { filename: string; language: RecordLanguage; engine: 'whisper'; draft_text: string; text: string; whisper_text: string; draft_prefix_preserved: boolean; removed_trailing_phrases: string[]; metrics: Record<string, unknown>; }

@Injectable({ providedIn: 'root' })
export class RecordApiService {
  readonly httpBase = this.localDevelopment ? `${location.protocol}//${location.hostname}:8100` : '';
  readonly wsBase = this.localDevelopment
    ? `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.hostname}:8100`
    : `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`;
  constructor(private readonly http: HttpClient) {}

  private get localDevelopment(): boolean { return location.port === '4400'; }

  transcribe(file: File, language: RecordLanguage): Promise<RecordResult> {
    return this.post('/api/record/transcribe', file, language, '');
  }

  improve(file: File, language: RecordLanguage, draft: string): Promise<RecordResult> {
    return this.post('/api/record/improve', file, language, draft);
  }

  formatError(error: unknown): string {
    const http = error as HttpErrorResponse;
    return String(http?.error?.detail || http?.message || 'Le service Record est indisponible.');
  }

  private post(path: string, file: File, language: RecordLanguage, draft: string): Promise<RecordResult> {
    const form = new FormData();
    form.append('audio_file', file, file.name);
    form.append('language', language);
    if (draft) form.append('draft_text', draft);
    return firstValueFrom(this.http.post<RecordResult>(`${this.httpBase}${path}`, form).pipe(timeout({ first: 15 * 60 * 1000 })));
  }
}
