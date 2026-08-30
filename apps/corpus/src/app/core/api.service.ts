// corpus/corpus-collaboratif/frontend/src/app/core/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface Phrase {
  id: number;
  texte: string;
  traduction_fr?: string | null;
  theme: string | null;
  niveau: string | null;
  source: string | null;
  source_url?: string | null;
  langue: string | null;
  auteur: string | null;
  url_audio?: string | null;
  created_at: string;
}

export interface AudioRead {
  id: number;
  phrase_id: number;
  filename: string;
  status: 'pending' | 'approved' | 'rejected';
  phrase_source?: string | null;
  domain?: string | null;
  speaker_region?: string | null;
  speaker_city?: string | null;
  speaker_accent?: string | null;
  speaker_level?: string | null;
  created_at: string;
  validated_at?: string | null;
  validated_by?: string | null;
  validator_role?: string | null;
  validation_weight?: string | null;
  validation_comment?: string | null;
  contributor_name?: string | null;
  contributor_email?: string | null;
  contributor_school?: string | null;
  contributor_school_level?: string | null;
  validations?: Array<{
    id: number;
    audio_id: number;
    decision: string;
    validator?: string | null;
    validator_role?: string | null;
    validation_weight?: string | null;
    pronunciation_level?: string | null;
    pronunciation_region?: string | null;
    comment?: string | null;
    created_at: string;
  }>;
}

export interface AudioUploadMetadata {
  phraseSource?: 'suggested' | 'custom';
  domain?: string;
  speakerRegion?: string;
  speakerCity?: string;
  speakerAccent?: string;
  speakerLevel?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = '/api'; // via proxy Angular

  constructor(
    private http: HttpClient,
    private auth: AuthService,
  ) {}

  // ---- PHRASES ----
  getPhrases(langue?: string): Observable<Phrase[]> {
    const options = langue ? { params: { langue } as any } : {};
    return this.http.get<Phrase[]>(`${this.baseUrl}/phrases/`, options);
  }

  getPhrase(id: number): Observable<Phrase> {
    return this.http.get<Phrase>(`${this.baseUrl}/phrases/${id}`);
  }

  createPhrase(p: Partial<Phrase>): Observable<Phrase> {
    return this.http.post<Phrase>(`${this.baseUrl}/phrases/`, p, { headers: this.auth.authHeaders });
  }

  updatePhrase(id: number, p: Partial<Phrase>): Observable<Phrase> {
    return this.http.patch<Phrase>(`${this.baseUrl}/phrases/${id}`, p, { headers: this.auth.authHeaders });
  }

  deletePhrase(id: number) {
    return this.http.delete(`${this.baseUrl}/phrases/${id}`, { headers: this.auth.authHeaders });
  }

  // ---- AUDIOS ----

  /**
   * Upload d'un enregistrement.
   * Accepte un File OU un Blob (ex: issu de MediaRecorder).
   * Si c'est un Blob, on le convertit en File avec un nom/extension cohérents.
   */
  uploadAudio(
    phraseId: number,
    fileOrBlob: File | Blob,
    filenameHint?: string,
    metadata: AudioUploadMetadata = {},
  ) {
    const file = this.ensureFile(fileOrBlob, filenameHint);
    const form = new FormData();
    form.append('phrase_id', String(phraseId));
    if (metadata.phraseSource) form.append('phrase_source', metadata.phraseSource);
    if (metadata.domain) form.append('domain', metadata.domain);
    if (metadata.speakerRegion) form.append('speaker_region', metadata.speakerRegion);
    if (metadata.speakerCity) form.append('speaker_city', metadata.speakerCity);
    if (metadata.speakerAccent) form.append('speaker_accent', metadata.speakerAccent);
    if (metadata.speakerLevel) form.append('speaker_level', metadata.speakerLevel);
    form.append('file', file, file.name);
    return this.http.post<AudioRead>(`${this.baseUrl}/audios/`, form, {
      headers: this.auth.authHeaders,
    });
  }

  listAudios(status: 'pending' | 'approved' | 'rejected') {
    return this.http.get<AudioRead[]>(`${this.baseUrl}/audios/`, { params: { status } as any });
  }

  validateAudio(id: number, approved: boolean) {
    const body = new URLSearchParams();
    body.set('approved', String(approved));
    return this.http.post<AudioRead>(`${this.baseUrl}/audios/${id}/validate`, body.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  }

  // --- helpers ---

  /** Convertit un Blob en File si nécessaire, en devinant un nom/extension à partir du MIME */
  private ensureFile(fileOrBlob: File | Blob, filenameHint?: string): File {
    if (fileOrBlob instanceof File) return fileOrBlob;

    const mime = fileOrBlob.type || 'application/octet-stream';
    const ext = this.extFromMime(mime);
    const name = (filenameHint && this.normalizeNameWithExt(filenameHint, ext))
              || `clip${ext}`;
    return new File([fileOrBlob], name, { type: mime });
  }

  private extFromMime(mime: string): string {
    const m = mime.toLowerCase();
    if (m.includes('webm')) return '.webm';
    if (m.includes('mpeg') || m === 'audio/mp3') return '.mp3';
    if (m.includes('ogg'))  return '.ogg';
    if (m.includes('wav'))  return '.wav';
    if (m.includes('mp4'))  return '.m4a'; // Safari enregistre souvent audio/mp4
    return '.webm';
  }

  private normalizeNameWithExt(name: string, ext: string): string {
    const lower = name.toLowerCase();
    if (lower.endsWith('.webm') || lower.endsWith('.mp3') || lower.endsWith('.ogg') ||
        lower.endsWith('.wav')  || lower.endsWith('.m4a') || lower.endsWith('.mp4')) {
      return name; // déjà une extension
    }
    return name + ext;
  }
}
