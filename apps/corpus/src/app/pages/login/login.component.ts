import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { AuthService } from '../../core/auth.service';
import {
  LEVEL_OPTIONS,
  ProfileService,
  ROLE_OPTIONS,
  SessionProfile,
} from '../../core/profile.service';

interface DemoProfile {
  group: string;
  name: string;
  detail: string;
  email: string;
  password: string;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  readonly roles = ROLE_OPTIONS;
  readonly levels = LEVEL_OPTIONS;
  readonly demoProfiles: DemoProfile[] = [
    {
      group: 'Ti ar Vretonned',
      name: 'Mael Le Gall',
      detail: 'Eleve niveau 1',
      email: 'tiar1@keltia.test',
      password: 'classe123',
    },
    {
      group: 'Professeur',
      name: 'Nolwenn Morvan',
      detail: 'Ti ar Vretonned',
      email: 'prof.tiar1@keltia.test',
      password: 'classe123',
    },
  ];
  successKey: string | null = null;
  mode: 'login' | 'register' = 'login';
  password = '';
  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  error: string | null = null;
  passwordError: string | null = null;
  busy = false;
  changingPassword = false;
  savingProfile = false;

  constructor(
    readonly profileService: ProfileService,
    readonly auth: AuthService,
    private readonly i18n: I18nService,
  ) {}

  get profile(): SessionProfile {
    return this.profileService.profile();
  }

  get weight(): number {
    return this.profileService.validationWeight();
  }

  get accountStateKey(): string {
    if (this.auth.user()) return 'account.state.identified';
    return 'account.state.visitor';
  }

  get accountHelpKey(): string {
    if (this.auth.user()) return 'account.help.identified';
    return 'account.help.visitor';
  }

  update(key: keyof SessionProfile, value: string): void {
    this.profileService.update({ [key]: value } as Partial<SessionProfile>);
    this.successKey = null;
  }

  save(): void {
    if (this.busy) return;
    this.error = null;
    this.successKey = null;
    if (this.mode === 'register' && this.password.length < 8) {
      this.error = this.i18n.translate('account.passwordTooShort');
      return;
    }
    this.busy = true;

    const request = this.mode === 'login'
      ? this.auth.login({ email: this.profile.email, password: this.password })
      : this.auth.register({
          email: this.profile.email,
          password: this.password,
          display_name: this.profile.displayName || this.profile.email,
          breton_level: this.profile.bretonLevel,
          organization: this.profile.organization,
          comments: this.profile.comments,
        });

    request.subscribe({
      next: () => {
        this.password = '';
        this.successKey = this.mode === 'login' ? 'account.loggedIn' : 'account.created';
        this.busy = false;
      },
      error: (err) => {
        const detail = err?.error?.detail;
        if (detail === 'Email already registered') {
          this.error = this.i18n.translate('account.emailExists');
          this.mode = 'login';
        } else if (detail === 'Invalid email or password') {
          this.error = this.i18n.translate('account.badCredentials');
        } else {
          this.error = this.errorDetail(detail, err?.message || 'Authentication failed');
        }
        this.busy = false;
      },
    });
  }

  loginDemo(profile: DemoProfile): void {
    if (this.busy) return;
    this.mode = 'login';
    this.password = profile.password;
    this.profileService.update({
      email: profile.email,
      displayName: profile.name,
    });
    this.save();
  }

  changePassword(): void {
    if (this.changingPassword) return;
    this.passwordError = null;
    this.successKey = null;

    if (this.newPassword !== this.confirmPassword) {
      this.passwordError = this.i18n.translate('account.passwordMismatch');
      return;
    }
    if (this.newPassword.length < 8) {
      this.passwordError = this.i18n.translate('account.passwordTooShort');
      return;
    }

    this.changingPassword = true;
    this.auth.changePassword({
      current_password: this.currentPassword,
      new_password: this.newPassword,
    }).subscribe({
      next: () => {
        this.currentPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
        this.successKey = 'account.passwordChanged';
        this.changingPassword = false;
      },
      error: (err) => {
        const detail = err?.error?.detail;
        this.passwordError = detail === 'Invalid current password'
          ? this.i18n.translate('account.badCurrentPassword')
          : detail || err?.message || 'Password change failed';
        this.changingPassword = false;
      },
    });
  }

  saveProfile(): void {
    if (this.savingProfile || !this.auth.user()) return;
    this.error = null;
    this.successKey = null;
    this.savingProfile = true;

    this.auth.updateMe({
      display_name: this.profile.displayName,
      breton_level: this.profile.bretonLevel,
      organization: this.profile.organization || null,
      comments: this.profile.comments || null,
    }).subscribe({
      next: () => {
        this.successKey = 'account.profileSaved';
        this.savingProfile = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Profile update failed';
        this.savingProfile = false;
      },
    });
  }

  useAsVisitor(): void {
    this.auth.logout();
    this.successKey = 'account.visitorMode';
  }

  logout(): void {
    this.auth.logout();
    this.password = '';
    this.currentPassword = '';
    this.newPassword = '';
    this.confirmPassword = '';
    this.successKey = null;
    this.passwordError = null;
  }

  roleLabelFor(role: string): string {
    return this.i18n.translate(`profile.role.${role}`);
  }

  private errorDetail(detail: unknown, fallback: string): string {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item?.msg || JSON.stringify(item)).join(' ');
    }
    return fallback;
  }

}
