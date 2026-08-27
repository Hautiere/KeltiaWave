import { Injectable, signal } from '@angular/core';

export type UserRole = 'admin' | 'teacher' | 'contributor' | 'learner';
export type BretonLevel = 'undefined' | 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | 'native';

export interface UserProfile {
  displayName: string;
  email: string;
  role: UserRole;
  bretonLevel: BretonLevel;
  organization?: string;
  comments?: string;
  avatar?: string;
}

export type SessionProfile = UserProfile;

export interface RoleOption {
  value: UserRole;
  label: string;
  description: string;
  baseWeight: number;
}

const STORAGE_KEY = 'keltiaVoice.profile';

export const ROLE_OPTIONS: RoleOption[] = [
  { value: 'learner', label: 'Apprenant', description: 'Contribue au corpus avec un profil apprenant.', baseWeight: 0.25 },
  { value: 'contributor', label: 'Contributeur', description: 'Contribue au corpus et effectue une relecture indicative.', baseWeight: 0.25 },
  { value: 'teacher', label: 'Professeur', description: 'Enseignant ou formateur reconnu.', baseWeight: 1.5 },
  { value: 'admin', label: 'Administrateur', description: 'Gere les comptes et la configuration.', baseWeight: 2.5 },
];

export const LEVEL_OPTIONS = [
  { value: 'undefined' as BretonLevel, labelKey: 'level.undefined', factor: 0.8 },
  { value: 'A1' as BretonLevel, labelKey: 'level.A1', factor: 0.5 },
  { value: 'A2' as BretonLevel, labelKey: 'level.A2', factor: 0.6 },
  { value: 'B1' as BretonLevel, labelKey: 'level.B1', factor: 0.8 },
  { value: 'B2' as BretonLevel, labelKey: 'level.B2', factor: 1 },
  { value: 'C1' as BretonLevel, labelKey: 'level.C1', factor: 1.15 },
  { value: 'C2' as BretonLevel, labelKey: 'level.C2', factor: 1.25 },
  { value: 'native' as BretonLevel, labelKey: 'level.nativeHeritage', factor: 1.35 },
];

// Historical audio metadata still uses the former school fields.
export const SCHOOL_OPTIONS = [
  { value: '', labelKey: 'school.none' },
  { value: 'ti-ar-vretonned', labelKey: 'school.tiArVretonned' },
  { value: 'skol-an-emsav', labelKey: 'school.skolAnEmsav' },
];

export const SCHOOL_LEVEL_OPTIONS = [
  { value: '', labelKey: 'schoolLevel.none' },
  { value: 'niveau-1', labelKey: 'schoolLevel.1' },
  { value: 'niveau-2', labelKey: 'schoolLevel.2' },
  { value: 'niveau-3', labelKey: 'schoolLevel.3' },
  { value: 'niveau-4', labelKey: 'schoolLevel.4' },
];

const DEFAULT_PROFILE: SessionProfile = {
  displayName: '',
  email: '',
  role: 'contributor',
  bretonLevel: 'undefined',
  organization: '',
  comments: '',
  avatar: '/assets/profile-avatar-01.png',
};

@Injectable({ providedIn: 'root' })
export class ProfileService {
  readonly profile = signal<SessionProfile>(this.load());

  update(patch: Partial<SessionProfile>): void {
    const next = { ...this.profile(), ...patch };
    this.profile.set(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  reset(): void {
    this.profile.set(DEFAULT_PROFILE);
    localStorage.removeItem(STORAGE_KEY);
  }

  roleOption(role = this.profile().role): RoleOption {
    return ROLE_OPTIONS.find((option) => option.value === role) ?? ROLE_OPTIONS[0];
  }

  validationWeight(profile = this.profile()): number {
    const roleWeight = this.roleOption(profile.role).baseWeight;
    const levelFactor = LEVEL_OPTIONS.find((level) => level.value === profile.bretonLevel)?.factor ?? 0.8;
    return Math.round(roleWeight * levelFactor * 100) / 100;
  }

  canValidate(profile = this.profile()): boolean {
    return this.validationWeight(profile) >= 0.5;
  }

  private load(): SessionProfile {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return DEFAULT_PROFILE;
      const stored = JSON.parse(raw);
      return {
        ...DEFAULT_PROFILE,
        ...stored,
        bretonLevel: this.normalizeLevel(stored.bretonLevel ?? stored.languageLevel),
        organization: stored.organization ?? stored.affiliation ?? stored.school ?? '',
        comments: stored.comments ?? stored.notes ?? '',
        avatar: stored.avatar || DEFAULT_PROFILE.avatar,
      };
    } catch {
      return DEFAULT_PROFILE;
    }
  }

  private normalizeLevel(value: string | undefined): BretonLevel {
    if (!value) return 'undefined';
    if (value === 'native-heritage') return 'native';
    const normalized = value.toUpperCase();
    return LEVEL_OPTIONS.some((level) => level.value === normalized) ? normalized as BretonLevel : 'undefined';
  }
}
