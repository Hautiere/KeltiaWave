import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ProfileService } from '../../core/profile.service';
import { TranslatePipe } from '../../core/translate.pipe';

interface QuickDemoProfile {
  label: string;
  name: string;
  email: string;
  password: string;
  avatar: string;
  tone: 'student' | 'teacher' | 'admin';
}

@Component({
  selector: 'app-v2-session-action',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe],
  template: `
    <details *ngIf="!auth.user()" #signinMenu class="session-menu signin-menu">
      <summary class="session-action">
        {{ 'v2.login' | t }}
        <span class="chevron" aria-hidden="true">⌄</span>
      </summary>
      <div class="session-dropdown signin-dropdown">
        <a routerLink="/compte" [queryParams]="{ auth: 'login' }" (click)="closeMenu()">
          <span aria-hidden="true">◉</span>
          Se connecter avec mon compte
        </a>
        <div class="demo-menu-head">
          <strong>Profils de démonstration</strong>
          <span>Connexion immédiate</span>
        </div>
        <button
          *ngFor="let demo of demoProfiles"
          class="demo-login"
          type="button"
          (click)="loginDemo(demo)"
          [disabled]="busyDemoEmail !== null"
        >
          <span class="demo-avatar" [class]="'demo-avatar ' + demo.tone">{{ demo.name.charAt(0) }}</span>
          <span class="demo-label"><strong>{{ demo.label }}</strong><small>{{ demo.name }}</small></span>
          <span aria-hidden="true">›</span>
        </button>
        <p class="signin-error" *ngIf="loginError">{{ loginError }}</p>
      </div>
    </details>
    <details *ngIf="auth.user() as user" #sessionMenu class="session-menu">
      <summary class="session-action">
        <span class="session-avatar" aria-hidden="true">{{ userInitial }}</span>
        <span>{{ user.display_name || user.email }}</span>
        <span class="chevron" aria-hidden="true">⌄</span>
      </summary>
      <div class="session-dropdown">
        <div class="session-identity">
          <strong>{{ user.display_name || user.email }}</strong>
          <span>{{ user.email }}</span>
        </div>
        <a routerLink="/compte" (click)="closeMenu()">
          <span aria-hidden="true">◉</span>
          {{ 'nav.profile' | t }}
        </a>
        <button type="button" (click)="logout()">
          <span aria-hidden="true">↪</span>
          {{ 'account.logout' | t }}
        </button>
      </div>
    </details>
  `,
  styles: [`
    :host {
      display: inline-flex;
      position: relative;
      z-index: 30;
    }

    .session-menu {
      position: relative;
    }

    .session-action {
      min-height: 42px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 18px;
      border: 1px solid #cbd9f2;
      border-radius: 12px;
      background: #fff;
      color: #145be7;
      font: inherit;
      font-size: 12px;
      font-weight: 850;
      text-decoration: none;
      cursor: pointer;
      white-space: nowrap;
    }

    summary.session-action {
      gap: 9px;
      list-style: none;
    }

    summary.session-action::-webkit-details-marker {
      display: none;
    }

    .session-avatar {
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background: #2563eb;
      color: #fff;
      font-size: 13px;
      font-weight: 900;
    }

    .chevron {
      color: #65738c;
      transition: transform .18s ease;
    }

    .session-menu[open] .chevron {
      transform: rotate(180deg);
    }

    .session-action:hover,
    .session-action:focus-visible {
      border-color: #2563eb;
      background: #eef4ff;
      outline: none;
    }

    .session-dropdown {
      position: absolute;
      top: calc(100% + 9px);
      right: 0;
      width: 250px;
      overflow: hidden;
      border: 1px solid #d8e1f1;
      border-radius: 14px;
      background: #fff;
      box-shadow: 0 18px 44px rgba(24, 50, 91, .18);
    }

    .session-identity {
      display: grid;
      gap: 3px;
      padding: 14px 16px;
      border-bottom: 1px solid #e6ecf6;
      color: #102345;
    }

    .session-identity span {
      overflow: hidden;
      color: #65738c;
      font-size: 12px;
      text-overflow: ellipsis;
    }

    .session-dropdown a,
    .session-dropdown button {
      width: 100%;
      min-height: 44px;
      display: flex;
      align-items: center;
      gap: 11px;
      padding: 0 16px;
      border: 0;
      background: #fff;
      color: #102345;
      font: inherit;
      font-size: 13px;
      font-weight: 750;
      text-align: left;
      text-decoration: none;
      cursor: pointer;
    }

    .session-dropdown a:hover,
    .session-dropdown a:focus-visible,
    .session-dropdown button:hover,
    .session-dropdown button:focus-visible {
      background: #eef4ff;
      color: #145be7;
      outline: none;
    }

    .session-dropdown button {
      border-top: 1px solid #e6ecf6;
      color: #b42318;
    }

    .signin-dropdown {
      width: 290px;
    }

    .signin-dropdown .demo-login {
      border-top: 0;
      color: #102345;
    }

    .demo-menu-head {
      display: grid;
      gap: 3px;
      padding: 12px 16px 8px;
      border-top: 1px solid #e6ecf6;
      color: #102345;
    }

    .demo-menu-head strong {
      font-size: 12px;
    }

    .demo-menu-head span,
    .demo-label small {
      color: #65738c;
      font-size: 11px;
    }

    .demo-avatar {
      width: 28px;
      height: 28px;
      flex: 0 0 28px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      color: #15803d;
      background: #dcfce7;
      font-size: 12px;
      font-weight: 900;
    }

    .demo-avatar.teacher { color: #155ee8; background: #eaf1ff; }
    .demo-avatar.admin { color: #7e22ce; background: #f3e8ff; }

    .demo-label {
      flex: 1;
      display: grid;
      gap: 2px;
    }

    .demo-label strong,
    .demo-label small {
      display: block;
    }

    .signin-error {
      margin: 0;
      padding: 10px 16px;
      color: #b42318;
      background: #fff1f2;
      font-size: 11px;
      font-weight: 750;
    }
  `],
})
export class V2SessionActionComponent {
  @ViewChild('sessionMenu') private sessionMenu?: ElementRef<HTMLDetailsElement>;
  @ViewChild('signinMenu') private signinMenu?: ElementRef<HTMLDetailsElement>;

  readonly demoProfiles: QuickDemoProfile[] = [
    { label: 'Élève', name: 'Mael Le Gall', email: 'tiar1@keltia.test', password: 'classe123', avatar: '/assets/profile-avatar-17.png', tone: 'student' },
    { label: 'Professeur', name: 'Nolwenn Morvan', email: 'prof.tiar1@keltia.test', password: 'classe123', avatar: '/assets/profile-avatar-26.png', tone: 'teacher' },
    { label: 'Admin', name: 'Admin Learning', email: 'learning.admin@keltia.test', password: 'classe123', avatar: '/assets/profile-avatar-04.png', tone: 'admin' },
  ];

  busyDemoEmail: string | null = null;
  loginError: string | null = null;

  constructor(
    readonly auth: AuthService,
    private readonly profileService: ProfileService,
    private readonly router: Router,
    private readonly host: ElementRef<HTMLElement>,
  ) {}

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target;
    if (target instanceof Node && !this.host.nativeElement.contains(target)) {
      this.closeMenu();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeMenu();
  }

  get userInitial(): string {
    const user = this.auth.user();
    return (user?.display_name || user?.email || '?').trim().charAt(0).toUpperCase();
  }

  closeMenu(): void {
    if (this.sessionMenu) this.sessionMenu.nativeElement.open = false;
    if (this.signinMenu) this.signinMenu.nativeElement.open = false;
  }

  loginDemo(demo: QuickDemoProfile): void {
    if (this.busyDemoEmail) return;
    this.busyDemoEmail = demo.email;
    this.loginError = null;
    this.auth.login({ email: demo.email, password: demo.password }).subscribe({
      next: () => {
        this.profileService.update({ avatar: demo.avatar });
        this.busyDemoEmail = null;
        this.closeMenu();
        void this.router.navigate([this.landingRoute()]);
      },
      error: (err) => {
        this.loginError = err?.error?.detail === 'Invalid email or password'
          ? 'Compte de démonstration indisponible.'
          : err?.error?.detail || 'Connexion impossible.';
        this.busyDemoEmail = null;
      },
    });
  }

  logout(): void {
    this.auth.logout();
    this.closeMenu();
    void this.router.navigateByUrl('/');
  }

  private landingRoute(): string {
    const role = this.auth.user()?.role;
    if (role === 'teacher') return '/ma-classe';
    if (role === 'admin') return '/admin';
    return '/';
  }
}
