import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { ApiService, type Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { DOMAIN_OPTIONS, domainLabelKey } from '../../core/domains';

@Component({
  selector: 'app-ecrire',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './ecrire.component.html',
  styleUrls: ['./ecrire.component.scss'],
})
export class EcrireComponent implements OnInit {
  texte = '';
  selectedDomains: string[] = [];
  selectedSource = '';
  submitting = false;
  loading = false;
  statusMessage: string | null = null;
  statusKind: 'success' | 'error' | null = null;
  recentPhrases: Phrase[] = [];
  readonly domains = DOMAIN_OPTIONS.filter((domain) => !!domain.value);
  readonly maxDomains = 3;
  readonly sources = [
    { value: 'livre', labelKey: 'write.source.book' },
    { value: 'dictionnaire', labelKey: 'write.source.dictionary' },
    { value: 'lecon', labelKey: 'write.source.lesson' },
    { value: 'journal', labelKey: 'write.source.newspaper' },
    { value: 'archive-dastum', labelKey: 'write.source.dastum' },
  ];

  constructor(
    private readonly api: ApiService,
    readonly auth: AuthService,
    private readonly i18n: I18nService,
  ) {}

  ngOnInit(): void {
    void this.loadRecent();
  }

  get remaining(): number {
    return Math.max(0, 180 - this.texte.trim().length);
  }

  get canSubmit(): boolean {
    const text = this.texte.trim();
    return text.length >= 6 && text.length <= 180 && !this.submitting;
  }

  sourceLabel(value?: string | null): string {
    return value ? this.i18n.translate(this.sourceLabelKey(value)) : this.i18n.translate('write.noSource');
  }

  isSourceSelected(value: string): boolean {
    return this.selectedSource === value;
  }

  toggleSource(value: string): void {
    if (this.submitting) return;
    this.selectedSource = this.selectedSource === value ? '' : value;
  }

  domainLabel(value?: string | null): string {
    const values = this.parseDomains(value);
    if (!values.length) return this.i18n.translate('write.noTheme');
    return values.map((item) => this.i18n.translate(domainLabelKey(item))).join(', ');
  }

  isDomainSelected(value: string): boolean {
    return this.selectedDomains.includes(value);
  }

  toggleDomain(value: string): void {
    if (this.submitting) return;
    if (this.isDomainSelected(value)) {
      this.selectedDomains = this.selectedDomains.filter((item) => item !== value);
      return;
    }
    if (this.selectedDomains.length >= this.maxDomains) return;
    this.selectedDomains = [...this.selectedDomains, value];
  }

  async submit(): Promise<void> {
    if (!this.canSubmit) {
      this.showStatus('error', this.i18n.translate('write.invalid'));
      return;
    }

    this.submitting = true;
    this.statusMessage = null;
    this.statusKind = null;

    try {
      const created = await firstValueFrom(this.api.createPhrase({
        texte: this.texte.trim(),
        theme: this.selectedDomains.length ? this.selectedDomains.join(',') : null,
        niveau: null,
        source: this.selectedSource || null,
        langue: 'br',
        auteur: this.auth.user()?.display_name || 'contributor',
      }));

      this.recentPhrases = [created, ...this.recentPhrases].slice(0, 5);
      this.texte = '';
      this.selectedDomains = [];
      this.selectedSource = '';
      this.showStatus('success', this.i18n.translate('write.success'));
    } catch {
      this.showStatus('error', this.i18n.translate('write.error'));
    } finally {
      this.submitting = false;
    }
  }

  private async loadRecent(): Promise<void> {
    this.loading = true;
    try {
      const phrases = await firstValueFrom(this.api.getPhrases());
      this.recentPhrases = phrases.slice(0, 3);
    } catch {
      this.showStatus('error', this.i18n.translate('write.loadError'));
    } finally {
      this.loading = false;
    }
  }

  private showStatus(kind: 'success' | 'error', message: string): void {
    this.statusKind = kind;
    this.statusMessage = message;
  }

  private parseDomains(value?: string | null): string[] {
    return (value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  private sourceLabelKey(value: string): string {
    return this.sources.find((item) => item.value === value)?.labelKey || 'write.noSource';
  }
}
