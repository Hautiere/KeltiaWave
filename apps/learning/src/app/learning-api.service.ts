import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { tap } from 'rxjs';


const API_BASE = '/api';
const TOKEN_KEY = 'keltiaVoice.authToken';

export interface LearningUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
}

interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  user: LearningUser;
}

export interface LearningBlankPayload {
  id?: number;
  position: number;
  answer: string;
  accepted_variants: string[];
  accept_mutations: boolean;
}

export interface LearningSegmentPayload {
  id?: number;
  position: number;
  start_ms: number | null;
  end_ms: number | null;
  text: string;
  translation: string;
  blanks: LearningBlankPayload[];
}

export interface LearningVocabularyPayload {
  id?: number;
  position: number;
  term: string;
  translation: string;
  note: string;
}

export interface LearningGrammarPayload {
  id?: number;
  position: number;
  title: string;
  explanation: string;
  example: string;
  translation: string;
}

export interface LearningVideoDto {
  id: number;
  lesson_id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  duration_seconds: number | null;
  source_url: string | null;
  source_link_label: string | null;
  position: number;
}

export interface LearningLessonDto {
  id: number;
  title: string;
  level: string;
  domain: string;
  description: string;
  status: 'draft' | 'published' | 'archived';
  created_by_id: number;
  published_at: string | null;
  thumbnail_url: string | null;
  videos: LearningVideoDto[];
  segments: LearningSegmentPayload[];
  vocabulary: LearningVocabularyPayload[];
  grammar: LearningGrammarPayload[];
}

export interface LearningLessonWrite {
  title: string;
  level: string;
  domain: string;
  description: string;
  segments: LearningSegmentPayload[];
  vocabulary: LearningVocabularyPayload[];
  grammar: LearningGrammarPayload[];
}

export interface LearningProgressDto {
  id: number;
  lesson_id: number;
  status: 'started' | 'completed';
  best_score: number;
  total_questions: number;
  attempts: number;
  started_at: string;
  completed_at: string | null;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class LearningApiService {
  private readonly http = inject(HttpClient);
  readonly token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  readonly user = signal<LearningUser | null>(null);

  get headers(): HttpHeaders | undefined {
    const token = this.token();
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
  }

  login(email: string, password: string) {
    return this.http.post<AuthResponse>(`${API_BASE}/auth/login`, { email, password }).pipe(
      tap((response) => {
        localStorage.setItem(TOKEN_KEY, response.access_token);
        this.token.set(response.access_token);
        this.user.set(response.user);
      }),
    );
  }

  me() {
    return this.http.get<LearningUser>(`${API_BASE}/auth/me`, { headers: this.headers }).pipe(
      tap((user) => this.user.set(user)),
    );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.token.set(null);
    this.user.set(null);
  }

  listPublishedLessons() {
    return this.http.get<LearningLessonDto[]>(`${API_BASE}/learning/lessons`);
  }

  listAdminLessons() {
    return this.http.get<LearningLessonDto[]>(`${API_BASE}/learning/lessons?include_unpublished=true`, { headers: this.headers });
  }

  createLesson(payload: LearningLessonWrite) {
    return this.http.post<LearningLessonDto>(`${API_BASE}/learning/lessons`, payload, { headers: this.headers });
  }

  updateLesson(id: number, payload: LearningLessonWrite) {
    return this.http.put<LearningLessonDto>(`${API_BASE}/learning/lessons/${id}`, payload, { headers: this.headers });
  }

  uploadVideo(lessonId: number, file: File, durationSeconds: number | null) {
    const form = new FormData();
    form.append('file', file);
    form.append('position', '0');
    form.append('replace_existing', 'true');
    if (durationSeconds !== null) form.append('duration_seconds', String(durationSeconds));
    return this.http.post<LearningVideoDto>(`${API_BASE}/learning/lessons/${lessonId}/videos`, form, { headers: this.headers });
  }

  updateVideo(videoId: number, durationSeconds: number | null, sourceUrl: string | null, sourceLinkLabel: string | null) {
    return this.http.patch<LearningVideoDto>(`${API_BASE}/learning/videos/${videoId}`, {
      duration_seconds: durationSeconds,
      source_url: sourceUrl,
      source_link_label: sourceLinkLabel,
    }, { headers: this.headers });
  }

  uploadThumbnail(lessonId: number, file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<LearningLessonDto>(`${API_BASE}/learning/lessons/${lessonId}/thumbnail`, form, { headers: this.headers });
  }

  loadThumbnail(lessonId: number) {
    return this.http.get(`${API_BASE}/learning/lessons/${lessonId}/thumbnail`, { headers: this.headers, responseType: 'blob' });
  }

  listProgress() {
    return this.http.get<LearningProgressDto[]>(`${API_BASE}/learning/progress`, { headers: this.headers });
  }

  saveProgress(lessonId: number, status: 'started' | 'completed', score = 0, totalQuestions = 0) {
    return this.http.put<LearningProgressDto>(`${API_BASE}/learning/lessons/${lessonId}/progress`, {
      status, score, total_questions: totalQuestions,
    }, { headers: this.headers });
  }

  publishLesson(id: number) {
    return this.http.post<LearningLessonDto>(`${API_BASE}/learning/lessons/${id}/publish`, {}, { headers: this.headers });
  }

  mediaUrl(videoId: number): string {
    return `${API_BASE}/learning/videos/${videoId}/file`;
  }

  loadVideo(videoId: number) {
    return this.http.get(this.mediaUrl(videoId), { headers: this.headers, responseType: 'blob' });
  }
}
