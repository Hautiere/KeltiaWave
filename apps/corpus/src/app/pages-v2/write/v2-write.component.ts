import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ApiService, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

@Component({
  selector: 'app-v2-write',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-write.component.html',
  styleUrls: ['./v2-write.component.scss'],
})
export class V2WriteComponent implements OnInit {
  texte = '';
  traductionFr = '';
  selectedDomains: string[] = [];
  selectedSource = '';
  customSource = '';
  sourceUrl = '';
  selectedLevel = '';
  recentPhrases: Phrase[] = [];
  loading = true;
  submitting = false;
  error: string | null = null;
  success: string | null = null;

  readonly maxDomains = 1;
  readonly levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
  readonly domains = [
    { value: 'vie-quotidienne', label: '☕ Vie quotidienne' },
    { value: 'education', label: '🎓 Éducation' },
    { value: 'famille', label: '👨‍👩‍👧 Famille' },
    { value: 'travail', label: '💼 Travail' },
    { value: 'nature', label: '🌿 Nature' },
    { value: 'transports', label: '🚗 Transports' },
    { value: 'sante', label: '🩺 Santé' },
    { value: 'culture-patrimoine', label: '🏰 Culture & patrimoine' },
    { value: 'histoire', label: '📜 Histoire' },
    { value: 'traditions-fetes', label: '🎉 Traditions & fêtes' },
    { value: 'cuisine', label: '🍽 Cuisine' },
    { value: 'sports-loisirs', label: '⚽ Sports & loisirs' },
    { value: 'technologies', label: '💻 Technologies' },
    { value: 'administration', label: '🏛 Administration' },
    { value: 'non-classe', label: '📦 Non classé' },
  ];
  readonly sources = [
    { value: 'livre', label: '📚 Livre' },
    { value: 'manuel-scolaire', label: '📖 Manuel scolaire' },
    { value: 'cours-breton', label: '🎓 Cours de breton' },
    { value: 'presse-article', label: '📰 Presse / Article' },
    { value: 'internet', label: '🌐 Internet' },
    { value: 'conversation', label: '🎤 Conversation' },
    { value: 'locuteur-natif', label: '👵 Locuteur natif' },
    { value: 'enregistrement-personnel', label: '🎙 Enregistrement personnel' },
    { value: 'archive', label: '🏛 Archive' },
    { value: 'creation-originale', label: '📄 Création originale' },
    { value: 'autre', label: '➕ Autre' },
  ];

  constructor(
    private readonly api: ApiService,
    readonly auth: AuthService,
    readonly i18n: I18nService,
  ) {}

  ngOnInit(): void {
    void this.loadRecent();
  }

  get remaining(): number {
    return Math.max(0, 180 - this.texte.trim().length);
  }

  get canSubmit(): boolean {
    const text = this.texte.trim();
    const hasRequiredSourceUrl = this.selectedSource !== 'internet' || /^https?:\/\//i.test(this.sourceUrl.trim());
    return this.canWriteRole && text.length >= 6 && text.length <= 180 && this.selectedDomains.length === 1 && !!this.selectedLevel && hasRequiredSourceUrl && !this.submitting;
  }

  get canWriteRole(): boolean {
    const role = this.auth.user()?.role;
    return role === 'teacher' || role === 'admin';
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      void this.loadRecent();
    }
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

  isSourceSelected(value: string): boolean {
    return this.selectedSource === value;
  }

  toggleSource(value: string): void {
    if (this.submitting) return;
    this.selectedSource = this.selectedSource === value ? '' : value;
    if (this.selectedSource !== 'autre') this.customSource = '';
  }

  onSourceChange(value: string): void {
    if (value !== 'autre') this.customSource = '';
    if (value !== 'internet') this.sourceUrl = '';
  }

  domainLabel(value?: string | null): string {
    const values = this.parseDomains(value);
    if (!values.length) return 'Sans theme';
    return values.map((item) => this.domains.find((domain) => domain.value === item)?.label || item).join(', ');
  }

  sourceLabel(value?: string | null): string {
    return this.sources.find((source) => source.value === value)?.label || value || '';
  }

  async submit(): Promise<void> {
    if (!this.canWriteRole) {
      this.error = 'Seuls les professeurs et administrateurs peuvent ajouter une phrase.';
      return;
    }
    if (this.selectedDomains.length !== 1 || !this.selectedLevel) {
      this.error = 'Le thème et le niveau sont obligatoires.';
      this.success = null;
      return;
    }
    if (!this.canSubmit) {
      this.error = 'La phrase doit contenir entre 6 et 180 caracteres.';
      this.success = null;
      return;
    }
    this.submitting = true;
    this.error = null;
    this.success = null;
    try {
      const created = await firstValueFrom(this.api.createPhrase({
        texte: this.texte.trim(),
        traduction_fr: this.traductionFr.trim() || null,
        theme: this.selectedDomains.length ? this.selectedDomains.join(',') : null,
        niveau: this.selectedLevel,
        source: this.selectedSource === 'autre' ? this.customSource.trim() || null : this.selectedSource || null,
        source_url: this.selectedSource === 'internet' ? this.sourceUrl.trim() : null,
        langue: 'br',
        auteur: this.auth.user()?.display_name || 'contributor',
      }));
      this.recentPhrases = [created, ...this.recentPhrases].slice(0, 5);
      this.texte = '';
      this.traductionFr = '';
      this.selectedDomains = [];
      this.selectedLevel = '';
      this.selectedSource = '';
      this.customSource = '';
      this.sourceUrl = '';
      this.success = this.i18n.translate('write.success');
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Ajout de phrase impossible.';
    } finally {
      this.submitting = false;
    }
  }

  private async loadRecent(): Promise<void> {
    this.loading = true;
    this.error = null;
    try {
      const phrases = await firstValueFrom(this.api.getPhrases(this.i18n.contentLanguage()));
      this.recentPhrases = phrases.slice(0, 3);
    } catch (err: any) {
      this.error = err?.error?.detail || err?.message || 'Chargement des phrases recentes impossible.';
    } finally {
      this.loading = false;
    }
  }

  private parseDomains(value?: string | null): string[] {
    return (value ?? '').split(',').map((item) => item.trim()).filter(Boolean);
  }
}
