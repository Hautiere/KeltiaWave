import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { audioFileUrl } from '../../core/constants';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

interface StatCard {
  label: string;
  value: number;
  trend: string;
  tone: 'blue' | 'green' | 'purple' | 'orange';
  icon: string;
}

@Component({
  selector: 'app-v2-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-dashboard.component.html',
  styleUrls: ['./v2-dashboard.component.scss'],
})
export class V2DashboardComponent implements OnInit {
  phrases: Phrase[] = [];
  pendingAudios: AudioRead[] = [];
  approvedAudios: AudioRead[] = [];
  rejectedAudios: AudioRead[] = [];
  loading = true;
  error: string | null = null;
  phraseById = new Map<number, Phrase>();

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  get stats(): StatCard[] {
    const totalAudios = this.pendingAudios.length + this.approvedAudios.length + this.rejectedAudios.length;
    return [
      { label: this.i18n.translate('home.pending'), value: totalAudios, trend: `${this.phrases.length} ${this.i18n.translate('corpus.title').toLowerCase()}`, tone: 'blue', icon: '▥' },
      { label: 'Phrases', value: this.phrases.length, trend: this.i18n.translate('home.eyebrow'), tone: 'green', icon: '●' },
      { label: this.i18n.translate('home.approved'), value: this.approvedAudios.length, trend: this.i18n.translate('corpus.qualified'), tone: 'purple', icon: '✓' },
      { label: this.i18n.translate('home.rejected'), value: this.pendingAudios.length, trend: this.i18n.translate('adminData.pending'), tone: 'orange', icon: '☆' },
    ];
  }

  get recentAudios(): AudioRead[] {
    return [...this.pendingAudios, ...this.approvedAudios, ...this.rejectedAudios]
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, 5);
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.load();
    }
  }

  statusLabel(status: AudioRead['status']): string {
    if (status === 'approved') return this.i18n.translate('corpus.valid');
    if (status === 'rejected') return this.i18n.translate('home.rejected');
    return this.i18n.translate('adminData.pending');
  }

  statusClass(status: AudioRead['status']): string {
    if (status === 'approved') return 'ok';
    if (status === 'rejected') return 'review';
    return 'todo';
  }

  phraseText(audio: AudioRead): string {
    return this.phraseById.get(audio.phrase_id)?.texte || `Phrase #${audio.phrase_id}`;
  }

  audioUrl(audio: AudioRead): string {
    return audioFileUrl(audio.id);
  }

  private load(): void {
    this.loading = true;
    this.error = null;
    forkJoin({
      phrases: this.api.getPhrases(this.i18n.contentLanguage()),
      pending: this.api.listAudios('pending'),
      approved: this.api.listAudios('approved'),
      rejected: this.api.listAudios('rejected'),
    }).subscribe({
      next: ({ phrases, pending, approved, rejected }) => {
        this.phrases = phrases;
        this.phraseById = new Map(phrases.map((phrase) => [phrase.id, phrase]));
        this.pendingAudios = pending;
        this.approvedAudios = approved;
        this.rejectedAudios = rejected;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Chargement impossible.';
        this.loading = false;
      },
    });
  }
}
