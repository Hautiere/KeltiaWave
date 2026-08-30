import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { LEVEL_OPTIONS, ProfileService, SessionProfile } from '../../core/profile.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

interface LibraryStat {
  icon: string;
  label: string;
  value: string;
  tone?: 'green' | 'yellow';
}

@Component({
  selector: 'app-v2-account',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-account.component.html',
  styleUrls: ['./v2-account.component.scss'],
})
export class V2AccountComponent implements OnInit {
  readonly levels = LEVEL_OPTIONS;
  readonly avatarChoices = Array.from(
    { length: 32 },
    (_, index) => `/assets/profile-avatar-${String(index + 1).padStart(2, '0')}.png`,
  );
  readonly maxCustomAvatarBytes = 1_500_000;
  mode: 'login' | 'register' = 'login';
  email = '';
  password = '';
  busy = false;
  profileSaving = false;
  showAuthForm = false;
  error: string | null = null;
  success: string | null = null;
  profileDraft: Partial<SessionProfile> = {};
  avatarPickerOpen = false;
  phrases: Phrase[] = [];
  pendingAudios: AudioRead[] = [];
  approvedAudios: AudioRead[] = [];
  rejectedAudios: AudioRead[] = [];
  metricsLoading = true;

  constructor(
    readonly auth: AuthService,
    readonly profileService: ProfileService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
    private readonly router: Router,
    private readonly route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.resetProfileDraft();
    this.loadMetrics();
    if (this.route.snapshot.queryParamMap.get('auth') === 'login' && !this.auth.user()) {
      if (this.route.snapshot.queryParamMap.get('account') === 'admin') {
        this.email = 'contact@keltiawave.com';
      }
      this.showLogin();
    }
  }

  get profile(): SessionProfile {
    return this.profileService.profile();
  }

  get displayEmail(): string {
    return this.email || this.profile.email;
  }

  get draftAvatar(): string {
    return this.profileDraft.avatar || this.profile.avatar || this.avatarChoices[0];
  }

  get selectedAvatarIndex(): number {
    return this.avatarChoices.indexOf(this.draftAvatar);
  }

  get avatarPickerLabel(): string {
    const index = this.selectedAvatarIndex;
    return index >= 0 ? `Avatar ${index + 1} / ${this.avatarChoices.length}` : 'Image personnelle';
  }

  get profileDirty(): boolean {
    const profile = this.profile;
    return (
      (this.profileDraft.displayName ?? '') !== (profile.displayName ?? '') ||
      (this.profileDraft.bretonLevel ?? 'undefined') !== (profile.bretonLevel ?? 'undefined') ||
      (this.profileDraft.organization ?? '') !== (profile.organization ?? '') ||
      (this.profileDraft.comments ?? '') !== (profile.comments ?? '') ||
      (this.profileDraft.avatar ?? this.avatarChoices[0]) !== (profile.avatar ?? this.avatarChoices[0])
    );
  }

  get progressStats() {
    return [
      { label: this.i18n.translate('v2.readPhrases'), value: 14 },
      { label: this.i18n.translate('adminData.recordings'), value: 10 },
      { label: this.i18n.translate('adminData.approved'), value: 7 },
    ];
  }

  get libraryStats(): LibraryStat[] {
    const allAudios = [...this.pendingAudios, ...this.approvedAudios, ...this.rejectedAudios];
    const teacherCount = this.countTeachers(allAudios);
    const schoolCount = this.uniqueCount(allAudios.map((audio) => audio.contributor_school));
    const speakerCount = this.uniqueCount(allAudios.map((audio) => audio.contributor_email || audio.contributor_name));
    const collectionCount = this.uniqueCount([
      ...this.phrases.map((phrase) => phrase.source),
      ...allAudios.map((audio) => audio.phrase_source),
    ]);
    return [
      { icon: '▥', label: 'audios', value: this.metricValue(allAudios.length) },
      { icon: '▤', label: 'textes', value: this.metricValue(this.phrases.length) },
      { icon: '♙', label: 'enseignants', value: this.metricValue(teacherCount) },
      { icon: '⌂', label: 'ecoles', value: this.metricValue(schoolCount) },
      { icon: '◉', label: 'locuteurs', value: this.metricValue(speakerCount) },
      { icon: '✓', label: 'valides', value: this.metricValue(this.approvedAudios.length), tone: 'green' },
      { icon: '▣', label: 'collections', value: this.metricValue(collectionCount), tone: 'yellow' },
    ];
  }

  showLogin(): void {
    this.mode = 'login';
    this.showAuthForm = true;
  }

  showRegister(): void {
    this.mode = 'register';
    this.showAuthForm = true;
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.loadMetrics();
    }
  }

  update(key: keyof SessionProfile, value: string): void {
    if (key === 'email') this.email = value;
    this.profileService.update({ [key]: value } as Partial<SessionProfile>);
    this.error = null;
    this.success = null;
  }

  updateProfileDraft(key: keyof SessionProfile, value: string): void {
    this.profileDraft = { ...this.profileDraft, [key]: value };
    this.error = null;
    this.success = null;
  }

  selectAvatar(avatar: string): void {
    this.profileDraft = { ...this.profileDraft, avatar };
    this.error = null;
    this.success = null;
  }

  cycleAvatar(direction: number): void {
    const currentIndex = this.selectedAvatarIndex >= 0 ? this.selectedAvatarIndex : direction > 0 ? -1 : 0;
    const nextIndex = (currentIndex + direction + this.avatarChoices.length) % this.avatarChoices.length;
    this.selectAvatar(this.avatarChoices[nextIndex]);
  }

  onAvatarFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      this.error = 'Choisissez un fichier image.';
      if (input) input.value = '';
      return;
    }

    if (file.size > this.maxCustomAvatarBytes) {
      this.error = 'Image trop lourde. Choisissez une image de moins de 1,5 Mo.';
      if (input) input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        this.selectAvatar(reader.result);
      }
    };
    reader.onerror = () => {
      this.error = "Lecture de l'image impossible.";
    };
    reader.readAsDataURL(file);
    if (input) input.value = '';
  }

  saveProfile(): void {
    if (this.profileSaving || !this.profileDirty) return;
    this.profileSaving = true;
    this.error = null;
    this.success = null;

    const draftLevel = this.profileDraft.bretonLevel;
    const patch: Partial<SessionProfile> = {
      displayName: this.profileDraft.displayName ?? '',
      bretonLevel: draftLevel === 'undefined' || draftLevel === 'A1' || draftLevel === 'A2' || draftLevel === 'B1' || draftLevel === 'B2' || draftLevel === 'C1' || draftLevel === 'C2' || draftLevel === 'native'
        ? draftLevel
        : 'undefined',
      organization: this.profileDraft.organization ?? '',
      comments: this.profileDraft.comments ?? '',
      avatar: this.profileDraft.avatar || this.avatarChoices[0],
    };

    if (!this.auth.user()) {
      this.profileService.update(patch);
      this.resetProfileDraft();
      this.success = 'Profil enregistre localement.';
      this.profileSaving = false;
      return;
    }

    this.auth.updateMe({
      display_name: patch.displayName,
      breton_level: patch.bretonLevel,
      organization: patch.organization,
      comments: patch.comments,
    }).subscribe({
      next: () => {
        this.profileService.update(patch);
        this.resetProfileDraft();
        this.success = 'Profil enregistre.';
        this.profileSaving = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Enregistrement du profil impossible.';
        this.profileSaving = false;
      },
    });
  }

  resetProfileDraft(): void {
    const profile = this.profileService.profile();
    this.profileDraft = {
      displayName: profile.displayName,
      bretonLevel: profile.bretonLevel,
      organization: profile.organization ?? '',
      comments: profile.comments ?? '',
      avatar: profile.avatar || this.avatarChoices[0],
    };
  }

  submit(event?: Event): void {
    if (this.busy) return;
    this.error = null;
    this.success = null;
    this.readFormValues(event);

    const email = this.displayEmail.trim();
    const password = this.password;

    if (!email || !password) {
      this.error = 'Email et mot de passe sont requis.';
      return;
    }

    if (this.mode === 'register' && this.password.length < 8) {
      this.error = 'Le mot de passe doit contenir au moins 8 caracteres.';
      return;
    }

    if (this.mode === 'login') {
      this.loginWithCredentials(email, password);
      return;
    }

    this.busy = true;
    this.auth.register({
          email,
          password,
          display_name: this.profileDraft.displayName || email,
          breton_level: this.profileDraft.bretonLevel === 'undefined' || this.profileDraft.bretonLevel === 'A1' || this.profileDraft.bretonLevel === 'A2' || this.profileDraft.bretonLevel === 'B1' || this.profileDraft.bretonLevel === 'B2' || this.profileDraft.bretonLevel === 'C1' || this.profileDraft.bretonLevel === 'C2' || this.profileDraft.bretonLevel === 'native'
            ? this.profileDraft.bretonLevel
            : 'undefined',
          organization: this.profileDraft.organization,
          comments: this.profileDraft.comments,
        }).subscribe({
      next: () => {
        this.profileService.update({
          displayName: this.profileDraft.displayName || email,
          bretonLevel: this.profileDraft.bretonLevel === 'undefined' || this.profileDraft.bretonLevel === 'A1' || this.profileDraft.bretonLevel === 'A2' || this.profileDraft.bretonLevel === 'B1' || this.profileDraft.bretonLevel === 'B2' || this.profileDraft.bretonLevel === 'C1' || this.profileDraft.bretonLevel === 'C2' || this.profileDraft.bretonLevel === 'native'
            ? this.profileDraft.bretonLevel
            : 'undefined',
          organization: this.profileDraft.organization,
          comments: this.profileDraft.comments,
          avatar: this.profileDraft.avatar || this.avatarChoices[0],
        });
        this.resetProfileDraft();
        this.password = '';
        this.busy = false;
        this.success = 'Compte cree.';
        void this.router.navigate(['/']);
      },
      error: (err) => {
        const detail = err?.error?.detail;
        if (detail === 'Email already registered') {
          this.error = 'Cet email existe deja. Essayez de vous connecter.';
          this.mode = 'login';
        } else {
          this.error = detail || err?.message || 'Creation impossible.';
        }
        this.busy = false;
      },
    });
  }

  continueAsVisitor(): void {
    this.auth.logout();
    this.success = 'Mode visiteur active.';
    this.error = null;
    void this.router.navigateByUrl('/');
  }

  logout(): void {
    this.auth.logout();
    this.email = '';
    this.password = '';
    this.error = null;
    this.success = null;
    this.showAuthForm = false;
    void this.router.navigateByUrl('/');
  }

  private loadMetrics(): void {
    this.metricsLoading = true;
    forkJoin({
      phrases: this.api.getPhrases(this.i18n.contentLanguage()),
      pending: this.api.listAudios('pending'),
      approved: this.api.listAudios('approved'),
      rejected: this.api.listAudios('rejected'),
    }).subscribe({
      next: ({ phrases, pending, approved, rejected }) => {
        this.phrases = phrases;
        this.pendingAudios = pending;
        this.approvedAudios = approved;
        this.rejectedAudios = rejected;
        this.metricsLoading = false;
      },
      error: () => {
        this.metricsLoading = false;
      },
    });
  }

  private metricValue(value: number): string {
    if (this.metricsLoading) return '...';
    return new Intl.NumberFormat('fr-FR').format(value);
  }

  private uniqueCount(values: Array<string | null | undefined>): number {
    return new Set(
      values
        .map((value) => this.normalizeMetricKey(value))
        .filter(Boolean),
    ).size;
  }

  private countTeachers(audios: AudioRead[]): number {
    const teachers = new Set<string>();
    for (const audio of audios) {
      const roles = [
        audio.validator_role,
        ...(audio.validations ?? []).map((validation) => validation.validator_role),
      ];
      const hasTeacherRole = roles.some((role) => {
        const normalized = this.normalizeMetricKey(role);
        return normalized === 'teacher' || normalized === 'professeur';
      });
      if (hasTeacherRole) {
        teachers.add(this.normalizeMetricKey(audio.validated_by) || String(audio.id));
      }
    }
    return teachers.size;
  }

  private normalizeMetricKey(value?: string | null): string {
    return (value ?? '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  private readFormValues(event?: Event): void {
    const form = event?.target instanceof HTMLFormElement ? event.target : null;
    if (!form) return;
    const formData = new FormData(form);
    const email = String(formData.get('email') || '').trim();
    const password = String(formData.get('password') || '');
    if (email) {
      this.email = email;
      this.profileService.update({ email });
    }
    if (password) this.password = password;
  }

  private loginWithCredentials(email: string, password: string, returnHome = true): void {
    this.busy = true;
    this.error = null;
    this.success = 'Connexion en cours...';
    this.auth.login({ email, password }).subscribe({
      next: () => {
        this.password = '';
        this.busy = false;
        this.success = 'Connexion reussie.';
        if (returnHome) void this.router.navigate([this.landingRoute()]);
      },
      error: (err) => {
        const detail = err?.error?.detail;
        if (detail === 'Invalid email or password') {
          this.error = 'Email ou mot de passe incorrect.';
        } else if (err?.status === 0) {
          this.error = 'Backend indisponible. Verifiez que ./start_backend.sh est lance.';
        } else {
          this.error = detail || err?.message || 'Connexion impossible.';
        }
        this.success = null;
        this.busy = false;
      },
    });
  }

  private landingRoute(): string {
    const role = this.auth.user()?.role;
    if (role === 'teacher') return '/ma-classe';
    if (role === 'admin') return '/admin';
    return '/';
  }
}
