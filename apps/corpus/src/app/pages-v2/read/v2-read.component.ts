import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

@Component({
  selector: 'app-v2-read',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-read.component.html',
  styleUrls: ['./v2-read.component.scss'],
})
export class V2ReadComponent implements OnInit {
  phrases: Phrase[] = [];
  currentIndex = 0;
  loading = true;
  error: string | null = null;

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
  ) {}

  ngOnInit(): void {
    this.loadPhrases();
  }

  get currentPhrase(): Phrase | null {
    return this.phrases[this.currentIndex] ?? null;
  }

  get phrasePosition(): string {
    if (!this.phrases.length) return `${this.i18n.translate('home.phrase')} 0 / 0`;
    return `${this.i18n.translate('home.phrase')} ${this.currentIndex + 1} / ${this.phrases.length}`;
  }

  get progressPercent(): number {
    if (!this.phrases.length) return 0;
    return Math.round(((this.currentIndex + 1) / this.phrases.length) * 100);
  }

  get classLabel(): string {
    const user = this.auth.user();
    if (!user) return this.i18n.translate('v2.classNotConnected');
    const organization = (user.school || user.organization)?.trim();
    if (!organization) return this.i18n.translate('v2.classNotMember');
    return organization;
  }

  get hasClassContext(): boolean {
    const user = this.auth.user();
    return !!user?.organization?.trim() || !!user?.school?.trim();
  }

  get classHelp(): string {
    const user = this.auth.user();
    if (!user) return this.i18n.translate('v2.classLoginHelp');
    const organization = (user.school || user.organization)?.trim();
    if (!organization) return this.i18n.translate('v2.classMemberHelp');
    return this.i18n.translate('v2.classOpenHelp');
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.loadPhrases();
    }
  }

  previous(): void {
    if (!this.phrases.length) return;
    this.currentIndex = Math.max(0, this.currentIndex - 1);
  }

  next(): void {
    if (!this.phrases.length) return;
    this.currentIndex = (this.currentIndex + 1) % this.phrases.length;
  }

  private loadPhrases(): void {
    this.loading = true;
    this.error = null;
    // Le sélecteur change la langue de l'interface, pas celle du corpus lu.
    this.api.getPhrases('br').subscribe({
      next: (phrases) => {
        this.phrases = phrases;
        this.currentIndex = 0;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Chargement des phrases impossible.';
        this.loading = false;
      },
    });
  }
}
