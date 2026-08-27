// corpus-collaboratif/frontend/src/app/app.ts
import { Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs/operators';
import { I18nService, type AppLanguage } from './core/i18n.service';
import { TranslatePipe } from './core/translate.pipe';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, TranslatePipe], // <-- ajout ici
})
export class AppComponent {
  @ViewChild('moreMenu') private moreMenu?: ElementRef<HTMLDetailsElement>;
  @ViewChild('adminMenu') private adminMenu?: ElementRef<HTMLDetailsElement>;
  @ViewChild('sessionMenu') private sessionMenu?: ElementRef<HTMLDetailsElement>;
  isV2Route = false;

  constructor(
    readonly i18n: I18nService,
    readonly auth: AuthService,
    private readonly router: Router,
  ) {
    this.isV2Route = !this.router.url.startsWith('/legacy');
    this.router.events.pipe(filter((event) => event instanceof NavigationEnd)).subscribe((event) => {
      this.isV2Route = !(event as NavigationEnd).urlAfterRedirects.startsWith('/legacy');
      this.closeMoreMenu();
    });
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
    }
  }

  closeMoreMenu(): void {
    if (this.moreMenu) this.moreMenu.nativeElement.open = false;
    if (this.adminMenu) this.adminMenu.nativeElement.open = false;
    if (this.sessionMenu) this.sessionMenu.nativeElement.open = false;
  }

  logout(): void {
    this.auth.logout();
    this.closeMoreMenu();
    void this.router.navigate(['/']);
  }
}
