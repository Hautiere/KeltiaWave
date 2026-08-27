import { HttpClient, HttpEventType, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, filter, map } from 'rxjs';

export interface SubtitleSegment { start: number; end: number; text: string; }
export interface SubtitleJobEvent { upload: number; result?: { filename: string; text: string; segments: SubtitleSegment[] }; }

@Injectable({ providedIn: 'root' })
export class SubtitlesApiService {
  private readonly base = location.port === '4600' ? `${location.protocol}//${location.hostname}:8100` : '';
  constructor(private readonly http: HttpClient) {}

  transcribe(file: File, language: 'br'|'cy', engine: 'vosk'|'whisper'): Observable<SubtitleJobEvent> {
    const form = new FormData(); form.append('audio_file', file, file.name);
    const url = `${this.base}/api/subtitles/transcribe?language=${language}&engine=${engine}`;
    return this.http.request<{ filename:string; text:string; segments:SubtitleSegment[] }>(new HttpRequest('POST', url, form, { reportProgress:true })).pipe(
      filter(event => event.type === HttpEventType.UploadProgress || event.type === HttpEventType.Response),
      map(event => event.type === HttpEventType.UploadProgress
        ? { upload: event.total ? Math.round(event.loaded * 100 / event.total) : 0 }
        : { upload:100, result:event.body || undefined }),
    );
  }
}
