import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { tap } from 'rxjs';
import { API_BASE } from './constants';
import { BretonLevel, ProfileService, UserProfile } from './profile.service';

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  role: UserProfile['role'];
  breton_level: BretonLevel;
  organization?: string | null;
  school?: string | null;
  school_level?: string | null;
  comments?: string | null;
  must_change_password: boolean;
  active: boolean;
  created_at?: string;
  validation_weight: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  user: AuthUser;
}

export interface AdminUserUpdate {
  display_name?: string;
  role?: UserProfile['role'];
  breton_level?: BretonLevel;
  organization?: string | null;
  school?: string | null;
  school_level?: string | null;
  comments?: string | null;
  must_change_password?: boolean;
  active?: boolean;
}

export interface UserProfileUpdate {
  display_name?: string;
  breton_level?: BretonLevel;
  organization?: string | null;
  comments?: string | null;
}

const TOKEN_KEY = 'keltiaVoice.authToken';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly profileService = inject(ProfileService);
  readonly token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  readonly user = signal<AuthUser | null>(null);

  constructor() {
    if (this.token()) {
      this.me().subscribe({ error: () => this.logout() });
    }
  }

  get authHeaders(): HttpHeaders | undefined {
    const token = this.token();
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
  }

  register(payload: { email: string; password: string; display_name: string; breton_level: BretonLevel; organization?: string; comments?: string }) {
    return this.http.post<AuthResponse>(`${API_BASE}/auth/register`, payload).pipe(
      tap((response) => this.applyAuth(response)),
    );
  }

  login(payload: { email: string; password: string }) {
    return this.http.post<AuthResponse>(`${API_BASE}/auth/login`, payload).pipe(
      tap((response) => this.applyAuth(response)),
    );
  }

  me() {
    return this.http.get<AuthUser>(`${API_BASE}/auth/me`, { headers: this.authHeaders }).pipe(
      tap((user) => this.applyUser(user)),
    );
  }

  changePassword(payload: { current_password: string; new_password: string }) {
    return this.http.post<AuthUser>(`${API_BASE}/auth/change-password`, payload, { headers: this.authHeaders }).pipe(
      tap((user) => this.applyUser(user)),
    );
  }

  updateMe(payload: UserProfileUpdate) {
    return this.http.patch<AuthUser>(`${API_BASE}/auth/me`, payload, { headers: this.authHeaders }).pipe(
      tap((user) => this.applyUser(user)),
    );
  }

  listUsers() {
    return this.http.get<AuthUser[]>(`${API_BASE}/auth/users`, { headers: this.authHeaders });
  }

  updateUser(id: number, payload: AdminUserUpdate) {
    return this.http.patch<AuthUser>(`${API_BASE}/auth/users/${id}`, payload, { headers: this.authHeaders }).pipe(
      tap((user) => {
        if (this.user()?.id === user.id) this.applyUser(user);
      }),
    );
  }

  deleteUser(id: number) {
    return this.http.delete<void>(`${API_BASE}/auth/users/${id}`, { headers: this.authHeaders });
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.token.set(null);
    this.user.set(null);
  }

  private applyAuth(response: AuthResponse): void {
    localStorage.setItem(TOKEN_KEY, response.access_token);
    this.token.set(response.access_token);
    this.applyUser(response.user);
  }

  private applyUser(user: AuthUser): void {
    this.user.set(user);
    this.profileService.update({
      displayName: user.display_name,
      email: user.email,
      role: user.role,
      bretonLevel: user.breton_level,
      organization: user.organization ?? '',
      comments: user.comments ?? '',
    });
  }
}
