import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService, AudioRead, Phrase } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { audioFileUrl } from '../../core/constants';
import { I18nService, type AppLanguage } from '../../core/i18n.service';
import { TranslatePipe } from '../../core/translate.pipe';
import { V2SessionActionComponent } from '../shared/v2-session-action.component';

interface ClassAudioRow {
  audio: AudioRead;
  phrase: Phrase | null;
}

interface ClassAudioGroup {
  name: string;
  rows: ClassAudioRow[];
}

interface PriorityValidation {
  label: string;
  tone: 'teacher' | 'admin' | 'neutral';
}

@Component({
  selector: 'app-v2-my-class',
  standalone: true,
  imports: [CommonModule, RouterLink, TranslatePipe, V2SessionActionComponent],
  templateUrl: './v2-my-class.component.html',
  styleUrls: ['./v2-my-class.component.scss'],
})
export class V2MyClassComponent implements OnInit {
  @ViewChild('classPlayer') private classPlayer?: ElementRef<HTMLAudioElement>;

  phrases: Phrase[] = [];
  fallbackPhrases: Phrase[] = [];
  audios: AudioRead[] = [];
  loading = true;
  error: string | null = null;
  activeAudioId: number | null = null;
  isPlayingAudio = false;
  playbackError: string | null = null;
  studentSort: 'theme' | 'status' | 'date' = 'date';
  studentSortDirection: 'asc' | 'desc' = 'desc';

  readonly waveformBars = [12, 20, 30, 16, 22, 14, 28, 36, 18, 12, 24, 16, 10, 20, 14, 8];

  constructor(
    readonly auth: AuthService,
    readonly i18n: I18nService,
    private readonly api: ApiService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  get classNames(): string[] {
    const user = this.auth.user();
    return this.parseClassNames([
      user?.school,
      user?.organization,
    ]);
  }

  get hasClassContext(): boolean {
    return this.classNames.length > 0;
  }

  get isTeacherContext(): boolean {
    const role = this.auth.user()?.role;
    return role === 'teacher' || role === 'admin';
  }

  get rows(): ClassAudioRow[] {
    const user = this.auth.user();
    const userEmail = user?.email?.toLowerCase() || '';
    if (!userEmail) return [];
    const allRows = this.toRows(this.audios);
    if (!this.isTeacherContext) {
      return allRows.filter(({ audio }) => audio.contributor_email?.toLowerCase() === userEmail);
    }
    if (!this.hasClassContext) return [];
    const classes = new Set(this.classNames.map((name) => this.canonicalClassValue(name)));
    const userLevel = this.canonicalSchoolLevel(user?.school_level);
    return allRows.filter(({ audio }) => {
      const audioSchool = this.canonicalClassValue(audio.contributor_school);
      const audioLevel = this.canonicalSchoolLevel(audio.contributor_school_level);
      const classMatch = !!audioSchool && classes.has(audioSchool);
      const levelMatch = !userLevel || !audioLevel || userLevel === audioLevel || this.isTeacherContext;
      const ownAudio = !!userEmail && audio.contributor_email?.toLowerCase() === userEmail;
      return ownAudio || (classMatch && levelMatch);
    });
  }

  get classLabel(): string {
    if (!this.auth.user()) return this.i18n.translate('v2.classNotConnected');
    if (!this.hasClassContext) return this.i18n.translate('v2.classNotMember');
    return this.classNames.join(', ');
  }

  get classGroups(): ClassAudioGroup[] {
    const groups = new Map<string, ClassAudioRow[]>();
    for (const row of this.rows) {
      const name = row.audio.contributor_school?.trim() || 'Classe non renseignée';
      const existing = groups.get(name) ?? [];
      existing.push(row);
      groups.set(name, existing);
    }
    return Array.from(groups, ([name, rows]) => ({ name, rows }));
  }

  get summary(): Array<{ label: string; value: number }> {
    const rows = this.rows;
    return [
      { label: 'Enregistrements', value: rows.length },
      { label: 'Validés', value: rows.filter((row) => row.audio.status === 'approved').length },
      { label: 'À valider', value: rows.filter((row) => row.audio.status === 'pending').length },
      { label: 'Rejetés', value: rows.filter((row) => row.audio.status === 'rejected').length },
    ];
  }

  get progressCompleted(): number {
    return new Set(this.rows.map((row) => row.audio.phrase_id).filter((id): id is number => Number.isInteger(id))).size;
  }

  get progressTotal(): number {
    const bretonPhrases = this.fallbackPhrases.filter((phrase) => !phrase.langue || phrase.langue === 'br');
    return new Set(bretonPhrases.map((phrase) => phrase.texte.trim().toLocaleLowerCase()).filter(Boolean)).size;
  }

  get progressPercent(): number {
    return this.progressTotal ? Math.min(100, Math.round((this.progressCompleted / this.progressTotal) * 100)) : 0;
  }

  sortStudentRows(column: 'theme' | 'status' | 'date'): void {
    if (this.studentSort === column) {
      this.studentSortDirection = this.studentSortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.studentSort = column;
    this.studentSortDirection = column === 'date' ? 'desc' : 'asc';
  }

  studentRows(rows: ClassAudioRow[]): ClassAudioRow[] {
    return [...rows].sort((a, b) => {
      let comparison = 0;
      if (this.studentSort === 'theme') comparison = this.themeLabel(a).localeCompare(this.themeLabel(b), 'fr');
      else if (this.studentSort === 'status') comparison = this.statusOrder(a.audio) - this.statusOrder(b.audio);
      else comparison = Date.parse(a.audio.created_at) - Date.parse(b.audio.created_at);
      return this.studentSortDirection === 'asc' ? comparison : -comparison;
    });
  }

  sortIndicator(column: 'theme' | 'status' | 'date'): string {
    if (this.studentSort !== column) return '△';
    return this.studentSortDirection === 'asc' ? '▲' : '▼';
  }

  setLanguage(value: string): void {
    if (value === 'fr' || value === 'br' || value === 'en' || value === 'cy') {
      this.i18n.setLanguage(value as AppLanguage);
      this.load();
    }
  }

  phraseText(row: ClassAudioRow): string {
    return row.phrase?.texte || 'Enregistrement sans texte associé';
  }

  themeLabel(row: ClassAudioRow): string {
    return row.phrase?.theme || row.audio.domain || 'Sans thème';
  }

  statusLabel(audio: AudioRead): string {
    if (audio.status === 'approved') return 'Validé';
    if (audio.status === 'rejected') return 'Rejeté';
    return 'En attente';
  }

  validationSummary(audio: AudioRead): string {
    const validations = audio.validations ?? [];
    const approved = validations.length
      ? validations.filter((validation) => validation.decision === 'approved').length
      : (audio.status === 'approved' ? 1 : 0);
    const rejected = validations.length
      ? validations.filter((validation) => validation.decision === 'rejected').length
      : (audio.status === 'rejected' ? 1 : 0);
    return `${approved} validation(s) · ${rejected} rejet(s)`;
  }

  teacherComment(audio: AudioRead): string | null {
    const user = this.auth.user();
    const isOwnAudio = !!user?.email && audio.contributor_email?.toLowerCase() === user.email.toLowerCase();
    if (!this.isTeacherContext && !isOwnAudio) return null;

    const validation = (audio.validations ?? [])
      .find((item) => item.comment && (item.validator_role === 'teacher' || item.validator_role === 'admin'));
    return validation?.comment || (audio.validator_role === 'teacher' || audio.validator_role === 'admin' ? audio.validation_comment || null : null);
  }

  priorityValidation(audio: AudioRead): PriorityValidation {
    const validations = [...(audio.validations ?? [])].sort((a, b) => this.validationWeight(b) - this.validationWeight(a));
    const priority = validations.find((validation) => {
      const role = (validation.validator_role || '').toLowerCase();
      return role === 'teacher' || role === 'admin';
    }) ?? validations[0];

    if (priority) {
      const role = priority.validator_role || 'validateur';
      const name = priority.validator || role;
      const decision = priority.decision === 'approved'
        ? 'validé'
        : priority.decision === 'commented'
          ? 'commenté'
          : 'rejeté';
      return {
        label: `${decision} par ${name}`,
        tone: role.toLowerCase() === 'admin' ? 'admin' : role.toLowerCase() === 'teacher' ? 'teacher' : 'neutral',
      };
    }

    if (audio.validated_by) {
      const role = audio.validator_role || 'validateur';
      return {
        label: `${this.statusLabel(audio).toLowerCase()} par ${audio.validated_by}`,
        tone: role.toLowerCase() === 'admin' ? 'admin' : role.toLowerCase() === 'teacher' ? 'teacher' : 'neutral',
      };
    }

    return { label: 'Aucun avis professeur pour le moment', tone: 'neutral' };
  }

  displayDate(value: string): string {
    const locale = this.i18n.language() === 'fr' ? 'fr-FR' : this.i18n.language() === 'br' ? 'br-FR' : this.i18n.language() === 'cy' ? 'cy-GB' : 'en-GB';
    return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
  }

  toggleAudio(row: ClassAudioRow): void {
    const player = this.classPlayer?.nativeElement;
    if (!player) return;

    this.playbackError = null;
    if (this.activeAudioId === row.audio.id && this.isPlayingAudio) {
      player.pause();
      this.isPlayingAudio = false;
      return;
    }

    this.activeAudioId = row.audio.id;
    player.src = audioFileUrl(row.audio.id);
    player.load();
    player.play()
      .then(() => {
        this.isPlayingAudio = true;
      })
      .catch(() => {
        this.isPlayingAudio = false;
        this.playbackError = 'Lecture impossible pour cet audio.';
      });
  }

  isRowPlaying(row: ClassAudioRow): boolean {
    return this.activeAudioId === row.audio.id && this.isPlayingAudio;
  }

  onPlaybackEnded(): void {
    this.activeAudioId = null;
    this.isPlayingAudio = false;
  }

  onPlaybackPaused(): void {
    this.isPlayingAudio = false;
  }

  onPlaybackError(): void {
    this.isPlayingAudio = false;
    this.playbackError = 'Lecture impossible pour cet audio.';
  }

  private load(): void {
    this.loading = true;
    this.error = null;
    forkJoin({
      phrases: this.api.getPhrases(this.i18n.contentLanguage()),
      fallbackPhrases: this.api.getPhrases(),
      approved: this.api.listAudios('approved'),
      pending: this.api.listAudios('pending'),
      rejected: this.api.listAudios('rejected'),
    }).subscribe({
      next: ({ phrases, fallbackPhrases, approved, pending, rejected }) => {
        this.phrases = phrases;
        this.fallbackPhrases = fallbackPhrases;
        this.audios = [...approved, ...pending, ...rejected];
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Chargement des enregistrements impossible.';
        this.loading = false;
      },
    });
  }

  private toRows(audios: AudioRead[]): ClassAudioRow[] {
    const phraseById = new Map([
      ...this.fallbackPhrases.map((phrase) => [phrase.id, phrase] as const),
      ...this.phrases.map((phrase) => [phrase.id, phrase] as const),
    ]);
    return audios
      .map((audio) => ({ audio, phrase: phraseById.get(audio.phrase_id) ?? null }))
      .sort((a, b) => b.audio.created_at.localeCompare(a.audio.created_at));
  }

  private parseClassNames(values: Array<string | null | undefined>): string[] {
    const names = values
      .flatMap((value) => (value || '').split(/[;,]/))
      .map((value) => value.trim())
      .filter(Boolean);
    return Array.from(new Set(names));
  }

  private canonicalClassValue(value?: string | null): string {
    return (value || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/_/g, '-')
      .replace(/\s+/g, '-');
  }

  private canonicalSchoolLevel(value?: string | null): string {
    return (value || '')
      .trim()
      .toLowerCase()
      .replace(/niveau\s*/g, 'niveau-')
      .replace(/\s+/g, '-');
  }

  private validationWeight(validation: NonNullable<AudioRead['validations']>[number]): number {
    const parsed = Number.parseFloat(validation.validation_weight || '0');
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private statusOrder(audio: AudioRead): number {
    if (audio.status === 'approved') return 0;
    if (audio.status === 'pending') return 1;
    return 2;
  }
}
