// frontend/src/app/core/validations.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AUDIOS_ENDPOINT } from './constants';
import { AudioRead } from './models';
import { AuthService } from './auth.service';

export interface AudioMetadataUpdate {
  phrase_source?: string;
  domain?: string;
  speaker_region?: string;
  speaker_city?: string;
  speaker_accent?: string;
  speaker_level?: string;
}

export interface ValidationDecisionProfile {
  validator?: string;
  validator_role?: string;
  validation_weight?: number;
  comment?: string;
  pronunciation_level?: string;
  pronunciation_region?: string;
}

function withSlash(url: string) {
  return url.endsWith('/') ? url : url + '/';
}

@Injectable({ providedIn: 'root' })
export class ValidationsService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly base = withSlash(AUDIOS_ENDPOINT); // garantit le slash final

  listByStatus(status: 'pending' | 'approved' | 'rejected') {
    const params = new HttpParams().set('status', status);
    return this.http.get<AudioRead[]>(this.base, { params });
  }

  listPending(): Observable<AudioRead[]> {
    return this.listByStatus('pending');
  }

  updateMetadata(id: number, metadata: AudioMetadataUpdate) {
    const body = new URLSearchParams();
    body.set('phrase_source', metadata.phrase_source ?? '');
    body.set('domain', metadata.domain ?? '');
    body.set('speaker_region', metadata.speaker_region ?? '');
    body.set('speaker_city', metadata.speaker_city ?? '');
    body.set('speaker_accent', metadata.speaker_accent ?? '');
    body.set('speaker_level', metadata.speaker_level ?? '');
    return this.http.patch<AudioRead>(`${this.base}${id}`, body.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  }

  approve(id: number, profile?: ValidationDecisionProfile) {
    const url = `${this.base}${id}/validate`;
    const body = this.validationBody(true, profile);
    console.debug('[ValidationsService] POST', url, body);
    return this.http.post<AudioRead>(url, body, {
      headers: this.headers()
    });
  }

  reject(id: number, profile?: ValidationDecisionProfile) {
    const url = `${this.base}${id}/validate`;
    const body = this.validationBody(false, profile);
    console.debug('[ValidationsService] POST', url, body);
    return this.http.post<AudioRead>(url, body, {
      headers: this.headers()
    });
  }

  comment(id: number, comment: string) {
    const body = new URLSearchParams({ comment });
    return this.http.post<AudioRead>(`${this.base}${id}/comment`, body.toString(), {
      headers: this.headers()
    });
  }

  private validationBody(approved: boolean, profile?: ValidationDecisionProfile): string {
    const body = new URLSearchParams({ approved: String(approved) });
    if (profile?.validator) body.set('validator', profile.validator);
    if (profile?.validator_role) body.set('validator_role', profile.validator_role);
    if (profile?.validation_weight != null) body.set('validation_weight', String(profile.validation_weight));
    if (profile?.comment) body.set('comment', profile.comment);
    if (profile?.pronunciation_level) body.set('pronunciation_level', profile.pronunciation_level);
    if (profile?.pronunciation_region) body.set('pronunciation_region', profile.pronunciation_region);
    return body.toString();
  }

  private headers() {
    const headers: Record<string, string> = { 'Content-Type': 'application/x-www-form-urlencoded' };
    const token = this.auth.token();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
  }
}
